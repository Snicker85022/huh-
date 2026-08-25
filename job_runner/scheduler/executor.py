"""Ornith executor -- the seam between the scheduler and the production model.

The scheduler is a pure OpenAI-compatible client of the locked llama-server on
:8082. It never touches the iGPU directly and never changes the server config.

The DOE (Phase 3) taught two operational facts that are baked in here:
  1. Ornith-1.5 emits `reasoning_content`; it can spend its whole token budget
     thinking. max_tokens is kept large (config.MAX_TOKENS) and reasoning
     output is discarded, not treated as the answer.
  2. The 26 GiB thrash failure is a SILENT slowdown, not an error, so every
     HTTP call gets a hard wall-clock stall timeout (config).

SANDBOXING (review decision 2026-08-25): verify_cmd runs code the model just
wrote, on the same box as production Ornith/LibreChat. Every verify subprocess
is dropped to the unprivileged `ornith-sandbox` user via `sudo -n -u`, with
resource.setrlimit CPU/memory/fsize caps applied in the child, HOME/TMPDIR
pointed into the workspace, and the workspace chowned to that user so it is
the only writable tree it gets. If the sandbox user is missing the executor
REFUSES to run (fail fast) rather than silently running generated code as taza.

v1 scope note: this is a single-file "write the solution, then verify" loop.
The full tool-calling / screenshots agent loop is a clean replacement point
behind `execute_once` -- nothing else in the scheduler cares how the code was
produced.
"""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from . import config
from .sandbox import SandboxRunner

_FENCE_RE = re.compile(r"```[ \t]*([A-Za-z0-9_+-]*)[ \t]*\n(.*?)```", re.DOTALL)


@dataclass
class AttemptResult:
    code: str
    passed: bool
    error: Optional[str] = None
    wall_s: float = 0.0
    gen_tokens: int = 0
    gen_tps: float = 0.0
    meta: Dict[str, Any] = field(default_factory=dict)


class OrnithClient:
    def __init__(self) -> None:
        self.base = config.ORNITH_BASE_URL.rstrip("/")
        self.model = config.ORNITH_MODEL

    def health(self) -> Dict[str, Any]:
        try:
            with urllib.request.urlopen(self.base + "/health", timeout=5) as r:
                return {"ok": r.status == 200, "body": r.read().decode()[:120]}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    def chat(self, system: str, user: str) -> Dict[str, Any]:
        """One non-streamed completion. Raises on timeout / transport error."""
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": config.MAX_TOKENS,
            "temperature": config.TEMP,
            "top_p": config.TOP_P,
            "top_k": config.TOP_K,
            "stream": False,
        }
        req = urllib.request.Request(
            self.base + "/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=config.GENERATION_TIMEOUT_S) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        wall = time.time() - t0
        choice = data["choices"][0]
        msg = choice.get("message", {})
        content = msg.get("content") or ""
        usage = data.get("usage", {})
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
        gen_tps = (completion_tokens / wall) if wall > 0 else 0.0
        return {
            "content": content,
            "usage": usage,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "wall_s": wall,
            "gen_tps": gen_tps,
        }


def extract_code_block(content: str, lang_hint: Optional[str] = None) -> str:
    """Pull the solution out of the model output.

    Preference: a fenced block whose language tag matches the hint; else the
    first fenced block; else (no fence at all) the whole stripped content.
    """
    matches = _FENCE_RE.findall(content or "")
    if matches:
        if lang_hint:
            hint = lang_hint.strip().lower()
            for lang, code in matches:
                if lang.strip().lower() == hint:
                    return code
        return matches[0][1]
    return (content or "").strip()


def run_verify(workspace: str, cmd: str, timeout: float = config.VERIFY_TIMEOUT_S):
    """Un-sandboxed fallback (dev/offline only). Returns (passed, output, wall)."""
    t0 = time.time()
    try:
        p = subprocess.run(
            cmd, shell=True, cwd=workspace, capture_output=True,
            text=True, timeout=timeout,
        )
        out = ""
        if p.stdout:
            out += p.stdout
        if p.stderr:
            out += ("\n" if out else "") + p.stderr
        return p.returncode == 0, out.strip(), time.time() - t0
    except subprocess.TimeoutExpired:
        return False, f"VERIFY TIMEOUT after {timeout:.0f}s", time.time() - t0


class Executor:
    """Runs one attempt of a task: prompt -> Ornith -> code -> verify (sandboxed)."""

    def __init__(self, client: Optional[OrnithClient] = None) -> None:
        self.client = client or OrnithClient()
        self._sandbox: Optional[SandboxRunner] = None

    def _get_sandbox(self) -> SandboxRunner:
        # Built lazily: the API/health path must not require the sandbox user to
        # exist, but the first time generated code would RUN we fail fast if it
        # does not (security posture -- never silently unsandboxed).
        if self._sandbox is None:
            self._sandbox = SandboxRunner()
        return self._sandbox

    def make_workspace(self, task: Dict[str, Any]) -> str:
        ws = task.get("workspace")
        if not ws:
            slug = re.sub(r"[^A-Za-z0-9_-]+", "-", task["title"]).strip("-").lower()[:40]
            ws = os.path.join(config.WORKSPACE_ROOT, f"{slug}-{task['id'][:8]}")
        os.makedirs(ws, exist_ok=True)
        if config.SANDBOX_ENABLED:
            self._get_sandbox().ensure_workspace(ws)
        return ws

    def _verify(self, ws: str, cmd: str):
        """Verify under the sandbox when enabled; plain subprocess only in dev/offline."""
        if config.SANDBOX_ENABLED:
            return self._get_sandbox().run(cmd, ws, config.VERIFY_TIMEOUT_S)
        return run_verify(ws, cmd, config.VERIFY_TIMEOUT_S)

    def execute_once(self, task: Dict[str, Any], system: str, user: str) -> AttemptResult:
        ws = self.make_workspace(task)
        target_file = task.get("target_file") or "solution.py"
        lang_hint = "python" if target_file.endswith(".py") else os.path.splitext(target_file)[1].lstrip(".")
        try:
            resp = self.client.chat(system, user)
        except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as e:
            return AttemptResult(
                code="",
                passed=False,
                error=f"ORNITH CALL FAILED: {type(e).__name__}: {e}",
            )

        code = extract_code_block(resp.get("content", ""), lang_hint)
        path = os.path.join(ws, target_file)
        with open(path, "w") as f:
            f.write(code)
        if config.SANDBOX_ENABLED:
            self._get_sandbox().prepare_file(path)

        error: Optional[str] = None
        wall_v = 0.0
        if task.get("verify_cmd"):
            passed, error, wall_v = self._verify(ws, task["verify_cmd"])
        else:
            # No acceptance command supplied: syntactic validity is the bar.
            try:
                compile(code, path, "exec")
                passed = True
            except SyntaxError as e:
                passed = False
                error = f"SYNTAX ERROR: {e}"

        return AttemptResult(
            code=code,
            passed=passed,
            error=error,
            wall_s=resp.get("wall_s", 0.0),
            gen_tokens=resp.get("completion_tokens", 0),
            gen_tps=resp.get("gen_tps", 0.0),
            meta={"workspace": ws, "target_file": target_file, "verify_wall_s": wall_v},
        )
