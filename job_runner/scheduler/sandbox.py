"""Sandbox for model-generated code (review decision 2026-08-25).

verify_cmd runs code the model just wrote, on the same box as production Ornith,
LibreChat, and everything else. v1 policy (lightweight, real, no containerization
yet):

  * The verify subprocess runs as an unprivileged user (ornith-sandbox, nologin),
    via `sudo -n -u ornith-sandbox ...` -- NEVER as root, NEVER as the taza
    account that owns the repo/models/secrets.
  * resource.setrlimit caps (RLIMIT_CPU, RLIMIT_AS, RLIMIT_FSIZE) are applied
    via the bash `ulimit` builtin inside the sandbox shell, as the sandbox user.
    A runaway generation cannot spin the CPU forever, exhaust RAM, or write a
    huge file. (preexec_fn RLIMIT_AS was measured broken on this box -- it
    breaks sudo's libc mapping -- so the limits are set in-shell instead.)
  * The task workspace (under WORKSPACE_ROOT) is chowned to the sandbox user and
    is the only writable tree it gets: its shell is nologin, HOME/TMPDIR point
    into the workspace, and every other writable surface it could touch is
    outside its uid's reach. Full containerization is deferred until there is a
    real need.

If the sandbox user is missing, we REFUSE to run generated code rather than
silently falling back to unsandboxed execution (fail fast -- security posture).
"""
from __future__ import annotations

import os
import signal
import subprocess
import time
from typing import Optional, Tuple

from . import config


class SandboxRunner:
    def __init__(self, user: Optional[str] = None, enabled: Optional[bool] = None,
                 cpu_s: Optional[float] = None, mem_mb: Optional[int] = None,
                 fsize_mb: Optional[int] = None) -> None:
        self.user = user or config.SANDBOX_USER
        self.group = self.user
        self.enabled = config.SANDBOX_ENABLED if enabled is None else enabled
        self.cpu_s = cpu_s if cpu_s is not None else config.SANDBOX_CPU_S
        self.mem_bytes = (mem_mb if mem_mb is not None else config.SANDBOX_MEM_MB) * 1024 * 1024
        self.fsize_bytes = (fsize_mb if fsize_mb is not None else config.SANDBOX_FSIZE_MB) * 1024 * 1024
        if self.enabled:
            self.ensure_user()

    # -- setup --------------------------------------------------------------

    def ensure_user(self) -> None:
        import grp
        import pwd
        try:
            pwd.getpwnam(self.user)
            grp.getgrnam(self.group)
        except KeyError as e:
            raise RuntimeError(
                f"sandbox user/group {self.user!r} not found -- run "
                f"job_runner/scheduler/setup_sandbox.sh once. Refusing to run "
                f"model-generated code unsandboxed on a production box."
            ) from e

    def _sudo(self, *args: str) -> None:
        subprocess.run(["sudo", "-n", *args], check=True, capture_output=True, text=True)

    # -- workspace / file ownership -----------------------------------------

    def ensure_workspace(self, ws: str) -> None:
        """Workspace becomes sandbox-owned (user:group, 0770).

        The dir is created AS the sandbox user via sudo, so this never depends
        on the scheduler process having the sandbox group in its login session.
        Mode 0770 keeps the scheduler (group member) able to drop the solution
        file in on the next attempt."""
        self._sudo("-u", self.user, "mkdir", "-p", ws)
        self._sudo("chmod", "0770", ws)
        tmp = os.path.join(ws, ".tmp")
        self._sudo("-u", self.user, "mkdir", "-p", tmp)
        self._sudo("chmod", "0770", tmp)

    def prepare_file(self, path: str) -> None:
        """Solution file becomes sandbox-readable (and group-writable so the
        scheduler can overwrite it on the next attempt)."""
        self._sudo("chown", f"{self.user}:{self.group}", path)
        self._sudo("chmod", "0660", path)

    # -- execution ------------------------------------------------------------

    def _ulimit_prefix(self) -> str:
        """Caps applied INSIDE the sandboxed shell, as the sandbox user.

        Measured decision (2026-08-25): applying RLIMIT_AS via preexec_fn in the
        scheduler process is broken on this box -- the forked child inherits the
        scheduler's large address space, and sudo then fails to map libc
        ("failed to map segment from shared object"). Applying the SAME
        resource.setrlimit caps via the bash `ulimit` builtin (RLIMIT_AS/-v,
        RLIMIT_CPU/-t, RLIMIT_FSIZE/-f) inside the sandbox shell is robust,
        runs as the unprivileged user, and is inherited by every child.
        """
        mem_kb = self.mem_bytes // 1024
        fsize_kb = self.fsize_bytes // 1024
        return f"ulimit -v {mem_kb} -t {int(self.cpu_s)} -f {fsize_kb}; "

    def run(self, cmd: str, cwd: str, timeout: float) -> Tuple[bool, str, float]:
        t0 = time.time()
        if not self.enabled:
            # dev/offline only -- NO privilege drop. Never point a production
            # SCHED_SANDBOX_ENABLED=0 at a box with real data.
            p = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True,
                               text=True, timeout=timeout)
            out = (p.stdout or "") + ("\n" if p.stdout and p.stderr else "") + (p.stderr or "")
            return p.returncode == 0, out.strip(), time.time() - t0

        tmp = os.path.join(cwd, ".tmp")
        argv = ["sudo", "-n", "-u", self.user, "env",
                f"HOME={cwd}", f"TMPDIR={tmp}",
                "bash", "-lc", self._ulimit_prefix() + cmd]
        try:
            p = subprocess.Popen(argv, cwd=cwd, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True,
                                 start_new_session=True)
            try:
                out, err = p.communicate(timeout=timeout)
                rc = p.returncode
            except subprocess.TimeoutExpired:
                # kill the WHOLE sandbox process group, not just sudo
                try:
                    os.killpg(os.getpgid(p.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
                p.communicate()
                return False, f"VERIFY TIMEOUT after {timeout:.0f}s (sandboxed; process group killed)", time.time() - t0
        except FileNotFoundError as e:
            return False, f"sandbox runner error: {e}", time.time() - t0

        output = (out or "") + ("\n" if out and err else "") + (err or "")
        return rc == 0, output.strip(), time.time() - t0


def verify_sandbox(runner: Optional[SandboxRunner] = None) -> dict:
    """Probe the sandbox really is a box: writable workspace, no escape to the
    repo/root-owned trees, memory cap enforced. Returns {check: bool}."""
    r = runner or SandboxRunner()
    results: dict = {}
    os.makedirs(config.WORKSPACE_ROOT, exist_ok=True)
    scratch = os.path.join(config.WORKSPACE_ROOT, f"probe-{int(time.time())}")
    try:
        r.ensure_workspace(scratch)
        ok, out, _ = r.run("touch probe-ok && test -f probe-ok && echo WRITE_OK", scratch, 15)
        results["workspace_write"] = bool(ok) and "WRITE_OK" in out

        ok, out, _ = r.run("touch /home/taza/repo/.sandbox_probe && echo LEAK", scratch, 15)
        results["no_escape_to_repo"] = bool(not ok) and "LEAK" not in out
        if ok:  # unexpected leak; clean up the stray file we own
            try:
                os.unlink("/home/taza/repo/.sandbox_probe")
            except OSError:
                pass

        ok, out, _ = r.run("touch /etc/.sandbox_probe && echo LEAK", scratch, 15)
        results["no_escape_to_root_owned"] = bool(not ok) and "LEAK" not in out

        ok, out, _ = r.run(
            "python3 -c 'x=[0]*300_000_000' 2>/dev/null && echo NO_LIMIT || echo MEM_LIMITED",
            scratch, 30,
        )
        results["mem_cap_enforced"] = "MEM_LIMITED" in out
    finally:
        import shutil
        shutil.rmtree(scratch, ignore_errors=True)
    return results
