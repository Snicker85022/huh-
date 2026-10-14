#!/bin/bash
# MT2 kiosk maintenance — ensures ADB TCP and portrait rotation
# Mirror of mt1-maintain.sh (IP .108). Rotation value matched to MT1 baseline (user_rotation=1).
MT2_IP="192.168.2.108"
MT2_TCP="${MT2_IP}:5555"
LOG="/home/taza/reports/mt2-maintain.log"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG"; }

# Check if MT2 is reachable via TCP ADB
if adb connect "$MT2_TCP" 2>&1 | grep -q 'connected'; then
    log "TCP ADB alive at $MT2_TCP"
else
    # Try to re-enable via USB
    USB_SERIAL=$(adb devices | grep -Ev 'List|^$|:5555' | head -1 | awk '{print $1}')
    if [ -n "$USB_SERIAL" ]; then
        adb -s "$USB_SERIAL" tcpip 5555
        sleep 3
        adb connect "$MT2_TCP"
        log "Re-enabled TCP ADB via USB serial $USB_SERIAL"
    else
        log "WARN: No USB device found, cannot bootstrap TCP ADB"
    fi
fi

# Ensure portrait rotation (user_rotation=1, auto-rotate off) — identical to MT1
CUR_ROT=$(adb -s "$MT2_TCP" shell settings get system user_rotation 2>/dev/null | tr -d '\r')
CUR_AUTO=$(adb -s "$MT2_TCP" shell settings get system accelerometer_rotation 2>/dev/null | tr -d '\r')
if [ "$CUR_ROT" != "1" ] || [ "$CUR_AUTO" != "0" ]; then
    adb -s "$MT2_TCP" shell settings put system user_rotation 1
    adb -s "$MT2_TCP" shell settings put system accelerometer_rotation 0
    log "Fixed rotation: was rot=$CUR_ROT auto=$CUR_AUTO, set to rot=1 auto=0"
else
    log "Rotation OK: rot=1 auto=0"
fi
