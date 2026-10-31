from datetime import date, timedelta
import report

heute = date.today()
morgen = heute + timedelta(days=1)
if morgen.day == 1:
    text = report.auswertung(heute.year, heute.month)
    report.mail_senden(f"Ausgaben {heute:%m/%Y}", text)
