import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import (
    MAX_PASSWORD_LENGTH,
    create_user,
    get_user_by_email,
    update_password,
    validate_password_length,
)


def read_password(prompt):
    """Fragt interaktiv ein Passwort ab (ohne Echo auf der Konsole)."""
    return getpass.getpass(prompt)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Benutzer in der Datenbank verwalten.')
    subparsers = parser.add_subparsers(dest='command', required=True)

    create_parser = subparsers.add_parser('create', help='Neuen Benutzer erstellen.')
    create_parser.add_argument('--email', required=True, help='E-Mail-Adresse des Benutzers.')

    update_parser = subparsers.add_parser('update-password', help='Passwort eines Benutzers aktualisieren.')
    update_parser.add_argument('--email', required=True, help='E-Mail-Adresse des Benutzers.')

    args = parser.parse_args()

    if args.command == 'create':
        password = read_password('Passwort eingeben: ')
        confirm = read_password('Passwort wiederholen: ')
        if password != confirm:
            print('Fehler: Die Passwörter stimmen nicht überein.', file=sys.stderr)
            sys.exit(1)
        try:
            user_id = create_user(args.email, password)
            print(f'Benutzer erstellt (ID: {user_id}, E-Mail: {args.email}).')
        except ValueError as error:
            print(f'Fehler: {error}', file=sys.stderr)
            sys.exit(1)

    elif args.command == 'update-password':
        if get_user_by_email(args.email) is None:
            print(f'Fehler: Kein Benutzer mit E-Mail {args.email} gefunden.', file=sys.stderr)
            sys.exit(1)
        new_password = read_password('Neues Passwort eingeben: ')
        confirm = read_password('Neues Passwort wiederholen: ')
        if new_password != confirm:
            print('Fehler: Die Passwörter stimmen nicht überein.', file=sys.stderr)
            sys.exit(1)
        try:
            if update_password(args.email, new_password):
                print(f'Passwort für {args.email} wurde aktualisiert.')
            else:
                print(f'Fehler: Passwort für {args.email} konnte nicht aktualisiert werden.', file=sys.stderr)
                sys.exit(1)
        except ValueError as error:
            print(f'Fehler: {error}', file=sys.stderr)
            sys.exit(1)