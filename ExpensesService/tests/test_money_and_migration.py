import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

from money import Money, total  # noqa: E402
import migrate_float_to_cents as migration  # noqa: E402


def test_parse_comma_and_dot():
    assert Money.from_string('12,50').cents == 1250
    assert Money.from_string('12.5').cents == 1250


def test_rounding_half_up():
    assert Money.from_string('0.005').cents == 1


def test_legacy_float_has_no_drift():
    assert Money.from_legacy_float(0.1 + 0.2).cents == 30
    assert Money.from_legacy_float(19.99).cents == 1999


def test_format():
    assert Money(1250).format() == '12,50'
    assert str(Money(5)) == '0,05 €'


def test_total():
    assert total([Money(10), Money(20)]).cents == 30


def _make_old_db(path):
    with sqlite3.connect(path) as c:
        c.execute(
            'CREATE TABLE expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, '
            'expense_date TEXT NOT NULL, user_name TEXT NOT NULL, '
            'amount REAL NOT NULL, description TEXT NOT NULL, category TEXT NOT NULL)'
        )
        c.executemany(
            'INSERT INTO expenses (expense_date, user_name, amount, description, category) '
            'VALUES (?, ?, ?, ?, ?)',
            [('2026-11-01', 'a', 19.99, 'x', 'Other'),
             ('2026-11-02', 'a', 0.1, 'y', 'Other'),
             ('2026-11-03', 'b', 0.2, 'z', 'Other')],
        )


def test_migration_and_dry_run(tmp_path):
    old, new = tmp_path / 'old.db', tmp_path / 'new.db'
    _make_old_db(old)
    count, amount = migration.migrate(old, new, dry_run=True)
    assert (count, amount.cents) == (3, 2029) and not new.exists()
    count, amount = migration.migrate(old, new)
    assert (count, amount.cents) == (3, 2029)
    assert list(tmp_path.glob('old.backup-*.db'))
    with sqlite3.connect(new) as c:
        assert c.execute('SELECT SUM(amount_cents) FROM expenses').fetchone()[0] == 2029


def test_existing_target_requires_force(tmp_path):
    old, new = tmp_path / 'old.db', tmp_path / 'new.db'
    _make_old_db(old)
    migration.migrate(old, new)
    with pytest.raises(SystemExit):
        migration.migrate(old, new)
