#!/usr/bin/env python3
"""Step E patcher: self-heal hardening (two approved changes).

1) mongo probe false positive: `docker exec chat-mongodb pgrep -x mongod` can fail
   transiently and is currently enough on its own to restart LibreChat (this fired
   on 2026-10-14 20:31 against a container that had been Up 16 hours and was
   serving). New behaviour: on mongo-probe failure, wait 5 s, re-probe, and if
   /health is still 200, alert without restarting.
2) settle delay: replace `sleep 12; health=once` with polling /health up to 60 s,
   so a restart is not judged failed (or repeated) while the app is still booting.
   The 20:32:20 backoff entry was caused by exactly that race
   (reasons=container-down;health-000000 immediately after its own restart).

Dry-run by default; --apply requires write access to the script (root-owned).
Usage: python3 patch_selfheal.py [--apply] [FILE]
"""
import datetime
import difflib
import shutil
import subprocess
import sys
import tempfile

DEFAULT_PATH = "/usr/local/bin/taza-librechat-selfheal.sh"

OLD_MONGO = ('docker exec chat-mongodb pgrep -x mongod >/dev/null 2>&1 || '
             '{ needs_restart=1; reasons="${reasons}mongo-down;"; }\n')
NEW_MONGO = ('mongo_down=0\n'
             'docker exec chat-mongodb pgrep -x mongod >/dev/null 2>&1 || mongo_down=1\n')

OLD_HEALTH = ('code=$(http_code http://127.0.0.1:3080/health)\n'
              'if [ "$code" != "200" ]; then\n'
              '    needs_restart=1; reasons="${reasons}health-$code;"\n'
              'fi\n')
RECHECK = '''
# mongo probe is exec-based and can fail transiently (busy host/container). Never
# let it alone restart an app that is actually serving: re-probe once, cross-check
# /health, and alert instead of restarting when the app is up.
if [ "$mongo_down" -eq 1 ]; then
    sleep 5
    if docker exec chat-mongodb pgrep -x mongod >/dev/null 2>&1; then
        log "mongo probe failed once then recovered (transient exec failure) - no action"
    elif [ "$code" = "200" ]; then
        log "mongo probe failing but /health=200 - LibreChat serving, NOT restarting (alert only)"
        notify "LibreChat self-heal: mongo probe failed" "chat-mongodb pgrep failed twice but http://127.0.0.1:3080/health=$code. No restart taken. reasons=$reasons"
    else
        needs_restart=1; reasons="${reasons}mongo-down;"
    fi
fi
'''

OLD_SETTLE = ('sleep 12\n'
              'after=$(http_code http://127.0.0.1:3080/health)\n'
              'log "post-restart health=$after"\n')
NEW_SETTLE = ('after=000\n'
              'checks=0\n'
              'for checks in $(seq 1 12); do\n'
              '    sleep 5\n'
              '    after=$(http_code http://127.0.0.1:3080/health)\n'
              '    [ "$after" = "200" ] && break\n'
              'done\n'
              'log "post-restart health=$after (settled after ~$((checks * 5))s, $checks checks)"\n')

APPLY = "--apply" in sys.argv
path = next((a for a in sys.argv[1:] if not a.startswith("--")), DEFAULT_PATH)

src = open(path).read()
changes = []


def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        sys.exit("FATAL: anchor for '%s' matched %d times (expected 1) - patch aborted" % (label, n))
    changes.append(label)
    return text.replace(old, new, 1)


new = src
if "mongo_down=0" in src and "settled after" in src:
    sys.exit("ALREADY APPLIED: self-heal script already contains both changes.")
if "mongo_down=0" not in src:
    new = replace_once(new, OLD_MONGO, NEW_MONGO, "mongo probe: record result instead of forcing a restart")
    new = replace_once(new, OLD_HEALTH, OLD_HEALTH + RECHECK, "mongo probe: re-probe + /health cross-check before restart")
else:
    changes.append("SKIP mongo changes (already present)")
if "settled after" not in new:
    new = replace_once(new, OLD_SETTLE, NEW_SETTLE, "post-restart: poll /health up to 60s instead of a single check at 12s")
else:
    changes.append("SKIP settle change (already present)")

tmp = tempfile.NamedTemporaryFile("w", delete=False, suffix=".sh")
tmp.write(new)
tmp.close()
syntax = subprocess.run(["bash", "-n", tmp.name], capture_output=True, text=True)
print("=== planned changes ===")
for c in changes:
    print("  " + c)
print("\n=== bash -n syntax check on patched file ===")
print("  " + ("OK" if syntax.returncode == 0 else "FAILED: " + syntax.stderr.strip()))
if syntax.returncode != 0:
    sys.exit("FATAL: patched script is not valid bash - aborting")
print("\n=== diff ===")
print("".join(difflib.unified_diff(src.splitlines(True), new.splitlines(True),
                                 fromfile=path, tofile=path + " (patched)")), end="")

if APPLY:
    import os
    if not os.access(path, os.W_OK):
        sys.exit("\nFATAL: %s not writable by %s - re-run with sudo" % (path, os.environ.get("USER", "?")))
    backup = "%s.bak-selfheal-%s" % (path, datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(path, backup)
    with open(path, "w") as fh:
        fh.write(new)
    print("\nAPPLIED. backup=%s" % backup)
else:
    print("\nDRY RUN - nothing written. Re-run with --apply (sudo) to patch.")
