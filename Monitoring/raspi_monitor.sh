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