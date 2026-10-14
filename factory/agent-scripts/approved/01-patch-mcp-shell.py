#!/usr/bin/env python3
"""
Phase 3 fix: MCP shell timeouts.

Three changes to /home/taza/mcp_shell.py:

  1. SUBPROCESS_TIMEOUT 120s -> 55s, so the tool returns a clean, readable
     timeout message BEFORE LibreChat's MCP client hard-caps the call at 60s.
     Eliminates "MCP error -32001: Request timed out" at the source.

  2. Move subprocess.run() OFF the event loop via anyio.to_thread.run_sync().
     Previously a long command blocked the single uvicorn worker, which
     starved SSE keepalive pings, so the client's idle timer fired even for
     commands that would have finished in time.

  3. Explicit uvicorn timeout_keep_alive so the TCP connection outlives the
     client's idle window.

Affects BOTH services: mcp_shell_owui.py does `import mcp_shell` and reuses
these tools, so :8182 (LibreChat) and :8183 (Open WebUI) both pick this up.

Idempotent. Writes a timestamped .bak first.
"""
import json
import os
import re
import shutil
import sys
import time

TARGET = os.environ.get("MCP_SHELL_TARGET", "/home/taza/mcp_shell.py")
SNIPPETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_phase3_snippets.json")


def main():
    src = open(TARGET).read()

    if "SUBPROCESS_TIMEOUT" in src:
        print("ALREADY PATCHED - refusing to double-apply. Nothing done.")
        return 0

    s = json.load(open(SNIPPETS))

    backup = TARGET + ".bak-phase3-" + time.strftime("%Y%m%d-%H%M%S")
    shutil.copy2(TARGET, backup)
    print("backup written: " + backup)

    out = src

    old_imports = "from mcp.server.fastmcp import FastMCP\nimport subprocess, uvicorn, re\n"
    if old_imports not in out:
        print("ERROR: import block not found verbatim; aborting without changes.")
        return 1
    out = out.replace(old_imports, s["imports"], 1)

    anchor = 'mcp.settings.transport_security.allowed_origins.append("http://192.168.2.107:*")\n'
    if anchor not in out:
        print("ERROR: transport_security anchor not found; aborting.")
        return 1
    out = out.replace(anchor, anchor + "\n" + s["timeout_block"], 1)

    out, n = re.subn(r"def _run\(cmd\):.*?\n\n\n", lambda m: s["run"] + "\n\n", out, count=1, flags=re.DOTALL)
    if n != 1:
        print("ERROR: _run() replacement failed; aborting.")
        return 1

    out, n = re.subn(r"@mcp\.tool\(\)\ndef run_shell.*?(?=\n\nif __name__)", lambda m: s["tools"].rstrip() + "\n", out, count=1, flags=re.DOTALL)
    if n != 1:
        print("ERROR: tool replacement failed; aborting.")
        return 1

    out, n = re.subn(r'if __name__ == "__main__":\n.*$', lambda m: s["main"], out, count=1, flags=re.DOTALL)
    if n != 1:
        print("ERROR: __main__ replacement failed; aborting.")
        return 1

    open(TARGET, "w").write(out)
    print("patched: " + TARGET)

    import py_compile
    py_compile.compile(TARGET, doraise=True)
    print("syntax check: OK")
    print("")
    print("Now restart the two services:")
    print("  sudo systemctl restart mcp_shell.service mcp_shell_owui.service")
    return 0


if __name__ == "__main__":
    sys.exit(main())
