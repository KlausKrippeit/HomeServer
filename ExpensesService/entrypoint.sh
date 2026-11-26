#!/bin/sh
set -e

# Wenn keine .env vorhanden, von Beispiel kopieren.
# Der Benutzer muss .env mit eigenen Secrets ergänzen (SECRET_KEY, USERS, etc.).
if [ ! -f .env ]; then
    cp .env.example .env
fi

exec "$@"
