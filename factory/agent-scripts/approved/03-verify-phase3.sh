#!/usr/bin/env bash
# Phase 3 verification. Run AFTER scripts 01 and 02 and their restarts.
# Read-only: makes no changes. Safe to run repeatedly.
#
# --- REVISIONS (draft for review 2026-10-14) ---
#  A. Check 4 rewritten. The original probed /sse on BOTH 8182 and 8183.
#     8183 (mcp_shell_owui.py) serves the *streamable HTTP* transport at
#     /mcp -- it has NO /sse route by design (Open WebUI's MCP client only
#     speaks streamable_http). A hard-coded /sse probe on 8183 is therefore
#     guaranteed to 404 on a perfectly healthy system.
#  B. Fixed the "200000" artifact. The original used
#         code=$(curl ... -w '%{http_code}' ... || echo 000)
#     On a long-lived (or slow) stream curl exits non-zero, so the `|| echo 000`
#     appended "000" to the already-printed "200" -> "200000". Now curl's exit
#     status is captured separately from the http_code, and we test both.
#  C. Check 4 is now transport-aware: SSE on 8182, streamable HTTP on 8183,
#     with the correct Accept header for each (a bare GET to /mcp returns 406
#     by spec, so we assert on the MCP handshake, not on a naive 200).
#  D. Service check unchanged in intent, but reports "activating"/"failed"
#     distinctly so a restart-in-progress does not look like a hard failure.
# Everything else is carried over from the original unchanged.
# -------------------------------------------------

set -uo pipefail

PASS=0; FAIL=0
ok(){ echo "  PASS  $1"; PASS=$((PASS+1)); }
no(){ echo "  FAIL  $1"; FAIL=$((FAIL+1)); }

echo "=== 1. MCP shell service health ==="
for svc in mcp_shell mcp_shell_owui; do
  state=$(systemctl is-active "$svc" 2>/dev/null || true)
  if [ "$state" = "active" ]; then
    ok "$svc active"
  else
    no "$svc NOT active (state: ${state:-unknown})"
  fi
done

echo
echo "=== 2. Patched constants present ==="
if grep -q 'SUBPROCESS_TIMEOUT = int' /home/taza/mcp_shell.py; then
  ok "SUBPROCESS_TIMEOUT defined"
  echo "        value: $(grep -m1 '^SUBPROCESS_TIMEOUT' /home/taza/mcp_shell.py)"
else
  no "SUBPROCESS_TIMEOUT missing - script 01 not applied"
fi
if grep -q 'anyio.to_thread.run_sync' /home/taza/mcp_shell.py; then
  ok "_run() runs off the event loop"
else
  no "anyio.to_thread.run_sync missing - event loop still blocks"
fi
if grep -q 'async def _run' /home/taza/mcp_shell.py; then
  ok "_run() is async"
else
  no "_run() is not async"
fi

echo
echo "=== 3. Timeout ordering (must be subprocess < client) ==="
SUBP=$(grep -m1 '^SUBPROCESS_TIMEOUT' /home/taza/mcp_shell.py | grep -oE '[0-9]+' | head -1)
echo "        subprocess timeout : ${SUBP:-?}s"
echo "        client timeout     : 60s (from -32001 payloads)"
if [ -n "${SUBP:-}" ] && [ "$SUBP" -lt 60 ]; then
  ok "subprocess (${SUBP}s) < client (60s)"
else
  no "subprocess timeout not below the 60s client cap"
fi

echo
echo "=== 4. MCP transports reachable (transport-aware) ==="
# Capture body + http_code, and curl's OWN exit status separately so a
# non-zero exit (e.g. SSE stream kept open until --max-time) is not mistaken
# for a bad HTTP status.
probe(){ # $1=label  $2..=curl args ; echoes "HTTPCODE CURLRC"
  local label="$1"; shift
  local out
  out=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 5 "$@" 2>/dev/null)
  local rc=$?
  echo "$out $rc"
}

# 4a. LibreChat instance: legacy SSE at /sse on 8182.
# An open SSE stream legitimately never "completes"; curl may exit 28.
# What matters is that the response line was 200.
read -r CODE RC <<<"$(probe 8182-sse "http://127.0.0.1:8182/sse")"
if [ "$CODE" = "200" ]; then
  if [ "$RC" -eq 0 ]; then
    ok "8182 /sse -> 200 (stream closed within timeout)"
  else
    ok "8182 /sse -> 200 (stream open, curl rc=$RC as expected for SSE)"
  fi
else
  no "8182 /sse -> ${CODE:-no-response} (curl rc=$RC)"
fi

# 4b. Open WebUI instance: streamable HTTP at /mcp on 8183, via a real
# MCP initialize handshake. A bare GET returns 406 by spec, so we must POST
# with Accept: text/event-stream and assert on the JSON-RPC result.
MCP_RESP=$(curl -sS --max-time 5 \
  -X POST "http://127.0.0.1:8183/mcp" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"verify","version":"0"}}}' \
  2>/dev/null)
if printf '%s' "$MCP_RESP" | grep -q '"serverInfo"'; then
  SNAME=$(printf '%s' "$MCP_RESP" | grep -oE '"name":"[^"]*"' | head -1 | cut -d'"' -f4)
  ok "8183 /mcp -> MCP initialize OK (serverInfo.name=${SNAME:-?})"
else
  no "8183 /mcp -> no valid MCP initialize response"
fi

echo
echo "=== 5. LibreChat recursionLimit ==="
if grep -q 'recursionLimit' /home/taza/librechat/librechat.yaml; then
  ok "recursionLimit present: $(grep -m1 'recursionLimit' /home/taza/librechat/librechat.yaml | tr -d ' ')"
else
  no "recursionLimit missing - script 02 not applied"
fi

echo
echo "=== 6. Recent -32001 count (report only, no pass/fail) ==="
LOG=/home/taza/librechat/logs/error-$(date +%Y-%m-%d).log
if [ -f "$LOG" ]; then
  echo "        scanning $LOG"
  echo "        (whole-file -32001 count: $(grep -c '32001' "$LOG" 2>/dev/null || echo 0))"
  echo "        NOTE: historical count includes pre-fix errors; compare after a real workload."
else
  echo "        (no error log for today yet)"
fi

echo
echo "=== 7. Syntax + import sanity ==="
if /home/taza/mcp_shell_env/bin/python -m py_compile /home/taza/mcp_shell.py 2>/dev/null; then
  ok "mcp_shell.py compiles"
else
  no "mcp_shell.py does NOT compile"
fi
if /home/taza/mcp_shell_env/bin/python -c "import anyio" 2>/dev/null; then
  ok "anyio importable"
else
  no "anyio NOT importable"
fi

echo
echo "================================"
echo " PASS: $PASS   FAIL: $FAIL"
echo "================================"
[ "$FAIL" -eq 0 ] || exit 1
