import re
import sqlite3
from datetime import date
import config

BETRAG_RE = re.compile(r"(\d+(?:[.,]\d{1,2})?)\s*(?:€|eur|euro)?", re.I)


def verbindung():
    conn = sqlite3.connect(config.DB_PFAD)
    conn.execute("""CREATE TABLE IF NOT EXISTS ausgaben (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        datum TEXT NOT NULL,
        name TEXT NOT NULL,
        betrag REAL NOT NULL,
        beschreibung TEXT,
        kategorie TEXT
    )""")
    return conn


def kategorie_finden(text):
    lower_text = text.lower()
    for stichwort, kategorie in config.KATEGORIEN.items():
        if stichwort in lower_text:
            return kategorie
    return "Sonstiges"


def parse_eingabe(text):
    treffer = BETRAG_RE.search(text)
    if not treffer:
        return None
    betrag = float(treffer.group(1).replace(",", "."))
    beschreibung = (text[:treffer.start()] + " " + text[treffer.end():]).strip()
    beschreibung = " ".join(beschreibung.split()) or "ohne Beschreibung"
    return betrag, beschreibung


def eintragen(name, betrag, beschreibung, kategorie):
    conn = verbindung()
    try:
        conn.execute(
            "INSERT INTO ausgaben (datum, name, betrag, beschreibung, kategorie) VALUES (?, ?, ?, ?, ?)",
            (date.today().isoformat(), name, betrag, beschreibung, kategorie),
        )
        conn.commit()
    finally:
        conn.close()


def letzte(name, anzahl=5):
    conn = verbindung()
    try:
        return conn.execute(
            "SELECT datum, betrag, beschreibung FROM ausgaben WHERE name = ? ORDER BY id DESC LIMIT ?",
            (name, anzahl),
        ).fetchall()
    finally:
        conn.close()


def letzten_loeschen(name):
    conn = verbindung()
    try:
        row = conn.execute("SELECT id FROM ausgaben WHERE name = ? ORDER BY id DESC LIMIT 1", (name,)).fetchone()
        if row is None:
            return False
        conn.execute("DELETE FROM ausgaben WHERE id = ?", (row[0],))
        conn.commit()
        return True
    finally:
        conn.close()


def monat(jahr, monat_nr):
    conn = verbindung()
    try:
        return conn.execute(
            "SELECT datum, name, betrag, beschreibung, kategorie FROM ausgaben WHERE datum LIKE ? ORDER BY datum",
            (f"{jahr:04d}-{monat_nr:02d}%",),
        ).fetchall()
    finally:
        conn.close()
