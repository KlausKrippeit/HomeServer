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
    """Fragt alle Werte ab und installiert den Service."""
    print("\n--- Installation ---")                         # Überschrift
    source_dir = Path(ask("Ordner mit Script und .service-Datei", str(Path.cwd()))).expanduser()  # Quellordner
    service_name = ask("Service-Name (ohne .service)", "myservice")     # Name des Services
    script_name = ask("Name des Python-Scripts", f"{service_name}.py")  # Python-Datei
    target_dir = Path(ask("Zielverzeichnis für das Script", str(Path.home() / "scripts" / service_name))).expanduser()  # wohin kopieren (Unterordner pro Service)

    service_src = source_dir / f"{service_name}.service"    # Quelle der Service-Datei
    script_src = source_dir / script_name                   # Quelle des Python-Scripts

    for file in (service_src, script_src):                  # beide Dateien prüfen
        if not file.exists():                               # Datei fehlt?
            sys.exit(f"Fehler: {file} nicht gefunden")      # abbrechen

    print(f"\nKopiere {script_name} nach {target_dir}")     # Statusmeldung
    target_dir.mkdir(parents=True, exist_ok=True)           # Ordner anlegen (kein sudo nötig)
    shutil.copy2(script_src, target_dir / script_name)      # Script kopieren (kein sudo nötig)

    if ask_yes_no("Gibt es eine .env-Datei zum Kopieren?"): # optionale Konfigurationsdatei
        env_src = source_dir / ask(".env-Dateiname", ".env")    # Quelle abfragen
        if env_src.exists():                                # existiert sie?
            shutil.copy2(env_src, target_dir / env_src.name)    # kopieren
            (target_dir / env_src.name).chmod(0o600)        # nur der Besitzer darf lesen/schreiben
        else:                                               # nicht gefunden
            print(f"Warnung: {env_src} nicht gefunden, übersprungen")   # nur warnen

    print("\nInstalliere Service-Datei (hier wird sudo benötigt)")     # ab hier braucht man Root
    run_sudo(["cp", str(service_src), str(SERVICE_DIR / f"{service_name}.service")])   # Service nach /etc/systemd/system
    run_sudo(["systemctl", "daemon-reload"])                # systemd neue Dateien einlesen lassen
    run_sudo(["systemctl", "enable", service_name])         # Autostart beim Booten aktivieren
    run_sudo(["systemctl", "restart", service_name])        # Service jetzt starten
    run_sudo(["systemctl", "status", service_name, "--no-pager"], check=False)  # Status anzeigen


def uninstall():
    """Fragt alle Werte ab und entfernt den Service."""
    print("\n--- Deinstallation ---")                       # Überschrift
    service_name = ask("Service-Name (ohne .service)", "myservice")     # Name des Services
    script_name = ask("Name des Python-Scripts", f"{service_name}.py")  # Python-Datei
    target_dir = Path(ask("Verzeichnis des installierten Scripts", str(Path.home() / "scripts" / service_name))).expanduser()  # wo liegt es (Unterordner pro Service)

    if not ask_yes_no(f"Service '{service_name}' wirklich entfernen?"):     # Sicherheitsabfrage
        print("Abgebrochen.")                               # Hinweis
        return                                              # zurück zum Menü

    run_sudo(["systemctl", "stop", service_name], check=False)          # Service stoppen
    run_sudo(["systemctl", "disable", service_name], check=False)       # Autostart abschalten
    run_sudo(["rm", "-f", str(SERVICE_DIR / f"{service_name}.service")])    # Service-Datei löschen

    script_file = target_dir / script_name                  # Pfad zum kopierten Script
    if script_file.exists():                                # existiert es noch?
        script_file.unlink()                                # löschen (kein sudo nötig)
        print(f"Gelöscht: {script_file}")                   # Statusmeldung

    env_file = target_dir / ".env"                          # mögliche .env-Datei
    if env_file.exists() and ask_yes_no(f"{env_file} ebenfalls löschen?"):  # nachfragen
        env_file.unlink()                                   # löschen

    run_sudo(["systemctl", "daemon-reload"])                # systemd aktualisieren
    run_sudo(["systemctl", "reset-failed"], check=False)    # Fehlerstatus aufräumen
    print("Deinstallation abgeschlossen.")                  # fertig


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
