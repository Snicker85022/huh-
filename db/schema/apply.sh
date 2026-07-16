#!/usr/bin/env bash
# Apply the Taza OS schema to a PostgreSQL database, in dependency order.
#
# Usage:
#   DATABASE_URL=postgres://user@host/taza ./apply.sh
#   # or rely on libpq env vars (PGHOST/PGPORT/PGDATABASE/PGUSER)
#
# Idempotency: files use CREATE ... (not IF NOT EXISTS on every object), so this
# is intended for a FRESH database. To rebuild, drop and recreate the DB first.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PSQL=(psql -v ON_ERROR_STOP=1 -q)
[[ -n "${DATABASE_URL:-}" ]] && PSQL+=("$DATABASE_URL")

for f in "$DIR"/[0-9]*.sql; do
  echo ">> applying $(basename "$f")"
  "${PSQL[@]}" -f "$f"
done
echo "Taza OS schema applied."
