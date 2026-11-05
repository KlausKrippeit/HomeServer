"""Überführt die alte DB (amount REAL) in eine neue DB (amount_cents INTEGER).

Die alte DB wird nur lesend geöffnet und vorher mit Zeitstempel gesichert.
Aufruf (aus ExpensesService/):
    python scripts/migrate_float_to_cents.py expenses.db expenses_v2.db [--dry-run] [--force]
"""
import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import SCHEMA  # noqa: E402
from money import Money, total  # noqa: E402


def backup(source):
    """Kopiert die alte DB mit Zeitstempel neben das Original."""
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    target = source.with_name(f'{source.stem}.backup-{stamp}{source.suffix}')
    shutil.copy2(source, target)
    return target


def read_old_rows(source):
    uri = f'file:{source}?mode=ro'
    with sqlite3.connect(uri, uri=True) as connection:
        connection.row_factory = sqlite3.Row
        return connection.execute(
            'SELECT id, expense_date, user_name, amount, description, category '
            'FROM expenses ORDER BY id'
        ).fetchall()


def migrate(source, target, dry_run=False, force=False):
    """Führt die Migration aus und gibt (Zeilen, Summe) zurück."""
    if target.exists() and not force and not dry_run:
        raise SystemExit(f'{target} existiert bereits (--force zum Überschreiben).')
    rows = read_old_rows(source)
    converted = [
        (r['id'], r['expense_date'], r['user_name'],
         Money.from_legacy_float(r['amount']).cents,
         r['description'], r['category'])
        for r in rows
    ]
    old_sum = total(Money.from_legacy_float(r['amount']) for r in rows)
    if dry_run:
        return len(converted), old_sum
    backup(source)
    if target.exists():
        target.unlink()
    with sqlite3.connect(target) as connection:
        connection.execute(SCHEMA)
        connection.executemany(
            'INSERT INTO expenses (id, expense_date, user_name, amount_cents, '
            'description, category) VALUES (?, ?, ?, ?, ?, ?)', converted,
        )
        count, new_cents = connection.execute(
            'SELECT COUNT(*), COALESCE(SUM(amount_cents), 0) FROM expenses'
        ).fetchone()
        if count != len(rows) or Money(new_cents) != old_sum:
            raise SystemExit('Abgleich fehlgeschlagen, es wurde nichts übernommen.')
    return count, Money(new_cents)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('old_db', type=Path)
    parser.add_argument('new_db', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    count, amount = migrate(args.old_db, args.new_db, args.dry_run, args.force)
    mode = 'Trockenlauf' if args.dry_run else 'Migriert'
    print(f'{mode}: {count} Einträge, Summe {amount}')


if __name__ == '__main__':
    main()
