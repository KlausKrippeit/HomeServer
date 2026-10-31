import os

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()


def parse_users(raw_users):
    """Liest Nutzer und Kennwörter aus der Umgebungsvariable."""
    users = {}
    for entry in raw_users.split(','):
        entry = entry.strip()
        if not entry or ':' not in entry:
            continue
        user_name, password = entry.split(':', 1)
        user_name = user_name.strip()
        if user_name and password:
            users[user_name] = generate_password_hash(password)
    return users


def parse_category_map(raw_categories, defaults=None):
    """Ergänzt Standardzuordnungen mit Einträgen aus der Umgebung."""
    category_map = dict(defaults or {})
    for entry in raw_categories.split(','):
        if '=' not in entry:
            continue
        keyword, category = (part.strip() for part in entry.split('=', 1))
        if keyword and category:
            category_map[keyword.casefold()] = category
    return category_map


USERS = parse_users(os.getenv('USERS', ''))
SECRET_KEY = os.getenv('SECRET_KEY', 'development-only-change-this-secret')
DB_PATH = os.getenv('DB_PATH', 'expenses.db')
BIND_HOST = os.getenv('BIND_HOST', '127.0.0.1')
BIND_PORT = int(os.getenv('BIND_PORT', '8080'))
SMTP_HOST = os.getenv('SMTP_HOST', '')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASS = os.getenv('SMTP_PASS', '')
MAIL_FROM = os.getenv('MAIL_FROM', '')
MAIL_TO = os.getenv('MAIL_TO', '')
DEFAULT_CATEGORY = 'Other'
CATEGORY_MAP = {
    'rewe': 'Lebensmittel',
    'edeka': 'Lebensmittel',
    'aldi': 'Lebensmittel',
    'lidl': 'Lebensmittel',
    'dm': 'Drogerie',
    'rossmann': 'Drogerie',
    'tanken': 'Auto',
    'shell': 'Auto',
    'aral': 'Auto',
    'restaurant': 'Essen gehen',
    'pizza': 'Essen gehen',
    'kaffee': 'Essen gehen',
    'miete': 'Wohnen',
    'strom': 'Wohnen',
    'internet': 'Wohnen',
    'kino': 'Freizeit',
    'netflix': 'Freizeit',
}
CATEGORY_MAP = parse_category_map(os.getenv('CATEGORIES', ''), CATEGORY_MAP)
