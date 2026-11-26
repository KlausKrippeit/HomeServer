import sqlite3
from pathlib import Path

from config import DB_PATH

EXPENSES_SCHEMA = (
    'CREATE TABLE IF NOT EXISTS expenses ('
    'id INTEGER PRIMARY KEY AUTOINCREMENT, '
    "expense_date TEXT NOT NULL CHECK (expense_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'), "
    'user_name TEXT NOT NULL, '
    'amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0), '
    'description TEXT NOT NULL, category TEXT NOT NULL)'
)

USERS_SCHEMA = (
    'CREATE TABLE IF NOT EXISTS users ('
    'id INTEGER PRIMARY KEY AUTOINCREMENT, '
    'email TEXT UNIQUE NOT NULL, '
    'password_hash TEXT NOT NULL, '
    'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)'
)

COLUMNS = 'id, expense_date, user_name, amount_cents, description, category'


def get_connection():
    """Stellt eine Verbindung her und legt die benötigten Tabellen an."""
    database_path = Path(DB_PATH)
    print(f'get_connection: database_path: {database_path}')
    if str(database_path.parent) not in ('', '.'):
        database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(database_path))
    connection.row_factory = sqlite3.Row
    connection.execute(EXPENSES_SCHEMA)
    connection.execute(USERS_SCHEMA)
    return connection