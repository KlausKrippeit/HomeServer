import re
import sqlite3
from datetime import date

from config import CATEGORY_MAP, DEFAULT_CATEGORY
from database import COLUMNS, get_connection
from money import MAX_CENTS, Money
from werkzeug.security import check_password_hash, generate_password_hash

AMOUNT_PATTERN = re.compile(
    r'(?i)(?:(?:euro|eur\b|€)\s*)?(\d+(?:[.,]\d{1,2})?)'
    r'(?:\s*(?:euro|eur\b|€))?'
)


def find_category(description):
    """Ordnet anhand des Beschreibungstextes die erste passende Kategorie zu."""
    lowered_description = description.casefold()
    for keyword, category in CATEGORY_MAP.items():
        if keyword in lowered_description:
            return category
    return DEFAULT_CATEGORY


def parse_input(raw_input):
    """Liest Betrag (als Money) und Beschreibung aus einer Eingabezeile."""
    normalized_input = raw_input.strip()
    match = AMOUNT_PATTERN.search(normalized_input)
    if not match:
        raise ValueError('Gib einen Betrag mit anschließender Beschreibung ein.')
    amount = Money.from_string(match.group(1))
    if amount.cents <= 0 or amount.cents > MAX_CENTS:
        raise ValueError(
            'Der Betrag muss größer als null sein und innerhalb des zulässigen Höchstbetrags liegen.'
        )
    description = (
        normalized_input[:match.start()] + ' ' + normalized_input[match.end():]
    ).strip(' ,.-')
    if not description:
        raise ValueError('Füge nach dem Betrag eine Beschreibung hinzu.')
    return amount, description, find_category(description)


def add_expense(user_name, raw_input, expense_date=None):
    """Speichert einen Eintrag samt Nutzername und erkannter Kategorie."""
    amount, description, category = parse_input(raw_input)
    with get_connection() as connection:
        cursor = connection.execute(
            'INSERT INTO expenses '
            '(expense_date, user_name, amount_cents, description, category) '
            'VALUES (?, ?, ?, ?, ?)',
            (
                expense_date or date.today().isoformat(), user_name,
                amount.cents, description, category,
            ),
        )
        return cursor.lastrowid


def get_latest(limit=25, user_name=None):
    """Liefert jüngste Einträge; optional auf einen Nutzer beschränkt."""
    with get_connection() as connection:
        if user_name is None:
            return connection.execute(
                f'SELECT {COLUMNS} FROM expenses '
                'ORDER BY expense_date DESC, id DESC LIMIT ?',
                (limit,),
            ).fetchall()
        return connection.execute(
            f'SELECT {COLUMNS} FROM expenses WHERE user_name = ? '
            'ORDER BY expense_date DESC, id DESC LIMIT ?',
            (user_name, limit),
        ).fetchall()


def delete_latest(user_name):
    """Löscht den jüngsten Eintrag des angemeldeten Nutzers."""
    with get_connection() as connection:
        row = connection.execute(
            'SELECT id FROM expenses WHERE user_name = ? '
            'ORDER BY expense_date DESC, id DESC LIMIT 1',
            (user_name,),
        ).fetchone()
        if row is None:
            return False
        connection.execute(
            'DELETE FROM expenses WHERE id = ? AND user_name = ?',
            (row['id'], user_name),
        )
        return True


def get_month(user_name, year=None, month=None):
    """Liefert alle Einträge des Nutzers für den angegebenen oder aktuellen Monat."""
    today = date.today()
    year = year or today.year
    month = month or today.month
    month_start = date(year, month, 1).isoformat()
    next_year = year + (month == 12)
    next_month = 1 if month == 12 else month + 1
    month_end = date(next_year, next_month, 1).isoformat()
    with get_connection() as connection:
        return connection.execute(
            f'SELECT {COLUMNS} FROM expenses WHERE user_name = ? '
            'AND expense_date >= ? AND expense_date < ? '
            'ORDER BY expense_date DESC, id DESC',
            (user_name, month_start, month_end),
        ).fetchall()


def sum_month(rows):
    """Einzige Stelle der Summenbildung über Datenbankzeilen."""
    from money import total
    return total(Money(row['amount_cents']) for row in rows)


MAX_PASSWORD_LENGTH = 128


def validate_password_length(password):
    """Prüft, ob das Passwort die maximale Länge von 128 Zeichen einhält."""
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError(
            f'Das Passwort darf maximal {MAX_PASSWORD_LENGTH} Zeichen lang sein '
            f'(aktuell: {len(password)} Zeichen).'
        )


def get_user_by_email(email):
    """Liefert einen Benutzer nach E-Mail oder None."""
    with get_connection() as connection:
        return connection.execute(
            'SELECT id, email, password_hash, created_at FROM users WHERE email = ?',
            (email,),
        ).fetchone()


def create_user(email, password):
    """Erstellt einen neuen Benutzer mit gehashtem Passwort in der Datenbank."""
    validate_password_length(password)
    password_hash = generate_password_hash(password)
    with get_connection() as connection:
        try:
            cursor = connection.execute(
                'INSERT INTO users (email, password_hash) VALUES (?, ?)',
                (email, password_hash),
            )
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError(f'Ein Benutzer mit der E-Mail {email} existiert bereits.')


def update_password(email, new_password):
    """Aktualisiert das Passwort eines bestehenden Benutzers."""
    validate_password_length(new_password)
    password_hash = generate_password_hash(new_password)
    with get_connection() as connection:
        cursor = connection.execute(
            'UPDATE users SET password_hash = ? WHERE email = ?',
            (password_hash, email),
        )
        return cursor.rowcount > 0


def verify_password(email, password):
    """Prüft, ob das übergebene Passwort zum gespeicherten Hash passt."""
    user = get_user_by_email(email)
    if user is None:
        return False
    return check_password_hash(user['password_hash'], password)