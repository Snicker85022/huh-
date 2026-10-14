#!/bin/bash
# Taza OS one-shot ntfy reminder: surfaces Nick's backlog items
# canonical: /opt/taza/repo/scripts/taza-ntfy-reminder.sh
CONF=/etc/taza/ntfy.conf
[ -f "$CONF" ] && . "$CONF"
NTFY_URL=${NTFY_URL:-https://ntfy.sh}
NTFY_TOPIC=${NTFY_TOPIC:-taza-ops}
mkdir -p /var/log/taza
case "${1:---fire}" in
  --test)
    TITLE="Taza OS: reminder channel test"; TAG=test_tube
    MSG="[test] ntfy reminder channel works. Real backlog nudge scheduled 2026-08-08 09:00 Phoenix."
    ;;
  --fire)
    TITLE="Taza OS: backlog reminder"; TAG=bell
    MSG="Backlog nudge: reduce daily ntfy notification noise (requested 2026-08-01). Details: /opt/taza/repo/TODO.md. Also pending: ntfy.sh quota vs self-hosted primary decision."
    ;;
  *) echo "usage: $0 [--test|--fire]" >&2; exit 1;;
esac
if curl -sf --max-time 8 -H "Title: $TITLE" -H "Priority: default" -H "Tags: $TAG" -d "$MSG" "$NTFY_URL/$NTFY_TOPIC" >/dev/null 2>&1; then
  echo "$(date -Is) ok ($NTFY_URL/$NTFY_TOPIC): $TITLE" | tee -a /var/log/taza/reminder.log
elif [ -n "$NTFY_FALLBACK_URL" ] && curl -sf --max-time 8 -H "Title: $TITLE" -H "Priority: default" -H "Tags: $TAG" -d "$MSG" "$NTFY_FALLBACK_URL/$NTFY_FALLBACK_TOPIC" >/dev/null 2>&1; then
  echo "$(date -Is) ok fallback ($NTFY_FALLBACK_URL/$NTFY_FALLBACK_TOPIC): $TITLE" | tee -a /var/log/taza/reminder.log
else
  echo "$(date -Is) FAIL: $TITLE" | tee -a /var/log/taza/reminder.log
fi
