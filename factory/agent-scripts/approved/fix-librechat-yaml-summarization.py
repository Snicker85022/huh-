#!/usr/bin/env python3
"""Step D (Fixes 3 + 4): librechat.yaml summarization block + maxToolResultChars.

Why (measured): no 'summarization:' block existed, so shouldTriggerSummarization()
returned true on EVERY prune event -> 82 triggers/24h, incl. a burst of 6 triggers
in 110 s that produced no summary at all, with context pinned at 105-115k tokens
(87-105% of the 121600 budget). 20% of all stored messages are >20k chars and the
largest single message is 1,818,044 chars, so the retained 2-turn recency window
often contained the whole budget => 'nothing to refine' => retrigger loop.

Patcher is line-anchored and comment-preserving (no YAML round-trip), idempotent,
dry-run by default. Validates the result with pyyaml and asserts that ONLY the two
intended keys were added.

Usage: python3 fix-librechat-yaml-summarization.py [--apply] [FILE]
"""
import datetime
import difflib
import re
import shutil
import sys

DEFAULT_PATH = "/home/taza/librechat/librechat.yaml"

SUMMARIZATION = [
    "summarization:\n",
    "  enabled: true\n",
    "  trigger:\n",
    "    type: remaining_tokens\n",
    "    value: 8000\n",
    "  reserveRatio: 0.10\n",
    "  maxSummaryTokens: 2048\n",
    "  retainRecent:\n",
    "    turns: 6\n",
    "    tokens: 32000\n",
    "  contextPruning:\n",
    "    keepLastAssistants: 2\n",
]
ENDPOINT = "DeepSeek"
MAX_TOOL_RESULT_CHARS = "20000"
EXPECTED_SUMMARIZATION = {
    "enabled": True,
    "trigger": {"type": "remaining_tokens", "value": 8000},
    "reserveRatio": 0.10,
    "maxSummaryTokens": 2048,
    "retainRecent": {"turns": 6, "tokens": 32000},
    "contextPruning": {"keepLastAssistants": 2},
}

APPLY = "--apply" in sys.argv
path = next((a for a in sys.argv[1:] if not a.startswith("--")), DEFAULT_PATH)

src = open(path).read()
lines = src.splitlines(keepends=True)
changes = []

# --- 1) top-level summarization block, inserted after 'cache: true' ---
has_sum = any(re.match(r"^summarization:", l) for l in lines)
if has_sum:
    try:
        import yaml
        current = yaml.safe_load(src).get("summarization")
    except Exception:
        current = None
    if current == EXPECTED_SUMMARIZATION:
        changes.append("SKIP summarization block already present with expected values")
    else:
        sys.exit("FATAL: a 'summarization:' key already exists with different values:\n%r\n"
                 "Refusing to overwrite - resolve by hand." % (current,))
else:
    anchor = next((i for i, l in enumerate(lines) if re.match(r"^cache:[ \t]*true[ \t]*$", l)), None)
    if anchor is None:
        sys.exit("FATAL: anchor 'cache: true' not found - refusing to guess insertion point")
    lines[anchor + 1:anchor + 1] = SUMMARIZATION
    changes.append("ADD  top-level summarization block (after line %d 'cache: true')" % (anchor + 1))

# --- 2) maxToolResultChars inside the DeepSeek custom endpoint ---
start = next((i for i, l in enumerate(lines) if re.match(r"^  - name:[ \t]*%s[ \t]*$" % re.escape(ENDPOINT), l)), None)
if start is None:
    sys.exit("FATAL: endpoint '- name: %s' not found" % ENDPOINT)
end = len(lines)
for j in range(start + 1, len(lines)):
    if re.match(r"^  - ", lines[j]) or (lines[j].strip() and not lines[j].startswith((" ", "\t"))):
        end = j
        break
block = lines[start:end]
if any(re.match(r"^    maxToolResultChars:", l) for l in block):
    changes.append("SKIP maxToolResultChars already present on endpoint %s" % ENDPOINT)
else:
    ins = next((j for j in range(start, end) if re.match(r"^    streamRate:[ \t]*0[ \t]*$", lines[j])), None)
    if ins is None:
        sys.exit("FATAL: anchor '    streamRate: 0' not found inside endpoint %s" % ENDPOINT)
    lines[ins + 1:ins + 1] = ["    maxToolResultChars: %s\n" % MAX_TOOL_RESULT_CHARS]
    changes.append("ADD  maxToolResultChars: %s to endpoint %s (after 'streamRate: 0')"
                   % (MAX_TOOL_RESULT_CHARS, ENDPOINT))

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
    assert set(after) - set(before) == {"summarization"}, "unexpected top-level keys added"
    assert before.get("summarization") is None
    assert after["summarization"] == EXPECTED_SUMMARIZATION, after["summarization"]
    b2 = dict(before)
    assert after["endpoints"]["custom"][0]["name"] == ENDPOINT
    assert after["endpoints"]["custom"][0]["maxToolResultChars"] == int(MAX_TOOL_RESULT_CHARS)
    assert after["endpoints"]["custom"][0]["streamRate"] == 0, "streamRate must stay 0"
    # structural equivalence check: remove the two additions, compare to original
    before_cmp = yaml.safe_load(src)
    after_cmp = yaml.safe_load(new)
    del after_cmp["summarization"]
    after_cmp["endpoints"]["custom"][0].pop("maxToolResultChars")
    assert before_cmp == after_cmp, "something else changed in the file"
    print()
    print("=== YAML validation: OK (only summarization + maxToolResultChars added; streamRate still 0) ===")
except ImportError:
    print()
    print("=== YAML validation skipped (pyyaml unavailable) ===")

if APPLY:
    backup = "%s.bak-summarization-%s" % (path, datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(path, backup)
    shutil.copymode(path, backup)
    with open(path, "w") as fh:
        fh.write(new)
    print()
    print("APPLIED. backup=%s" % backup)
else:
    print()
    print("DRY RUN - nothing written. Re-run with --apply to patch.")
