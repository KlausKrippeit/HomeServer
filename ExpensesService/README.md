# Ausgaben-Bot

Kleine Flask-Webanwendung zum Erfassen gemeinsamer Ausgaben und zum Versenden einer Monatsauswertung.

## Installation

```sh
cd /home/pi/ausgaben-bot
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
chmod 600 .env
```

In `.env` Benutzer, Passwoerter, `SECRET_KEY`, Datenbankpfad und SMTP-Zugangsdaten eintragen. Den Dienst installieren und starten:

```sh
sudo cp systemd/ausgaben-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ausgaben-web.service
```

Monatsbericht am Monatsende per Cron versenden (zum Beispiel in der Crontab von `pi`):

```cron
0 20 * * * cd /home/pi/ausgaben-bot && /home/pi/ausgaben-bot/venv/bin/python monatsmail.py
```

## iPhone

Die Anwendung in Safari oeffnen, auf Teilen tippen und „Zum Home-Bildschirm“ waehlen. Der Service Worker funktioniert nur ueber HTTPS (oder lokal auf `localhost`).

Den Anwendungsport nicht im Router ins Internet freigeben. `.env` enthaelt Zugangsdaten und darf niemals in Git eingecheckt werden.
