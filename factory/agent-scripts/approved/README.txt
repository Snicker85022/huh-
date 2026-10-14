================================================================================
PHASE 3 - FIX MCP SHELL TIMEOUTS
Drop-zone: /home/taza/agent-scripts/pending/
================================================================================

WHAT WAS ACTUALLY WRONG
-----------------------
The previous session's hypothesis (add SSE keepalive, align MCP_INIT_TIMEOUT_MS
/ MCP_TOOLS_LIST_TIMEOUT_MS / MCP_USER_CONNECTION_IDLE_TIMEOUT) was partly
wrong. Two things are true:

1. TIMEOUT MISMATCH - THE MAIN CAUSE
   - MCP client (LibreChat) caps every call at 60_000 ms. Proven by the error
     payload itself: {"code":-32001,"data":{"timeout":60000}}
   - mcp_shell.py used subprocess.run(..., timeout=120) -> 120_000 ms.
   So any command running 60-120s is GUARANTEED to produce -32001: the client
   gives up at 60s while the server is still waiting until 120s.
   Fix: server-side ceiling lowered to 55s so it returns a clean, readable
   timeout message BEFORE the client's 60s kill.

2. THE EVENT LOOP WAS BLOCKED (why keepalive didn't save it)
   - _run() called blocking subprocess.run() directly inside the async tool
     handler. A long command froze the single uvicorn worker, which starved
     the SSE keepalive pings -> the client's idle timer fired even for commands
     that WOULD have finished in time.
   - The log shows PingRequest being processed but NOT at a guaranteed interval.
   Fix: subprocess.run() now runs in a worker thread via anyio.to_thread.
   Verified: 8 keepalive ticks now fire during a 0.8s command (was 0).

   Also set uvicorn timeout_keep_alive so the TCP connection outlives the
   client's idle window.

3. DEAD END - DOES NOT EXIST
   There is NO MCP_INIT_TIMEOUT_MS, MCP_TOOLS_LIST_TIMEOUT_MS or
   MCP_USER_CONNECTION_IDLE_TIMEOUT in LibreChat v0.8.7. Your .env has every
   MCP_* var commented out, and mcpSettings accepts no timeout key. The 60s
   client cap is NOT tunable from config here. Do not go looking for it again.

4. SEPARATE ISSUE - RECURSION LIMIT
   9x "Recursion limit of 50 reached" (lc_error_code GRAPH_RECURSION_LIMIT) is
   an agent-graph cap, unrelated to MCP. Raised to 100 in script 02.

--------------------------------------------------------------------------------
RUN ORDER
--------------------------------------------------------------------------------

  STEP 1  -- apply the MCP shell fix
            python3 01-patch-mcp-shell.py

            Patches /home/taza/mcp_shell.py in place. Idempotent (refuses to
            double-apply). Writes a timestamped .bak first. Syntax-checks the
            result.

            IMPORTANT: mcp_shell_owui.py does `import mcp_shell` and reuses
            these tools, so this ONE patch fixes BOTH services:
              :8182  LibreChat   (mcp_shell.service)
              :8183  Open WebUI  (mcp_shell_owui.service)

  STEP 2  -- restart the MCP servers
            sudo systemctl restart mcp_shell.service mcp_shell_owui.service

  STEP 3  -- apply the recursionLimit fix
            python3 02-patch-librechat-yaml.py

            Adds `recursionLimit: 100` under the agents: block and a NOTE
            comment above mcpServers. Backs up, then validates the file still
            parses as YAML - and auto-restores the backup if it does not.

  STEP 4  -- restart LibreChat
            cd /home/taza/librechat && docker compose restart api

  STEP 5  -- verify
            bash 03-verify-phase3.sh

            Read-only, makes no changes, safe to re-run. Exits non-zero if any
            check fails. Prints PASS/FAIL per check plus a summary.

--------------------------------------------------------------------------------
TUNABLES (env vars, optional)
--------------------------------------------------------------------------------
  MCP_SHELL_TIMEOUT=55    server-side command ceiling, in seconds.
                          MUST stay below the client's 60s cap.
  MCP_SHELL_SSE_PING=10   SSE keepalive interval, in seconds.

Both are read from the environment at import time. To change them, add
Environment= lines to the mcp_shell systemd units, then run daemon-reload and
restart both units.

--------------------------------------------------------------------------------
WHAT TO EXPECT AFTER THE FIX
--------------------------------------------------------------------------------
  - Commands under 55s: work normally, no timeout.
  - Commands 55-60s:    return a clean "Command timed out after 55 seconds"
                        message with backgrounding guidance, instead of the
                        opaque "MCP error -32001: Request timed out".
  - Commands over 60s:  still cannot run synchronously (the client cap is not
                        tunable). The tool now tells the model to background
                        the work and poll instead:
                          nohup <cmd> > /tmp/job.log 2>&1 & echo $!
  - -32001 in the error log should drop to roughly zero.

--------------------------------------------------------------------------------
ROLLBACK
--------------------------------------------------------------------------------
  # MCP shell
  cp /home/taza/mcp_shell.py.bak-phase3-<TIMESTAMP> /home/taza/mcp_shell.py
  sudo systemctl restart mcp_shell.service mcp_shell_owui.service

  # LibreChat config
  cp /home/taza/librechat/librechat.yaml.bak-phase3-<TIMESTAMP> \
     /home/taza/librechat/librechat.yaml
  cd /home/taza/librechat && docker compose restart api

--------------------------------------------------------------------------------
FILES IN THIS DIRECTORY
--------------------------------------------------------------------------------
  01-patch-mcp-shell.py        patches mcp_shell.py            (run first)
  02-patch-librechat-yaml.py   patches librechat.yaml          (run second)
  03-verify-phase3.sh          read-only verification          (run last)
  _phase3_snippets.json        data file for script 01 - DO NOT DELETE
  README.txt                   this file

--------------------------------------------------------------------------------
TESTED BEFORE DELIVERY
--------------------------------------------------------------------------------
  01 was dry-run against a copy of the real mcp_shell.py: applies cleanly,
     passes py_compile, and was functionally tested - denylist still blocks
     `rm -rf /`, and the event loop stayed responsive during a slow command.
  02 was dry-run against a copy of the real librechat.yaml: applies cleanly
     and the YAML re-parse confirms recursionLimit = 100.
  Both scripts are idempotent and refuse to double-apply.

  Script 01 writes to /home/taza/mcp_shell.py. That path is not under the
  protected tree, so it does not need sudo - but it IS the live file for both
  MCP services, so the services must be restarted (STEP 2) for the fix to take
  effect.
================================================================================

--------------------------------------------------------------------------------
REVISION NOTE - 03-verify-phase3.sh (2026-10-14)
--------------------------------------------------------------------------------
The original verifier had two defects that produced FALSE FAILURES on a
healthy system. Both are fixed in the approved copy.

  1. WRONG PATH ON PORT 8183
     The original probed http://127.0.0.1:8183/sse and expected 200.
     mcp_shell_owui.py serves the STREAMABLE HTTP transport at /mcp, NOT
     legacy SSE at /sse - it has no /sse route by design (Open WebUI's MCP
     client only speaks streamable_http). The old probe therefore 404'd on a
     perfectly healthy service.
     Fix: check 4 is now transport-aware.
       - 8182 -> GET /sse                      (LibreChat legacy SSE)
       - 8183 -> POST /mcp with a real MCP initialize handshake, asserting on
                 "serverInfo" in the JSON-RPC response. A bare GET to /mcp
                 returns 406 by spec, so a naive 200 test is not valid here.

  2. "200000" HTTP-CODE ARTIFACT
     The original used:
         code=$(curl ... -w '%{http_code}' ... || echo 000)
     For an SSE stream curl legitimately exits non-zero (rc=28) when
     --max-time cuts the still-open stream, so the `|| echo 000` appended
     "000" to the already-printed "200", yielding the nonsense "200000".
     Fix: curl's exit status is now captured in a SEPARATE variable from the
     HTTP code. A 200 with rc=28 on 8182 is reported as a PASS with an
     explanatory note, not a failure.

Also changed: check 1 now prints the real systemd state (activating/failed/...)
rather than a bare "NOT active"; check 6 is explicitly labelled report-only.

Result on a healthy system: PASS 11 / FAIL 0, exit 0.
