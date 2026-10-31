# ExpensesService

Kleine, selbst betriebene Ausgabenliste mit Flask und SQLite. Die Oberfläche passt sich Mobiltelefonen an und kann auf dem iPhone als Web-App installiert werden.

## Installation und virtuelle Umgebung

1. Projekt in ein eigenes Verzeichnis entpacken und dorthin wechseln.
2. Eine virtuelle Umgebung anlegen und aktivieren:
   - Linux/macOS: `python3 -m venv venv` und `source venv/bin/activate`
   - Windows: `py -m venv venv` und `venv\Scripts\activate`
3. Abhängigkeiten installieren: `pip install -r requirements.txt`.
4. Konfiguration kopieren: `cp .env.example .env` (Windows: `copy .env.example .env`).
5. In `.env` mindestens `SECRET_KEY` und `USERS` ändern. Nutzer werden als `name:kennwort` eingetragen; mehrere Nutzer werden mit Kommas getrennt. Außerdem können Kategorie-Stichwörter, Datenbankpfad, Bind-Adresse und E-Mail-Versand eingestellt werden.
6. Symbole erzeugen: `python gen-icons.py`.
7. Lokal starten: `python web.py`. Die Standardadresse ist `http://127.0.0.1:8080`.

Ausgabeneinträge können beispielsweise als `12,50 Rewe` oder `EUR 8.90 Bus pass` eingegeben werden. Beträge müssen positiv sein. Die Kategorie wird anhand passender Stichwörter in der Beschreibung erkannt. Standardzuordnungen sind in `config.py` hinterlegt; unbekannte Stichwörter erhalten die Ersatzkategorie `Other`. Die Datenbanktabelle wird beim Zugriff angelegt. Es gibt absichtlich keine Datenbankmigration; eine vorhandene Datenbank mit einem älteren Schema muss vor dem Start gesichert und entfernt oder manuell angepasst werden.

## Monatsübersicht und E-Mail-Bericht

Die Monatsauswahl auf der Startseite filtert die angezeigten Einträge. Die Schaltfläche zum Versenden erstellt den Bericht für den ausgewählten Monat. Dafür müssen `SMTP_HOST`, `MAIL_FROM` und `MAIL_TO` konfiguriert sein. Der Versand verwendet STARTTLS; `SMTP_USER` und `SMTP_PASS` sind optional.

Das Skript `monthly-mail.py` versendet den Bericht des laufenden Monats ausschließlich, wenn es am letzten Kalendertag des Monats gestartet wird. Beispiel für einen täglichen Cron-Aufruf (Pfade anpassen):

```cron
5 23 * * * /home/pi/ExpensesService/venv/bin/python /home/pi/ExpensesService/monthly-mail.py
```

## systemd

Die Beispieldatei `systemd/expenses-service.service` erwartet das Projekt unter `/home/pi/ExpensesService` sowie eine virtuelle Umgebung im Unterordner `venv`. Pfad und Benutzer `pi` müssen an das eigene System angepasst werden. Danach:

```sh
sudo cp systemd/expenses-service.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now expenses-service.service
sudo systemctl status expenses-service.service
```

Die systemd-Datei lädt `.env`; der Start über `python web.py` berücksichtigt `BIND_HOST` und `BIND_PORT`.

## Installation auf dem iPhone

Die Web-App muss über HTTPS erreichbar sein, damit iOS den Service Worker zuverlässig verwenden kann. In Safari die Seite öffnen, die Teilen-Taste wählen und „Zum Home-Bildschirm“ antippen. Das Manifest sowie `apple-touch-icon` und die weiteren PWA-Bilddateien werden vom Projekt bereitgestellt.

## Sicherheit

**Nicht direkt ins Internet freigeben.** Der Dienst enthält keinen Schutz wie eine vollständige öffentliche Webanwendung. Betreibe ihn nur in einem vertrauenswürdigen privaten Netz oder hinter einem korrekt abgesicherten HTTPS-Reverse-Proxy. Verwende ein starkes, geheimes `SECRET_KEY`, sichere `.env` und die Datenbank und beschränke den Zugriff auf den Rechner und die E-Mail-Konfiguration.

## Konfiguration

Die Einstellungen werden mit `os.getenv` aus `.env` gelesen. `CATEGORIES` akzeptiert kommaseparierte Zuordnungen im Format `stichwort=Kategorie`, zum Beispiel `markt=Lebensmittel,apotheke=Drogerie`. Diese Einträge ergänzen die Standardzuordnungen oder überschreiben ein vorhandenes Stichwort, etwa `rewe=Einkauf`. Die Stichwörter werden ohne Beachtung der Groß-/Kleinschreibung gesucht. Unbekannte Stichwörter erhalten `Other`. Die übrigen Einstellungen sind `USERS`, `SECRET_KEY`, `DB_PATH`, `BIND_HOST`, `BIND_PORT`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `MAIL_FROM` und `MAIL_TO`.

## Hinweis zu Dateinamen

`monthly-mail.py` und `gen-icons.py` enthalten Bindestriche. Sie werden als Skripte gestartet, nicht als Python-Module importiert. Die importierten Module haben Dateinamen ohne Bindestriche: `config.py`, `db.py`, `report.py` und `web.py`.
