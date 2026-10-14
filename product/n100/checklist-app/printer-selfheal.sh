#!/bin/bash
# ---------------------------------------------------------------------------
# Taza checklist print path self-heal -- n100, USB-first.   (v2, 2026-10-14)
#
# WHY v2 EXISTS (D101 step 2c): v1 (2026-10-08) healed the printer over Wi-Fi
# (192.168.2.118, then a lease at 192.168.2.123). Both addresses are dead: the
# radio naps and the DHCP lease moves. The HP cable moved to n100 on
# 2026-10-13, ipp-usb publishes the device at ipp://localhost:60000/ipp/print,
# and queue TazaHP-USB points at it (D101). D84 makes TazaHP-USB PRIMARY and
# the Wi-Fi queue TazaHP the FALLBACK member, so the print target is the CLASS
# "Checklist" -- never a bare queue.
# v1 also appended ~5 lines every 3 min (~2400 lines/day, 1.2 MB of log, every
# line inside a months-long DOWN). v2 writes to the log only when the state
# CHANGES, plus one heartbeat a day.
#
# HOW A CLASS PICKS A MEMBER (measured 2026-10-13 with zero-paper probe
# classes): CUPS tries the LAST-added member FIRST. TazaHP-USB must therefore
# be added LAST. classes.conf lists members in add-order, so the LAST Member
# line of the class is the printer tried first; this script rebuilds the list
# when that is not TazaHP-USB.
#
#   USB   (primary) : TazaHP-USB -> ipp://localhost:60000/ipp/print (ipp-usb)
#   Wi-Fi (fallback): TazaHP     -> ipp://<lan-ip>/ipp/print
#
# Idempotent. Only touches what it has just probed OK. Removes nothing.
#
# Test knobs (README-FIRST sec.5 rule 6 -- verify, don't assume):
#   APP, USB_URI, USB_QUEUE, LAN_QUEUE, CLASS, DEST, SPOOL,
#   PROBE_ONLY=1   probe and log only, mutate nothing.
#   NO_INTERCOM=1  do not emit a state-change event (tests only)
#   MEDIA=         media for the spool flush (empty = queue default)
# ---------------------------------------------------------------------------
set -u

APP="${APP:-/home/taza/checklist-app}"
USB_URI="${USB_URI:-ipp://localhost:60000/ipp/print}"
USB_QUEUE="${USB_QUEUE:-TazaHP-USB}"
LAN_QUEUE="${LAN_QUEUE:-TazaHP}"
CLASS="${CLASS:-Checklist}"
DEST="${DEST:-$CLASS}"
MEDIA="${MEDIA:-na_letter_8.5x11in}"
SPOOL="${SPOOL:-$APP/spool}"
PROBE_ONLY="${PROBE_ONLY:-0}"
LAN_HOST="${LAN_HOST:-HP98E7F4760AB1.local}"
LAN_NET="${LAN_NET:-192.168.2.0/24}"
LOG="$APP/printer-selfheal.log"
STATE_FILE="$APP/.printer_state"
PATH_FILE="$APP/.printer_path"
SWEEP_STAMP="$APP/.lan_sweep"
LOG_MAX=524288

mkdir -p "$SPOOL" "$SPOOL/sent" "$APP/archive-log"
log(){ printf '%s %s\n' "$(date '+%F %T')" "$*" >>"$LOG"; }
if [ "$PROBE_ONLY" = "1" ]; then MUTATE=0; else MUTATE=1; fi
NO_INTERCOM="${NO_INTERCOM:-0}"

# ---- the log stays small: archive it, never delete it ---------------------
if [ -s "$LOG" ] && [ "$(stat -c %s "$LOG")" -gt "$LOG_MAX" ]; then
  mv "$LOG" "$APP/archive-log/printer-selfheal.log.$(date '+%Y%m%d-%H%M%S')"
  log "log rotated past ${LOG_MAX}B -- previous log kept in archive-log/"
fi

probe(){ timeout 6 ipptool -tv "$1" get-printer-attributes.test >/dev/null 2>&1; }
is_ours(){ ipptool -tv "ipp://$1/ipp/print" get-printer-attributes.test 2>/dev/null | grep -qi 'DeskJet'; }
health(){ ipptool -tv "$1" get-printer-attributes.test 2>/dev/null \
  | grep -iE 'printer-state \(|printer-state-reasons|marker-levels|printer-alert-description' \
  | sed 's/^ *//' | tr '\n' '; '; }

wol(){                      # only worth it on the Wi-Fi fallback path
python3 - <<'WOL' 2>/dev/null || true
import socket, binascii
mac = binascii.unhexlify("98e7f4760ab1")            # HP DeskJet 3700 [760AB1]
pkt = b"\xff" * 6 + mac * 16
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
for _ in range(3):
    try: s.sendto(pkt, ("192.168.2.255", 9))
    except OSError: pass
WOL
}

lan_ip(){
  local u
  if command -v ippfind >/dev/null 2>&1; then
    u=$(timeout 8 ippfind --service _ipp._tcp 2>/dev/null | head -1)
    if [ -n "$u" ]; then printf '%s' "$u" | sed -E 's#^ipp?s?://([^:/]+).*#\1#'; return 0; fi
  fi
  getent hosts "$LAN_HOST" 2>/dev/null | awk '{print $1; exit}'
}

sweep(){                    # full /24 sweep, at most every 30 min, never takes the Zebra
  local now last h
  now=$(date +%s); last=$(cat "$SWEEP_STAMP" 2>/dev/null || echo 0)
  if [ $((now - last)) -lt 1800 ]; then return 1; fi
  echo "$now" > "$SWEEP_STAMP"
  command -v nmap >/dev/null 2>&1 || return 1
  for h in $(nmap -sn -oG - "$LAN_NET" 2>/dev/null | awk '/Up$/{print $2}'); do
    if timeout 2 bash -c "echo > /dev/tcp/$h/631" 2>/dev/null && is_ours "$h"; then
      printf '%s' "$h"; return 0
    fi
  done
  return 1
}

intercom(){   # $1 = from-state, $2 = to-state, $3 = detail
  # ops.printer_state is a STRICT registered topic: source_module printer_selfheal,
  # entity_type printer, payload_required {state,host,detail}, to_states {UP,DOWN},
  # correlation required, must transition. Anything else is rejected by validate_event().
  [ "$NO_INTERCOM" = "1" ] && return 0
  local out
  out=$(timeout 15 psql -U taza -d tazaos -qt -v ON_ERROR_STOP=1 -c \
    "select emit_event('ops.printer_state','printer_selfheal','printer','hp-deskjet-3700',\
'info', jsonb_build_object('state','$2','host','${DEV_URI:-$USB_URI}','detail','$3'),\
gen_random_uuid(), '$1', '$2', now())" 2>&1) || \
    log "intercom REJECTED ($1 -> $2): $(printf '%s' "$out" | tr '\n' ' ' | cut -c1-300)"
}

# ---- 1. probe the USB path first, then the LAN fallback -------------------
PATH_LABEL=none; DEV_URI=""; IP=""; HEALTH=""

if probe "$USB_URI"; then
  PATH_LABEL=USB; DEV_URI="$USB_URI"
else
  wol
  IP=$(lan_ip)
  case "$IP" in 127.*|"") IP="";; esac
  if [ -n "$IP" ]; then
    for o in $(hostname -I 2>/dev/null); do [ "$o" = "$IP" ] && IP=""; done
  fi
  if [ -z "$IP" ] || ! is_ours "$IP"; then IP=$(sweep) || IP=""; fi
  if [ -n "$IP" ] && is_ours "$IP"; then
    PATH_LABEL=LAN; DEV_URI="ipp://$IP/ipp/print"
  fi
fi
[ "$PATH_LABEL" != none ] && HEALTH=$(health "$DEV_URI")

# ---- 2. state change? that is the only thing worth logging ----------------
STATE=DOWN
if [ "$PATH_LABEL" != none ]; then STATE=UP; DETAIL="$PATH_LABEL $DEV_URI"; else DETAIL="USB $USB_URI and the LAN both unreachable"; fi
prevc=$(cat "$STATE_FILE" 2>/dev/null || echo unknown)
printf '%s\n' "$STATE" > "$STATE_FILE"
printf '%s\n' "$PATH_LABEL" > "$PATH_FILE"

if [ "$STATE" != "$prevc" ]; then
  if [ "$STATE" = UP ]; then
    log "printer UP via $PATH_LABEL ($DEV_URI) | $HEALTH"
  else
    log "printer DOWN: $DETAIL"
  fi
  log "intercom: printer $prevc -> $STATE ($DETAIL)"
  intercom "$prevc" "$STATE" "$DETAIL"
  if [ "$STATE" = DOWN ]; then exit 0; fi
else
  today=$(date '+%F'); lastlog=$(date -r "$LOG" '+%F' 2>/dev/null || echo "")
  if [ "$lastlog" != "$today" ]; then
    log "heartbeat: $STATE via $PATH_LABEL | $HEALTH"
  fi
fi

if [ "$MUTATE" = "0" ]; then
  log "PROBE_ONLY: no changes made (path=$PATH_LABEL state=$STATE)"
  exit 0
fi

# ---- 3. the queue that serves the ACTIVE path: exists, enabled, points here
Q="$USB_QUEUE"; U="$USB_URI"
if [ "$PATH_LABEL" = LAN ]; then Q="$LAN_QUEUE"; U="$DEV_URI"; fi
cur=$(lpstat -v "$Q" 2>/dev/null | sed -E 's#^device for [^:]*: ##')
if [ -z "$cur" ]; then
  sudo lpadmin -p "$Q" -E -v "$U" -m everywhere \
       -D "Taza Checklist Printer (HP DeskJet 3700 series)" -o printer-is-shared=false \
       -o printer-error-policy=retry-job >>"$LOG" 2>&1
  log "created queue $Q -> $U"
elif [ "$cur" != "$U" ]; then
  sudo lpadmin -p "$Q" -v "$U" >>"$LOG" 2>&1
  log "queue $Q repointed $cur -> $U"
fi
if ! lpstat -p "$Q" 2>/dev/null | grep -qE 'is idle|now printing|printing'; then
  sudo cupsenable "$Q" >>"$LOG" 2>&1
  sudo cupsaccept "$Q" >>"$LOG" 2>&1
  log "queue $Q re-enabled (CUPS had disabled it)"
fi

# ---- 4. class: exists, enabled, and USB is the LAST member (tried first) ---
class_members(){   # live member list, in the order cupsd holds it (from lpstat, not classes.conf)
  lpstat -c "$CLASS" 2>/dev/null | tail -n +2 | tr -d '\t ' | paste -sd' ' -
}
first_tried(){   # the LAST member CUPS lists for the class is the member it tries FIRST
  # Read it from the RUNNING cupsd (lpstat), not from classes.conf: cupsd writes
  # classes.conf lazily, so right after an lpadmin change the file is stale and the
  # script would think a broken class was fine (measured 2026-10-14, D101 step 2c).
  local m
  m=$(lpstat -c "$CLASS" 2>/dev/null | tail -1 | tr -d '\t ')
  if [ -z "$m" ] || [ "$m" = : ]; then
    m=$(sudo awk -v c="$CLASS" '$0 == "<Class " c ">" {f=1; next} /^<\/Class>/ {f=0} f && /^Printer / {m=$2} END {if (m) print m}' /etc/cups/classes.conf 2>/dev/null)
  fi
  printf '%s' "$m"
}
if [ -z "$(lpstat -c "$CLASS" 2>/dev/null)" ]; then
  sudo lpadmin -p "$LAN_QUEUE" -c "$CLASS" >>"$LOG" 2>&1
  sudo lpadmin -p "$USB_QUEUE" -c "$CLASS" >>"$LOG" 2>&1
  log "created class $CLASS ($LAN_QUEUE then $USB_QUEUE)"
fi
# D84 contract: the class is exactly "$LAN_QUEUE $USB_QUEUE" - USB last, so USB is
# tried first and the Wi-Fi queue is the fallback. Anything else gets rebuilt.
was=$(class_members)
if [ "$was" != "$LAN_QUEUE $USB_QUEUE" ]; then
  for m in "$LAN_QUEUE" "$USB_QUEUE"; do sudo lpadmin -p "$m" -r "$CLASS" >/dev/null 2>&1 || true; done
  sudo lpadmin -p "$LAN_QUEUE" -c "$CLASS" >>"$LOG" 2>&1
  sudo lpadmin -p "$USB_QUEUE" -c "$CLASS" >>"$LOG" 2>&1
  log "class $CLASS rebuilt to [$LAN_QUEUE $USB_QUEUE] (last = tried first); was [$was]"
fi
sudo cupsenable "$CLASS" >>"$LOG" 2>&1
sudo cupsaccept "$CLASS" >>"$LOG" 2>&1

# ---- 5. flush the spool ----------------------------------------------------
n=0
for p in "$SPOOL"/*.pdf; do
  [ -e "$p" ] || continue
  opts=()
  [ -n "$MEDIA" ] && opts=("-o" "media=$MEDIA")
  if lp -d "$DEST" "${opts[@]}" -o print-color-mode=monochrome \
        -t "CHECKLIST $(basename "$p" .pdf)" "$p" >>"$LOG" 2>&1; then
    mv "$p" "$SPOOL/sent/"; n=$((n+1))
  else
    log "spool flush FAILED for $p"
  fi
done
[ "$n" -gt 0 ] && log "queued $n spooled checklist(s) to $DEST"

# ---- 6. did it actually come out? confirm, or say so ----------------------
if lpstat -o "$DEST" 2>/dev/null | grep -q .; then
  log "STILL QUEUED: $(lpstat -o "$DEST" 2>/dev/null | wc -l) job(s) on $DEST - not yet confirmed"
elif [ "$n" -gt 0 ]; then
  sleep 5
  log "CONFIRMED: $DEST drained | $HEALTH"
fi
exit 0
