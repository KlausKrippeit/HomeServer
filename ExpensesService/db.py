import re
import sqlite3
from datetime import date
from pathlib import Path

from config import CATEGORY_MAP, DB_PATH, DEFAULT_CATEGORY
from money import MAX_CENTS, Money

AMOUNT_PATTERN = re.compile(
    r'(?i)(?:(?:euro|eur\b|€)\s*)?(\d+(?:[.,]\d{1,2})?)'
    r'(?:\s*(?:euro|eur\b|€))?'
)

SCHEMA = (
    'CREATE TABLE IF NOT EXISTS expenses ('
    'id INTEGER PRIMARY KEY AUTOINCREMENT, '
    "expense_date TEXT NOT NULL CHECK (expense_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'), "
    'user_name TEXT NOT NULL, '
    'amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0), '
    'description TEXT NOT NULL, category TEXT NOT NULL)'
)

COLUMNS = 'id, expense_date, user_name, amount_cents, description, category'


def get_connection():
    """Stellt eine Verbindung her und legt die benötigte Tabelle an."""
    database_path = Path(DB_PATH)
    if str(database_path.parent) not in ('', '.'):
        database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(database_path))
    connection.row_factory = sqlite3.Row
    connection.execute(SCHEMA)
    return connection


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


def insert_expense(user_name, amount_cents, description, expense_date=None):
    """Gemeinsame Schreibfunktion für Oberfläche und API.

    Validiert den Cent-Betrag und die Beschreibung, erkennt die Kategorie
    anhand der Beschreibung und speichert den Eintrag; liefert die neue ID.
    """
    if isinstance(amount_cents, bool) or not isinstance(amount_cents, int):
        raise ValueError('Der Betrag muss eine ganze Zahl in Cent sein.')
    if amount_cents <= 0 or amount_cents > MAX_CENTS:
        raise ValueError(
            'Der Betrag muss größer als null sein und innerhalb des zulässigen Höchstbetrags liegen.'
        )
    cleaned_description = str(description).strip()
    if not cleaned_description:
        raise ValueError('Füge eine Beschreibung hinzu.')
    category = find_category(cleaned_description)
    with get_connection() as connection:
        cursor = connection.execute(
            'INSERT INTO expenses '
            '(expense_date, user_name, amount_cents, description, category) '
            'VALUES (?, ?, ?, ?, ?)',
            (
                expense_date or date.today().isoformat(), user_name,
                amount_cents, cleaned_description, category,
            ),
        )
        return cursor.lastrowid


def add_expense(user_name, raw_input, expense_date=None):
    """Speichert einen Eintrag samt Nutzername und erkannter Kategorie."""
    amount, description, _ = parse_input(raw_input)
    return insert_expense(user_name, amount.cents, description, expense_date=expense_date)


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


def get_months_with_entries(user_name):
    """Liefert die Monate (YYYY-MM) mit Einträgen des Nutzers, neueste zuerst."""
    with get_connection() as connection:
        rows = connection.execute(
            'SELECT DISTINCT substr(expense_date, 1, 7) AS month '
            'FROM expenses WHERE user_name = ? ORDER BY month DESC',
            (user_name,),
        ).fetchall()
        return [row['month'] for row in rows]


def sum_month(rows):
    """Einzige Stelle der Summenbildung über Datenbankzeilen."""
    from money import total
    return total(Money(row['amount_cents']) for row in rows)
