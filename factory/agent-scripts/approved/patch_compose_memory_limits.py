#!/usr/bin/env python3
"""Step C patcher: docker-compose.yml memory limits + api NODE_OPTIONS.

Comment-preserving, line-anchored, idempotent. Dry-run by default.
  python3 patch_compose_memory_limits.py [--apply] [--skip-wiredtiger-cache] [FILE]
"""
import datetime
import difflib
import re
import shutil
import sys

DEFAULT_PATH = "/home/taza/librechat/docker-compose.yml"
LIMITS = {
    "api": "1g",
    "admin-panel": "256m",
    "mongodb": "1g",
    "meilisearch": "512m",
    "vectordb": "512m",
    "rag_api": "512m",
}
NODE_HEAP_MB = "768"
MONGO_CACHE_GB = "0.25"

APPLY = "--apply" in sys.argv
SKIP_WT = "--skip-wiredtiger-cache" in sys.argv
path = next((a for a in sys.argv[1:] if not a.startswith("--")), DEFAULT_PATH)

src = open(path).read()
lines = src.splitlines(keepends=True)

svc_re = re.compile(r"^  ([A-Za-z0-9_.-]+):[ \t]*$")
starts = [i for i, l in enumerate(lines) if svc_re.match(l)]
if not starts:
    sys.exit("FATAL: no service blocks found in %s" % path)

changes = []


def block_range(idx):
    start = starts[idx]
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if svc_re.match(lines[j]) and j in starts:
            end = j
            break
        if lines[j].strip() and not lines[j].startswith((" ", "\t")):
            end = j
            break
    while end > start and not lines[end - 1].strip():
        end -= 1
    return start, end


# --- 1) deploy.resources.limits.memory for each target service (bottom-up) ---
targets = [(i, svc_re.match(lines[s]).group(1)) for i, s in enumerate(starts)]
for i, name in sorted([t for t in targets if t[1] in LIMITS], reverse=True):
    start, end = block_range(i)
    block = lines[start:end]
    if any(re.match(r"^    deploy:", l) for l in block):
        changes.append("SKIP %-12s deploy block already present" % name)
        continue
    lines[end:end] = [
        "    deploy:\n",
        "      resources:\n",
        "        limits:\n",
        "          memory: %s\n" % LIMITS[name],
    ]
    changes.append("ADD  %-12s deploy.resources.limits.memory = %s" % (name, LIMITS[name]))

# --- 2) api NODE_OPTIONS ---
for i, name in targets:
    if name != "api":
        continue
    start, end = block_range(i)
    block = lines[start:end]
    if any("NODE_OPTIONS" in l for l in block):
        changes.append("SKIP %-12s NODE_OPTIONS already present" % name)
        break
    env_at = next((j for j in range(start, end) if re.match(r"^    environment:", lines[j])), None)
    if env_at is None:
        sys.exit("FATAL: api service has no 'environment:' block - aborting")
    last_item = None
    for j in range(env_at + 1, end):
        if re.match(r"^      - ", lines[j]):
            last_item = j
        elif lines[j].strip() and not lines[j].startswith("        "):
            break
    if last_item is None:
        sys.exit("FATAL: api environment is not list-style - aborting")
    lines[last_item + 1:last_item + 1] = [
        "      - NODE_OPTIONS=--max-old-space-size=%s\n" % NODE_HEAP_MB
    ]
    changes.append("ADD  %-12s NODE_OPTIONS=--max-old-space-size=%s" % (name, NODE_HEAP_MB))
    break

# --- 3) mongod WiredTiger cache cap (required for a 1g container limit) ---
for i, name in targets:
    if name != "mongodb":
        continue
    start, end = block_range(i)
    block = lines[start:end]
    if any("wiredTigerCacheSizeGB" in l for l in block):
        changes.append("SKIP %-12s wiredTigerCacheSizeGB already present" % name)
        break
    cmd_at = next((j for j in range(start, end) if re.match(r"^    command: mongod", lines[j])), None)
    if cmd_at is None or SKIP_WT:
        changes.append("SKIP %-12s static cache setting not applied" % name)
        break
    old = lines[cmd_at].rstrip("\n")
    lines[cmd_at] = "%s --wiredTigerCacheSizeGB %s\n" % (old, MONGO_CACHE_GB)
    changes.append("ADD  %-12s mongod --wiredTigerCacheSizeGB %s (cache max was 30.5 GB)" % (name, MONGO_CACHE_GB))
    break

new = "".join(lines)

print("=== planned changes ===")
for c in changes:
    print("  " + c)
print()
print("=== diff ===")
print("".join(difflib.unified_diff(src.splitlines(True), new.splitlines(True),
                                 fromfile=path, tofile=path + " (patched)")), end="")

try:
    import yaml
    before, after = yaml.safe_load(src), yaml.safe_load(new)
    assert set(before) == set(after), "top-level keys changed"
    assert set(before["services"]) == set(after["services"]), "service set changed"
    for n in before["services"]:
        bb = dict(before["services"][n])
        aa = dict(after["services"][n])
        aa.pop("deploy", None)
        if n == "api":
            aa["environment"] = [e for e in aa["environment"] if not str(e).startswith("NODE_OPTIONS=")]
        if n == "mongodb":
            aa["command"] = bb["command"]
        assert bb == aa, "unexpected change to service %s" % n
    for n, mem in LIMITS.items():
        assert after["services"][n]["deploy"]["resources"]["limits"]["memory"] == mem, n
    assert any(str(e) == "NODE_OPTIONS=--max-old-space-size=%s" % NODE_HEAP_MB
               for e in after["services"]["api"]["environment"])
    print()
    print("=== YAML validation: OK (only the intended keys differ) ===")
except ImportError:
    print()
    print("=== YAML validation skipped (pyyaml unavailable) ===")

if APPLY:
    backup = "%s.bak-memlimits-%s" % (path, datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(path, backup)
    shutil.copymode(path, backup)
    with open(path, "w") as fh:
        fh.write(new)
    print()
    print("APPLIED. backup=%s" % backup)
else:
    print()
    print("DRY RUN - nothing written. Re-run with --apply to patch.")
