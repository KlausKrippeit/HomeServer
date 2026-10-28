#!/usr/bin/env python3

import gzip
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


# Festgelegter Ort der Konfiguration. So funktioniert das Skript auch dann,
# wenn systemd es mit einem anderen Arbeitsverzeichnis startet.
SCRIPT_DIR = Path(__file__).resolve().parent
ENV_FILE = SCRIPT_DIR / ".env"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("fhem-db-backup")


def required_env(name: str) -> str:
    """Liest eine erforderliche Umgebungsvariable oder bricht verständlich ab."""
    value = os.getenv(name)
    if value is None or not value.strip():
        raise ValueError(f"Die erforderliche Einstellung {name} fehlt in {ENV_FILE}")
    return value.strip()


def load_config() -> dict:
    if not ENV_FILE.is_file():
        raise FileNotFoundError(f".env-Datei nicht gefunden: {ENV_FILE}")

    keep_value = os.getenv("KEEP_BACKUPS", "6")
    try:
        keep_backups = int(keep_value)
    except ValueError as exc:
        raise ValueError("KEEP_BACKUPS muss eine ganze Zahl sein.") from exc

    if keep_backups < 1:
        raise ValueError("KEEP_BACKUPS muss mindestens 1 sein.")

    return {
        "container": required_env("DB_CONTAINER"),
        "database": required_env("DB_NAME"),
        "table": os.getenv("DB_TABLE", "history").strip(),
        "user": required_env("DB_USER"),
        "password": required_env("DB_PASSWORD"),
        "backup_dir": Path(required_env("BACKUP_DIR")).expanduser(),
        "keep_backups": keep_backups,
        "docker_bin": os.getenv("DOCKER_BIN", "docker").strip(),
        "dump_bin": os.getenv("MARIADB_DUMP_BIN", "mariadb-dump").strip(),
    }


def safe_filename_part(value: str) -> str:
    """Erlaubt nur unkritische Zeichen in Dateinamen."""
    cleaned = re.sub(r"[^A-Za-z0-9_.-]", "_", value)
    if not cleaned:
        raise ValueError("Ungültiger leerer Wert für den Dateinamen.")
    return cleaned


def get_backup_files(backup_dir: Path, database: str, table: str) -> list[Path]:
    prefix = (
        f"{safe_filename_part(database)}_"
        f"{safe_filename_part(table)}_"
    )
    return sorted(
        backup_dir.glob(f"{prefix}*.sql.gz"),
        key=lambda path: path.name,
    )


def prune_old_backups(
    backup_dir: Path,
    database: str,
    table: str,
    keep_backups: int,
) -> None:
    backups = get_backup_files(backup_dir, database, table)

    if len(backups) <= keep_backups:
        logger.info(
            "Aufbewahrung: %d Backup(s), nichts zu löschen.",
            len(backups),
        )
        return

    # Das chronologisch erste Backup wird dauerhaft behalten. Von den übrigen
    # werden die neuesten so lange behalten, bis die Gesamtzahl dem Limit
    # entspricht.
    oldest = backups[0]
    newest_to_keep = backups[-(keep_backups - 1):] if keep_backups > 1 else []
    keep = {oldest, *newest_to_keep}

    for backup in backups:
        if backup not in keep:
            backup.unlink()
            logger.info("Altes Backup gelöscht: %s", backup)


def create_backup(config: dict) -> Path:
    backup_dir: Path = config["backup_dir"]
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d_%H-%M-%S")
    base_name = (
        f"{safe_filename_part(config['database'])}_"
        f"{safe_filename_part(config['table'])}_"
        f"{timestamp}.sql.gz"
    )
    final_path = backup_dir / base_name
    partial_path = backup_dir / f".{base_name}.partial"
    error_path = None

    if final_path.exists() or partial_path.exists():
        raise FileExistsError(f"Backup-Datei existiert bereits: {final_path}")

    # Passwort wird nicht als Befehlszeilenargument übergeben. Docker reicht
    # es als MYSQL_PWD-Umgebungsvariable an den MariaDB-Client im Container.
    docker_env = os.environ.copy()
    docker_env["MYSQL_PWD"] = config["password"]

    command = [
        config["docker_bin"],
        "exec",
        "-e",
        "MYSQL_PWD",
        config["container"],
        config["dump_bin"],
        "--user",
        config["user"],
        "--quick",
        "--single-transaction",
        "--skip-lock-tables",
        "--skip-comments",
        config["database"],
        config["table"],
    ]

    logger.info(
        "Starte Backup von %s.%s aus Container %s.",
        config["database"],
        config["table"],
        config["container"],
    )

    try:
        # stderr geht in eine Datei statt in PIPE: Dadurch kann der Kindprozess
        # nicht wegen eines vollen Fehlerausgabe-Puffers hängen bleiben.
        with tempfile.NamedTemporaryFile(
            mode="w+b",
            prefix="fhem-db-backup-",
            suffix=".stderr",
            delete=False,
        ) as error_file:
            error_path = Path(error_file.name)

            with partial_path.open("wb") as raw_file:
                with gzip.GzipFile(
                    fileobj=raw_file,
                    mode="wb",
                    compresslevel=6,
                    mtime=0,
                ) as compressed_file:
                    process = subprocess.Popen(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=error_file,
                        env=docker_env,
                    )

                    assert process.stdout is not None
                    try:
                        # Begrenzter Speicherverbrauch: Daten werden in Blöcken
                        # direkt vom Dump in die gzip-Datei geschrieben.
                        while True:
                            chunk = process.stdout.read(1024 * 1024)
                            if not chunk:
                                break
                            compressed_file.write(chunk)
                    except BaseException:
                        process.kill()
                        process.wait()
                        raise
                    finally:
                        process.stdout.close()

                    return_code = process.wait()

            error_file.flush()
            error_file.seek(0)
            error_text = error_file.read().decode(
                "utf-8",
                errors="replace",
            ).strip()

        if return_code != 0:
            details = error_text or "(keine Fehlermeldung ausgegeben)"
            raise RuntimeError(
                f"mariadb-dump schlug mit Rückgabecode {return_code} fehl:\n"
                f"{details}"
            )

        if not partial_path.is_file() or partial_path.stat().st_size == 0:
            raise RuntimeError("Der Dump hat eine leere Backup-Datei erzeugt.")

        # Prüft den gzip-Datenstrom vollständig, bevor die Datei als fertiges
        # Backup sichtbar wird.
        with gzip.open(partial_path, "rb") as compressed_file:
            while compressed_file.read(1024 * 1024):
                pass

        # Atomare Umbenennung: Ein unvollständiges Backup erscheint nicht unter
        # dem endgültigen Dateinamen.
        os.replace(partial_path, final_path)
        logger.info(
            "Backup erfolgreich: %s (%.2f GiB)",
            final_path,
            final_path.stat().st_size / (1024 ** 3),
        )

        # Erst nach erfolgreichem Erstellen und Prüfen alte Dateien entfernen.
        prune_old_backups(
            backup_dir,
            config["database"],
            config["table"],
            config["keep_backups"],
        )

        return final_path

    finally:
        if partial_path.exists():
            partial_path.unlink()

        if error_path is not None:
            error_path.unlink(missing_ok=True)


def main() -> int:
    try:
        config = load_config()
        create_backup(config)
        return 0
    except Exception as exc:
        logger.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
