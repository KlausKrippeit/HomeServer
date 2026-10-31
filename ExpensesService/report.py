import smtplib
from datetime import date
from email.message import EmailMessage

from config import MAIL_FROM, MAIL_TO, SMTP_HOST, SMTP_PASS, SMTP_PORT, SMTP_USER
from db import get_month


def build_report(year=None, month=None):
    """Erstellt den deutschsprachigen Textbericht für einen Monat."""
    today = date.today()
    year = year or today.year
    month = month or today.month
    rows = get_month(year, month)
    lines = [f'Ausgabenbericht — {month:02d}/{year:04d}', '', f'Einträge: {len(rows)}']
    total = sum(float(row['amount']) for row in rows)
    lines.extend((f'Gesamtsumme: {total:.2f}'.replace('.', ',') + ' €', ''))
    for row in rows:
        lines.append(
            f"{row['expense_date']} | {row['user_name']} | "
            f"{float(row['amount']):.2f}".replace('.', ',') + f" € | {'Sonstiges' if row['category'] == 'Other' else row['category']} | {row['description']}"
        )
    return '\n'.join(lines)


def send_mail(year=None, month=None):
    """Versendet den Monatsbericht über SMTP mit STARTTLS."""
    if not all((SMTP_HOST, MAIL_FROM, MAIL_TO)):
        raise RuntimeError('SMTP_HOST, MAIL_FROM und MAIL_TO müssen konfiguriert sein.')
    today = date.today()
    report_year = year or today.year
    report_month = month or today.month
    message = EmailMessage()
    message['Subject'] = f'Ausgabenbericht {report_month:02d}/{report_year:04d}'
    message['From'] = MAIL_FROM
    message['To'] = MAIL_TO
    message.set_content(build_report(report_year, report_month))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        server.starttls()
        if SMTP_USER:
            server.login(SMTP_USER, SMTP_PASS)
        server.send_message(message)
