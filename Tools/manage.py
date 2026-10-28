#!/usr/bin/env python3
"""
manage.py - Interaktives Install/Uninstall-Script für systemd-Services.

Aufruf (OHNE sudo, sudo fragt selbst nach dem Passwort, wenn es nötig ist):
    python3 manage.py
"""

import shutil                       # zum Kopieren von Dateien
import subprocess                   # zum Ausführen von Shell-Befehlen
import sys                          # für sys.exit()
from pathlib import Path            # moderner Umgang mit Dateipfaden

SERVICE_DIR = Path("/etc/systemd/system")   # Ort, wo systemd seine Service-Dateien erwartet


def ask(question, default):
    """Stellt eine Frage und gibt die Antwort zurück (Enter = Standardwert)."""
    answer = input(f"{question} [{default}]: ").strip()     # Eingabe lesen, Leerzeichen entfernen
    return answer if answer else default                    # leer? -> Standardwert verwenden


def ask_yes_no(question, default="n"):
    """Stellt eine Ja/Nein-Frage und gibt True oder False zurück."""
    hint = "Y/n" if default == "y" else "y/N"               # Großbuchstabe zeigt den Standard
    answer = input(f"{question} [{hint}]: ").strip().lower()    # Eingabe in Kleinbuchstaben
    if not answer:                                          # nichts eingegeben?
        answer = default                                    # Standard nehmen
    return answer == "y"                                    # True nur bei "y"


def run_sudo(cmd, check=True):
    """Führt einen Befehl mit sudo aus (sudo fragt selbst nach dem Passwort)."""
    print(f"$ sudo {' '.join(cmd)}")                        # Befehl zur Info anzeigen
    return subprocess.run(["sudo"] + cmd, check=check)      # sudo davorsetzen und ausführen

def install():
    """Fragt alle Werte ab und installiert den Service (optional mit Timer)."""
    print("\n--- Installation ---")                         # Überschrift
    source_dir = Path(ask("Ordner mit Script und .service-Datei", str(Path.cwd()))).expanduser()  # Quellordner
    service_name = ask("Service-Name (ohne .service)", "myservice")     # Name des Services
    script_name = ask("Name des Python-Scripts", f"{service_name}.py")  # Python-Datei
    target_dir = Path(ask("Zielverzeichnis für das Script", str(Path.home() / "scripts" / service_name))).expanduser()  # Zielordner

    service_file = source_dir / f"{service_name}.service"   # Pfad zur Service-Datei im Quellordner
    timer_file = source_dir / f"{service_name}.timer"       # Pfad zur (optionalen) Timer-Datei
    script_file = source_dir / script_name                  # Pfad zum Python-Script im Quellordner
    has_timer = timer_file.exists()                         # True, wenn eine Timer-Datei existiert

    for required in (service_file, script_file):            # Pflichtdateien durchgehen
        if not required.exists():                           # Datei fehlt?
            print(f"Fehler: {required} nicht gefunden.")    # Fehlermeldung
            return                                          # Installation abbrechen

    if has_timer:                                           # Timer vorhanden?
        print(f"Timer-Datei gefunden: {timer_file.name}")   # Info für den Nutzer
    else:                                                   # kein Timer
        print("Keine Timer-Datei gefunden, installiere nur den Service.")   # Info

    autostart = ask_yes_no("Beim Booten automatisch starten (enable)?", "y")    # Autostart gewünscht?
    print(f"\nQuelle:  {source_dir}\nZiel:    {target_dir}\nService: {service_name}\nTimer:   {'ja' if has_timer else 'nein'}")   # Zusammenfassung
    if not ask_yes_no("Fortfahren?", "y"):                  # Bestätigung einholen
        print("Abgebrochen.")                               # Hinweis
        return                                              # zurück zum Menü

    target_dir.mkdir(parents=True, exist_ok=True)           # Zielordner anlegen (falls nötig)
    shutil.copy2(script_file, target_dir / script_name)     # Script kopieren (ohne sudo, gehört dem User)
    env_file = source_dir / ".env"                          # mögliche .env-Datei im Quellordner
    if env_file.exists():                                   # existiert sie?
        shutil.copy2(env_file, target_dir / ".env")         # dann mitkopieren
        (target_dir / ".env").chmod(0o600)                  # nur der Besitzer darf lesen/schreiben

    run_sudo(["cp", str(service_file), str(SERVICE_DIR / service_file.name)])   # Service-Datei nach /etc/systemd/system
    if has_timer:                                           # Timer vorhanden?
        run_sudo(["cp", str(timer_file), str(SERVICE_DIR / timer_file.name)])   # Timer-Datei ebenfalls kopieren

    run_sudo(["systemctl", "daemon-reload"])                # systemd über neue Dateien informieren

    if has_timer:                                           # mit Timer?
        timer_unit = f"{service_name}.timer"                # Name der Timer-Unit
        if autostart:                                       # Autostart gewünscht?
            run_sudo(["systemctl", "enable", timer_unit])   # Timer beim Booten aktivieren
        run_sudo(["systemctl", "start", timer_unit])        # Timer jetzt starten (NICHT den Service!)
        run_sudo(["systemctl", "list-timers", timer_unit, "--no-pager"], check=False)   # nächsten Ablaufzeitpunkt anzeigen
        run_sudo(["systemctl", "status", timer_unit, "--no-pager"], check=False)        # Timer-Status anzeigen
    else:                                                   # ohne Timer (normaler Service)
        if autostart:                                       # Autostart gewünscht?
            run_sudo(["systemctl", "enable", service_name]) # Service beim Booten aktivieren
        run_sudo(["systemctl", "start", service_name])      # Service sofort starten
        run_sudo(["systemctl", "status", service_name, "--no-pager"], check=False)      # Status anzeigen

    print("\nInstallation abgeschlossen.")                  # Erfolgsmeldung


def uninstall():
    """Fragt alle Werte ab und entfernt den Service (und Timer, falls vorhanden)."""
    print("\n--- Deinstallation ---")                       # Überschrift
    service_name = ask("Service-Name (ohne .service)", "myservice")     # Name des Services
    target_dir = Path(ask("Verzeichnis des installierten Scripts", str(Path.home() / "scripts" / service_name))).expanduser()  # Scriptordner

    service_path = SERVICE_DIR / f"{service_name}.service"  # installierte Service-Datei
    timer_path = SERVICE_DIR / f"{service_name}.timer"      # installierte Timer-Datei
    has_timer = timer_path.exists()                         # gibt es einen Timer?

    remove_files = ask_yes_no(f"Ordner {target_dir} samt Inhalt (inkl. .env) löschen?", "n")    # Dateien auch löschen?
    print(f"\nEntfernt wird: {service_name}" + (" (inkl. Timer)" if has_timer else ""))         # Zusammenfassung
    if not ask_yes_no("Fortfahren?", "n"):                  # Bestätigung einholen
        print("Abgebrochen.")                               # Hinweis
        return                                              # zurück zum Menü

    if has_timer:                                           # Timer zuerst entfernen
        timer_unit = f"{service_name}.timer"                # Name der Timer-Unit
        run_sudo(["systemctl", "stop", timer_unit], check=False)        # Timer stoppen (Fehler ignorieren)
        run_sudo(["systemctl", "disable", timer_unit], check=False)     # Autostart des Timers entfernen
        run_sudo(["rm", "-f", str(timer_path)])             # Timer-Datei löschen

    run_sudo(["systemctl", "stop", service_name], check=False)          # Service stoppen (falls er gerade läuft)
    run_sudo(["systemctl", "disable", service_name], check=False)       # Autostart entfernen (bei Timer-Services evtl. wirkungslos)
    run_sudo(["rm", "-f", str(service_path)])               # Service-Datei löschen
    run_sudo(["systemctl", "daemon-reload"])                # systemd neu einlesen
    run_sudo(["systemctl", "reset-failed"], check=False)    # alte Fehlerzustände aufräumen

    if remove_files and target_dir.exists():                # Ordner löschen gewünscht und vorhanden?
        shutil.rmtree(target_dir)                           # Ordner samt Inhalt löschen (ohne sudo)
        print(f"{target_dir} gelöscht.")                    # Info

    print("\nDeinstallation abgeschlossen.")                # Erfolgsmeldung

def main():
    """Zeigt das Hauptmenü und startet die gewählte Aktion."""
    while True:                                             # Menü wiederholen bis Beenden
        print("\n=== Service-Manager ===")                  # Titel
        print("1) Installieren")                            # Option 1
        print("2) Deinstallieren")                          # Option 2
        print("3) Beenden")                                 # Option 3
        choice = input("Auswahl: ").strip()                 # Eingabe lesen

        if choice == "1":                                   # Installieren gewählt?
            install()                                       # Funktion aufrufen
        elif choice == "2":                                 # Deinstallieren gewählt?
            uninstall()                                     # Funktion aufrufen
        elif choice == "3":                                 # Beenden gewählt?
            print("Tschüss!")                               # Verabschiedung
            break                                           # Schleife verlassen
        else:                                               # ungültige Eingabe
            print("Ungültige Auswahl.")                     # Hinweis


if __name__ == "__main__":                                  # nur ausführen, wenn direkt gestartet
    try:                                                    # Fehler abfangen
        main()                                              # Hauptmenü starten
    except KeyboardInterrupt:                               # Strg+C gedrückt?
        print("\nAbgebrochen.")                             # sauber beenden
    except subprocess.CalledProcessError as error:          # ein Befehl ist fehlgeschlagen?
        sys.exit(f"Befehl fehlgeschlagen: {error}")         # Fehlermeldung ausgeben
