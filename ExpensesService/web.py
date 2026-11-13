import re
import secrets
from datetime import date, timedelta
from flask import jsonify, g, make_response
from functools import wraps

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from config import API_TOKENS, BIND_HOST, BIND_PORT, SECRET_KEY, USERS
from db import (
    add_expense,
    delete_latest,
    get_latest,
    get_month,
    get_months_with_entries,
    insert_expense,
    sum_month,
)
from money import Money
from report import build_report

app = Flask(__name__)
if not SECRET_KEY:
    raise RuntimeError('SECRET_KEY muss als Umgebungsvariable oder in .env gesetzt sein.')
app.secret_key = SECRET_KEY
app.permanent_session_lifetime = timedelta(days=30)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')


def get_csrf_token():
    """Liefert das CSRF-Token der Sitzung und erzeugt es bei Bedarf."""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_urlsafe(32)
    return session['_csrf_token']


app.jinja_env.globals['csrf_token'] = get_csrf_token


def expense_to_api(row):
    """Serialisiert eine Zeile: amount als Dezimalzahl (kompatibel) plus amount_cents."""
    return {
        'id': row['id'], 'expense_date': row['expense_date'],
        'user_name': row['user_name'],
        'amount': float(Money(row['amount_cents']).to_decimal()),
        'amount_cents': row['amount_cents'],
        'description': row['description'], 'category': row['category'],
    }


def expense_to_view(row):
    """Bereitet eine Zeile für das Template mit formatiertem Betrag auf."""
    view = dict(row)
    view['amount'] = str(Money(row['amount_cents']))
    return view


@app.before_request
def authenticate_bearer_token():
    """Setzt den Nutzer aus einem gültigen Authorization: Bearer-Header."""
    g.auth_user = None
    authorization = request.headers.get('Authorization', '')
    if not authorization.startswith('Bearer '):
        return None
    supplied = authorization[7:].strip()
    matched_user = None
    # Constant-time Vergleich mit jedem konfigurierten Token statt direktem Lookup.
    for configured_token, user_name in API_TOKENS.items():
        if secrets.compare_digest(supplied.encode('utf-8'), configured_token.encode('utf-8')):
            matched_user = user_name
    if matched_user is None:
        return jsonify(error='Invalid bearer token'), 401
    g.auth_user = matched_user


def current_user():
    """Liefert den Nutzer aus Bearer-Token oder Browser-Sitzung."""
    return getattr(g, 'auth_user', None) or session.get('user_name')


MONTH_VALUE = re.compile(r'\d{4}-\d{2}')


def parse_month(month_value):
    """Parst 'YYYY-MM' zu (Jahr, Monat); ungültige Werte werfen ValueError."""
    value = str(month_value or '').strip()
    if not MONTH_VALUE.fullmatch(value):
        raise ValueError('Invalid month; expected YYYY-MM')
    parsed = date.fromisoformat(f'{value}-01')
    return parsed.year, parsed.month


def api_error(message, status):
    """Liefert API-Fehler als JSON mit passendem HTTP-Statuscode."""
    return jsonify(error=message), status


def authenticate_user(user_name, password):
    """Prüft Zugangsdaten gegen die konfigurierten Nutzer (gemeinsam für HTML und API)."""
    if not user_name:
        return False
    password_hash = USERS.get(user_name)
    return bool(password_hash and check_password_hash(password_hash, password))


def json_login_required(view_function):
    """Schützt JSON-Endpunkte; ohne Anmeldung wird 401 als JSON geliefert."""
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if not current_user():
            return api_error('Anmeldung erforderlich.', 401)
        return view_function(*args, **kwargs)

    return wrapped_view


@app.before_request
def protect_against_csrf():
    """Lehnt schreibende Anfragen ohne gültiges CSRF-Token ab."""
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return None
    expected_token = session.get('_csrf_token', '')
    submitted_token = (
        request.form.get('csrf_token', '')
        or request.headers.get('X-CSRF-Token', '')
    )
    if expected_token and secrets.compare_digest(
        expected_token.encode('utf-8'), submitted_token.encode('utf-8')
    ):
        return None
    app.logger.warning('CSRF-Prüfung fehlgeschlagen für %s', request.path)
    if request.path.startswith('/api/'):
        message = (
            'Ungültiges oder fehlendes CSRF-Token. Rufe zuerst GET /api/v1/csrf-token ab '
            'und sende den Wert im Header X-CSRF-Token mit der Anfrage.'
        )
        return api_error(message, 403)
    message = 'Die Sitzung ist abgelaufen oder ungültig. Bitte erneut versuchen.'
    if 'user_name' in session:
        return redirect(url_for('index', message=message))
    return redirect(url_for('login', message=message))


def login_required(view_function):
    """Schützt eine Ansicht vor Zugriffen ohne Anmeldung."""
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if request.path.startswith('/api/') and not getattr(g, 'auth_user', None):
            return jsonify(error='Bearer token required'), 401
        if not current_user():
            return redirect(url_for('login'))
        return view_function(*args, **kwargs)
    return wrapped_view


@app.get('/login')
def login():
    """Zeigt das Anmeldeformular an."""
    return render_template('login.html', message=request.args.get('message', ''))


@app.post('/login')
def login_post():
    """Prüft die Zugangsdaten und startet eine Sitzung."""
    user_name = request.form.get('user_name', '').strip()
    password = request.form.get('password', '')
    if authenticate_user(user_name, password):
        session.clear()
        session.permanent = True
        session['user_name'] = user_name
        return redirect(url_for('index'))
    return redirect(
        url_for('login', message='Benutzername oder Passwort ist nicht korrekt.')
    )


@app.get('/logout')
def logout():
    """Beendet die aktuelle Sitzung."""
    session.clear()
    return redirect(url_for('login', message='Du hast dich abgemeldet.'))


@app.get('/')
@login_required
def index():
    """Zeigt Einträge für den gewählten Monat und dessen Summe."""
    month_value = request.args.get('month', '')
    today = date.today()
    try:
        selected_month = (
            date.fromisoformat(f'{month_value}-01')
            if month_value else today.replace(day=1)
        )
    except ValueError:
        selected_month = today.replace(day=1)
    expenses = get_month(current_user(), selected_month.year, selected_month.month)
    return render_template(
        'index.html', expenses=[expense_to_view(row) for row in expenses],
        selected_month=selected_month.strftime('%Y-%m'),
        total=sum_month(expenses),
        message=request.args.get('message', ''),
    )


@app.post('/add')
@login_required
def add_expense_view():
    """Speichert eine eingegebene Ausgabe."""
    try:
        add_expense(current_user(), request.form.get('expense', ''))
    except ValueError as error:
        return redirect(url_for('index', message=str(error)))
    return redirect(url_for('index', message='Ausgabe gespeichert.'))


@app.post('/delete-latest')
@login_required
def delete_latest_view():
    """Entfernt den jüngsten Eintrag des angemeldeten Nutzers."""
    removed = delete_latest(current_user())
    message = (
        'Letzter Eintrag gelöscht.' if removed
        else 'Es gibt keine Einträge zum Löschen.'
    )
    return redirect(url_for('index', message=message))


@app.post('/download-report')
@login_required
def download_report():
    """Liefert den Monatsbericht als Textdatei zum Herunterladen."""
    month_value = request.form.get('month', '')
    today = date.today()
    try:
        selected_month = (
            date.fromisoformat(f'{month_value}-01')
            if month_value else today
        )
        report_text = build_report(current_user(), selected_month.year, selected_month.month)
        filename = f'ausgabenbericht_{selected_month.year}_{selected_month.month:02d}.txt'
        response = make_response(report_text)
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        response.headers['Content-Type'] = 'text/plain; charset=utf-8'
        return response
    except Exception:
        app.logger.exception('Der Bericht konnte nicht erstellt werden')
        message = 'Der Bericht konnte nicht erstellt werden.'
        return redirect(url_for('index', month=month_value, message=message))


@app.get('/api/expenses')
@login_required
def api_expenses():
    """Liefert authentifizierte Ausgaben des Nutzers, optional nach Monat gefiltert."""
    month_value = request.args.get('month', '')
    today = date.today()
    try:
        year, month = (
            parse_month(month_value) if month_value.strip() else (today.year, today.month)
        )
    except ValueError as error:
        return api_error(str(error), 400)
    user_name = current_user()
    expenses = get_month(user_name, year, month)
    month_total = sum_month(expenses)
    return jsonify(
        user=user_name, month=f'{year:04d}-{month:02d}',
        total=float(month_total.to_decimal()), total_cents=month_total.cents,
        expenses=[expense_to_api(row) for row in expenses],
    )


@app.get('/api/expenses/latest')
@login_required
def api_latest_expenses():
    """Liefert die letzten 25 Einträge des authentifizierten Nutzers."""
    rows = [expense_to_api(row) for row in get_latest(limit=25, user_name=current_user())]
    return jsonify(user=current_user(), expenses=rows)


# --- JSON-API für eigene GUIs unter /api/v1 ---------------------------------
# Anmeldung wie im Browser über Sitzungs-Cookie (USERS). Schreibende Anfragen
# brauchen zusätzlich das CSRF-Token der Sitzung als Header X-CSRF-Token;
# Beträge gehen und kommen als ganzzahlige Cent.

@app.get('/api/v1/csrf-token')
def api_v1_csrf_token():
    """Liefert das CSRF-Token der aktuellen Sitzung und legt sie bei Bedarf an."""
    return jsonify(csrf_token=get_csrf_token())


@app.post('/api/v1/login')
def api_v1_login():
    """Prüft JSON-Zugangsdaten, startet eine Sitzung und liefert ein frisches CSRF-Token."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return api_error('Der Anfrageinhalt muss ein JSON-Objekt sein.', 400)
    user_name = str(payload.get('user_name', '')).strip()
    password = str(payload.get('password', ''))
    if authenticate_user(user_name, password):
        session.clear()
        session.permanent = True
        session['user_name'] = user_name
        return jsonify(user=user_name, csrf_token=get_csrf_token())
    return api_error('Benutzername oder Passwort ist nicht korrekt.', 401)


@app.post('/api/v1/logout')
def api_v1_logout():
    """Beendet die aktuelle Sitzung."""
    session.clear()
    return jsonify(message='Abgemeldet.')


@app.get('/api/v1/me')
@json_login_required
def api_v1_me():
    """Liefert den aktuell angemeldeten Nutzer."""
    return jsonify(user=current_user())


@app.get('/api/v1/months')
@json_login_required
def api_v1_months():
    """Listet die Monate mit Einträgen des Nutzers, neueste zuerst (YYYY-MM)."""
    user_name = current_user()
    return jsonify(user=user_name, months=get_months_with_entries(user_name))


@app.get('/api/v1/expenses')
@json_login_required
def api_v1_expenses():
    """Liefert Ausgaben und Summe in Cent eines Monats; Standard ist der aktuelle Monat."""
    month_value = request.args.get('month', '')
    today = date.today()
    try:
        year, month = (
            parse_month(month_value) if month_value.strip() else (today.year, today.month)
        )
    except ValueError as error:
        return api_error(str(error), 400)
    user_name = current_user()
    expenses = get_month(user_name, year, month)
    rows = [
        {
            'id': row['id'],
            'expense_date': row['expense_date'],
            'amount_cents': row['amount_cents'],
            'description': row['description'],
            'category': row['category'],
        }
        for row in expenses
    ]
    return jsonify(
        user=user_name,
        month=f'{year:04d}-{month:02d}',
        total_cents=sum_month(expenses).cents,
        expenses=rows,
    )


@app.post('/api/v1/expenses')
@json_login_required
def api_v1_add_expense():
    """Erfasst eine Ausgabe als JSON; Betrag als ganze Cent, optional mit Datum."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return api_error('Der Anfrageinhalt muss ein JSON-Objekt sein.', 400)
    amount_cents = payload.get('amount_cents')
    raw_description = payload.get('description')
    expense_date_value = payload.get('expense_date')
    if isinstance(amount_cents, bool) or not isinstance(amount_cents, int):
        return api_error('amount_cents muss eine ganze Zahl in Cent sein.', 400)
    if raw_description is None or not str(raw_description).strip():
        return api_error('Eine Beschreibung ist erforderlich.', 400)
    expense_date = None
    if expense_date_value is not None:
        date_text = str(expense_date_value)
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date_text):
            return api_error('expense_date muss das Format YYYY-MM-DD haben.', 400)
        try:
            expense_date = date.fromisoformat(date_text).isoformat()
        except ValueError:
            return api_error('expense_date ist kein gültiges Datum.', 400)
    user_name = current_user()
    try:
        new_id = insert_expense(
            user_name, amount_cents, str(raw_description), expense_date=expense_date
        )
    except ValueError as error:
        return api_error(str(error), 400)
    response = jsonify(id=new_id, user=user_name)
    response.status_code = 201
    return response


@app.get('/favicon.ico')
def favicon():
    """Liefert das Favicon für direkte Browser-Anfragen."""
    return app.send_static_file('favicon.ico')


@app.get('/sw.js')
def service_worker():
    """Liefert den Service Worker mit Gültigkeit für den Stamm-Pfad."""
    return app.send_static_file('sw.js'), 200, {
        'Content-Type': 'application/javascript', 'Service-Worker-Allowed': '/',
    }


if __name__ == '__main__':
    from waitress import serve

    serve(app, host=BIND_HOST, port=BIND_PORT)
