from datetime import date

from config import MAIL_FROM, MAIL_TO, SMTP_HOST, SMTP_PASS, SMTP_PORT, SMTP_USER
from db import get_month, sum_month
from money import Money


def build_report(user_name=None, year=None, month=None):
    """Erstellt den deutschsprachigen Textbericht für einen Monat."""
    today = date.today()
    year = year or today.year
    month = month or today.month
    rows = get_month(user_name, year, month)
    lines = [
        f'Ausgabenbericht — {month:02d}/{year:04d}', '',
        f'Einträge: {len(rows)}', f'Gesamtsumme: {sum_month(rows)}', '',
    ]
    for row in rows:
        category = 'Sonstiges' if row['category'] == 'Other' else row['category']
        lines.append(
            f"{row['expense_date']} | {row['user_name']} | "
            f"{Money(row['amount_cents'])} | {category} | {row['description']}"
        )
    return '\n'.join(lines)
