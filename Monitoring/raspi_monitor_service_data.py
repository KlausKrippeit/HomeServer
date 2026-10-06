#!/usr/bin/env python3
import psutil
import subprocess
import time
import socket
import os
import sys

# Pfad zum Shell-Skript
SENDING_SCRIPT = "/home/pi/scripts/raspi_monitor.py"

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

def send_to_script(resource, value):
    """Sendet den Wert an das Shell-Skript `sendingFurther.sh`."""
    try:
        if value is not None:
            subprocess.run([sys.executable, SENDING_SCRIPT, resource, str(value)], check=True)
        else:
            print(f"Kein gültiger Wert für {resource} erhalten.")
    except subprocess.CalledProcessError as e:
        print(f"Fehler beim Ausführen von {SENDING_SCRIPT}: {e}")
    except Exception as e:
        print(f"Allgemeiner Fehler beim Senden von {resource}: {e}")

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

        # Werte an das Shell-Skript senden
        send_to_script("cpu_temperature", cpu_temp)
        send_to_script("cpu_speed", cpu_speed)
        send_to_script("db_reachability", db_reachable)
        send_to_script("ping_status", ping_status)
        send_to_script("cpu_usage", cpu_usage)

        elapsed = time.monotonic() - cycle_start
        sleep_time = INTERVAL - elapsed

        if sleep_time > 0:
            time.sleep(sleep_time)

if __name__ == "__main__":
    main()
