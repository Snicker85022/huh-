#!/usr/bin/env bash
# Handoff snapshot for the mURS review + testability work.
# Prints live status so a fresh session can orient in one command.
# Usage: bash ~/repo/tools/handoff-snapshot.sh
cd /home/taza/repo || exit 1
echo "=== mURS review + testability — status snapshot $(date -Iseconds) ==="
echo "specs:                 $(grep -cE '^## [A-Za-z0-9._-]+ — ' master-urs.md)"
echo "refs.py check:         $(python3 urs/refs.py check)"
echo "generic 'Evidence:'    $(grep -cE 'Evidence: (psql|log|query|code-search|test|screenshot|observation log|hands-on verification|metrics)[.,]?$' master-urs.md)  (remaining)"
echo "SILENT-FAILURE pairs:  $(grep -c 'detected by' master-urs.md)"
echo "seam graph:            $(awk -F'\t' 'NR>1 && $2=="CONSUMES"{e++} NR>1 && $2=="NONE"{n++} END{printf "%d edges + %d NONE", e, n}' urs/seam-stamps.tsv 2>/dev/null); $(tail -n +2 urs/seam-open.tsv 2>/dev/null | wc -l) open"
echo "manual [NICK] scripts: $(ls tests/harness/manual/*.sh 2>/dev/null | wc -l)"
echo "cross-spec tests:      $(grep -c '@@ TEST' tests/harness/cross-spec/tests-from-debate-team.md 2>/dev/null) (debate) + $(grep -c '@@ TEST' tests/harness/cross-spec/tests-from-cortex.md 2>/dev/null) (cortex)"
echo "decisions:             $(grep -oE 'D[0-9]+ —' master-urs.md | sort -uV | tail -1 | tr -d ' —') (latest)"
echo "=== key artifacts ==="
ls -1 urs/*.md docs/schema-stub.md tests/harness/README.md 2>/dev/null | sed 's/^/  /'
