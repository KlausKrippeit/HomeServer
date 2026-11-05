# Feature Request: Trennung von GUI und Backend

Status: Entwurf | Betrifft: `ExpensesService`

## 1. Ziel

Die Geschäftslogik des ExpensesService soll unabhängig von Flask, HTML und SMTP
nutzbar und testbar sein. Die GUI wird zu einem dünnen Client, der ausschließlich
über definierte Schnittstellen (Service Layer bzw. JSON-API) auf das Backend zugreift.

## 2. Ist-Zustand

Stack: Flask + Jinja-Templates, SQLite, Waitress, Pillow (Icons), python-dotenv.

| Datei | Aktuelle Verantwortlichkeiten |
|---|---|
| `web.py` | Routen (HTML und `/api/*`), Session-Login, Bearer-Token-Auth, CSRF-Schutz, Monats-Parsing, Summenberechnung, Flash-Messages per Query-String, Aufruf von `db` und `report` |
| `db.py` | Verbindungsaufbau und Schema-Anlage, SQL-Zugriffe, Eingabeparsing (`parse_input`), Kategoriezuordnung (`find_category`), Betrag als `float` |
| `report.py` | Berichtstext-Erstellung, Formatierung (Dezimalkomma), SMTP-Versand, Zugriff auf `db.get_month` |
| `config.py` | Konfiguration als Modul-Konstanten (Import-Seiteneffekte) |
| `monthly-mail.py` | Cron-Einstieg, nutzt `report` direkt |

## 3. Probleme

1. **Vermischte Schichten:** `web.py` enthält Logik (Monatsauswahl, Summen), die in
   `report.py` und in der API dupliziert wird (Summe in `index`, `api_expenses` und `build_report`).
2. **Parsing in der Persistenzschicht:** `parse_input` und `find_category` gehören nicht in `db.py`.
3. **Geld als `float`:** Der Betrag wird als `REAL` gespeichert und mit `float` summiert, was Rundungsfehler ermöglicht.
4. **Globaler Zustand:** `app` und `config` werden beim Import erzeugt bzw. gelesen, daher sind Tests und Austausch von Abhängigkeiten schwierig.
5. **Harte Kopplung:** `report.send_mail` kennt SMTP und DB konkret, daher gibt es keine Fake-Implementierungen für Tests.
6. **Inkonsistente API:** Fehlerformate und Statuscodes sind uneinheitlich; ein Import mitten in der View (`from db import get_latest`).
7. **Datenbankverbindung:** Schema-Anlage bei jedem `get_connection()`.
8. **Fehlerbehandlung:** `except Exception` in `mail_report` verschluckt Ursachen.

## 4. Zielarchitektur

```
Presentation  (Flask-Blueprints: web, api)        -> kennt nur Services und DTOs
      |
Application   (Services: ExpenseService, ReportService, AuthService)
      |
Domain        (Expense, Money, Category, Month, Fehlerklassen)
      |
Infrastructure (SqliteExpenseRepository, SmtpMailer, Settings)
```

Regeln:
- Abhängigkeiten zeigen nur nach innen (Presentation -> Application -> Domain).
- Domain und Application importieren weder Flask noch sqlite3 noch smtplib.
- Die Presentation übersetzt HTTP in Service-Aufrufe und Domain-Fehler in HTTP-Antworten.

## 5. Patterns

- **Application Factory:** `create_app(settings, services)` statt globalem `app`.
- **Dependency Injection (manuell, Composition Root):** Verdrahtung in `bootstrap.py`.
- **Repository Pattern:** Interface `ExpenseRepository` (`add`, `list_month`, `list_latest`, `delete_latest`) mit `SqliteExpenseRepository`.
- **Adapter/Port:** `Mailer` (Protocol) mit `SmtpMailer`; Test-Double `FakeMailer`.
- **Service Layer:** `ExpenseService.add_from_text(user, text)`, `monthly_overview(user, month)`.
- **Value Object:** `Money` (Cent als `int` oder `Decimal`), `Month` (Jahr/Monat, Parsing von `YYYY-MM`).
- **DTOs:** `@dataclass(frozen=True)` für `ExpenseDto`, `MonthOverviewDto`; optional Pydantic für API-Schemas.
- **Strategy:** `CategoryClassifier` (Keyword-Map aus der Konfiguration, austauschbar).
- **Settings-Dataclass:** `Settings.from_env()` statt Modul-Konstanten.
- **Decorator/Middleware:** Auth (Session und Bearer) und CSRF als eigene Module.

## 6. API

Die GUI nutzt langfristig dieselbe versionierte API wie externe Clients:

| Methode | Pfad | Zweck |
|---|---|---|
| GET | `/api/v1/expenses?month=YYYY-MM` | Monatsübersicht inkl. Summe |
| GET | `/api/v1/expenses/latest?limit=25` | Letzte Einträge |
| POST | `/api/v1/expenses` | Ausgabe aus Freitext anlegen |
| DELETE | `/api/v1/expenses/latest` | Jüngsten Eintrag löschen |
| POST | `/api/v1/reports/monthly` | Monatsbericht per Mail senden |

Einheitliches Fehlerformat: `{"error": {"code": "...", "message": "..."}}`.
Die bestehenden `/api/expenses*`-Routen bleiben als Alias bis zur Migration der Clients erhalten.

## 7. Ziel-Ordnerstruktur

```
ExpensesService/
  app/
    __init__.py            # create_app
    bootstrap.py           # Composition Root
    settings.py
    domain/                # models.py, money.py, errors.py, classifier.py
    services/              # expense_service.py, report_service.py
    repositories/          # base.py, sqlite_repository.py
    adapters/              # mailer.py (Protocol + SmtpMailer)
    web/                   # Blueprint HTML: routes.py, auth.py, csrf.py
    api/                   # Blueprint JSON: routes.py, schemas.py
    templates/  static/
  scripts/monthly_mail.py  # nutzt ReportService
  tests/
  wsgi.py                  # Waitress-Einstieg
```

## 8. Migration in Etappen

Jede Etappe ist einzeln lauffähig und committbar; das Verhalten bleibt unverändert.

1. **Tests als Sicherheitsnetz:** Charakterisierungstests für `parse_input`, `find_category`, `get_month`, `build_report`.
2. **Settings:** `config.py` in eine `Settings`-Dataclass überführen.
3. **Domain extrahieren:** `parse_input`/`find_category` nach `domain`; `Month` und `Money` einführen.
4. **Repository:** SQL aus `db.py` in `SqliteExpenseRepository`; `db.py` delegiert vorübergehend.
5. **Services:** `ExpenseService` und `ReportService`; Summen und Monatslogik nur noch dort.
6. **Mailer-Adapter:** SMTP aus `report.py` in `SmtpMailer`.
7. **App Factory und Blueprints:** `web.py` aufteilen in `web` und `api`; Auth/CSRF auslagern.
8. **API v1 und Fehlerformat**, Alias für alte Routen.
9. **Geld-Migration:** `REAL` -> Cent (`INTEGER`) mit Backup und Migrationsskript.
10. **Aufräumen:** Alte Module entfernen, README und systemd-Unit anpassen.

## 9. Teststrategie

- **Unit:** Domain und Services mit `FakeRepository` und `FakeMailer` (pytest, ohne Flask und DB).
- **Integration:** `SqliteExpenseRepository` gegen temporäre SQLite-Datei (`tmp_path`).
- **API/Web:** Flask-Testclient mit `create_app(test_settings)`; Auth, CSRF, Fehlercodes.
- **Regression:** Golden-File-Test für den Berichtstext.
- Optional: CI über GitHub Actions (pytest, ruff, mypy).

## 10. Risiken

- **Datenmigration `float` -> Cent:** Backup vor der Migration, Rundungsprüfung, Rollback-Skript.
- **Bestehende Clients** (Bearer-Token, Shortcuts) nutzen die alten Pfade -> Alias beibehalten.
- **systemd/Deployment:** Einstiegspunkt ändert sich (`web.py` -> `wsgi.py`); Unit-Datei und README anpassen.
- **Umfang:** Etappenweises Vorgehen verhindert einen Big-Bang-Umbau.

## 11. Akzeptanzkriterien

- [ ] Kein Import von `flask`, `sqlite3` oder `smtplib` in `domain/` und `services/`.
- [ ] Summen- und Monatslogik existiert genau einmal.
- [ ] Services sind ohne Webserver und echte Datenbank testbar.
- [ ] HTML-GUI und API nutzen dieselben Services.
- [ ] Alle bisherigen Funktionen (Login, Erfassen, Löschen, Monatsbericht, API) verhalten sich unverändert.
- [ ] Testabdeckung der Domain und Services mindestens 80 %.

## 12. Nicht-Ziele

- Kein Wechsel auf ein SPA-Frontend und kein Framework-Wechsel in dieser Iteration.
- Kein Wechsel der Datenbank (SQLite bleibt).
