from datetime import date, timedelta
from functools import wraps

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from config import BIND_HOST, BIND_PORT, SECRET_KEY, USERS
from db import add_expense, delete_latest, get_month
from report import send_mail

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.permanent_session_lifetime = timedelta(days=30)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')


def login_required(view_function):
    """Schützt eine Ansicht vor Zugriffen ohne Anmeldung."""
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if 'user_name' not in session:
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
    password_hash = USERS.get(user_name)
    if password_hash and check_password_hash(password_hash, password):
        session.clear()
        session.permanent = True
        session['user_name'] = user_name
        return redirect(url_for('index'))
    return redirect(
        url_for('login', message='The username or password was not recognized.')
    )


@app.get('/logout')
def logout():
    """Beendet die aktuelle Sitzung."""
    session.clear()
    return redirect(url_for('login', message='You have signed out.'))


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
    expenses = get_month(session['user_name'], selected_month.year, selected_month.month)
    total = sum(float(expense['amount']) for expense in expenses)
    return render_template(
        'index.html', expenses=expenses,
        selected_month=selected_month.strftime('%Y-%m'), total=total,
        message=request.args.get('message', ''),
    )


@app.post('/add')
@login_required
def add_expense_view():
    """Speichert eine eingegebene Ausgabe."""
    try:
        add_expense(session['user_name'], request.form.get('expense', ''))
    except ValueError as error:
        return redirect(url_for('index', message=str(error)))
    return redirect(url_for('index', message='Expense saved.'))


@app.post('/delete-latest')
@login_required
def delete_latest_view():
    """Entfernt den jüngsten Eintrag des angemeldeten Nutzers."""
    removed = delete_latest(session['user_name'])
    message = (
        'Latest expense deleted.' if removed
        else 'There are no expenses to delete.'
    )
    return redirect(url_for('index', message=message))


@app.post('/mail-report')
@login_required
def mail_report():
    """Versendet den Bericht des aktuell angezeigten Monats."""
    month_value = request.form.get('month', '')
    try:
        selected_month = (
            date.fromisoformat(f'{month_value}-01')
            if month_value else date.today()
        )
        send_mail(selected_month.year, selected_month.month)
        message = 'Monthly report sent.'
    except Exception:
        app.logger.exception('Unable to send the expense report')
        message = 'The report could not be sent. Check the mail configuration.'
    return redirect(url_for('index', month=month_value, message=message))


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
