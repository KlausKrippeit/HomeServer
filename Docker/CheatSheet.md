# Docker in der Console – Cheat Sheet

## Container auflisten

```bash
docker ps                 # Laufende Container
docker ps -a              # Alle Container, auch gestoppte
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
docker container ls       # Entspricht docker ps
```

## Container starten und stoppen

```bash
docker start <name|id>    # Vorhandenen Container starten
docker stop <name|id>     # Graceful stoppen (SIGTERM, danach ggf. SIGKILL)
docker restart <name|id>  # Neustarten
docker kill <name|id>     # Sofort beenden (SIGKILL)
docker pause <name|id>    # Prozesse anhalten
docker unpause <name|id>  # Fortsetzen
```

## Neuen Container starten

```bash
docker run -d \
  --name web \
  -p 8080:80 \
  --restart unless-stopped \
  nginx:latest
```

- `docker run` erstellt und startet einen neuen Container.
- `-d` startet ihn im Hintergrund.
- `--name web` vergibt den Namen `web`.
- `-p 8080:80` leitet **Host-Port 8080** auf **Container-Port 80** weiter. Aufrufen kannst du ihn dann unter `http://localhost:8080`.
- `--restart unless-stopped` startet den Container nach einem Docker-Neustart automatisch wieder – außer, du hast ihn zuvor manuell gestoppt.
- `nginx:latest` gibt das Image und den Tag an. Docker lädt das Image herunter, falls es lokal noch nicht vorhanden ist.

Weitere häufige Optionen:

```bash
-e APP_MODE=prod       # Umgebungsvariable setzen
-v webdata:/data       # Volume einbinden
--network mein-netz    # Docker-Netzwerk festlegen
```

Beispiel mit zusätzlichen Optionen:

```bash
docker run -d \
  --name web \
  -p 8080:80 \
  -e APP_MODE=prod \
  -v webdata:/data \
  --restart unless-stopped \
  nginx:latest
```

## Logs und Zugriff

```bash
docker logs <name|id>             # Gesamte Logs anzeigen
docker logs -f <name|id>          # Logs live verfolgen (Strg+C beendet Anzeige)
docker logs --tail 100 <name|id>  # Letzte 100 Zeilen
docker logs -t <name|id>          # Mit Zeitstempeln
docker exec -it <name|id> sh      # Shell im laufenden Container öffnen
docker exec -it <name|id> bash    # Falls Bash installiert ist
```

## Container-Einstellungen und Details

```bash
docker inspect <name|id>                          # Vollständige Konfiguration als JSON
docker inspect -f '{{.State.Status}}' <name|id>   # Status
docker port <name|id>                             # Port-Zuordnungen
docker stats                                      # Live-Ressourcenverbrauch aller Container
docker stats <name|id>                            # Ressourcenverbrauch eines Containers
docker top <name|id>                              # Prozesse im Container
docker rename <alt> <neu>                         # Container umbenennen
```

Einstellungen wie Ports, Umgebungsvariablen oder Volumes lassen sich bei einem bestehenden Container nicht direkt ändern. Container mit den gewünschten Optionen neu erstellen.

```bash
docker rm -f web
docker run -d --name web -p 8081:80 -e MODE=prod -v webdata:/data nginx
# -e: Umgebungsvariable · -v: Volume
```

## Aufräumen

```bash
docker rm <name|id>       # Gestoppten Container löschen
docker rm -f <name|id>    # Container stoppen und löschen
docker container prune    # Alle gestoppten Container löschen
```
