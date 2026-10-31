import calendar
from datetime import date

from report import send_mail


def main():
    """Versendet den Bericht nur am letzten Kalendertag des Monats."""
    today = date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]
    if today.day == last_day:
        send_mail(today.year, today.month)


if __name__ == '__main__':
    main()
