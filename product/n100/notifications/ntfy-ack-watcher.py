#!/usr/bin/env python3
"""ntfy-ack-watcher.py - clear alarm notifications when Nick replies.

Watches the ntfy topic (JSON poll). Messages carrying the 'taza' system tag are
our own pushes (alarms and confirmations). An un-tagged message is a human
reply (Nick). On a reply, the newest active alarm (priority >= 4 with a
sequence_id) is cleared via PUT /<topic>/<seq>/clear, dismissing the persistent
notification on his phone, and a confirmation is published back to the topic.

State: /var/lib/taza/ntfy-ack-state.json (cursor, alarms, acked). stdlib only.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

STATE_FILE = "/var/lib/taza/ntfy-ack-state.json"
SYSTEM_TAG = "taza"
POLL_EVERY = 20
HTTP_TIMEOUT = 15


def log(msg):
    print("%s %s" % (time.strftime("%Y-%m-%dT%H:%M:%S%z"), msg), flush=True)


def _http(url, method="GET", data=None, headers=None, timeout=HTTP_TIMEOUT):
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except urllib.error.URLError as e:
        return 0, str(e)
    except OSError as e:
        return 0, str(e)


def parse_ntfy_body(body):
    """ntfy /json may return a JSON array, a JSON-lines stream, or an array
    followed by streamed events. Accept all three; skip non-object junk."""
    body = (body or "").strip()
    if not body:
        return []
    try:
        data = json.loads(body)
        return data if isinstance(data, list) else [data]
    except ValueError:
        pass
    out = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            doc = json.loads(line)
        except ValueError:
            continue
        if isinstance(doc, list):
            out.extend(doc)
        else:
            out.append(doc)
    return out


def fetch_messages(base, topic, since):
    url = "%s/%s/json?poll=1&since=%s" % (base, topic, since)
    status, body = _http(url)
    if status == 0:
        return []  # connection timed out / closed: no new data this cycle
    if status != 200:
        log("poll error HTTP %s" % status)
        return None
    return parse_ntfy_body(body)


def publish(base, topic, message, title="Taza OS: ack", priority="default", tags=None):
    status, _ = _http(
        base + "/" + topic,
        method="POST",
        data=message.encode("utf-8"),
        headers={"X-Title": title, "X-Priority": priority,
                 "X-Tags": ",".join(tags) if tags else SYSTEM_TAG},
    )
    return status


def clear_alarm(base, topic, seq):
    return _http("%s/%s/%s/clear" % (base, topic, seq), method="PUT")[0]


def load_state(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"cursor": None, "alarms": {}, "acked": {}}


def save_state(state, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def main():
    ap = argparse.ArgumentParser(description="ntfy ack watcher")
    ap.add_argument("--base", default="https://ntfy.sh")
    ap.add_argument("--topic", default="taza-ops")
    ap.add_argument("--once", action="store_true", help="single pass, then exit (testing)")
    ap.add_argument("--poll-every", type=int, default=POLL_EVERY)
    ap.add_argument("--state", default=STATE_FILE, help="state file (testing)")
    args = ap.parse_args()

    state = load_state(args.state)
    cursor = state.get("cursor")

    if cursor is None:
        msgs = fetch_messages(args.base, args.topic, "all")
        if msgs:
            for m in msgs:
                if m.get("event") == "message":
                    cursor = m["id"]
            state["cursor"] = cursor
            save_state(state, args.state)
            log("warm-up complete, cursor=%s" % cursor)
        else:
            log("warm-up: no messages yet")
        if args.once:
            return 0

    while True:
        if cursor is None:
            cursor = "all"
        msgs = fetch_messages(args.base, args.topic, cursor)
        if not msgs:
            if args.once:
                return 0
            time.sleep(args.poll_every)
            continue

        for m in msgs:
            if m.get("event") != "message":
                continue
            msg_id = m.get("id")
            tags = m.get("tags") or []
            seq = m.get("sequence_id")
            prio = m.get("priority") or 0
            if SYSTEM_TAG in tags:
                if prio >= 4 and seq:
                    if seq not in state["alarms"]:
                        state["alarms"][seq] = {
                            "time": m.get("time"), "title": m.get("title"),
                            "priority": prio, "acked": False,
                        }
                        log("alarm recorded: %s (prio %s)" % (seq, prio))
            else:
                log("reply seen: %r" % ((m.get("message") or "")[:60],))
                active = [s for s, a in state["alarms"].items()
                          if not a.get("acked") and (a.get("priority") or 0) >= 4]
                if not active:
                    log("reply but no active alarm to clear")
                else:
                    newest = max(active, key=lambda s: state["alarms"][s].get("time") or 0)
                    st = clear_alarm(args.base, args.topic, newest)
                    if 200 <= st < 300:
                        state["alarms"][newest]["acked"] = True
                        state["alarms"][newest]["acked_at"] = int(time.time())
                        save_state(state, args.state)
                        log("CLEARED alarm %s (HTTP %s)" % (newest, st))
                        pst = publish(
                            args.base, args.topic,
                            "alarm cleared - Nick replied at %s" % time.strftime("%H:%M:%S"),
                            tags=[SYSTEM_TAG],
                        )
                        log("confirmation publish HTTP %s" % pst)
                    else:
                        log("clear FAILED for %s (HTTP %s)" % (newest, st))
            if msg_id:
                cursor = msg_id
        state["cursor"] = cursor
        save_state(state, args.state)
        if args.once:
            return 0
        time.sleep(args.poll_every)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
