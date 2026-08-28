## Raspberry Pi Monitor Script

Schreibe mir ein bash script zur Überwachung meines raspberry pi.
Mit Werten aus dem System:

 - hardware des pi cpu speed,temp/ nvme speed , temp
 - docker monitor daten
 - ip monitor
 - Im loop sollen die daten gelesen werden und die Werte an ein anderes bash Script (sendToEndpoint.sh) geschickt werden.
 - Das sendToEndpoint.sh erwartet 2 parameter: Feldnamen und Wert.
 - Die Werte sollen nur die entsprechen den Values ohne Einheit sein oder OK/Not OK.

Schreibe wenn noch was wichtiges fehlt nicht gleich drauf los, sondern frage mich.

---

Bevor ich loslege, ein paar Rückfragen, damit das Script genau zu deinem Setup passt:

## Grundsätzliches

1. **Loop-Intervall** – Wie oft sollen die Werte gesammelt werden? (z. B. alle 5s, 30s, 1min, 5min?)
2. **Soll das Script dauerhaft laufen** (z. B. als systemd-Service) oder manuell gestartet und mit Strg+C beendet werden?
3. **NVMe** – Du sagst NVMe-Temp. Hast du die NVMe per Adapter (USB→NVMe, M.2 HAT etc.) am Pi hängen, oder meinst du die SD-Karte? Bei SD-Karten gibt es keine vernünftige Temperatur via Standardtools. Falls NVMe: hast du `nvme-cli` installiert, oder soll ich auf `smartctl` ausweichen (falls smartmontools vorhanden)?

## Docker

4. Welche **Docker-Werte** genau interessieren dich? Z. B.:
   - Anzahl laufender Container / gestoppter Container
   - CPU-/RAM-Verbrauch pro Container (würde `docker stats --no-stream` brauchen, ist deutlich schwergewichtiger)
   - Liste der Container-Namen + Status
   - „Geht es Docker" (Daemon erreichbar? ja/nein)

## IP-Monitor

5. **Welche IPs** willst du?
   - Lokale IP(s) (eth0/wlan0)
   - Öffentliche IP (via z. B. `curl ifconfig.me` – braucht Internet, kostet eine HTTP-Anfrage pro Loop)
   - Beides?

## Verhalten bei Fehlern

6. Was soll passieren, wenn ein einzelner Wert **nicht ermittelbar** ist (z. B. kein NVMe, Docker aus, kein Internet für Public IP)?
   - Als `"N/A"` senden
   - Gar nicht senden
   - Als `Not OK` senden

## Sonstiges

7. Soll ich noch **RAM-Auslastung** und **Disk-Auslastung** (Plattenplatz %) mit aufnehmen? Häufig die spannendsten Werte auf einem Pi.
8. Soll das Script ein **Logfile** schreiben (z. B. Fehler beim Sammeln, letzte erfolgreiche Übertragung) oder komplett still sein?

Sobald du das beantwortet hast, baue ich dir ein sauberes Script.

---
1. Loop-Intervall 20 sec
2. systemd-Service
3. M.2 HAT nvme-cli ist installiert
4. Anzahl laufender Container / gestoppter Container
   - Liste der Container-Namen + Status
   - Geht es Docker" (helthy status ? )
5. loclale ip (192.168.178.1)
6. not ok
7. RAM und Platte
8. logfile am anfang zu debug zwecken - ausschaltbar

Perfekt, damit kann ich arbeiten. Ich liefere dir:

1. Das **Monitor-Script** (`pi-monitor.sh`)
2. Den **systemd-Service** (`pi-monitor.service`)
3. Ein **Installations-Snippet** als Hinweis

---

## 1. `pi-monitor.sh`


<details>

<summary><strong>Script anzeigen</strong></summary>


```bash
#!/bin/bash
# =============================================================
# pi-monitor.sh
# Sammelt System-, Docker- und IP-Werte und übergibt sie
# zeilenweise an sendToEndpoint.sh als: <Feldname> <Wert>
# =============================================================

# ---- Konfiguration ----
SEND_SCRIPT="/usr/local/bin/sendToEndpoint.sh"   # Pfad zum Sendescript
INTERVAL=20                                      # Sekunden
LOGFILE="/var/log/pi-monitor.log"
DEBUG=1                                           # 1 = Logfile aktiv, 0 = aus

# ---- Logging ----
log() {
    if [ "$DEBUG" -eq 1 ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S')  $1" >> "$LOGFILE"
    fi
}

send() {
    # $1 = Feldname, $2 = Wert
    if [ -x "$SEND_SEND_SCRIPT" ] 2>/dev/null; then :; fi
    if [ -f "$SEND_SCRIPT" ]; then
        "$SEND_SCRIPT" "$1" "$2" >> "$LOGFILE" 2>&1
    else
        log "WARN: $SEND_SCRIPT nicht gefunden"
    fi
}

# ---- einmaliger Setup-Check ----
log "=== pi-monitor.sh gestartet (PID $$) ==="
if ! command -v docker &>/dev/null; then
    log "WARN: docker nicht installiert"
fi
if ! command -v nvme &>/dev/null; then
    log "WARN: nvme-cli nicht installiert"
fi

# ---- Hauptschleife ----
while true; do

    # ---------- Hardware / System ----------
    # CPU-Takt in MHz (kann leer sein, dann 0)
    cpu_speed=$(awk '{ printf "%.0f", $1/1000 }' /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null || echo 0)
    send "cpu_speed_mhz" "$cpu_speed"

    # CPU-Temperatur in °C (eine Nachkommastelle, . durch ersetzt)
    cpu_temp=$(vcgencmd measure_temp 2>/dev/null | awk -F"=" '{print $2}' | tr -d "'C")
    [ -z "$cpu_temp" ] && cpu_temp="Not OK"
    send "cpu_temp_c" "$cpu_temp"

    # NVMe: wird ermittelt
    if command -v nvme &>/dev/null; then
        # erste NVMe-Adresse automatisch finden
        nvme_dev=$(ls /dev/nvme? 2>/dev/null | head -n1)
        if [ -n "$nvme_dev" ]; then
            # Temperatur
            nvme_temp_raw=$(nvme smart-log "$nvme_dev" 2>/dev/null | awk -F": " '/^Temperature/ {print $2}' | awk '{print $1}')
            if [ -n "$nvme_temp_raw" ]; then
                # Ganzzahl (ohne Einheit)
                nvme_temp=$(printf "%.0f" "$nvme_temp_raw")
            else
                nvme_temp="Not OK"
            fi
            send "nvme_temp_c" "$nvme_temp"

            # Lese-/Schreibgeschwindigkeit in MB/s
            read_mb=$(nvme smart-log "$nvme_dev" 2>/dev/null | awk -F": " '/Data Units Read/    {print $2}' | awk '{printf "%.2f", $1*512/1048576/60}')  # 512 B * 1e6 / 1024^2
            write_mb=$(nvme smart-log "$nvme_dev" 2>/dev/null | awk -F": " '/Data Units Written/ {print $2}' | awk '{printf "%.2f", $1*512/1048576/60}')
            [ -z "$read_mb"  ] && read_mb="Not OK"
            [ -z "$write_mb" ] && write_mb="Not OK"
            send "nvme_read_mbs"  "$read_mb"
            send "nvme_write_mbs" "$write_mb"
        else
            send "nvme_temp_c"    "Not OK"
            send "nvme_read_mbs"  "Not OK"
            send "nvme_write_mbs" "Not OK"
        fi
    else
        send "nvme_temp_c"    "Not OK"
        send "nvme_read_mbs"  "Not OK"
        send "nvme_write_mbs" "Not OK"
    fi

    # RAM: total/used in MB + Auslastung in %
    ram_total=$(awk '/MemTotal/     {print int($2/1024)}' /proc/meminfo)
    ram_avail=$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo)
    ram_used=$((ram_total - ram_avail))
    if [ "$ram_total" -gt 0 ]; then
        ram_used_pct=$(( ram_used * 100 / ram_total ))
    else
        ram_used_pct=0
    fi
    send "ram_used_mb"     "$ram_used"
    send "ram_total_mb"    "$ram_total"
    send "ram_used_pct"    "$ram_used_pct"

    # Platte: Füllgrad in % der Root-Partition
    disk_pct=$(df -P / | awk 'NR==2 {gsub("%","",$5); print $5}')
    [ -z "$disk_pct" ] && disk_pct="Not OK"
    send "disk_used_pct" "$disk_pct"

    # ---------- Docker ----------
    if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
        docker_ok="OK"

        # laufende / gestoppte Container
        running=$(docker ps -q 2>/dev/null | wc -l)
        stopped=$(docker ps -q -f "status=exited" 2>/dev/null | wc -l)
        total=$(docker ps -aq 2>/dev/null | wc -l)
        send "docker_running"     "$running"
        send "docker_stopped"     "$stopped"
        send "docker_total"       "$total"

        # Container-Liste: Name + Status
        # Format: "name1=running,name2=exited,..."
        # Pro Container ein eigenes Feld
        idx=0
        while IFS= read -r line; do
            [ -z "$line" ] && continue
            name=$(echo "$line" | cut -d';' -f1)
            state=$(echo "$line" | cut -d';' -f2)
            # Status in "running"/"stopped" normalisieren
            if echo "$state" | grep -qi "^Up"; then
                norm="running"
            else
                norm="stopped"
            fi
            send "docker_container_${idx}_name"  "$name"
            send "docker_container_${idx}_state" "$norm"
            idx=$((idx+1))
        done < <(docker ps -a --format '{{.Names}};{{.Status}}' 2>/dev/null)

        send "docker_status" "$docker_ok"
    else
        send "docker_status"     "Not OK"
        send "docker_running"    "Not OK"
        send "docker_stopped"    "Not OK"
        send "docker_total"      "Not OK"
        send "docker_container"  "Not OK"
    fi

    # ---------- IP-Monitor ----------
    # lokale IP aus eth0 oder wlan0 (erste gefundene)
    local_ip=""
    for iface in eth0 wlan0 end0; do
        cand=$(ip -4 addr show "$iface" 2>/dev/null | awk '/inet /{print $2}' | cut -d/ -f1)
        if [ -n "$cand" ]; then
            local_ip="$cand"
            break
        fi
    done
    [ -z "$local_ip" ] && local_ip="Not OK"
    send "ip_local" "$local_ip"

    # ---------- Sleep ----------
    sleep "$INTERVAL"

done
```

</details>


### Kurze Erläuterung zu den Werten

| Kategorie | Feldname | Bedeutung |
|---|---|---|
| CPU | `cpu_speed_mhz` | aktueller Takt |
| | `cpu_temp_c` | Temperatur in °C |
| NVMe | `nvme_temp_c`, `nvme_read_mbs`, `nvme_write_mbs` | via `nvme smart-log` |
| RAM | `ram_used_mb`, `ram_total_mb`, `ram_used_pct` | aus `/proc/meminfo` |
| Disk | `disk_used_pct` | Root-Partition |
| Docker | `docker_status`, `docker_running`, `docker_stopped`, `docker_total` | Übersicht |
| | `docker_container_0_name`, `docker_container_0_state`, `docker_container_1_name`, … | je Container ein Paar |
| IP | `ip_local` | erste gefundene lokale IPv4 |

> Hinweis zu NVMe-IO: Aus `nvme smart-log` werden *Data Units* (512 KB pro Unit) summiert über die Lebenszeit ausgelesen. Eine echte Live-Rate pro 20 s ist damit nicht direkt machbar; falls du *Live-IO* willst, bräuchten wir `iostat` (sysstat) oder `sar`. Sag Bescheid, dann ergänze ich das.

---

## 2. `sendToEndpoint.sh` (nur zur Klarstellung – du hast es schon)

Das Script muss genau **2 Argumente** akzeptieren: `feldname` und `wert`. Aufruf erfolgt im Monitor-Script so:

```bash
/usr/local/bin/sendToEndpoint.sh "cpu_temp_c" "47.2"
```

---

## 3. systemd-Service `pi-monitor.service`

<details>
<summary><strong>Service-Unit anzeigen</strong></summary>

```ini
[Unit]
Description=Pi Monitor (System + Docker + IP)
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/pi-monitor.sh
Restart=on-failure
RestartSec=10
# als unprivilegierter User reicht meist; Docker-Aufruf geht dann nur,
# wenn der User in der docker-Gruppe ist. Alternativ root verwenden.
User=root

# Härtung
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true

[Install]
WantedBy=multi-user.target
```

</details>

---

## 4. Installations-Snippet (zur Info)

```bash
# 1. Scripte ablegen
sudo install -m 755 pi-monitor.sh        /usr/local/bin/pi-monitor.sh
sudo install -m 755 sendToEndpoint.sh    /usr/local/bin/sendToEndpoint.sh

# 2. Logfile anlegen
sudo touch /var/log/pi-monitor.log
sudo chmod 640 /var/log/pi-monitor.log

# 3. Service installieren
sudo install -m 644 pi-monitor.service /etc/systemd/system/pi-monitor.service
sudo systemctl daemon-reload
sudo systemctl enable --now pi-monitor.service

# 4. Status prüfen
systemctl status pi-monitor.service
tail -f /var/log/pi-monitor.log
```

---

Sag mir, falls du noch etwas möchtest, z. B.:

- **Live-IO der NVMe** (statt Smart-Werte) via `iostat`/`sysstat`
- **Docker-Container-Image + Ports** zusätzlich
- **CPU-Last in %** (`/proc/stat`-basiert) statt nur Takt
- **Öffentliche IP** (z. B. via `curl ifconfig.me`)

---

## Verbesserungen einbauen:
 - keine nvme_read_mbs / nvme_write_mbs werte sammeln.
 - es gibt ein befhel der liet den status ein ob die NVME lesend und schreibend eingehängt ist oder read only oder emergancy state
 - ping prüfung ob imm localen netzwerk die adresse 192.168.178.1 erreichbar ist

---

Top, hier sind die **Änderungen am bestehenden Script** – ich liefere dir das gesamte aktualisierte `pi-monitor.sh`, damit du es 1:1 austauschen kannst.

Zusammenfassung der Änderungen:

1. **NVMe-IO-Werte entfernt** (`nvme_read_mbs` / `nvme_write_mbs` weg, nur `nvme_temp_c` bleibt)
2. **Neues Feld `nvme_state`** – erkennt `read-write`, `read-only`, `emergency read-only`, oder `Not OK`
3. **Neues Feld `ping_gateway`** – `OK` / `Not OK` (Ping auf `192.168.178.1`, 3 Versuche, 1s Timeout)

---

## Aktualisiertes `pi-monitor.sh`

<details>
<summary><strong>Script anzeigen</strong></summary>

```bash
#!/bin/bash
# =============================================================
# pi-monitor.sh  (v2)
# Sammelt System-, Docker-, NVMe-State-, IP- und Ping-Werte
# und übergibt sie an sendToEndpoint.sh als: <Feldname> <Wert>
# =============================================================

# ---- Konfiguration ----
SEND_SCRIPT="/usr/local/bin/sendToEndpoint.sh"
INTERVAL=20
LOGFILE="/var/log/pi-monitor.log"
DEBUG=1

# Ping-Config
PING_HOST="192.168.178.1"
PING_COUNT=3
PING_TIMEOUT=1

# ---- Logging ----
log() {
    if [ "$DEBUG" -eq 1 ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S')  $1" >> "$LOGFILE"
    fi
}

send() {
    # $1 = Feldname, $2 = Wert
    if [ -f "$SEND_SCRIPT" ]; then
        "$SEND_SCRIPT" "$1" "$2" >> "$LOGFILE" 2>&1
    else
        log "WARN: $SEND_SCRIPT nicht gefunden"
    fi
}

# ---- einmaliger Setup-Check ----
log "=== pi-monitor.sh gestartet (PID $$) ==="
command -v docker &>/dev/null || log "WARN: docker nicht installiert"
command -v nvme   &>/dev/null || log "WARN: nvme-cli nicht installiert"

# ---- Hauptschleife ----
while true; do

    # ---------- Hardware / System ----------
    cpu_speed=$(awk '{ printf "%.0f", $1/1000 }' /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null || echo 0)
    send "cpu_speed_mhz" "$cpu_speed"

    cpu_temp=$(vcgencmd measure_temp 2>/dev/null | awk -F"=" '{print $2}' | tr -d "'C")
    [ -z "$cpu_temp" ] && cpu_temp="Not OK"
    send "cpu_temp_c" "$cpu_temp"

    # ---------- NVMe: Temperatur + Mount-/RW-Status ----------
    if command -v nvme &>/dev/null; then
        nvme_dev=$(ls /dev/nvme? 2>/dev/null | head -n1)
        if [ -n "$nvme_dev" ]; then
            # Temperatur
            nvme_temp_raw=$(nvme smart-log "$nvme_dev" 2>/dev/null \
                | awk -F": " '/^Temperature/ {print $2}' | awk '{print $1}')
            if [ -n "$nvme_temp_raw" ]; then
                nvme_temp=$(printf "%.0f" "$nvme_temp_raw")
            else
                nvme_temp="Not OK"
            fi
            send "nvme_temp_c" "$nvme_temp"

            # Mount-/RW-State
            # nvme id-ctrl liefert u. a. "Sanicap" (RW/RO/ERO) und "Oacs"
            # Wir parsen mehrfach und werten die Klartext-Felder aus.
            idctrl=$(nvme id-ctrl "$nvme_dev" 2>/dev/null)

            # Sanicap (Read/Write-State-Field) – nvme-cli gibt das je nach
            # Version als "Sanicap" oder "Sanicap (Sanitize Capabilities)" aus.
            # Wir entscheiden über das nächstgelegene Wort (rw/ro/ero/...).
            nvme_state="Not OK"

            if [ -n "$idctrl" ]; then
                # Versuch 1: "rw" / "ro" / "ero" in der Ausgabe finden
                found_state=$(echo "$idctrl" \
                    | grep -iE "sanicap|nsanicap|read-only|read.write|emergency" \
                    | head -n1)

                if echo "$found_state" | grep -qiE "rw|read.write"; then
                    nvme_state="read-write"
                elif echo "$found_state" | grep -qi "emergency"; then
                    nvme_state="emergency read-only"
                elif echo "$found_state" | grep -qiE "ro|read.only"; then
                    nvme_state="read-only"
                fi

                # Fallback: am Block-Device schauen (mount-Status)
                if [ "$nvme_state" = "Not OK" ]; then
                    mount_state=$(lsblk -no STATE "$nvme_dev" 2>/dev/null | head -n1 | tr 'A-Z' 'a-z')
                    case "$mount_state" in
                        running) nvme_state="read-write" ;;
                        suspended|"read-only") nvme_state="read-only" ;;
                        *) nvme_state="Not OK" ;;
                    esac
                fi
            fi

            send "nvme_state" "$nvme_state"
        else
            send "nvme_temp_c" "Not OK"
            send "nvme_state"  "Not OK"
        fi
    else
        send "nvme_temp_c" "Not OK"
        send "nvme_state"  "Not OK"
    fi

    # ---------- RAM ----------
    ram_total=$(awk '/MemTotal/     {print int($2/1024)}' /proc/meminfo)
    ram_avail=$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo)
    ram_used=$((ram_total - ram_avail))
    if [ "$ram_total" -gt 0 ]; then
        ram_used_pct=$(( ram_used * 100 / ram_total ))
    else
        ram_used_pct=0
    fi
    send "ram_used_mb"  "$ram_used"
    send "ram_total_mb" "$ram_total"
    send "ram_used_pct" "$ram_used_pct"

    # ---------- Disk (Root) ----------
    disk_pct=$(df -P / | awk 'NR==2 {gsub("%","",$5); print $5}')
    [ -z "$disk_pct" ] && disk_pct="Not OK"
    send "disk_used_pct" "$disk_pct"

    # ---------- Docker ----------
    if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
        docker_ok="OK"
        running=$(docker ps -q 2>/dev/null | wc -l)
        stopped=$(docker ps -q -f "status=exited" 2>/dev/null | wc -l)
        total=$(docker ps -aq 2>/dev/null | wc -l)
        send "docker_running" "$running"
        send "docker_stopped" "$stopped"
        send "docker_total"   "$total"

        idx=0
        while IFS= read -r line; do
            [ -z "$line" ] && continue
            name=$(echo "$line"  | cut -d';' -f1)
            state=$(echo "$line" | cut -d';' -f2)
            if echo "$state" | grep -qi "^Up"; then
                norm="running"
            else
                norm="stopped"
            fi
            send "docker_container_${idx}_name"  "$name"
            send "docker_container_${idx}_state" "$norm"
            idx=$((idx+1))
        done < <(docker ps -a --format '{{.Names}};{{.Status}}' 2>/dev/null)

        send "docker_status" "$docker_ok"
    else
        send "docker_status"  "Not OK"
        send "docker_running" "Not OK"
        send "docker_stopped" "Not OK"
        send "docker_total"   "Not OK"
    fi

    # ---------- IP (lokal) ----------
    local_ip=""
    for iface in eth0 wlan0 end0; do
        cand=$(ip -4 addr show "$iface" 2>/dev/null | awk '/inet /{print $2}' | cut -d/ -f1)
        if [ -n "$cand" ]; then
            local_ip="$cand"
            break
        fi
    done
    [ -z "$local_ip" ] && local_ip="Not OK"
    send "ip_local" "$local_ip"

    # ---------- Ping auf Gateway ----------
    # -c Anzahl, -W Timeout in Sekunden
    if ping -c "$PING_COUNT" -W "$PING_TIMEOUT" "$PING_HOST" &>/dev/null; then
        send "ping_gateway" "OK"
    else
        send "ping_gateway" "Not OK"
    fi

    # ---------- Sleep ----------
    sleep "$INTERVAL"

done
```

</details>

---

## Felderübersicht (aktuell)

| Bereich | Feldname | Mögliche Werte |
|---|---|---|
| CPU | `cpu_speed_mhz` | Zahl in MHz |
| | `cpu_temp_c` | Zahl in °C oder `Not OK` |
| NVMe | `nvme_temp_c` | Zahl in °C oder `Not OK` |
| | `nvme_state` | `read-write` / `read-only` / `emergency read-only` / `Not OK` |
| RAM | `ram_used_mb`, `ram_total_mb`, `ram_used_pct` | Zahlen |
| Disk | `disk_used_pct` | Zahl in % |
| Docker | `docker_status`, `docker_running`, `docker_stopped`, `docker_total` | `OK`/Zahlen / `Not OK` |
| | `docker_container_0_name`, `docker_container_0_state`, … | je Container ein Paar |
| Netz | `ip_local` | IPv4 oder `Not OK` |
| | `ping_gateway` | `OK` / `Not OK` |

---

## Hinweise zur NVMe-State-Erkennung

Die Quelle ist `nvme id-ctrl /dev/nvmeXn1`, Feld **Sanicap / nSanicap** (das ist der Sanitize-Capability-Block, der u. a. den R/W-State anzeigt). Je nach `nvme-cli`-Version sieht die Zeile anders aus, daher:

- Zuerst wird nach Schlüsselwörtern in der Ausgabe gesucht:
  - `rw` / `read.write` → `read-write`
  - `emergency` → `emergency read-only`
  - `ro` / `read.only` → `read-only`
- **Fallback** über `lsblk -no STATE`, falls `id-ctrl` nichts Brauchbares liefert.

Falls bei dir der State falsch erkannt wird, schick mir bitte einmal die Ausgabe von:

```bash
nvme id-ctrl /dev/nvme0n1
```

…dann passe ich das Parsing exakt an deine nvme-cli-Version an.