# Migration: amount REAL -> amount_cents INTEGER

Beträge werden jetzt als ganzzahlige Cent-Werte gespeichert (`money.py`).

## Ablauf

1. Dienst stoppen (z. B. `systemctl stop expenses`).
2. Trockenlauf (schreibt nichts):
   `python scripts/migrate_float_to_cents.py expenses.db expenses_v2.db --dry-run`
3. Migration (legt vorher automatisch ein Backup `expenses.backup-<Zeitstempel>.db` an):
   `python scripts/migrate_float_to_cents.py expenses.db expenses_v2.db`
4. `DB_PATH=expenses_v2.db` in der `.env` setzen.
5. Dienst starten und Summen in der Oberfläche prüfen.

## Sicherheit

- Die alte DB wird nur lesend geöffnet und bleibt unverändert.
- Das Skript bricht ab, wenn Zeilenanzahl oder Gesamtsumme nicht übereinstimmen.
- Eine vorhandene Ziel-DB wird nur mit `--force` überschrieben.
- Rückweg: `DB_PATH` wieder auf die alte DB setzen (mit altem Code-Stand).

## API

`amount` bleibt eine Dezimalzahl (kompatibel); neu sind `amount_cents` und `total_cents`.

## Tests

`pip install pytest && pytest tests/`
