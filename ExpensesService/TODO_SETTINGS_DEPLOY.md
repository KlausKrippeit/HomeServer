# Prüfbericht: Deploy, offene Punkte und Sicherheit

**Projekt:** ExpensesService (Flask/Waitress, SQLite, serverseitige HTML-Oberfläche und GET-API)
**Prüfumfang:** Statische Sichtung des bereitgestellten Archivs. Es wurde kein Projektcode ausgeführt und keine Quelldatei geändert.
**Stand:** 3. November 2026. Prioritäten: **P0** sofort vor produktiver Freigabe, **P1** zeitnah/hohes Risiko, **P2** geplant, **P3** Verbesserung.

## Kurzfazit

Das Projekt ist eine kleine, selbst zu betreibende Flask-Anwendung mit plausiblen Basismaßnahmen (Passwort-Hashing, parametrisierte SQL-Abfragen, nutzerbezogene Ausgabenansichten und CSRF-Token für POST). Der dokumentierte sichere Einsatz ist ein privates Netz oder ein HTTPS-Reverse-Proxy, nicht die direkte öffentliche Exponierung. Vor dem produktiven Betrieb sind insbesondere der defekte E-Mail-Bericht (falscher Aufruf der Datenbankfunktion), die tatsächliche Schreibbarkeit von Bearer-Token-Sitzungen, sichere Cookie-/Proxy-Konfiguration, die systemd-Pfadabweichung und ein belastbarer Backup-/Restore-Prozess zu klären.

## 1. Deploy und Konfiguration

### P1 – systemd-Beispielpfade widersprechen der Betriebsanleitung ✅ behoben

- `systemd/expenses-service.service:7-10` setzt `User=pi`, `WorkingDirectory=/home/pi/scripts/ExpensesService`, lädt `/home/pi/scripts/ExpensesService/.env` und startet `.venv/bin/python`.
- `README.md:37` sagt dagegen `/home/pi/ExpensesService` und eine Umgebung namens `venv`; auch das Cron-Beispiel in `README.md:32` verwendet `/home/pi/ExpensesService/venv`.
- Folge: Wer die README-Kommandos unverändert befolgt, kann mit einem fehlenden Arbeitsverzeichnis, fehlender Environment-Datei oder nicht auffindbarem Python starten.
- **Empfehlung:** Einen kanonischen Installationspfad, venv-Namen und dedizierten Dienstbenutzer festlegen; README, systemd-Datei und Cron-Pfad darauf abstimmen. Vor Aktivierung `systemd-analyze verify` sowie `systemctl status`/Journal prüfen. Eigentümer und Rechte des Projektverzeichnisses, der `.env` und des Datenbankverzeichnisses explizit setzen.

**Lösung**
Pfad  /home/pi/scripts/ExpensesService/.venv angepasst. README angepasst.

### P1 – `.env.example` Kategorienformat ist nicht kompatibel mit dem Parser

- `.env.example:17-18` setzt `CATEGORIES=Food,Transport,Home,Health,Other`.
- `config.py:37-46` verarbeitet jedoch ausschließlich Einträge im Format `stichwort=Kategorie`; Einträge ohne `=` werden stillschweigend ignoriert. Das Beispiel konfiguriert somit keine solche Kategorienliste, obwohl der Kommentar sie als Kategorien beschreibt. `README.md:58` beschreibt dagegen die Zuordnungsform `stichwort=Kategorie`.
- **Empfehlung:** Klären, ob `CATEGORIES` eine Stichwort-Zuordnung oder eine Kategorienliste sein soll, und Beispiel/Kommentar/Dokumentation konsistent gestalten. Beim Start ungültige oder ignorierte Werte melden statt stillschweigend zu verwerfen.

### P1 – E-Mail-Bericht kann die Datenbankfunktion nicht korrekt aufrufen ✅ behoben

- `db.py:112-127` definiert `get_month(user_name, year=None, month=None)` – der erste Parameter ist zwingend ein Nutzername.
- `report.py:9-14` ruft `get_month(year, month)` auf. Damit wird das Jahr als Nutzername und der Monat als Jahr interpretiert; der Monat fällt auf den aktuellen Monat zurück. Das führt typischerweise zu einer leeren bzw. sachlich falschen Abfrage (Jahr im niedrigen Zahlenbereich) statt zum angeforderten Monatsbericht.
- `report.py:18-22` deutet einen Bericht mit Nutzername und Ausgaben mehrerer Benutzer an; eine globale Abfrage ist in `db.py` aber nicht vorgesehen. Sowohl der manuelle Versand (`web.py:161-176`) als auch `monthly-mail.py:7-12` verwenden denselben Reportpfad.
- **Empfehlung:** Vor Nutzung des Mailversands fachlich festlegen, ob ein Bericht je angemeldeter Person oder ein aggregierter Gesamtbericht gemeint ist. Schnittstelle und Datenzugriff explizit darauf ausrichten und mit Datensätzen von mindestens zwei Nutzern sowie historischem Monat testen. Bis dahin den Versand nicht als verlässlich ansehen.

**Lösung**
user_name an allen Funktionsaufrufen eingebaut, montly-mail mit parameter aufruf umgesetzt.

### P1 – Datenbankpfad, Backups und Wiederherstellung operationalisieren

- `config.py:52-53` verwendet standardmäßig `expenses.db` relativ zum Arbeitsverzeichnis. Abweichende systemd-`WorkingDirectory`-Pfade können unbemerkt eine zweite, leere Datenbank erzeugen.
- `db.py:17-27` legt Elternverzeichnisse automatisch an und erstellt die Tabelle, aber es gibt keine Schema-Migration (auch im `README.md:17` ausdrücklich erwähnt).
- **Empfehlung:** `DB_PATH` immer als absoluten Pfad in einem persistenten, nur für den Dienstbenutzer zugänglichen Verzeichnis konfigurieren. Backup-Routine mit SQLite-konsistentem Verfahren (z. B. SQLite Online Backup API bzw. `sqlite3 .backup`) einrichten, nicht nur eine laufende DB-Datei blind kopieren. Backups verschlüsselt/off-host aufbewahren, Aufbewahrung und Monitoring festlegen und Restore regelmäßig in einer isolierten Umgebung testen. Vor jedem Update DB sichern und Schemaänderungen als kontrollierte Migration ausführen.

### P2 – reproduzierbarer Release-/Abhängigkeitsprozess fehlt

- `requirements.txt:1-4` beschränkt Hauptpakete nur auf breite Versionsbereiche, keine exakten, geprüften Lock-Versionen bzw. Hashes. Es ist keine CI-/Test-/Deployment-Konfiguration im geprüften Archiv enthalten.
- **Empfehlung:** Python-Version und Abhängigkeiten reproduzierbar pinnen, Installation aus vertrauenswürdiger Quelle und regelmäßige Update-/Schwachstellenprüfung einführen. Release gegen Staging und Restore-Kopie testen. `Pillow` ist für `gen-icons.py` nötig; sofern das Skript nur beim Erzeugen der Symbole gebraucht wird, prüfen, ob es Laufzeitabhängigkeit bleiben muss.

### P2 – Monatsmail-Cron braucht Betriebsregeln

- `monthly-mail.py:7-12` versendet nur, wenn das Skript am letzten lokalen Kalendertag läuft. Ein verpasster Cron-Lauf wird nicht nachgeholt; erneute manuelle Ausführung am Monatsende kann doppelte E-Mails versenden. Fehler werden im Skript nicht abgefangen.
- **Empfehlung:** Zeitzone und Cron-Laufzeit explizit definieren, Ausgabe/Fehler überwachen und Idempotenz bzw. nachvollziehbare Versandmarkierung ergänzen. Empfänger und Berichtsinhalte wegen Finanzdaten eng begrenzen. SMTP mit gültigem STARTTLS-Zertifikat, Secret-Schutz und passender Berechtigung konfigurieren (`report.py:26-42`).

## 2. Bugs und offene TODOs

### P1 – API-Token sind nicht auf GET/API beschränkt

- `web.py:31-47` akzeptiert einen gültigen Bearer-Token global für jede Anfrage und setzt `g.auth_user`. `current_user()` verwendet dieses Konto (`web.py:49-51`); `login_required` schützt damit auch die HTML-Oberfläche (`web.py:75-84`, `web.py:116-176`).
- CSRF verhindert nicht zuverlässig, dass ein Bearer-Inhaber schreibende Aktionen ausführt: Über eine mit Bearer aufgerufene HTML-Seite kann die Sitzung ein CSRF-Token erhalten; nachfolgende POSTs mit Sitzungscookie und CSRF-Token gelangen zu Ausgabe hinzufügen, Löschen und Mailversand. Das steht im Widerspruch zur Aussage „schreibgeschützte GET-API“ in `README.md:83,119`.
- **Empfehlung:** Als **P1** Token-Berechtigungen tatsächlich auf die API-GET-Routen begrenzen und Bearer-Authentifizierung für HTML- und schreibende Routen ablehnen. Bis zur Behebung alle ausgegebenen Tokens als potenziell schreibberechtigt behandeln, nur minimale Rechte vergeben und bei Zweifel rotieren.

### P1 – Sitzungscookie hat kein Secure-Attribut

- `web.py:17-18` setzt `HttpOnly` und `SameSite=Lax`, aber nicht `SESSION_COOKIE_SECURE=True`. Bei direktem HTTP kann ein Session-Cookie daher unverschlüsselt übertragen werden; TLS-Terminierung am Proxy allein erzwingt dieses Browserattribut nicht.
- **Empfehlung:** Produktion ausschließlich über HTTPS betreiben, Secure-Cookie aktivieren und HTTP am Proxy auf HTTPS umleiten bzw. blockieren. HSTS erst nach verifizierter HTTPS-Konfiguration am Reverse-Proxy setzen. Proxy-Zugriff auf den Waitress-Port per Firewall auf Loopback/Proxy-Netz beschränken; keine nicht vertrauenswürdigen `Host`-/Forwarded-Header übernehmen.

### P1 – keine Login-Drosselung oder Kontosperrung erkennbar

- `web.py:93-106` prüft Zugangsdaten, aber im Projekt ist kein Rate-Limit, Backoff, Lockout oder Alarm für wiederholte Fehlversuche erkennbar. Passwort-Hashing ist vorhanden (`config.py:9-19`, `web.py:98-100`), verhindert jedoch keine Online-Brute-Force-Versuche.
- **Empfehlung:** Reverse-Proxy oder Anwendung mit nutzer- und IP-begrenzter Drosselung ergänzen; Fehlversuche datensparsam überwachen. Für alle Nutzer lange, einzigartige Kennwörter und einen sicheren Prozess zur Änderung/Rotation vorgeben.

### P2 – Logout per GET und CSRF-Verhalten prüfen

- `web.py:109-113` meldet per GET `/logout` ab; der CSRF-Schutz überspringt GET/HEAD/OPTIONS (`web.py:54-72`). Dadurch kann ein fremder Link eine Abmeldung auslösen (kein direkter Datenverlust, aber unerwarteter Zustandswechsel).
- **Empfehlung:** Logout als POST mit CSRF gestalten. CSRF-Fehler liefern derzeit Redirects statt eines klaren 403 (`web.py:68-72`); dies ist eher UX/Diagnostik als unmittelbare Umgehung.

### P2 – Geldwerte werden als Binär-Float gespeichert und summiert

- Eingaben werden zunächst als `Decimal` validiert, aber in `db.py:59` in `float` umgewandelt; SQLite speichert `amount REAL` (`db.py:23-26`). Summen erfolgen ebenfalls mit `float` (`web.py:130`, `report.py:16-17`, `web.py:195`). Das kann Rundungsabweichungen verursachen.
- **Empfehlung:** Für finanzielle Genauigkeit Beträge als ganzzahlige Cent oder dezimale Textdarstellung persistieren und Summen exakt berechnen. Schemaänderung mit Backup und Migration planen.

### P2 – keine automatisierten Tests bzw. Validierung im Archiv erkennbar

- Im Archiv ist kein Testverzeichnis/Testlauf sichtbar. Kritische Funktionen wie Betragseingabe, Nutzerisolation, Monatsgrenzen, CSRF, Token-Scope, E-Mail und DB-Migration sind damit nicht nachvollziehbar abgesichert.
- **Empfehlung:** Tests für Authentifizierung/Autorisierung und Mandantentrennung, ungültige Eingaben, Zeit-/Monatsgrenzen, SQL-Zugriffe, Mailfehler und SQLite-Restore ergänzen. Vor Deploy Syntax-/Unit-/Integrationstest und Smoke-Test von Login, CRUD und beiden API-Routen automatisieren.

### P2 – Kategorienmatching ist Teilstring und Reihenfolge-abhängig

- `db.py:31-37` nimmt das erste Schlüsselwort, das irgendwo in der Beschreibung als Teilstring vorkommt. Überlappende/kurze Stichwörter können unerwartet matchen; Reihenfolge ist die Einfügereihenfolge der Standard- und Umgebungswerte.
- **Empfehlung:** Kategorienregeln dokumentieren und mit repräsentativen Beschreibungen testen; längere bzw. spezifischere Treffer priorisieren oder Grenzen/Normalisierung festlegen. Unbekannte Zuordnung sichtbar machen.

### P3 – Service-Worker-Cache-Aufräumen und Offline-Erwartung

- `static/sw.js:1-20` cached nur statische Dateien, nicht die HTML-Seiten; das ist mit der Offline-Einschränkung in `README.md:50` konsistent. Alte Cache-Namen werden beim Aktivieren nicht gelöscht (`sw.js:13-15`).
- **Empfehlung:** Alte `expenses-static-*`-Caches beim Aktivieren entfernen und Cache-Version bei Asset-Änderungen bewusst erhöhen. Keine privaten API-/HTML-Antworten in Cache aufnehmen, sofern keine gesonderte Datenschutzprüfung erfolgt.

## 3. Sicherheit und weitere Betriebs-/Architekturpunkte

### Sicherheitsstärken, die erhalten werden sollten

- Passwortwerte werden beim Laden gehasht (`config.py:9-19`) und bei Login gegen Hash geprüft (`web.py:98-100`).
- SQLite-Zugriffe verwenden Platzhalterparameter (`db.py:66-73, 87-92, 122-128`); Nutzeransichten und API-Abfragen filtern nach Nutzer.
- Schreibende Formulare haben CSRF-Token (`web.py:54-72`; Formulare z. B. `templates/index.html:16-20,58-66`); Sessioncookie ist `HttpOnly` und `SameSite=Lax`.
- Standard-Bind-Adresse ist lokal (`config.py:53-54`, `.env.example:7-9`), und README warnt vor direkter Internetfreigabe (`README.md:52-54`).

### P1 – Secret- und Dateirechte vor Start absichern

- `SECRET_KEY` ist zwingend (`web.py:13-16`), aber Flask signiert Cookies clientseitig. Bei bekanntem oder wiederverwendetem Schlüssel können Sitzungen gefälscht werden. `.env.example` enthält absichtlich Platzhalter, die nicht produktiv bleiben dürfen.
- **Empfehlung:** Separaten kryptografisch zufälligen Schlüssel sowie individuelle Benutzerpasswörter und API-Token verwenden; `.env` nur für den Dienstbenutzer lesbar machen (typisch `0600`), nicht ins Repository/Backup unverschlüsselt einchecken. Schlüsselrotation invalidiert Sitzungen und ist geplant durchzuführen. Geheimnisse nicht in systemd-Unit, Shell-Historie oder Logs kopieren.

### P1 – Reverse-Proxy-/Netzgrenze ist nicht mitgeliefert

- Keine Proxy-Konfiguration, TLS-Zertifikate, Firewallregeln, Security-Header oder Proxy-Header-Trust-Konfiguration sind Teil des Archivs. `BIND_HOST` kann laut `.env.example` geändert werden.
- **Empfehlung:** Waitress nicht direkt ans Internet binden. Reverse-Proxy mit TLS, HTTP→HTTPS, Request-Limits, geeigneten Timeout-/Body-Limits, Zugriffsschutz/Netz-ACL und korrekter Weiterleitung einsetzen; Backend-Port nur dem Proxy zugänglich machen. Keine forwarded headers vertrauen, wenn der Proxy die Verbindung nicht zuverlässig überschreibt. HSTS, `X-Content-Type-Options`, `frame-ancestors`/CSP und Referrer-Policy am Proxy nach Kompatibilität konfigurieren.

### P2 – Eingabe-/Ressourcenlimits und HTTP-Schutz

- `web.py` setzt im geprüften Code keine explizite maximale Request-Größe; Beschreibungstexte und Anzahl Datensätze sind nicht sichtbar begrenzt. `db.py:40-59` beschränkt den Betrag, aber keine Textlänge; die monatliche Ansicht lädt alle passenden Einträge (`db.py:112-128`).
- **Empfehlung:** Request-Body und Beschreibungslänge begrenzen, paginieren bzw. für große Datenbestände passende Indizes (z. B. Nutzer/Datum) evaluieren. Backups, Datenträgerkapazität und SQLite-Dateigröße überwachen.

### P2 – Datenschutz und Mehrbenutzer-E-Mail

- Die Oberfläche/API sind nutzergefiltert, aber `report.py:18-22` nimmt an, dass Berichte Nutzernamen enthalten. Der geplante Berichtsempfänger bekommt gegebenenfalls personenbezogene Finanzdaten mehrerer Nutzer.
- **Empfehlung:** Datenminimierung, Zweck/Empfängerkreis, Aufbewahrung und Zugriff auf E-Mail-Postfach klären. Den Bericht nur nach fachlich bestätigtem Nutzerumfang versenden. Keine Finanzinhalte in Proxy-/App-Logs aufnehmen.

### P2 – Beobachtbarkeit und Wiederanlauf

- systemd setzt `Restart=on-failure` (`systemd/expenses-service.service:11`), aber keine dedizierte Health-Route, Alarmierung, Ressourcenlimits oder Hardening-Optionen sind erkennbar. `web.py:173-175` protokolliert Ausnahmen beim Mailversand.
- **Empfehlung:** Journald-Zugriff/Rotation, Prozess- und Datenträgerüberwachung, Alarm bei Neustart-/Mailfehlern sowie kontrollierte Healthchecks einrichten. systemd-Härtung (dedizierter unprivilegierter User, `NoNewPrivileges`, restriktive Schreibpfade und passende `Protect*`-Optionen) nach Prüfung des benötigten DB-/Dateipfads ergänzen.

## Empfohlene Reihenfolge vor produktivem Einsatz

1. **P1:** Bearer-Token auf read-only GET-API beschränken; Tokens ggf. rotieren.
2. **P1:** Berichtsdatenzugriff korrigieren und fachlich auf Einzel- oder Gesamtbericht festlegen; Versand mit realistischen Testdaten verifizieren.
3. **P1:** Einheitliche Installationspfade, Dienstkonto, venv und `.env`-Rechte festlegen; systemd/Cron dokumentationsgleich machen.
4. **P1:** HTTPS-/Proxy-/Firewall-Setup samt Secure-Cookie, Login-Drosselung und Secret-Rotation festlegen.
5. **P1:** Absoluten persistenten DB-Pfad, konsistente Backups und getesteten Restore einrichten; Migrationen für Updates planen.
6. **P2:** `CATEGORIES`-Beispiel korrigieren, Geldrepräsentation und Eingabegrenzen planen sowie Regressionstests/Monitoring ergänzen.

## Befundgrenzen

Dies ist eine statische Code- und Konfigurationssichtung des gelieferten Archivs, kein Penetrationstest und keine Laufzeitprüfung. Abhängigkeiten wurden nicht installiert, Projektcode wurde nicht ausgeführt, SMTP/Proxy/systemd wurden nicht gestartet. Aussagen über externe Infrastruktur oder tatsächliche Hostkonfiguration lassen sich aus dem Archiv allein nicht bestätigen.
