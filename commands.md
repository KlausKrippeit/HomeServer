# Commands 
## Script von git ordner in den ausführ ordner kopieren
``cp Monitoring/raspi_monitor_service.py ../scripts/``

## Service deamon reloaden (nach Script Änderung)
``sudo systemctl daemon-reload``

## Restart service
``sudo systemctl restart resource_monitor``
``sudo systemctl status resource_monitor``

## Datei in git bearbeiten
``nano Monitoring/raspi_monitor_service.py``

## Ordnergrössen anzeigen
 ``du -h --max-depth=1 . | sort -rh``
 ``sudo du -h --max-depth=1 . | sort -rh``
 ``sudo du -h --max-depth=2 . | sort -rh``
 ``sudo du -h --max-depth=2 / | sort -rh``

## Container Status
| Befehl |
|---|
|``docker inspect -f '{{.State.Status}}' homeassistant``|
|``docker inspect -f '{{.State.Status}}' fhem``|
|``docker inspect -f '{{.State.Status}}' mariadb-fhem``|

## Docker Statistik alle Container
| Befehl|
|---|
|``docker stats``|
|``docker stop opencloud-compose-opencloud-1``|
|``docker stop opencloud-compose-radicale-1``|

## Alle container -a auch die gestoppen
``docker ps -a``

## Alle Container anzeigen in formatierter Tabelle
|Befehl|
|---|
|``docker  ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"``|
|``docker  ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}"``|
|``docker  ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}\t{{.ContainserId}}"``|
|``docker  ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}\t{{.Containser Id}}"``|
|``docker  ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}\t{{.Container Id}}"``|
|``docker  ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}\t{{.ContainerId}}"``|
|``docker  ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}\t{{.Container}}"``|
|``docker  ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}\t{{.ContainerId}}"``|
|``docker  ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}\t{{.RunningFor}}"``|
|``docker  ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}\t{{.ID}}"``|

|Befehl|Komentar|
|---|---|
|``docker compose ps``| # Status der Stack-Container|
|``docker compose stop``| # alle stoppen|
|``docker compose stop mariadb``| # einzelnen Service stoppen|
|``docker compose start``| # alle starten|
|``docker compose restart``| # alle neu starten|
|``docker compose restart mariadb``| # einzelnen Service neu starten|
|``docker compose down``| # alle stoppen UND Container entfernen|
|``docker compose up -d``| # Stack hochfahren (mit evtl. Config-Änderungen)|


## Python

|Befehl|Kommentar|
|---|---|
|``(set -a; source .env; set +a; python3 service_fhem_db_backup.py)``| # python script ausführen mit .env in eigener subshell|


## gzip
|Befehl|Kommentar|
|---|---|
|``gzip -l datei.sql.gz``| # ursprüngliche datei Grösse anzeigen.|
|``zcat datei.sql.gz | head -n 200``| # ersten 200 Zeilen in Datei anzeigen |
|``zcat datei.sql.gz | tail -n 50``| # liest die letzen 50 zeilen - dauert bei grossen datein |
