#!/bin/bash
# MT1 kiosk maintenance — ensures ADB TCP and portrait rotation
MT1_IP="192.168.2.104"
MT1_TCP="${MT1_IP}:5555"
LOG="/home/taza/reports/mt1-maintain.log"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG"; }

# Check if MT1 is reachable via TCP ADB
if adb connect "$MT1_TCP" 2>&1 | grep -q 'connected'; then
    log "TCP ADB alive at $MT1_TCP"
else
    # Try to re-enable via USB
    USB_SERIAL=$(adb devices | grep -Ev 'List|^$|:5555' | head -1 | awk '{print $1}')
    if [ -n "$USB_SERIAL" ]; then
        adb -s "$USB_SERIAL" tcpip 5555
        sleep 3
        adb connect "$MT1_TCP"
        log "Re-enabled TCP ADB via USB serial $USB_SERIAL"
    else
        log "WARN: No USB device found, cannot bootstrap TCP ADB"
    fi
fi

# Ensure portrait rotation (user_rotation=1, auto-rotate off)
CUR_ROT=$(adb -s "$MT1_TCP" shell settings get system user_rotation 2>/dev/null | tr -d '\r')
CUR_AUTO=$(adb -s "$MT1_TCP" shell settings get system accelerometer_rotation 2>/dev/null | tr -d '\r')
if [ "$CUR_ROT" != "1" ] || [ "$CUR_AUTO" != "0" ]; then
    adb -s "$MT1_TCP" shell settings put system user_rotation 1
    adb -s "$MT1_TCP" shell settings put system accelerometer_rotation 0
    log "Fixed rotation: was rot=$CUR_ROT auto=$CUR_AUTO, set to rot=1 auto=0"
else
    log "Rotation OK: rot=1 auto=0"
fi
