#!/bin/bash
# ---------------------------------------------------------------------------
# Self-healing print path for the Taza checklist printer.
#   HP DeskJet 3700 series [760AB1]  MAC 98:e7:f4:76:0a:b1   last good 192.168.2.118
#
# WHY (root cause, 2026-10-08):
#   The queue cups-browsed auto-creates ("HP_DeskJet_3700_series_760AB1") is an
#   implicitclass:// queue - a pointer, not an address. When the printer's Wi-Fi naps,
#   cups-browsed drops the device and EVERY later job dies with
#       "No destination host name supplied by cups-browsed for printer ..."
#       "Backend returned status 4 (stop printer)"      [CUPS error_log, jobs 26/27]
#   ...and CUPS leaves the queue DISABLED, so it never recovers alone.
#   This script uses a permanent non-browsed IPP queue and repairs it in place.
#
# It is idempotent; it only acts when the printer is actually reachable.
# checklist-printer.timer runs it every 3 min - that is also the keep-alive that
# stops the printer's radio from going back to sleep.
#
# VERIFY, DON'T ASSUME (README-FIRST sec.5 rule 6): every reachable probe records
# printer-state / state-reasons / ink, and a flush is only reported as CONFIRMED
# after the queue actually drains.
# ---------------------------------------------------------------------------
set -u
QUEUE="${QUEUE:-TazaHP}"
HOST="${HOST:-HP98E7F4760AB1.local}"
APP=/home/taza/checklist-app
SPOOL="$APP/spool"; SENT="$SPOOL/sent"
LOG="$APP/printer-selfheal.log"
mkdir -p "$SPOOL" "$SENT"
log(){ printf '%s %s\n' "$(date '+%F %T')" "$*" >>"$LOG"; }

reachable(){ timeout 3 bash -c "echo > /dev/tcp/$1/631" 2>/dev/null; }
is_ours(){ ipptool -tv "ipp://$1/ipp/print" get-printer-attributes.test 2>/dev/null | grep -qi 'DeskJet'; }
# health + paper + ink, so tomorrow's failure has evidence attached
health(){
  ipptool -tv "ipp://$1/ipp/print" get-printer-attributes.test 2>/dev/null \
    | grep -iE "printer-state \(|printer-state-reasons|marker-levels|impressions-completed" \
    | sed 's/^ *//' | tr '\n' '; '
}

# ---- 0. wake it (network standby; free if unsupported) ---------------------
python3 - <<'WOL' 2>/dev/null || true
import socket, binascii
mac = binascii.unhexlify("98e7f4760ab1")
pkt = b"\xff" * 6 + mac * 16
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
for _ in range(3):
    try: s.sendto(pkt, ("192.168.2.255", 9))
    except OSError: pass
WOL

# ---- 1. locate the printer -------------------------------------------------
IP=""
if command -v ippfind >/dev/null 2>&1; then
  u=$(timeout 8 ippfind --service _ipp._tcp 2>/dev/null | head -1)
  [ -n "$u" ] && IP=$(printf '%s' "$u" | sed -E 's#^ipp://([^:/]+).*#\1#')
fi
[ -z "$IP" ] && IP=$(getent hosts "$HOST" 2>/dev/null | awk '{print $1; exit}')
[ -z "$IP" ] && IP=$(lpstat -v "$QUEUE" 2>/dev/null | sed -E 's#.*ipp://([^/:]+).*#\1#')
if [ -z "$IP" ] || ! reachable "$IP" || ! is_ours "$IP"; then
  found=""
  if command -v nmap >/dev/null 2>&1; then          # sweep, but never grab the Zebra
    for h in $(nmap -sn -oG - 192.168.2.0/24 2>/dev/null | awk '/Up$/{print $2}'); do
      if reachable "$h" && is_ours "$h"; then found="$h"; break; fi
    done
  fi
  IP="$found"
fi
# ---- report a state CHANGE to the intercom (not every 3 minutes - that is noise) ----
STATE_FILE=/home/taza/checklist-app/.printer_state
prev=$(cat "$STATE_FILE" 2>/dev/null || echo unknown)
announce(){   # $1 = UP|DOWN, $2 = detail
  [ "$1" = "$prev" ] && return 0
  echo "$1" > "$STATE_FILE"
  timeout 15 psql -U taza -d tazaos -q -c \
    "select emit_event('ops.printer_state','printer_selfheal','printer','hp-deskjet-3700',
      'info', jsonb_build_object('state','$1','host','${IP:-unknown}','detail','$2'),
      gen_random_uuid(), '$prev', '$1', now())" >>"$LOG" 2>&1 || true
  log "intercom: printer $prev -> $1 ($2)"
}

if [ -z "$IP" ]; then
  log "printer not reachable - waiting (queue left as-is)"
  announce DOWN "not reachable on the LAN"
  exit 0
fi
log "printer reachable at $IP | $(health "$IP")"

# ---- what network is it on? (it must stay on "Taza") ----------------------
ssid=$(curl -s --compressed -m 6 "http://$IP/IoMgmt/Adapters" 2>/dev/null \
       | grep -oE '<wifi:SSID>[0-9a-fA-F]+' | head -1 | sed 's/.*>//')
[ -n "$ssid" ] && log "wifi: joined SSID '$(printf '%s' "$ssid" | xxd -r -p)' at $IP"

# ---- AirPrint capability (URF in the mDNS TXT = AirPrint) -----------------
ap=$(ipptool -tv "ipp://$IP/ipp/print" get-printer-attributes.test 2>/dev/null)
if printf '%s' "$ap" | grep -q 'image/urf\|AppleRaster\|application/urf'; then
  log "airprint: advertised (URF/AppleRaster present)"
else
  log "airprint: NOT advertised in printer attributes"
fi

# ---- is it refusing jobs until a HUMAN presses a button on the printer? ---
# This looks exactly like a network fault: IPP answers, state=idle,
# is-accepting=true, and every job is rejected "Print job was not accepted".
alert=$(printf '%s' "$ap" | grep -i 'printer-alert-description' | sed 's/.*= //')
case "$alert" in
  *calibrationRequired*|*artridge*)
     log "PANEL PROMPT: refusing jobs until someone presses a button ON THE PRINTER -> $alert" ;;
esac

# ---- 2. queue exists, enabled, pointing at it ------------------------------
cur=$(lpstat -v "$QUEUE" 2>/dev/null | sed -E 's#.*ipp://([^/:]+).*#\1#')
if [ -z "$cur" ]; then
  sudo lpadmin -p "$QUEUE" -E -v "ipp://$IP/ipp/print" -m everywhere \
       -D "Taza Checklist Printer (HP DeskJet 3700 series)" -o printer-is-shared=false \
       -o printer-error-policy=retry-job >>"$LOG" 2>&1
  log "created queue $QUEUE -> ipp://$IP/ipp/print"
elif [ "$cur" != "$IP" ]; then
  sudo lpadmin -p "$QUEUE" -v "ipp://$IP/ipp/print" >>"$LOG" 2>&1
  log "queue $QUEUE repointed $cur -> $IP"
fi
if ! lpstat -p "$QUEUE" 2>/dev/null | grep -q 'is idle\|now printing'; then
  sudo cupsenable "$QUEUE" >>"$LOG" 2>&1
  sudo cupsaccept "$QUEUE" >>"$LOG" 2>&1
  log "queue $QUEUE re-enabled (CUPS had disabled it)"
fi

# the browsed twin is the trap - keep anything from queuing into it
for q in HP_DeskJet_3700_series_760AB1 "HP_DeskJet_3700_series_760AB1@HP98E7F4760AB1.local"; do
  lpstat -p "$q" >/dev/null 2>&1 && sudo cupsreject "$q" >>"$LOG" 2>&1
done

# ---- 3. flush the spool ----------------------------------------------------
n=0
for p in "$SPOOL"/*.pdf; do
  [ -e "$p" ] || continue
  if lp -d "$QUEUE" -o media=na_letter_8.5x11in -o print-color-mode=monochrome \
        -t "CHECKLIST $(basename "$p" .pdf)" "$p" >>"$LOG" 2>&1; then
    mv "$p" "$SENT/"; n=$((n+1))
  else
    log "spool flush FAILED for $p"
  fi
done
[ "$n" -gt 0 ] && log "queued $n spooled checklist(s)"

# ---- 4. did it actually come out? confirm or report ------------------------
if lpstat -o "$QUEUE" 2>/dev/null | grep -q .; then
  log "STILL QUEUED: $(lpstat -o "$QUEUE" 2>/dev/null | wc -l) job(s) waiting - not yet confirmed"
else
  if [ "$n" -gt 0 ]; then
    sleep 5
    log "CONFIRMED: queue drained | $(health "$IP")"
  fi
fi
exit 0
announce UP "reachable at $IP"
