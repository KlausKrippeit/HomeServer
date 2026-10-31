import re
import sqlite3
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from config import CATEGORIES, DB_PATH

AMOUNT_PATTERN = re.compile(
    r'(?i)(?:(?:euro|eur\b|€)\s*)?(\d+(?:[.,]\d{1,2})?)'
    r'(?:\s*(?:euro|eur\b|€))?'
)


def get_connection():
    """Stellt eine Verbindung her und legt die benötigte Tabelle an."""
    database_path = Path(DB_PATH)
    if str(database_path.parent) not in ('', '.'):
        database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(database_path))
    connection.row_factory = sqlite3.Row
    connection.execute(
        'CREATE TABLE IF NOT EXISTS expenses ('
        'id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'expense_date TEXT NOT NULL, user_name TEXT NOT NULL, '
        'amount REAL NOT NULL, description TEXT NOT NULL, category TEXT NOT NULL)'
    )
    return connection


def find_category(description):
    """Ordnet anhand des Beschreibungstextes die erste passende Kategorie zu."""
    lowered_description = description.casefold()
    for category in CATEGORIES:
        if category.casefold() in lowered_description:
            return category
    return CATEGORIES[-1]


def parse_input(raw_input):
    """Liest Betrag und Beschreibung aus einer Eingabezeile."""
    normalized_input = raw_input.strip()
    match = AMOUNT_PATTERN.search(normalized_input)
    if not match:
        raise ValueError('Enter an amount followed by a description.')
    try:
        amount = Decimal(match.group(1).replace(',', '.'))
    except InvalidOperation as error:
        raise ValueError('Enter a valid amount.') from error
    if amount <= 0 or amount > Decimal('10000000'):
        raise ValueError(
            'Amount must be greater than zero and within the supported limit.'
        )
    description = (
        normalized_input[:match.start()] + ' ' + normalized_input[match.end():]
    ).strip(' ,.-')
    if not description:
        raise ValueError('Add a description after the amount.')
    return round(float(amount), 2), description, find_category(description)


def add_expense(user_name, raw_input, expense_date=None):
    """Speichert einen Eintrag samt Nutzername und erkannter Kategorie."""
    amount, description, category = parse_input(raw_input)
    with get_connection() as connection:
        cursor = connection.execute(
            'INSERT INTO expenses '
            '(expense_date, user_name, amount, description, category) '
            'VALUES (?, ?, ?, ?, ?)',
            (
                expense_date or date.today().isoformat(), user_name, amount,
                description, category,
            ),
        )
        return cursor.lastrowid


def get_latest(limit=25):
    """Liefert die jüngsten Einträge unabhängig vom Monat."""
    with get_connection() as connection:
        return connection.execute(
            'SELECT id, expense_date, user_name, amount, description, category '
            'FROM expenses ORDER BY expense_date DESC, id DESC LIMIT ?',
            (limit,),
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
        connection.execute('DELETE FROM expenses WHERE id = ?', (row['id'],))
        return True


def get_month(year=None, month=None):
    """Liefert alle Einträge des angegebenen oder aktuellen Monats."""
    today = date.today()
    year = year or today.year
    month = month or today.month
    month_start = date(year, month, 1).isoformat()
    next_year = year + (month == 12)
    next_month = 1 if month == 12 else month + 1
    month_end = date(next_year, next_month, 1).isoformat()
    with get_connection() as connection:
        return connection.execute(
            'SELECT id, expense_date, user_name, amount, description, category '
            'FROM expenses WHERE expense_date >= ? AND expense_date < ? '
            'ORDER BY expense_date DESC, id DESC',
            (month_start, month_end),
        ).fetchall()
