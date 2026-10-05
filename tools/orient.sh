#!/usr/bin/env bash
# ONE-PASTE orientation for a fresh session on the mURS review + testability work.
# Prints: live status snapshot + the full handoff doc + the resume prompt + next action.
# Usage:  bash /home/taza/repo/tools/orient.sh
cd /home/taza/repo || exit 1

echo "############################################################################"
echo "#  TAZA OS — mURS review + testability : SESSION ORIENTATION               #"
echo "#  (paste the OUTPUT of this script to a fresh session to orient it)       #"
echo "############################################################################"
echo

echo "========== 1. LIVE STATUS =========="
bash tools/handoff-snapshot.sh
echo

echo "========== 2. HANDOFF DOCUMENT =========="
cat HANDOFF-2026-10-01-mURS-testability.md
echo

echo "========== 3. RESUME PROMPT =========="
cat urs/resume-mURS-work-prompt.md
echo

echo "========== 4. RULES THAT NEVER CHANGE =========="
echo "  - master-urs.md is the ONLY source of truth (290 specs; decisions D1-D28 at top)."
echo "  - python3 urs/refs.py check MUST be 0 after ANY edit."
echo "  - Never edit Notion. It is frozen."
echo "  - NocoDB mirrors public.master_urs (space-named cols), never the pckp* schema."
echo "  - Keep batches small (the Main slot context-exhausts on large ones)."
echo

echo "========== 5. IMMEDIATE NEXT ACTION =========="
GEN=$(grep -cE 'Evidence: (psql|log|query|code-search|test|screenshot|observation log|hands-on verification|metrics)[.,]?$' master-urs.md)
NS=$(grep -c 'NEEDS-SCHEMA:' master-urs.md)
STAMPS=$(awk -F'\t' 'NR>1 && $2=="CONSUMES"{e++} END{print e+0}' urs/seam-stamps.tsv 2>/dev/null)
if [ "$GEN" -gt 0 ]; then
  echo "  1. Evidence typing: $GEN generic 'Evidence:' lines remain."
  echo "     -> python3 tools/type-evidence.py          # dry-run"
  echo "        python3 tools/type-evidence.py --apply  # write + refs check"
else
  echo "  1. Evidence typing: DONE (0 generic lines). Outstanding: $NS NEEDS-SCHEMA item(s)."
  echo "     -> extend docs/schema-stub.md, then re-run: python3 tools/type-evidence.py --apply"
fi
echo "  2. Rec 6 seam graph: $STAMPS directed edges in urs/seam-stamps.tsv. Rec 4 [NICK] scripts: $(ls tests/harness/manual/*.sh 2>/dev/null | wc -l)."
echo "  3. Then: Pass 3 interrogation -> Pass 4 surgical debate -> Pass 5 synthesis -> Pass 6 red team -> Pass 7 Nick."
echo
echo "Tell the session what to do next (e.g., 'continue evidence typing for batch X')."
echo "Done."
