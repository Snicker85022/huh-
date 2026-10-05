#!/usr/bin/env bash
# Respawnable sync daemon: master-urs.md -> NocoDB every 335s.
# Single-instance via flock; respawned at boot by the taza @reboot crontab.
LOCK=/tmp/murs-nocodb-daemon.lock
exec 9>"$LOCK"
flock -n 9 || exit 0

LOG=/tmp/murs-nocodb-daemon.log
echo "[$(date '+%F %T')] daemon start (pid $$)" >> "$LOG"
while true; do
  /usr/bin/python3 /home/taza/repo/tools/sync-murs-to-nocodb.py >> "$LOG" 2>&1
  sleep 335
done
