from datetime import date
from flask import Flask, abort, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.security import check_password_hash
import config
import db
import report

app = Flask(__name__)
app.config.update(
    SECRET_KEY=config.SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=30 * 24 * 60 * 60,
)


def angemeldet():
    return session.get("user")


def zurueck(msg):
    return redirect(url_for("index", msg=msg))


@app.route("/login", methods=["GET", "POST"])
def login():
    fehler = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        pw = request.form.get("pw", "")
        hashwert = config.NUTZER.get(name)
        if hashwert and check_password_hash(hashwert, pw):
            session.clear()
            session["user"] = name
            session.permanent = True
            return redirect(url_for("index"))
        fehler = "Anmeldung fehlgeschlagen."
    return render_template("login.html", fehler=fehler)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def index():
    user = angemeldet()
    if not user:
        return redirect(url_for("login"))
    eintraege = db.letzte(user)
    return render_template("index.html", user=user, letzte=eintraege, msg=request.args.get("msg"))


@app.route("/eintragen", methods=["POST"])
def eintragen():
    user = angemeldet()
    if not user:
        return redirect(url_for("login"))
    text = request.form.get("text", "")
    parsed = db.parse_eingabe(text)
    if parsed is None:
        return zurueck("Kein Betrag erkannt.")
    betrag, beschreibung = parsed
    kategorie = db.kategorie_finden(beschreibung)
    db.eintragen(user, betrag, beschreibung, kategorie)
    return zurueck(f"Gespeichert: {betrag:.2f} EUR, {beschreibung} ({kategorie})")


@app.route("/loeschen", methods=["POST"])
def loeschen():
    if not angemeldet():
        return redirect(url_for("login"))
    if db.letzten_loeschen(angemeldet()):
        return zurueck("Letzter Eintrag geloescht.")
    return zurueck("Nichts zu loeschen.")


@app.route("/mailen", methods=["POST"])
def mailen():
    if not angemeldet():
        return redirect(url_for("login"))
    heute = date.today()
    try:
        report.mail_senden(f"Ausgaben {heute:%m/%Y}", report.auswertung(heute.year, heute.month))
        return zurueck("Mail versendet.")
    except Exception as exc:
        return zurueck(f"Mailversand fehlgeschlagen: {exc}")


@app.route("/sw.js")
def service_worker():
    response = send_from_directory("static", "sw.js", mimetype="application/javascript")
    response.headers["Cache-Control"] = "no-cache"
    return response


if __name__ == "__main__":
    app.run(host=config.BIND_HOST, port=config.BIND_PORT)
