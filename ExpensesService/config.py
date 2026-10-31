import os
from pathlib import Path
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

BASIS = Path(__file__).resolve().parent
load_dotenv(BASIS / ".env")


def _parse_nutzer(roh):
    nutzer = {}
    for eintrag in roh.split(","):
        name, _, pw = eintrag.strip().partition(":")
        if name and pw:
            nutzer[name] = generate_password_hash(pw)
    return nutzer


def _parse_kategorien(roh):
    kat = {}
    for eintrag in roh.split(","):
        stichwort, _, name = eintrag.partition("=")
        if stichwort.strip() and name.strip():
            kat[stichwort.strip().lower()] = name.strip()
    return kat


SECRET_KEY = os.getenv("SECRET_KEY") or os.urandom(32)
DB_PFAD = Path(os.getenv("DB_PFAD", BASIS / "ausgaben.db"))
NUTZER = _parse_nutzer(os.getenv("NUTZER", ""))
KATEGORIEN = _parse_kategorien(os.getenv("KATEGORIEN", ""))
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
MAIL_VON = os.getenv("MAIL_VON", "")
MAIL_AN = os.getenv("MAIL_AN", "")
BIND_HOST = os.getenv("BIND_HOST", "0.0.0.0")
BIND_PORT = int(os.getenv("BIND_PORT", 8080))

if not NUTZER:
    raise SystemExit("NUTZER fehlt oder ist fehlerhaft in der .env")
