"""Tests für die JSON-API unter /api/v1, die HTML-Oberfläche und das Bearer-Verhalten.

Alle Tests verwenden eine temporäre Datenbank und bekannte Testnutzer; vorhandene
Datenbanken bleiben unangetastet.
"""
import os
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# web.py verweigert ohne SECRET_KEY den Import; für die Tests ist ein fester Wert ausreichend.
os.environ.setdefault('SECRET_KEY', 'test-secret-key-fuer-api-tests')

import pytest  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

import db as db_module  # noqa: E402
import web  # noqa: E402


ANNAS_PASSWORT = 'anna-passwort'
BENS_PASSWORT = 'ben-passwort'


@pytest.fixture()
def clients(tmp_path, monkeypatch):
    """Liefert zwei Test-Clients (Anna, Ben) mit gemeinsamer temporärer Datenbank."""
    users = {
        'Anna': generate_password_hash(ANNAS_PASSWORT),
        'Ben': generate_password_hash(BENS_PASSWORT),
    }
    monkeypatch.setattr(web, 'USERS', users)
    monkeypatch.setattr(db_module, 'DB_PATH', str(tmp_path / 'test-expenses.db'))
    web.app.config.update(TESTING=True)
    return {'anna': web.app.test_client(), 'ben': web.app.test_client()}


def current_month():
    today = date.today()
    return f'{today.year:04d}-{today.month:02d}'


def fetch_csrf(client):
    response = client.get('/api/v1/csrf-token')
    assert response.status_code == 200
    body = response.get_json()
    assert body['csrf_token']
    return body['csrf_token']


def login_api(client, user_name='Anna', password=ANNAS_PASSWORT):
    token = fetch_csrf(client)
    response = client.post(
        '/api/v1/login',
        json={'user_name': user_name, 'password': password},
        headers={'X-CSRF-Token': token},
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()['csrf_token']


def add_api(client, csrf_token, payload):
    return client.post(
        '/api/v1/expenses', json=payload, headers={'X-CSRF-Token': csrf_token}
    )


def test_login_me_logout_flow(clients):
    anna = clients['anna']

    # Vor der Anmeldung: geschützte Endpunkte antworten mit JSON-401.
    response = anna.get('/api/v1/me')
    assert response.status_code == 401
    assert 'error' in response.get_json()
    assert anna.get('/api/v1/expenses').status_code == 401

    # Anmeldung über die API liefert Nutzer und frisches CSRF-Token.
    csrf_token = login_api(anna)
    me = anna.get('/api/v1/me')
    assert me.status_code == 200
    assert me.get_json() == {'user': 'Anna'}

    # Abmeldung beendet die Sitzung; danach ist /me wieder unzugänglich.
    response = anna.post('/api/v1/logout', headers={'X-CSRF-Token': csrf_token})
    assert response.status_code == 200
    assert anna.get('/api/v1/me').status_code == 401


def test_login_rejects_wrong_credentials_and_bad_json(clients):
    anna = clients['anna']

    token = fetch_csrf(anna)
    response = anna.post(
        '/api/v1/login',
        json={'user_name': 'Anna', 'password': 'falsch'},
        headers={'X-CSRF-Token': token},
    )
    assert response.status_code == 401
    assert 'error' in response.get_json()

    response = anna.post(
        '/api/v1/login', data='kein-json', headers={'X-CSRF-Token': token}
    )
    assert response.status_code == 400


def test_writes_require_csrf_token(clients):
    anna = clients['anna']

    # Ohne vorher abgerufenen Token wird die Schreib-Anfrage als JSON-403 abgelehnt.
    response = anna.post(
        '/api/v1/login', json={'user_name': 'Anna', 'password': ANNAS_PASSWORT}
    )
    assert response.status_code == 403
    assert 'CSRF' in response.get_json()['error']

    # Auch mit gültiger Sitzung, aber falschem Token: 403.
    csrf_token = login_api(anna)
    response = add_api(anna, 'falsches-token', {'amount_cents': 100, 'description': 'X'})
    assert response.status_code == 403


def test_add_expense_appears_in_month_summary_and_months_list(clients):
    anna = clients['anna']
    csrf_token = login_api(anna)

    response = add_api(anna, csrf_token, {'amount_cents': 490, 'description': 'Rewe'})
    assert response.status_code == 201
    created_id = response.get_json()['id']

    response = add_api(anna, csrf_token, {'amount_cents': 560, 'description': 'Kaffee'})
    assert response.status_code == 201

    # Monatsübersicht: beide Einträge plus Summe in Cent.
    response = anna.get(f'/api/v1/expenses?month={current_month()}')
    body = response.get_json()
    assert body['user'] == 'Anna'
    assert body['month'] == current_month()
    assert body['total_cents'] == 490 + 560
    descriptions = {row['description'] for row in body['expenses']}
    assert {'Rewe', 'Kaffee'} <= descriptions
    rewe = next(row for row in body['expenses'] if row['description'] == 'Rewe')
    assert rewe['id'] == created_id
    assert rewe['amount_cents'] == 490
    assert rewe['category'] == 'Lebensmittel'  # Stichwort-Erkennung wie im Formular

    # Der aktuelle Monat steht in der Liste verfügbarer Monate.
    response = anna.get('/api/v1/months')
    body = response.get_json()
    assert body['user'] == 'Anna'
    assert current_month() in body['months']


def test_second_user_cannot_see_first_users_entry_or_total(clients):
    anna, ben = clients['anna'], clients['ben']

    csrf_token = login_api(anna)
    response = add_api(anna, csrf_token, {'amount_cents': 490, 'description': 'Rewe'})
    assert response.status_code == 201

    # Ben sieht weder den Eintrag noch dessen Betrag in seiner Summe.
    ben_csrf = login_api(ben, user_name='Ben', password=BENS_PASSWORT)
    response = ben.get(f'/api/v1/expenses?month={current_month()}')
    body = response.get_json()
    assert body['user'] == 'Ben'
    assert body['total_cents'] == 0
    assert body['expenses'] == []

    response = ben.get('/api/v1/months')
    assert response.get_json()['months'] == []

    # Und Ben kann Annas Eintrag auch nicht löschen.
    from db import delete_latest, get_month

    assert delete_latest('Ben') is False
    rows = get_month('Anna', date.today().year, date.today().month)
    assert len(rows) == 1


def test_api_validation_errors(clients):
    anna = clients['anna']
    csrf_token = login_api(anna)

    cases = [
        {'amount_cents': 'zwölf', 'description': 'Rewe'},          # kein Integer
        {'amount_cents': 0, 'description': 'Rewe'},                # null-Betrag
        {'amount_cents': -100, 'description': 'Rewe'},             # negativ
        {'amount_cents': 1_000_000_001, 'description': 'Rewe'},    # über Höchstbetrag
        {'amount_cents': 100},                                     # keine Beschreibung
    ]
    for payload in cases:
        response = add_api(anna, csrf_token, payload)
        assert response.status_code == 400, payload
        assert 'error' in response.get_json()

    response = anna.get('/api/v1/expenses?month=2026-13')
    assert response.status_code == 400
    response = anna.get('/api/v1/expenses?month=nächster')
    assert response.status_code == 400


def test_expense_with_backdated_month(clients):
    anna = clients['anna']
    csrf_token = login_api(anna)

    response = add_api(
        anna, csrf_token, {'amount_cents': 1250, 'description': 'Bücher',
                           'expense_date': '2026-10-05'}
    )
    assert response.status_code == 201

    response = anna.get('/api/v1/expenses?month=2026-10')
    body = response.get_json()
    assert body['total_cents'] == 1250
    assert body['expenses'][0]['expense_date'] == '2026-10-05'

    for bad in ('2026/10/05', '2026-02-30'):
        response = add_api(
            anna, csrf_token, {'amount_cents': 100, 'description': 'X',
                               'expense_date': bad}
        )
        assert response.status_code == 400


def test_html_ui_still_works(clients):
    anna = clients['anna']

    # Anmeldung über das bestehende HTML-Formular.
    page = anna.get('/login')
    html = page.get_data(as_text=True)
    token_match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert token_match, 'CSRF-Feld fehlt im Anmeldeformular'

    response = anna.post(
        '/login',
        data={'user_name': 'Anna', 'password': ANNAS_PASSWORT,
              'csrf_token': token_match.group(1)},
    )
    assert response.status_code == 302
    assert response.headers['Location'].startswith('/')

    # Startseite rendert und die Ausgabe wird per Formular erfasst.
    page = anna.get('/?message=')
    html = page.get_data(as_text=True)
    assert 'Ausgaben' in html
    add_match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    response = anna.post(
        '/add', data={'expense': '7,50 Pizza', 'csrf_token': add_match.group(1)}
    )
    assert response.status_code == 302

    # Der Formulareintrag erscheint auch in der JSON-API desselben Nutzers.
    body = anna.get(f'/api/v1/expenses?month={current_month()}').get_json()
    assert body['total_cents'] >= 750
    assert any(row['description'] == 'Pizza' and row['amount_cents'] == 750
               for row in body['expenses'])

    # Abmelden über die HTML-Route.
    response = anna.get('/logout')
    assert response.status_code == 302
    follow = anna.get('/')
    assert follow.status_code == 302
    assert 'login' in follow.headers['Location']


def test_legacy_bearer_api_contract_unchanged(clients, monkeypatch):
    anna = clients['anna']

    # Eine Ausgabe über die v1-API legt den Datensatz an.
    csrf_token = login_api(anna)
    response = add_api(anna, csrf_token, {'amount_cents': 490, 'description': 'Rewe'})
    assert response.status_code == 201

    # Der alte Bearer-GET-Endpunkt bleibt mit seinem JSON-Vertrag erreichbar.
    monkeypatch.setattr(web, 'API_TOKENS', {'test-bearer-token': 'Anna'})
    response = anna.get(
        f'/api/expenses?month={current_month()}',
        headers={'Authorization': 'Bearer test-bearer-token'},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body['user'] == 'Anna'
    assert body['total_cents'] >= 490
    assert any(row['amount_cents'] == 490 for row in body['expenses'])

    # Ungültiges Bearer-Token bleibt ein JSON-401.
    response = anna.get(
        '/api/expenses', headers={'Authorization': 'Bearer falsch'}
    )
    assert response.status_code == 401
