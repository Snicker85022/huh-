#!/usr/bin/env python3
"""
Phase 3 (part 2): raise the agent graph recursion limit and note the MCP
timeout finding directly in librechat.yaml as a comment.

Background
----------
9x in 24h: "Recursion limit of 50 reached without hitting a stop condition"
(lc_error_code: GRAPH_RECURSION_LIMIT). LibreChat's agent graph caps tool-call
round trips at 50 by default. Raising it to 100 stops normal multi-step
tool workflows from aborting mid-task.

Finding on MCP timeouts
-----------------------
The MCP client timeout observed in the -32001 error payloads is 60_000 ms.
There is NO MCP_INIT_TIMEOUT_MS / MCP_TOOLS_LIST_TIMEOUT_MS /
MCP_USER_CONNECTION_IDLE_TIMEOUT key in LibreChat v0.8.7, and mcpSettings
accepts no timeout key. The client-side 60s cap is therefore not tunable from
here, which is exactly why script 01 caps the SERVER side at 55s instead.

Idempotent. Backs up first. Validates the result parses as YAML.
"""
import os
import shutil
import sys
import time

TARGET = os.environ.get("LIBRECHAT_YAML", "/home/taza/librechat/librechat.yaml")

RECURSION_LIMIT = 100                     # was implicitly 50

NOTE = """  # NOTE (Phase 3): 63x "MCP error -32001: Request timed out" in 24h came from
  # the MCP client's hard 60s cap vs a 120s subprocess timeout in mcp_shell.py.
  # LibreChat v0.8.7 exposes NO timeout key here (no MCP_INIT_TIMEOUT_MS,
  # MCP_TOOLS_LIST_TIMEOUT_MS or MCP_USER_CONNECTION_IDLE_TIMEOUT) and
  # mcpSettings takes no timeout field, so the server side was lowered to 55s
  # instead. See /home/taza/agent-scripts/pending/README.txt
"""


def main():
    src = open(TARGET).read()

    if "recursionLimit" in src:
        print("ALREADY PATCHED (recursionLimit present). Nothing done.")
        return 0

    backup = TARGET + ".bak-phase3-" + time.strftime("%Y%m%d-%H%M%S")
    shutil.copy2(TARGET, backup)
    print("backup written: " + backup)

    # Insert `recursionLimit` under the agents: block.
    # The agents: block currently reads:
    #   agents:
    #     disableBuilder: false
    #     capabilities:
    anchor = "  agents:\n    disableBuilder: false\n"
    if anchor not in src:
        print("ERROR: 'agents:' anchor not found verbatim; aborting without changes.")
        print("       Expected:\n" + anchor)
        return 1

    replacement = (
        anchor
        + "    # Raised from the default 50. 9x 'Recursion limit of 50 reached'\n"
        + "    # errors in 24h aborted normal multi-step tool workflows.\n"
        + "    recursionLimit: " + str(RECURSION_LIMIT) + "\n"
    )
    out = src.replace(anchor, replacement, 1)

    # Add an explanatory comment above mcpServers (informational only).
    if "mcpServers:" in out:
        out = out.replace(
            "mcpServers:\n",
            NOTE + "mcpServers:\n",
            1,
        )

    open(TARGET, "w").write(out)
    print("patched: " + TARGET)

    # validate YAML
    try:
        import yaml
        doc = yaml.safe_load(open(TARGET))
        rl = doc.get("endpoints", {}).get("custom")
        got = doc.get("endpoints", {}).get("agents", {}).get("recursionLimit")
        if got is None:
            # agents may sit under endpoints.custom list; search recursively
            def find(d, k):
                if isinstance(d, dict):
                    if k in d:
                        return d[k]
                    for v in d.values():
                        r = find(v, k)
                        if r is not None:
                            return r
                elif isinstance(d, list):
                    for v in d:
                        r = find(v, k)
                        if r is not None:
                            return r
                return None
            got = find(doc, "recursionLimit")
        print("YAML parse: OK   recursionLimit = " + str(got))
        if got != RECURSION_LIMIT:
            print("WARNING: recursionLimit not where expected - please eyeball the file.")
            return 1
    except ImportError:
        print("YAML parse: SKIPPED (no pyyaml). Please eyeball the file.")
    except Exception as e:
        print("YAML parse FAILED: " + str(e))
        print("Restoring backup.")
        shutil.copy2(backup, TARGET)
        return 1

    print("")
    print("Now restart LibreChat to pick up the config:")
    print("  cd /home/taza/librechat && docker compose restart api")
    return 0


if __name__ == "__main__":
    sys.exit(main())
