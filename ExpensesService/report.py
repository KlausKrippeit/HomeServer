from collections import defaultdict
from email.message import EmailMessage
import smtplib
import config
import db


def auswertung(jahr, monat):
    zeilen = db.monat(jahr, monat)
    kopf = f"Ausgaben {monat:02d}/{jahr}"
    if not zeilen:
        return f"Keine Ausgaben im {monat:02d}/{jahr}."
    text = [kopf, "-" * len(kopf)]
    personen = defaultdict(float)
    kategorien = defaultdict(float)
    gesamt = 0.0
    for datum, name, betrag, beschreibung, kategorie in zeilen:
        text.append(f"{datum}  {name:<10} {betrag:>8.2f} EUR  {beschreibung} ({kategorie})")
        personen[name] += betrag
        kategorien[kategorie or "Sonstiges"] += betrag
        gesamt += betrag
    text.extend(["", "Summe pro Person:"])
    text.extend(f"{name}: {betrag:.2f} EUR" for name, betrag in sorted(personen.items()))
    text.extend(["", "Summe pro Kategorie:"])
    text.extend(f"{name}: {betrag:.2f} EUR" for name, betrag in sorted(kategorien.items()))
    text.extend(["", f"Gesamt: {gesamt:.2f} EUR"])
    return "\n".join(text)


def mail_senden(betreff, text):
    msg = EmailMessage()
    msg["Subject"] = betreff
    msg["From"] = config.MAIL_VON
    msg["To"] = [adresse.strip() for adresse in config.MAIL_AN.split(",") if adresse.strip()]
    msg.set_content(text)
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(config.SMTP_USER, config.SMTP_PASS)
        smtp.send_message(msg)
