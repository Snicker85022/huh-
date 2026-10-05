#!/usr/bin/env bash

# DISARMED 2026-10-04 by decision D37. NocoDB is retired and its 144 metadata
# tables were dropped from tazaos. This daemon would sync markdown into a store
# that no longer exists. Refuses to run unless MURS_NOCODB_FORCE=1 is set.
[ -n "${MURS_NOCODB_FORCE:-}" ] || {
  echo "DISARMED: NocoDB retired 2026-10-04 (D37). Set MURS_NOCODB_FORCE=1 to override."
  exit 1
}
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
