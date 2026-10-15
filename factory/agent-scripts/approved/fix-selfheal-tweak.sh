#!/bin/bash
# Step E (Fix 5): self-heal hardening - two approved changes.
# The target script is root-owned, so --apply needs sudo:
#   sudo /home/taza/agent-scripts/pending/fix-selfheal-tweak.sh --apply
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
"$HERE/patch_selfheal.py" "$@"
