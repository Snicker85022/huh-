"""notify_nick(): thin ntfy wrapper per spec 06.

Signature/docstring verbatim from specs/06_output_interaction_rules.md.
Channel logic follows the proven llama-failover.sh pattern (specs/llama-gflip-
failover.md): primary ntfy.sh, on any non-success fall back to the self-hosted
n100:2586 instance, so a quota 429 on the primary never drops an alert. Fires
exactly once per call - one primary attempt, then at most one fallback attempt.

URLs from /etc/taza/ntfy.conf (canonical: repo/scripts/taza-ntfy.conf):
  NTFY_URL=https://ntfy.sh  NTFY_TOPIC=taza-ops
  NTFY_FALLBACK_URL=http://192.168.2.102:2586  NTFY_FALLBACK_TOPIC=taza-llama-alerts
"""

import urllib.error
import urllib.request

PRIMARY_BASE = "https://ntfy.sh"
FALLBACK_URL = "http://192.168.2.102:2586/taza-llama-alerts"
TIMEOUT_SECONDS = 8  # same as llama-failover.sh's curl --max-time 8

# urgency -> ntfy X-Priority, mirroring llama-failover.sh's own priorities:
# pause = Band 1 (Pause-for-Nick) -> urgent; inform = Band 2 -> default.
PRIORITY_MAP = {"pause": "urgent", "inform": "default"}


def _post(url: str, message: str, urgency: str, sequence_id=None, tags=None) -> int:
    """POST message to an ntfy endpoint. Returns the HTTP status code;
    0 on connection-level failure (curl -sf semantics: any non-success
    counts as a failed attempt, so the fallback chain engages)."""
    req = urllib.request.Request(url, data=message.encode("utf-8"), method="POST")
    req.add_header("Content-Type", "text/plain; charset=utf-8")
    req.add_header("X-Title", "Taza OS: %s" % urgency)
    req.add_header("X-Priority", PRIORITY_MAP[urgency])
    if sequence_id:
        req.add_header("X-Sequence-ID", sequence_id)
    if tags:
        req.add_header("X-Tags", ",".join(tags))
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code  # non-2xx (e.g. 429 quota-exhausted) -> fallback path
    except urllib.error.URLError:
        return 0  # network-level failure -> fallback path


def notify_nick(message: str, urgency: str, topic: str,
                  sequence_id=None, tags=None) -> dict:
    """urgency in {'pause', 'inform'} maps to 01's Band 1 / Band 2 actions.
    topic is the ntfy topic - fixed per install, not chosen per-call. Fires exactly
    once per triggering event; no retry/spam on the same event."""
    if urgency not in ("pause", "inform"):
        raise ValueError("urgency must be 'pause' or 'inform', got %r" % urgency)
    primary = "%s/%s" % (PRIMARY_BASE, topic)
    errors = {}
    primary_status = _post(primary, message, urgency, sequence_id, tags)
    if 200 <= primary_status < 300:
        return {"sent": True, "channel": "primary", "status": primary_status,
                "url": primary}
    errors["primary"] = primary_status
    fallback_status = _post(FALLBACK_URL, message, urgency, sequence_id, tags)
    if 200 <= fallback_status < 300:
        return {"sent": True, "channel": "fallback", "status": fallback_status,
                "url": FALLBACK_URL}
    errors["fallback"] = fallback_status
    return {"sent": False, "channel": None, "errors": errors}


def clear_notification(topic: str, sequence_id: str, base_url: str = PRIMARY_BASE) -> int:
    """Mark an ntfy notification as read and dismiss it (PUT /<topic>/<seq>/clear).

    Used by ntfy-ack-watcher: when Nick replies to an alarm, the persistent
    notification is cleared remotely. Returns HTTP status; 0 on network error."""
    url = "%s/%s/%s/clear" % (base_url, topic, sequence_id)
    req = urllib.request.Request(url, method="PUT")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except urllib.error.URLError:
        return 0
