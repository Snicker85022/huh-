#!/bin/bash
# Step B2 (NEW, required before the recreate): restore ownership of the bind mounts.
#
# Why: while UID/GID were blank, the containers ran as root (uid 0) - and mongod's
# entrypoint dropped to uid 999, so ./data-node is now 999:999, and ./logs,
# ./uploads, ./images and ./meili_data_v1.35.1 are root:root. Verified:
#   uid 1000 CANNOT write data-node / meili_data / uploads
# So patching .env alone and recreating would make mongod and meilisearch fail to
# start (non-root containers cannot chown, and their entrypoints skip the uid drop).
#
# Order: this script STOPS the stack first, so nothing can create fresh 999/root-owned
# files between the chown and the recreate. Step 5 (`docker compose up -d`) restarts
# everything afterwards.
#
# Usage:  fix-bind-mount-ownership.sh            # dry run: census + planned actions
#         sudo fix-bind-mount-ownership.sh --apply
set -euo pipefail

STACK_DIR=/home/taza/librechat
OWNER=1000:1000
DIRS="data-node meili_data_v1.35.1 logs uploads images skill"
APPLY=0
case "${1:-}" in
  --apply) APPLY=1 ;;
  --dry-run|"") ;;
  *) echo "usage: $0 [--dry-run|--apply]"; exit 2 ;;
esac

echo "=== current ownership census ==="
total=0
for d in $DIRS; do
  p="$STACK_DIR/$d"
  [ -e "$p" ] || { printf "  %-22s MISSING\n" "$d"; continue; }
  n=$( { find "$p" -xdev -not -type l ! -user 1000 -printf '.' 2>/dev/null || true; } | wc -c)
  m=$( { find "$p" -xdev -not -type l ! -group 1000 -printf '.' 2>/dev/null || true; } | wc -c)
  total=$((total + n + m))
  printf "  %-22s not owned by uid 1000: %-5s  not group 1000: %-5s  (dir: %s)\n" \
     "$d" "$n" "$m" "$(stat -c '%U:%G' "$p")"
done
echo "  ---> total entries needing chown (approx, uw+g combined): $total"

if [ "$APPLY" -ne 1 ]; then
  echo
  echo "DRY RUN - nothing stopped, nothing changed."
  echo "On --apply this script will:"
  echo "  1. cd $STACK_DIR && docker compose stop"
  echo "  2. chown -R $OWNER on: $DIRS"
  echo "  3. re-verify write access as uid 1000, then exit (step 5 does 'docker compose up -d')"
  exit 0
fi

[ "$(id -u)" -eq 0 ] || { echo "FATAL: --apply must run as root (sudo)"; exit 1; }

echo
echo "=== stopping stack so no new uid-999/root files appear ==="
( cd "$STACK_DIR" && docker compose stop ) || { echo "FATAL: docker compose stop failed"; exit 1; }

echo "=== chown -R $OWNER ==="
for d in $DIRS; do
  p="$STACK_DIR/$d"
  [ -e "$p" ] || continue
  chown -R -h "$OWNER" "$p"
  printf "  %-22s now %s (%s entries)\n" "$d" "$(stat -c '%U:%G' "$p")" \
     "$( { find "$p" -xdev -printf '.' 2>/dev/null || true; } | wc -c)"
done

echo
echo "=== verification: uid 1000 write access ==="
ok=1
for d in $DIRS; do
  p="$STACK_DIR/$d"
  [ -e "$p" ] || continue
  if setpriv --reuid=1000 --regid=1000 --clear-groups test -w "$p" 2>/dev/null; then
    printf "  %-22s writable by uid 1000: YES\n" "$d"
  else
    printf "  %-22s writable by uid 1000: NO   <-- fix before 'docker compose up -d'\n" "$d"
    ok=0
  fi
done
echo
echo "=== remaining root/999-owned entries in the mounts ==="
find $STACK_DIR/data-node $STACK_DIR/meili_data_v1.35.1 $STACK_DIR/logs \
     $STACK_DIR/uploads $STACK_DIR/images $STACK_DIR/skill \
     -xdev ! -user 1000 -printf '%u:%g %p\n' 2>/dev/null | head -10 || true

if [ "$ok" -eq 1 ]; then
  echo
  echo "OK: ownership restored. Stack is STOPPED - now run step 5:"
  echo "  cd $STACK_DIR && docker compose up -d"
else
  echo
  echo "WARNING: some dirs are still not writable by uid 1000 - do NOT start the stack yet."
  exit 1
fi
