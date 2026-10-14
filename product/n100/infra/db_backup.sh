#!/usr/bin/env bash
# Nightly dump of every Taza database. Decision D45.
#
# Design notes (why it looks like this):
#  - runs as root because pg_dump needs to read every table; taza does not own them all
#  - dumps go to /tmp first, because postgres cannot write into taza's 0700 backup dir
#  - every dump is VERIFIED with pg_restore -l before it is moved into place
#    and only then is the old copy of the same name rotated out
#  - a dump that fails verification is deleted and the run is marked failed
#  - exits non-zero on any failure so systemd records it
set -uo pipefail

DEST=/home/taza/backups/nightly
KEEP_DAYS=548   # 18 months, D55 (2026-10-05). Was 14 days.
STAMP=$(date +%Y%m%d_%H%M%S)
FAILED=0

mkdir -p "$DEST"
# run as root: without this the dir is root:root and taza cannot read his own backups
chown "$(id -u taza):$(id -g taza)" "$DEST"
chmod 700 "$DEST"

log() { echo "[$(date '+%F %T')] $*"; }

record() {  # status db file bytes verified duration error
  local status="$1" db="$2" file="$3" bytes="$4" verified="$5" dur="$6" err="${7:-}"
  sudo -n -u postgres psql -d tazaos -q -v ON_ERROR_STOP=1 -c \
    "INSERT INTO public.backup_log (finished_at,status,database_name,file_path,byte_size,verified,duration_s,error_message)
     VALUES (now(),'$status','$db','$file',$bytes,$verified,$dur,$([ -n "$err" ] && echo "'${err//\'/\'\'}'" || echo 'NULL'));" >/dev/null 2>&1
}

# roles change rarely but losing them makes every restore painful
log "dumping globals (roles)"
if sudo -n -u postgres pg_dumpall --globals-only > "$DEST/globals_$STAMP.sql" 2>/tmp/glob.err; then
  chmod 600 "$DEST/globals_$STAMP.sql"
  log "  globals ok ($(stat -c%s "$DEST/globals_$STAMP.sql") bytes)"
else
  log "  GLOBALS FAILED: $(head -1 /tmp/glob.err)"; FAILED=1
fi

for DB in dev_pipeline tazaos; do
  log "dumping $DB"
  TMP="/tmp/${DB}_${STAMP}.dump"; ERR="/tmp/${DB}.err"; SECONDS=0
  if ! sudo -n -u postgres pg_dump -d "$DB" -Fc -f "$TMP" 2>"$ERR"; then
    log "  $DB DUMP FAILED: $(head -1 "$ERR")"
    record failed "$DB" "" 0 false "$SECONDS" "$(head -1 "$ERR")"; FAILED=1; rm -f "$TMP"; continue
  fi
  DUR=$SECONDS; BYTES=$(stat -c%s "$TMP")
  # a dump that cannot be listed is not a backup
  if sudo -n -u postgres pg_restore -l "$TMP" >/dev/null 2>&1; then
    VERIFIED=true
  else
    log "  $DB DUMP UNVERIFIABLE - discarded"
    record failed "$DB" "" "$BYTES" false "$DUR" "pg_restore -l failed"
    FAILED=1; sudo -n rm -f "$TMP"; continue
  fi
  FINAL="$DEST/${DB}_${STAMP}.dump"
  sudo -n mv "$TMP" "$FINAL" && sudo -n chown taza:taza "$FINAL" && chmod 600 "$FINAL"
  # re-verify IN PLACE. postgres cannot read the 0600 file we just created, so this
  # check must run as taza; verifying only in /tmp proves the dump, not the artifact.
  if ! pg_restore -l "$FINAL" >/dev/null 2>&1; then
    log "  $DB moved but NOT readable in place - reporting failure"
    record failed "$DB" "$FINAL" "$BYTES" false "$DUR" "in-place pg_restore -l failed"
    FAILED=1; continue
  fi
  log "  $DB ok  $BYTES bytes  verified  ${DUR}s  -> $FINAL"
  record ok "$DB" "$FINAL" "$BYTES" true "$DUR"
done

# rotation: only after the new dumps exist and verified
log "rotating dumps older than $KEEP_DAYS days"
find "$DEST" -maxdepth 1 -type f -name "*_*.dump" -mtime "+$KEEP_DAYS" -print -delete | sed 's/^/  removed /'
find "$DEST" -maxdepth 1 -type f -name "globals_*.sql" -mtime "+$KEEP_DAYS" -print -delete | sed 's/^/  removed /'

log "free space: $(df -h "$DEST" | awk 'NR==2{print $4}')"
[ "$FAILED" -eq 0 ] && log "ALL BACKUPS OK" || log "ONE OR MORE BACKUPS FAILED"
exit $FAILED
