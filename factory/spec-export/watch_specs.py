#!/usr/bin/env python3
"""
watch_specs.py — keep specs.csv in step with the live table, continuously.

WHY A POLLER AND NOT A TRIGGER: the spec table already has a BEFORE UPDATE trigger
(trg_murs_specs_updated -> set_updated_at()). We do not need a second one, and adding a
trigger that shells out to gflip would put a network hop inside every write. Instead this
polls the SAME signal cheaply -- count + max(updated_at) + a content hash -- and only runs
the full export when that signal moves.

That satisfies Nick's rule ("any exported csv needs to update any time the database is
updated") without ever making a database write depend on gflip being up.

Interval default 30s. The watermark query is three cheap aggregates; the heavy COPY runs
only on a real change.

Run under systemd (spec-export-watch.service). Logs one line per change, one line per
failure. Never exits on a transient error -- the estate's ssh can hiccup, and a monitor
that dies on the first blip is not a monitor.
"""
import os, sys, time, subprocess, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORT = os.path.join(HERE, "export_specs.py")
INTERVAL = int(os.environ.get("SPEC_EXPORT_INTERVAL", "30"))


def log(msg: str) -> None:
    print(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] {msg}", flush=True)


def run_export(always_log: bool = False) -> int:
    """Run the exporter; log every real change, and an hourly heartbeat so a dead
    watcher is distinguishable from a quiet one."""
    # NOTE: do NOT pass --quiet. The watcher reads the exporter's own line to decide
    # whether a write happened; --quiet suppresses it and every change goes unlogged.
    r = subprocess.run([sys.executable, EXPORT], capture_output=True, text=True)
    out = (r.stdout or "").strip()
    if r.returncode != 0:
        log(f"export failed rc={r.returncode}: {(r.stderr or '').strip()[:300]}")
        return r.returncode
    if "wrote" in out:
        log(f"CHANGED -> {out}")
        return 0
    if always_log:
        # the exporter already says "no change (...)" — do not wrap it twice
        log(f"heartbeat: {out or 'watermark identical'}")
    return 0


def main() -> int:
    log(f"watch_specs starting: interval={INTERVAL}s, watching {os.environ.get('SPEC_DB_NAME','spec')}"
        f" on {os.environ.get('SPEC_DB_SSH','taza@192.168.2.102')}")
    # One export at startup so the mirror exists even with no prior run.
    run_export(always_log=True)
    fails = 0
    last_beat = time.time()
    while True:
        time.sleep(INTERVAL)
        beat = (time.time() - last_beat) >= 3600
        rc = run_export(always_log=beat)
        if beat:
            last_beat = time.time()
        if rc == 0:
            if fails:
                log(f"recovered after {fails} consecutive failure(s)")
            fails = 0
        else:
            fails += 1
            # Back off on repeated failure so a down host cannot spin this loop.
            if fails > 1:
                backoff = min(INTERVAL * fails, 300)
                log(f"backing off {backoff}s after {fails} failures")
                time.sleep(backoff)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("stopped")
        sys.exit(0)
