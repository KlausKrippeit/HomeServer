#!/usr/bin/env python3
"""
Sendet einen Messwert an einen FHEM-Server.
Aufruf: python3 send_to_fhem.py <wert> [<resource>]
"""
import re
import sys
import requests
import os

FHEM_URL      = os.getenv("FHEM_URL", "http://localhost:8083/fhem")
FHEM_USER     = os.getenv("FHEM_USER", "")
FHEM_PASS     = os.getenv("FHEM_PASS", "")
DEVICE_NAME   = os.getenv("FHEM_DEVICE_NAME", "HostDevice")

# Session wiederverwenden (Cookies wie beim curl cookie-jar)
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})

# HTTP-Auth, falls konfiguriert
if FHEM_USER and FHEM_PASS:
    session.auth = (FHEM_USER, FHEM_PASS)

def get_csrf_token() -> str:
    """Ruft die FHEM-Seite ab und extrahiert das CSRF-Token."""
    response = session.get(FHEM_URL, timeout=10)
    response.raise_for_status()

    match = re.search(r'name="fwcsrf" value="([^"]+)"', response.text)
    if not match:
        print("Fehler: Kein CSRF-Token gefunden.")
        sys.exit(1)

    return match.group(1)

def send_value(reading: str, value: str) -> None:
    """Sendet den Wert an die FHEM-API."""
    csrf_token = get_csrf_token()

    payload = {
        "fwcsrf": csrf_token,
        "cmd": f"set {DEVICE_NAME} {reading} {value}",
    }

    api_response = session.post(FHEM_URL, data=payload, timeout=10)
    api_response.raise_for_status()

def main():
    # Überprüfe, ob ein Parameter übergeben wurde
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <reading> <value>")
        sys.exit(1)

    send_value(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()
