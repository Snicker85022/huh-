#!/bin/bash
# Step B (Fix 1b): restore UID/GID in /home/taza/librechat/.env
#
# Regression of the 2026-10-11 root cause: docker-compose.yml uses
#   user: "${UID}:${GID}"   (api, mongodb, meilisearch)
# With UID/GID commented out, compose substitutes an empty string, containers
# come up as root (uid=0), and bind-mounted dirs (./logs, ./uploads, ./images)
# get root-owned files. Verified live: docker exec <c> id -> uid=0(root) in all
# four containers; 86 root-owned files in the three bind mounts.
#
# Usage:  fix-env-uid-gid.sh              # dry run: show diff, change nothing
#         fix-env-uid-gid.sh --apply      # backup + patch + verify
set -euo pipefail

ENV_FILE=/home/taza/librechat/.env
STACK_DIR=/home/taza/librechat
APPLY=0
case "${1:-}" in
  --apply) APPLY=1 ;;
  --dry-run|"") ;;
  *) echo "usage: $0 [--dry-run|--apply]"; exit 2 ;;
esac

[ -f "$ENV_FILE" ] || { echo "FATAL: $ENV_FILE missing"; exit 1; }
[ -w "$ENV_FILE" ] || { echo "FATAL: $ENV_FILE not writable by $(id -un)"; exit 1; }

if grep -qx 'UID=1000' "$ENV_FILE" && grep -qx 'GID=1000' "$ENV_FILE"; then
  echo "ALREADY APPLIED: uncommented UID=1000 / GID=1000 already present. Nothing to do."
  exit 0
fi
grep -qx '# UID=1000' "$ENV_FILE" || { echo "FATAL: exact line '# UID=1000' not found - refusing to guess"; exit 1; }
grep -qx '# GID=1000' "$ENV_FILE" || { echo "FATAL: exact line '# GID=1000' not found - refusing to guess"; exit 1; }

tmp=$(mktemp); trap 'rm -f "$tmp"' EXIT
sed -e 's/^# UID=1000$/UID=1000/' -e 's/^# GID=1000$/GID=1000/' "$ENV_FILE" > "$tmp"

# safety: exactly 2 lines changed (< and > pairs => 4 diff lines)
changed=$(diff "$ENV_FILE" "$tmp" | grep -c '^[<>]' || true)
if [ "$changed" -ne 4 ]; then
  echo "FATAL: expected exactly 4 diff lines (2 removed + 2 added), got $changed - aborting"; exit 1
fi
before_lines=$(wc -l < "$ENV_FILE"); after_lines=$(wc -l < "$tmp")
if [ "$before_lines" -ne "$after_lines" ]; then
  echo "FATAL: line count changed ($before_lines -> $after_lines) - aborting"; exit 1
fi

echo "=== $(basename "$ENV_FILE") before/after (context lines 95-106) ==="
diff -u "$ENV_FILE" "$tmp" | sed -n '1,40p' || true
echo
echo "=== all UID/GID lines in patched file ==="
grep -nE '^(# )?(UID|GID)=' "$tmp"

if [ "$APPLY" -eq 1 ]; then
  backup="$ENV_FILE.bak-uidgid-$(date +%Y%m%d-%H%M%S)"
  cp -p "$ENV_FILE" "$backup"
  cat "$tmp" > "$ENV_FILE"          # in-place: preserves inode, owner, mode
  echo
  echo "APPLIED. backup=$backup"
  echo "=== verification: compose now resolves a real user for 3 services ==="
  ( cd "$STACK_DIR" && docker compose config 2>/dev/null | grep -nE '^[[:space:]]+user:' ) || true
  echo "=== any remaining blank-UID warnings? (expect none) ==="
  ( cd "$STACK_DIR" && docker compose config >/dev/null ) 2>&1 | grep -i 'UID\|GID' || echo "  none"
  echo
  echo "NOTE: running containers are still root until 'docker compose up -d' recreates them."
else
  echo
  echo "DRY RUN - nothing written. Re-run with --apply to patch."
fi
