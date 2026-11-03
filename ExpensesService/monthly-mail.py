import argparse
import calendar
from datetime import date

from report import send_mail


def main():
    """Versendet den Bericht nur am letzten Kalendertag des Monats."""
    parser = argparse.ArgumentParser()
    parser.add_argument("user_name", help="Name des Benutzers")
    args = parser.parse_args()

    today = date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]
    if today.day == last_day:
        send_mail(args.user_name, today.year, today.month)


if __name__ == '__main__':
    main()
