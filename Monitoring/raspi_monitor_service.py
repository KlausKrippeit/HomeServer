#!/usr/bin/env python3
"""
Erstellt Monitor Daten eines Raspberry Pi.
Sendet einen Messwert an einen FHEM-Server.
"""
import re
import sys
import requests
import os
import psutil
import subprocess
import time

FHEM_URL      = os.getenv("FHEM_URL", "http://localhost:8083/fhem")
FHEM_USER     = os.getenv("FHEM_USER", "")
FHEM_PASS     = os.getenv("FHEM_PASS", "")
DEVICE_NAME   = os.getenv("FHEM_DEVICE_NAME", "HostDevice")
_csrf_token: str | None = None

# Session wiederverwenden (Cookies wie beim curl cookie-jar)
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})

# HTTP-Auth, falls konfiguriert
if FHEM_USER and FHEM_PASS:
    session.auth = (FHEM_USER, FHEM_PASS)

def get_csrf_token() -> str:
    global _csrf_token
    if _csrf_token is not None:
        return _csrf_token

    """Ruft die FHEM-Seite ab und extrahiert das CSRF-Token."""
    response = session.get(FHEM_URL, timeout=10)
    response.raise_for_status()

    match = re.search(r'name="fwcsrf" value="([^"]+)"', response.text)
    if not match:
        print("Fehler: Kein CSRF-Token gefunden.")
        sys.exit(1)

    _csrf_token = match.group(1)

    return match.group(1)

def send_value(reading: str, value: str) -> None:
    """Sendet den Wert an die FHEM-API."""

    if value is None:
        print(f"Reading {reading} übersprungen (Wert ist None).")
        return

    csrf_token = get_csrf_token()

    payload = {
        "fwcsrf": csrf_token,
        "cmd": f"set {DEVICE_NAME} {reading} {value}",
    }

    api_response = session.post(FHEM_URL, data=payload, timeout=10)
    api_response.raise_for_status()

# Monitor Daten
def get_cpu_temperature():
    """Gibt die CPU-Temperatur des Raspberry Pi 5 zurück (in °C, aber ohne Einheit)."""
    try:
        # Lese die Temperatur aus der Systemdatei
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = int(f.read().strip()) / 1000
        return temp
    except Exception as e:
        print(f"Fehler beim Lesen der CPU-Temperatur: {e}")
        return None

def get_cpu_speed():
    """Gibt die aktuelle CPU-Geschwindigkeit zurück (in MHz, ohne Einheit)."""
    try:
        # Nutze `psutil` für die CPU-Frequenz
        cpu_freq = psutil.cpu_freq()
        return cpu_freq.current
    except Exception as e:
        print(f"Fehler beim Lesen der CPU-Geschwindigkeit: {e}")
        return None

def check_ping_status(host="github.com"):
    """Überprüft den Ping-Status zu github.com (1 = erfolgreich, 0 = fehlgeschlagen)."""
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "2", host],
            capture_output=True,
            text=True
        )
        return 1 if result.returncode == 0 else 0
    except Exception as e:
        print(f"Fehler beim Ping zu {host}: {e}")
        return 0

def check_db_reachability():
    """Liest den Docker-Health-Status des DB-Containers aus.
    Rückgabe: 1 = healthy, 0 = unhealthy/starting/kein Status"""
    try:
        r = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Health.Status}}", "mariadb-fhem"],
            capture_output=True, text=True, timeout=5)
        status = r.stdout.strip()
        # return 1 if status == "healthy" else 0
        return status
    except Exception as e:
        print(f"Fehler beim Ermitteln des Health-Status: {e}")
        return 0

def get_cpu_usage_percent(interval=1):
    """
    Gibt die CPU-Auslastung in Prozent zurück (0–100).
    Hinweis: Der erste Aufruf von psutil.cpu_percent() ohne interval
    liefert 0.0 – daher hier mit Messintervall.
    """
    try:
        return psutil.cpu_percent(interval=interval)
    except Exception as e:
        print(f"Fehler beim Lesen der CPU-Auslastung: {e}")
        return None

def get_ram_available():
    """Tatsächlich verfügbarer RAM in MB (oder None)."""
    try:
        return round(psutil.virtual_memory().available / 1024**2, 0)
    except Exception as e:
        log.warning("Fehler beim Lesen des RAM: %s", e)
        return None

def main():
    """Hauptschleife: Abfragen der Ressourcen und Senden an das Shell-Skript."""
    INTERVAL = 10  # Sekunden

    while True:
        # Startzeit des Zyklus merken
        cycle_start = time.monotonic()
        # Ressourcen abfragen
        cpu_temp = get_cpu_temperature()
        cpu_speed = get_cpu_speed()
        db_reachable = check_db_reachability()
        ping_status = check_ping_status()
        cpu_usage = get_cpu_usage_percent()
        ram_available = get_ram_available()

        # Werte an das Shell-Skript senden
        send_value("cpu_temperature", cpu_temp)
        send_value("cpu_speed", cpu_speed)
        send_value("db_reachability", db_reachable)
        send_value("ping_status", ping_status)
        send_value("cpu_usage", cpu_usage)
        send_value("ram_available", ram_available)

        elapsed = time.monotonic() - cycle_start
        sleep_time = INTERVAL - elapsed

        if sleep_time > 0:
            time.sleep(sleep_time)

if __name__ == "__main__":
    main()
