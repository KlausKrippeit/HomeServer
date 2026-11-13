# ExpensesService

Kleine, selbst betriebene Ausgabenliste mit Flask und SQLite. Die Oberfläche passt sich Mobiltelefonen an und kann auf dem iPhone als Web-App installiert werden.

## Installation und virtuelle Umgebung

1. Projekt in ein eigenes Verzeichnis entpacken und dorthin wechseln.
2. Eine virtuelle Umgebung anlegen und aktivieren:
   - Linux/macOS: `python3 -m venv venv` und `source venv/bin/activate`
   - Windows: `py -m venv venv` und `venv\Scripts\activate`
3. Abhängigkeiten installieren: `pip install -r requirements.txt` (Flask, python-dotenv, waitress und Pillow).
4. Konfiguration kopieren: `cp .env.example .env` (Windows: `copy .env.example .env`).
5. In `.env` mindestens `SECRET_KEY` und `USERS` ändern (siehe zusätzlich „Bearer-Token und API“). Nutzer werden als `name:kennwort` eingetragen; mehrere Nutzer werden mit Kommas getrennt. Außerdem können Kategorie-Stichwörter, Datenbankpfad, Bind-Adresse und E-Mail-Versand eingestellt werden.
6. Symbole erzeugen: `python gen-icons.py`.
7. Lokal starten: `python web.py`. Der Dienst läuft mit dem Produktionsserver waitress. Die Standardadresse ist `http://127.0.0.1:8080`; sie lässt sich mit `BIND_HOST` und `BIND_PORT` ändern.

Ausgabeneinträge können beispielsweise als `12,50 Rewe` oder `48,90 EUR Monatskarte` eingegeben werden. Beträge müssen größer als null sein und dürfen 10.000.000 nicht überschreiten. Die Kategorie wird anhand passender Stichwörter in der Beschreibung erkannt. Standardzuordnungen sind in `config.py` hinterlegt; unbekannte Stichwörter erhalten intern die Ersatzkategorie `Other`, die in der Oberfläche als „Sonstiges“ angezeigt wird. Die Datenbanktabelle wird beim Zugriff angelegt. Es gibt absichtlich keine Datenbankmigration; eine vorhandene Datenbank mit einem älteren Schema muss vor dem Start gesichert und entfernt oder manuell angepasst werden.

## Anmeldung und Bedienung

Alle Seiten außer der Anmeldung sind nur nach dem Login erreichbar. Die Zugangsdaten stammen aus `USERS`; die Kennwörter werden beim Start gehasht im Speicher gehalten. Eine Sitzung bleibt 30 Tage gültig, das Session-Cookie ist `HttpOnly` und `SameSite=Lax`. Alle schreibenden Anfragen (Anmelden, Ausgabe hinzufügen, Löschen, Bericht senden) werden mit einem CSRF-Token geschützt.

Jeder Nutzer sieht in der Übersicht nur seine eigenen Einträge. Mit „Meinen letzten Eintrag löschen“ wird der jüngste Eintrag des angemeldeten Nutzers entfernt; Einträge anderer Nutzer sind davon nicht betroffen.

## Monatsübersicht und E-Mail-Bericht

Die Monatsauswahl auf der Startseite filtert die angezeigten Einträge des angemeldeten Nutzers und zeigt deren Summe an. Die Schaltfläche zum Versenden erstellt den Bericht für den ausgewählten Monat. Dafür müssen `SMTP_HOST`, `MAIL_FROM` und `MAIL_TO` konfiguriert sein. Der Versand verwendet STARTTLS; `SMTP_USER` und `SMTP_PASS` sind optional.

Das Skript `monthly-mail.py` versendet den Bericht des laufenden Monats ausschließlich, wenn es am letzten Kalendertag des Monats gestartet wird. Beispiel für einen täglichen Cron-Aufruf (Pfade anpassen):

```cron
5 23 * * * /home/pi/scripts/ExpensesService/.venv/bin/python /home/pi/scripts/ExpensesService/monthly-mail.py
```

## systemd

Die Beispieldatei `systemd/expenses-service.service` erwartet das Projekt unter `/home/pi/scripts/ExpensesService` sowie eine virtuelle Umgebung im Unterordner `.venv`. Pfad und Benutzer `pi` müssen an das eigene System angepasst werden. Danach:

```sh
sudo cp systemd/expenses-service.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now expenses-service.service
sudo systemctl status expenses-service.service
```

Die systemd-Datei lädt `.env`; der Start über `python web.py` berücksichtigt `BIND_HOST` und `BIND_PORT`.

## Installation auf dem iPhone

Die Web-App muss über HTTPS erreichbar sein, damit iOS den Service Worker zuverlässig verwenden kann. In Safari die Seite öffnen, die Teilen-Taste wählen und „Zum Home-Bildschirm“ antippen. Das Manifest sowie `apple-touch-icon` und die weiteren PWA-Bilddateien werden vom Projekt bereitgestellt. Der Service Worker (`/sw.js`) legt nur statische Dateien unter `/static/` (Stylesheet, Manifest, Symbole) im Cache ab. Die Seiten selbst werden immer vom Server geladen, ein Offline-Betrieb ist daher nicht möglich.

## Sicherheit

**Nicht direkt ins Internet freigeben.** Der Dienst enthält keinen Schutz wie eine vollständige öffentliche Webanwendung. Betreibe ihn nur in einem vertrauenswürdigen privaten Netz oder hinter einem korrekt abgesicherten HTTPS-Reverse-Proxy. Verwende ein starkes, geheimes `SECRET_KEY`, sichere `.env` und die Datenbank und beschränke den Zugriff auf den Rechner und die E-Mail-Konfiguration.

## Konfiguration

Die Einstellungen werden mit `os.getenv` aus `.env` gelesen. `CATEGORIES` akzeptiert kommaseparierte Zuordnungen im Format `stichwort=Kategorie`, zum Beispiel `markt=Lebensmittel,apotheke=Drogerie`. Diese Einträge ergänzen die Standardzuordnungen oder überschreiben ein vorhandenes Stichwort, etwa `rewe=Einkauf`. Die Stichwörter werden ohne Beachtung der Groß-/Kleinschreibung gesucht. Unbekannte Stichwörter erhalten intern `Other` und werden als „Sonstiges“ angezeigt. Die Einstellungen umfassen `USERS`, `API_TOKENS`, `SECRET_KEY`, `DB_PATH`, `BIND_HOST`, `BIND_PORT`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `MAIL_FROM` und `MAIL_TO`.

Standardwerte, falls eine Variable fehlt:

| Variable | Standard |
| --- | --- |
| `USERS` | leer (dann ist keine Anmeldung und Tokenzuordnung möglich) |
| `API_TOKENS` | leer (GET-API bleibt nicht authentifiziert unzugänglich) |
| `SECRET_KEY` | erforderlich; Dienst startet ohne gesetzten Wert nicht |
| `DB_PATH` | `expenses.db` im Arbeitsverzeichnis |
| `BIND_HOST` | `127.0.0.1` |
| `BIND_PORT` | `8080` |
| `SMTP_PORT` | `587` |
| `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS`, `MAIL_FROM`, `MAIL_TO` | leer |

## Hinweis zu Dateinamen

`monthly-mail.py` und `gen-icons.py` enthalten Bindestriche. Sie werden als Skripte gestartet, nicht als Python-Module importiert. Die importierten Module haben Dateinamen ohne Bindestriche: `config.py`, `db.py`, `report.py` und `web.py`.

## Theme wechseln

Oben rechts schaltet **DARK MODE** zwischen dem bestehenden hellen Design und dem dunklen Comic-inspirierten Design um. Die Auswahl wird lokal im Browser gespeichert. Es werden keine Comic-Sans-Schriften verwendet.

## Bearer-Token und API

Die Browser-GUI bleibt mit dem konfigurierten `USERS`-Benutzername/Kennwort und einer sicheren Sitzung geschützt. Zusätzlich akzeptiert sie für geschützte Ansichten `Authorization: Bearer <token>`. Externe Apps können dieselbe Token-Authentifizierung für schreibgeschützte GET-API-Aufrufe verwenden.

1. `.env` aus `.env.example` erstellen und `SECRET_KEY` durch einen eigenen, zufälligen Wert ersetzen:
   ```sh
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
2. Ein starkes, separates API-Token generieren:
   ```sh
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
3. In der nur für den Dienstbenutzer lesbaren `.env` konfigurieren. `API_TOKENS` ordnet Token den vorhandenen `USERS` zu. Beispiel (Werte ersetzen, nicht veröffentlichen):
   ```dotenv
   USERS=Anna:<starkes-login-passwort>
   SECRET_KEY=<zufälliger-secret-key>
   API_TOKENS=Anna:<zufälliges-bearer-token>
   ```
   Mehrere Zuweisungen sind kommasepariert: `API_TOKENS=Anna:<token-a>,Ben:<token-b>`. Ein Token für einen nicht in `USERS` definierten Nutzernamen wird ignoriert. Token und `.env` niemals in Versionsverwaltung oder Logs ablegen. Der Server startet nicht, wenn `SECRET_KEY` fehlt.
4. Start wie oben: `python web.py` (nach Installation der Abhängigkeiten und Aktivierung der virtuellen Umgebung). Lokal erreichbar unter `http://127.0.0.1:8080`; für externe Apps im Netz `BIND_HOST` passend setzen und ausschließlich über HTTPS bzw. einen abgesicherten Reverse-Proxy übertragen.

### GET-Endpunkte

Alle API-Antworten sind JSON. Fehlender oder ungültiger Bearer-Token ergibt an den API-Endpunkten HTTP `401`; ein falsch formatiertes `month` ergibt HTTP `400`.

| Methode und Pfad | Zweck |
| --- | --- |
| `GET /api/expenses` | Einträge und Summe des aktuellen Monats für den Token-Nutzer. Optional `?month=YYYY-MM`. |
| `GET /api/expenses/latest` | Bis zu 25 jüngste Einträge des Token-Nutzers. |

Beispielaufrufe (Token aus sicherer Konfiguration einsetzen):

```sh
curl -H "Authorization: Bearer $API_TOKEN" http://127.0.0.1:8080/api/expenses
curl -H "Authorization: Bearer $API_TOKEN" 'http://127.0.0.1:8080/api/expenses?month=2026-10'
curl -H "Authorization: Bearer $API_TOKEN" http://127.0.0.1:8080/api/expenses/latest
```

Die erste Route liefert `{user, month, total, expenses}`; die letzte `{user, expenses}`. Beide scopen Daten ausschließlich auf den Nutzer des Tokens. Die API bietet bewusst nur GET-Lesezugriff, keine Token-Ausgabe, Token-Rotation oder Schreiboperationen. Browser-Formulare verwenden weiterhin Sitzungs-Cookies und CSRF-Schutz.

## JSON-API für eigene GUIs (/api/v1)

Die Endpunkte unter `/api/v1` sind für selbst gebaute GUIs gedacht, die dieselbe Origin wie der Server verwenden (GUI und API hinter derselben Adresse). Sie nutzen exakt dieselbe Anmeldung (`USERS`), dieselbe Datenbank und dieselbe Betragsverarbeitung wie die Weboberfläche. Beträge kommen und gehen als **ganzzahlige Cent**; Fehler antworten mit JSON und passendem HTTP-Statuscode.

### Anmeldung und CSRF-Schutz

Die GUI meldet sich über `POST /api/v1/login` an; das Session-Cookie (`HttpOnly`, `SameSite=Lax`) bleibt für alle weiteren Anfragen bestehen. Wie die HTML-Oberfläche sind **alle schreibenden API-Anfragen (Anmelden, Abmelden, Ausgabe erfassen) CSRF-geschützt**:

1. Vor der ersten Anfrage `GET /api/v1/csrf-token` aufrufen — das legt die Sitzung an und liefert den Token als JSON.
2. Den Token bei jeder schreibenden Anfrage im Header `X-CSRF-Token` mitsenden. Das Session-Cookie wird automatisch mitgesendet, weil GUI und API dieselbe Origin haben; ein Cross-Site-Angriff kann den Header nicht setzen.
3. Nach einer erfolgreichen Anmeldung rotiert der Server die Sitzung (Schutz vor Session-Fixierung) und liefert in der Antwort ein **frisches** `csrf_token`. Dieses gilt ab sofort für alle weiteren schreibenden Anfragen — das alte Token ist danach ungültig.

Eine schreibende Anfrage ohne gültiges Token erhält HTTP `403` mit JSON-Fehler; Lese-Endpunkte ohne Anmeldung antworten mit HTTP `401`; ungültige Beträge, Beschreibungen oder Monatswerte liefern HTTP `400` als JSON.

### Endpunkte

| Methode und Pfad | Zweck |
| --- | --- |
| `GET /api/v1/csrf-token` | CSRF-Token der Sitzung holen (legt die Sitzung an). Antwort: `{csrf_token}`. |
| `POST /api/v1/login` | Anmelden mit `{user_name, password}`. Antwort: `{user, csrf_token}`. Falsche Zugangsdaten: `401`. |
| `POST /api/v1/logout` | Sitzung beenden. Antwort: `{message}`. |
| `GET /api/v1/me` | Aktuell angemeldeten Nutzer abfragen. Antwort: `{user}`. Ohne Anmeldung: `401`. |
| `GET /api/v1/months` | Monate des Nutzers mit Einträgen, neueste zuerst (`YYYY-MM`). Antwort: `{user, months}`. |
| `GET /api/v1/expenses?month=YYYY-MM` | Ausgaben und Summe eines Monats; ohne `month` der aktuelle Monat. Antwort: `{user, month, total_cents, expenses}`. Ungültiger Monat: `400`. |
| `POST /api/v1/expenses` | Ausgabe erfassen mit `{amount_cents, description}` plus optional `expense_date` (`YYYY-MM-DD`). Erfolg: `201` mit `{id, user}`. Ungültige Werte: `400`. |

Die Kategorie wird wie im Formular anhand der Beschreibung erkannt; unbekannte Stichwörter landen in `Other` (in der Oberfläche „Sonstiges“). Die bisherigen Bearer-Token-Endpunkte `/api/expenses` und `/api/expenses/latest` bleiben unverändert erhalten.

### JSON-Antworten

`GET /api/v1/expenses?month=2026-11`:

```json
{
  "user": "Anna",
  "month": "2026-11",
  "total_cents": 1050,
  "expenses": [
    {
      "id": 2,
      "expense_date": "2026-11-13",
      "amount_cents": 560,
      "description": "Kaffee",
      "category": "Essen gehen"
    },
    {
      "id": 1,
      "expense_date": "2026-11-13",
      "amount_cents": 490,
      "description": "Rewe",
      "category": "Lebensmittel"
    }
  ]
}
```

`POST /api/v1/login` (erfolg) bzw. `GET /api/v1/me`, `GET /api/v1/months`, `POST /api/v1/expenses` (erfolg, HTTP `201`) und ein typischer Fehler:

```json
{ "user": "Anna", "csrf_token": "<frisches-token-nach-login>" }
```

```json
{ "user": "Anna" }
```

```json
{ "user": "Anna", "months": ["2026-11"] }
```

```json
{ "id": 3, "user": "Anna" }
```

```json
{ "error": "Invalid month; expected YYYY-MM" }
```

### curl-Ablauf: Anmeldung → Ausgabe erfassen → Monatsübersicht

Kopier- und ausführungsfähig (Pfad `BASE` und Zugangsdaten anpassen):

```sh
BASE=http://127.0.0.1:8080
JAR=cookies.txt; rm -f "$JAR"
JSON='import json,sys; print(json.load(sys.stdin)["csrf_token"])'

# 1) CSRF-Token holen (legt die Sitzungs-Cookie an)
CSRF=$(curl -s -b "$JAR" -c "$JAR" "$BASE/api/v1/csrf-token" | python3 -c "$JSON")

# 2) Anmelden — die Antwort enthält ein frisches csrf_token, das danach verwendet wird
CSRF=$(curl -s -b "$JAR" -c "$JAR" -X POST "$BASE/api/v1/login" \
  -H 'Content-Type: application/json' -H "X-CSRF-Token: $CSRF" \
  -d '{"user_name":"Anna","password":"<passwort>"}' | python3 -c "$JSON")

# 3) Ausgabe erfassen (Betrag in Cent)
curl -s -b "$JAR" -X POST "$BASE/api/v1/expenses" \
  -H 'Content-Type: application/json' -H "X-CSRF-Token: $CSRF" \
  -d '{"amount_cents":490,"description":"Rewe"}'; echo

# 4) Verfügbare Monate und Monatsübersicht (Summe in Cent)
curl -s -b "$JAR" "$BASE/api/v1/months"; echo
curl -s -b "$JAR" "$BASE/api/v1/expenses?month=2026-11"; echo

# 5) Abmelden
curl -s -b "$JAR" -X POST "$BASE/api/v1/logout" -H "X-CSRF-Token: $CSRF"; echo
```
