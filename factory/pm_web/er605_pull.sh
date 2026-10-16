#!/bin/sh
# Pull the LIVE ER605 snapshot from n100 (where the playwright env lives).
# Reads only. Never truncates the good copy: writes .tmp, validates, then swaps.
DEST=/home/taza/repo/factory/arch/er605_live.json
TMP="$DEST.tmp"
ssh -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=no taza@192.168.2.102 \
  '/home/taza/playwright-env/bin/python3 /home/taza/er605_live.py >/dev/null 2>&1; cat /home/taza/er605_live.json' \
  > "$TMP" 2>/dev/null
if [ -s "$TMP" ] && /usr/bin/python3 -c "import json;d=json.load(open('$TMP'));assert d.get('ok')" 2>/dev/null; then
  mv "$TMP" "$DEST"
  echo "$(date '+%F %T') pulled ok ($(wc -c < "$DEST") bytes)"
else
  echo "$(date '+%F %T') pull FAILED - kept previous snapshot"
fi
