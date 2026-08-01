#!/bin/bash
# Taza OS llama-gflip watchdog: health check + graceful failover
# canonical: /opt/taza/repo/scripts/llama-watchdog.sh
UNIT=llama-gflip.service
STATE=/var/lib/taza/llama-mode
FCOUNT=/var/lib/taza/llama-fail-count
THRESHOLD=3

[ -f "$STATE" ] || echo "mode=GPU" > "$STATE"
systemctl is-active --quiet "$UNIT" || exit 0

pid=$(systemctl show -p MainPID --value "$UNIT")
age=$(ps -o etimes= -p "$pid" 2>/dev/null | tr -d ' ')
[ -n "$age" ] && [ "$age" -lt 90 ] && exit 0

if curl -sf -m 5 http://127.0.0.1:8080/health 2>/dev/null | grep -q '"status":"ok"'; then
  echo 0 > "$FCOUNT"; exit 0
fi

cnt=$(cat "$FCOUNT" 2>/dev/null || echo 0); cnt=$((cnt+1)); echo "$cnt" > "$FCOUNT"
mode=$(sed -n 's/^mode=//p' "$STATE" | head -1)
logger -t llama-watchdog "unhealthy ($cnt/$THRESHOLD) mode=$mode"

if [ "$cnt" -ge "$THRESHOLD" ]; then
  echo 0 > "$FCOUNT"
  if [ "$mode" = GPU ]; then
    /usr/local/bin/llama-failover.sh cpu "GPU unhealthy after $cnt checks -> graceful CPU fallback"
  elif [ "$mode" = CPU ]; then
    /usr/local/bin/llama-failover.sh down "CPU mode also unhealthy after $cnt checks"
  fi
else
  logger -t llama-watchdog "restart attempt $cnt/$THRESHOLD"
  systemctl restart "$UNIT" 2>/dev/null
fi

for pid in $(pgrep -f 'llama-benc[h]' 2>/dev/null); do
  secs=$(ps -o etimes= -p "$pid" 2>/dev/null | tr -d ' ')
  if [ -n "$secs" ] && [ "$secs" -gt 600 ]; then
    logger -t llama-watchdog "reaping stale llama-bench pid $pid"
    kill "$pid" 2>/dev/null
  fi
done
