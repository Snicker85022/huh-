#!/bin/bash
# Taza OS llama-gflip failover controller: graceful GPU<->CPU degradation
# canonical: /opt/taza/repo/scripts/llama-failover.sh
CONF=/etc/taza/ntfy.conf
[ -f "$CONF" ] && . "$CONF"
NTFY_URL=${NTFY_URL:-https://ntfy.sh}
NTFY_TOPIC=${NTFY_TOPIC:-taza-llama-alerts}
STATE=/var/lib/taza/llama-mode
LOG=/var/log/taza/llama-failover.log
ORIGGOV=/var/lib/taza/orig-governor
UNIT=llama-gflip.service
DROPIN=/etc/systemd/system/llama-gflip.service.d/failover-cpu.conf
GOVDIR=/sys/devices/system/cpu
NOTICE=/home/taza/.taza-ai-notice
WEB=/var/www/taza-status

mkdir -p /var/lib/taza /var/log/taza "$WEB"
log() { echo "$(date -Is) $*" | tee -a "$LOG" | logger -t llama-failover; }

ntfy() {
  if curl -sf --max-time 8 -H "Title: $1" -H "Priority: $2" -H "Tags: $3" -d "$4" "$NTFY_URL/$NTFY_TOPIC" >/dev/null 2>&1; then
    log "ntfy ok ($NTFY_URL/$NTFY_TOPIC): $1"
  elif [ -n "$NTFY_FALLBACK_URL" ] && curl -sf --max-time 8 -H "Title: $1" -H "Priority: $2" -H "Tags: $3" -d "$4" "$NTFY_FALLBACK_URL/$NTFY_FALLBACK_TOPIC" >/dev/null 2>&1; then
    log "ntfy ok fallback ($NTFY_FALLBACK_URL/$NTFY_FALLBACK_TOPIC): $1"
  else
    log "ntfy FAIL primary+fallback: $1"
  fi
}

get_mode() { [ -f "$STATE" ] && sed -n 's/^mode=//p' "$STATE" | head -1 || echo GPU; }

render_status() {
  case "$1" in
    GPU) c="#16a34a"; b="#dcfce7"; l="GPU - AMDVLK 52/17.5 t/s";;
    CPU) c="#d97706"; b="#fef3c7"; l="CPU FALLBACK 40/8.8 t/s";;
    DOWN) c="#dc2626"; b="#fee2e2"; l="DOWN";;
  esac
  printf '{"mode":"%s","since":"%s","reason":"%s","label":"%s","needs_root_cause":%s}\n' "$1" "$(date -Is)" "$2" "$l" "$([ "$1" = GPU ] && echo false || echo true)" > "$WEB/status.json"
  cat > "$WEB/index.html" <<H
<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="refresh" content="15"><title>Taza AI Status</title><style>body{font-family:system-ui;margin:0;background:#0f172a;color:#e2e8f0;height:100vh;display:flex;align-items:center;justify-content:center}.card{background:$b;color:#111827;border-radius:2rem;padding:4rem 6rem;text-align:center;box-shadow:0 0 80px ${c}66}.mode{font-size:6rem;font-weight:800;color:$c}.label{font-size:2rem;margin-top:1rem;color:$c}.reason{font-size:1.4rem;margin-top:2rem;color:#1f2937}.meta{font-size:1rem;margin-top:2rem;color:#4b5563}</style></head><body><div class="card"><div class="mode">$1</div><div class="label">$l</div><div class="reason">$2</div><div class="meta">since $(date -Is) - llama-gflip:8080 - refreshes every 15s</div></div></body></html>
H
  chmod 644 "$WEB/status.json" "$WEB/index.html"
}

write_state() {
  { echo "mode=$1"; echo "since=$(date -Is)"; echo "reason=$2"; echo "needs_root_cause=$([ "$1" = GPU ] && echo 0 || echo 1)"; } > "$STATE"
  chmod 644 "$STATE"
  render_status "$1" "$2"
  if [ "$1" = GPU ]; then
    rm -f "$NOTICE"
    ntfy "$4" default white_check_mark "$2"
  else
    printf 'ATTENTION: AI inference is in mode=%s.\nReason: %s\nGraceful degradation active. Root-cause session required before GPU restore.\nState: %s  Log: %s\n' "$1" "$2" "$STATE" "$LOG" > "$NOTICE"
    chmod 644 "$NOTICE"
    ntfy "$4" "$3" "$5" "$2"
  fi
}

set_governor() {
  for g in "$GOVDIR"/cpu*/cpufreq/scaling_governor; do
    [ -w "$g" ] || continue
    if [ "$1" = performance ]; then
      [ ! -f "$ORIGGOV" ] && cat "$g" > "$ORIGGOV" 2>/dev/null
      echo performance > "$g" 2>/dev/null
    else
      [ -f "$ORIGGOV" ] && cat "$ORIGGOV" > "$g" 2>/dev/null
    fi
  done
}

to_cpu() {
  log "GPU->CPU: $1"
  printf '[Service]\nExecStart=\nExecStart=/home/taza/llama.cpp/build/bin/llama-server -m /home/taza/models/Qwen3-30B-A3B-Q4_K_M.gguf -c 8192 --port 8080 --host 0.0.0.0 -t 16 -ngl 0\n' > "$DROPIN"
  systemctl daemon-reload
  set_governor performance
  systemctl restart "$UNIT"
  write_state CPU "$1" high "Taza AI: GPU failed - CPU fallback active" warning
}

to_gpu() {
  log "CPU->GPU: $1"
  rm -f "$DROPIN"
  systemctl daemon-reload
  systemctl restart "$UNIT"
  set_governor restore
  write_state GPU "$1" default "Taza AI: back on GPU" white_check_mark
}

case "${1:-status}" in
  status) echo "mode=$(get_mode)"; [ -f "$STATE" ] && cat "$STATE";;
  cpu) to_cpu "${2:-manual switch to CPU}";;
  gpu) to_gpu "${2:-manual restore to GPU}";;
  down)
    log "DOWN: ${2:-manual}"
    systemctl stop "$UNIT" 2>/dev/null
    write_state DOWN "${2:-CPU mode also failed - service stopped}" urgent "Taza AI: DOWN" skull
    ;;
  recover)
    [ "$(get_mode)" = GPU ] && { echo "already GPU"; exit 0; }
    log "daily GPU recovery attempt"
    to_gpu "daily recovery attempt"
    sleep 75
    if curl -sf -m 5 http://127.0.0.1:8080/health | grep -q '"status":"ok"'; then
      log "recovery SUCCESS"
    else
      log "recovery failed, back to CPU"
      to_cpu "daily recovery attempt failed"
    fi
    ;;
  *) echo "usage: llama-failover.sh {status|cpu|gpu|down|recover}" >&2; exit 1;;
esac
