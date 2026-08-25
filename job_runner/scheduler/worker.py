"""Sequential batch worker: claims queued tasks and runs them one at a time.

Two independent safety layers (both live here, neither can see the other):

  A. Circuit breaker (per-task, from the verified sibling module): breaks
     confirmation-bias loops with freeze -> fresh context + NEGATIVE examples
     -> retry, hard-stopping to "needs human review" after 2 freeze cycles.

  B. Session outer guard (per-run, whole-night): independent of the circuit
     breaker. Caps the overnight run as a whole by wall-clock time and by
     total tasks processed; either limit alone stops the worker from claiming
     new tasks. Catches infra-level hangs (e.g. the measured memory-floor
     thrash: 190 s for a 1.2 s generation, no error, no crash) that look like
     nothing to the circuit breaker because nothing fails in a way it checks.

  C. Per-attempt stall warning: an attempt that COMPLETES but takes more than
     STALL_FACTOR x the median of recent SUCCESSFUL attempts is flagged even
     though it stayed under every timeout -- that is the same 190 s-vs-1.2 s
     signature, and catching the pattern (not just the timeout) is what would
     have flagged it during the memory-floor DOE.

Crash recovery: on (re)start the worker replays persisted failed attempts into
a fresh CircuitBreaker so loop detection survives worker restarts.

  GUARANTEED PROPERTY (do not "optimize"): replay reconstructs the EXACT
  pre-crash breaker state, not an approximation. CircuitBreaker state is a
  pure function of the ordered (code, error) sequence, and this replay uses
  (1) the exact stored attempt text as persisted -- never re-derived,
  re-normalized, or reformatted -- and (2) the original order (attempt_no ASC,
  see DataStore.list_attempts). Dropping/reordering/re-deriving attempts would
  silently change freeze behavior.
"""
from __future__ import annotations

import os
import statistics
import sys
import threading
import time
from collections import deque
from typing import Any, Dict, List, Optional

# Allow importing the verified sibling module circuit_breaker.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import circuit_breaker as cb_mod  # noqa: E402

from . import config  # noqa: E402
from .db import DataStore, init_db  # noqa: E402
from .executor import Executor  # noqa: E402
from .prompt import SYSTEM_PROMPT, assemble_prompt  # noqa: E402

STOP_REASON_TIME = "stopped: session time limit"
STOP_REASON_TASKS = "stopped: task limit"
STOP_REASON_MANUAL = "stopped: manual shutdown"


def is_stall(attempt_wall_s: float, successful_walls: List[float],
             factor: float = config.STALL_FACTOR,
             min_samples: int = config.STALL_MIN_SAMPLES) -> bool:
    """True if an attempt's wall time is >factor x the median of recent successes.

    Needs >= min_samples successful samples to avoid flagging on a noisy
    bootstrap. Pure function -- unit tested directly.
    """
    if len(successful_walls) < min_samples:
        return False
    med = statistics.median(successful_walls)
    if med <= 0:
        return False
    return attempt_wall_s > factor * med


def _report_md(task: Dict[str, Any], cb: cb_mod.CircuitBreaker,
               attempts: list, final_status: str, note: str = "") -> str:
    lines = [
        f"# Batch report — {task['title']}",
        f"task_id: `{task['id']}`",
        f"final status: **{final_status}**",
        f"judgment: {cb.judgment}  |  freeze cycles: {cb.freeze_cycles}",
        f"attempts: {len(attempts)}",
    ]
    if note:
        lines.append(f"note: {note}")
    lines.append("")
    lines.append("| # | status | code_hash[:8] | error_sig[:8] | wall_s | gen_tok | t/s | stall |")
    lines.append("|---|--------|--------------|---------------|--------|---------|-----|-------|")
    for a in attempts:
        wall = a.get("wall_s") or 0.0
        tps = a.get("gen_tps") or 0.0
        lines.append(
            f"| {a['attempt_no']} | {a['status']} | {(a.get('code_hash') or '')[:8] or '-'} "
            f"| {(a.get('error_signature') or '')[:8] or '-'} | {wall:.1f} "
            f"| {a.get('gen_tokens') or 0} | {tps:.1f} | {'⚠' if a.get('stall_warning') else ''} |"
        )
    lines.append("")
    if attempts and attempts[-1].get("error"):
        lines.append("## Last error")
        lines.append("```")
        lines.append(str(attempts[-1]["error"])[:2000])
        lines.append("```")
    return "\n".join(lines)


class Worker:
    def __init__(self, store: Optional[DataStore] = None,
                 executor: Optional[Executor] = None,
                 poll_interval: float = config.POLL_INTERVAL_S,
                 stop: Optional[threading.Event] = None) -> None:
        self.store = store or DataStore()
        self.executor = executor or Executor()
        self.poll = poll_interval
        self.stop = stop or threading.Event()
        # session state
        self.session_id: Optional[str] = None
        self.session_started: float = 0.0
        self.success_walls: deque = deque(maxlen=config.STALL_MEDIAN_WINDOW)
        self._worker_active = False

    # -- session guard -----------------------------------------------------

    def _limit_reason(self) -> Optional[str]:
        """Both outer limits are checked every loop iteration; either one stops the run."""
        if config.SESSION_MAX_HOURS > 0:
            elapsed_h = (time.time() - self.session_started) / 3600.0
            if elapsed_h >= config.SESSION_MAX_HOURS:
                return STOP_REASON_TIME
        if config.SESSION_MAX_TASKS > 0 and self.session_id:
            tasks = (self.store.get_session(self.session_id) or {}).get("tasks_processed", 0)
            if tasks >= config.SESSION_MAX_TASKS:
                return STOP_REASON_TASKS
        return None

    def _end_session(self, reason: str) -> None:
        if not self.session_id:
            return
        self._worker_active = False
        self.store.end_session(self.session_id, reason)
        s = self.store.get_session(self.session_id) or {}
        self._write_session_report(s, reason)
        print(f"\n[scheduler] ========== SESSION STOPPED: {reason} ==========")
        print(f"[scheduler] session {self.session_id} | tasks processed: {s.get('tasks_processed', 0)}"
              f" | stall warnings: {s.get('stall_warnings', 0)}")
        print("[scheduler] state is reviewable via GET /api/v1/session and reports/session-*.md")

    def _write_session_report(self, s: Dict[str, Any], reason: str) -> None:
        try:
            path = os.path.join(config.REPORTS_DIR, f"session-{self.session_id}.md")
            tasks = self.store.list_tasks_since(s.get("started_at") or "")
            lines = [
                "# Session report",
                f"session_id: `{self.session_id}`",
                f"started: {s.get('started_at')}",
                f"stopped: {s.get('stopped_at')}",
                f"stop reason: **{reason}**",
                f"tasks processed: {s.get('tasks_processed', 0)}",
                f"stall warnings: {s.get('stall_warnings', 0)}",
                "",
                "## Tasks this session",
                "",
                "| status | title | task_id[:8] |",
                "|--------|-------|-------------|",
            ]
            for t in tasks:
                lines.append(f"| {t['status']} | {t['title']} | {t['id'][:8]} |")
            os.makedirs(config.REPORTS_DIR, exist_ok=True)
            with open(path, "w") as f:
                f.write("\n".join(lines) + "\n")
        except Exception as e:  # noqa: BLE001 -- report write must never crash the loop
            print(f"[scheduler] WARNING: could not write session report: {e}")

    # -- main loop ---------------------------------------------------------

    def run_forever(self) -> None:
        n = self.store.recover_stale_running()
        if n:
            print(f"[scheduler] re-queued {n} stale running task(s) for crash recovery")
        self.session_id = self.store.start_session()
        self.session_started = time.time()
        self._worker_active = True
        print(f"[scheduler] session started: {self.session_id} | max hours: "
              f"{config.SESSION_MAX_HOURS if config.SESSION_MAX_HOURS > 0 else 'unlimited'} | "
              f"max tasks: {config.SESSION_MAX_TASKS if config.SESSION_MAX_TASKS > 0 else 'unlimited'}")

        while not self.stop.is_set():
            reason = self._limit_reason()
            if reason:
                self._end_session(reason)
                return
            task = self.store.claim_next()
            if task is None:
                self.stop.wait(self.poll)
                continue
            try:
                self.run_task(task)
            except Exception as e:  # noqa: BLE001 -- never let a task kill the loop
                self.store.set_status(task["id"], "failed", f"WORKER ERROR: {type(e).__name__}: {e}")
                self.store.telemetry(task["id"], "worker_error", 1)
            if self.session_id:
                self.store.bump_session_tasks(self.session_id)

    # -- one task ---------------------------------------------------------

    def run_task(self, task: Dict[str, Any]) -> None:
        cb = cb_mod.CircuitBreaker(task["id"])
        attempts_log: list = list(self.store.list_attempts(task["id"]))
        note = "manual human-review retry (fresh cycle)" if task.get("fresh") else "auto"

        # Crash recovery: replay persisted attempts (guaranteed-exact, see module docstring).
        if not task.get("fresh"):
            for a in attempts_log:
                if a["status"] in ("failed", "frozen"):
                    out = cb.record_attempt(a.get("code") or "", a.get("error"))
                    if out.hard_stop:
                        report = _report_md(task, cb, attempts_log, "needs_review",
                                            "hard stop reached during crash replay")
                        self.store.finish(task["id"], "needs_review", cb.summary(), report)
                        return

        while True:
            # Honor a cancel request between attempts.
            cur = self.store.get_task(task["id"])
            if cur and cur.get("cancel_requested"):
                self.store.set_status(task["id"], "aborted", "cancelled by request")
                return

            try:
                negative = cb.retry_context()
            except cb_mod.CircuitBreakerError:
                report = _report_md(task, cb, attempts_log, "needs_review",
                                    f"{note}; {cb.last_freeze_reason}")
                self.store.finish(task["id"], "needs_review", cb.summary(), report)
                return

            ws = self.executor.make_workspace(task)
            user = assemble_prompt(
                title=task["title"], description=task.get("description", ""),
                constraints=task.get("constraints", []), tools=task.get("tools", []),
                workspace=ws, target_file=task.get("target_file") or "solution.py",
                negative_examples=negative,
            )

            result = self.executor.execute_once(task, SYSTEM_PROMPT, user)

            # Per-attempt stall check (the 190s-vs-1.2s thrash signature): an attempt
            # that completes under every timeout but blows past the median of recent
            # SUCCESSFUL attempts gets flagged even though nothing errored.
            attempt_wall = result.wall_s + float(result.meta.get("verify_wall_s", 0.0) or 0.0)
            stall = is_stall(attempt_wall, list(self.success_walls))
            if stall:
                print(f"[scheduler] STALL WARNING: task {task['id'][:8]} attempt wall {attempt_wall:.1f}s "
                      f"> {config.STALL_FACTOR}x median of recent successful attempts "
                      f"({statistics.median(self.success_walls):.1f}s) -- infra-level slowdown, not a code loop")
                if self.session_id:
                    self.store.add_session_stall(self.session_id)
                self.store.telemetry(task["id"], "stall_warning", attempt_wall)

            code_hash = cb_mod.normalize_ast_hash(result.code)
            err_sig = (cb_mod.normalize_error_signature(result.error)
                       if (not result.passed and result.error) else None)
            outcome = cb.record_attempt(
                result.code,
                None if result.passed else (result.error or "verify failed"),
            )
            attempt_no = len(attempts_log) + 1
            status = "passed" if result.passed else (
                "frozen" if outcome.status == cb_mod.STATUS_FROZEN else "failed"
            )
            self.store.add_attempt(
                task["id"], attempt_no, status, result.code,
                result.error if not result.passed else None,
                code_hash, err_sig, user,
                freeze_reason=outcome.freeze_reason,
                wall_s=result.wall_s, gen_tokens=result.gen_tokens, gen_tps=result.gen_tps,
                stall_warning=1 if stall else 0,
            )
            attempts_log = self.store.list_attempts(task["id"])

            self.store.telemetry(task["id"], "gen_wall_s", result.wall_s)
            self.store.telemetry(task["id"], "gen_tps", result.gen_tps)
            self.store.telemetry(task["id"], "attempt_wall_s", attempt_wall)

            if result.passed:
                self.success_walls.append(attempt_wall)
                report = _report_md(task, cb, attempts_log, "succeeded", note)
                self.store.finish(task["id"], "succeeded", cb.summary(), report)
                return

            if outcome.hard_stop:
                report = _report_md(task, cb, attempts_log, "needs_review",
                                    f"{note}; hard stop after {cb.freeze_cycles} freeze cycles")
                self.store.finish(task["id"], "needs_review", cb.summary(), report)
                return

            if attempt_no >= config.MAX_TOTAL_ATTEMPTS:
                report = _report_md(task, cb, attempts_log, "needs_review",
                                    f"absolute attempt cap ({config.MAX_TOTAL_ATTEMPTS}) hit")
                self.store.finish(task["id"], "needs_review", cb.summary(), report)
                return
            # else: active (retry normally) or frozen (next prompt includes negatives)
            self.stop.wait(config.CANCEL_CHECK_INTERVAL)

    @property
    def active(self) -> bool:
        return self._worker_active


def run_once(task_id: str) -> int:
    """CLI: run a single task through the full pipeline (testing/ops)."""
    init_db()
    store = DataStore()
    task = store.get_task(task_id)
    if task is None:
        print(f"task {task_id} not found")
        return 1
    Worker(store=store).run_task(task)
    print("final:", store.get_task(task_id)["status"])
    return 0


def main() -> None:
    init_db()
    w = Worker()
    try:
        w.run_forever()
    except KeyboardInterrupt:
        print("\n[scheduler] Ctrl-C received")
        w._end_session(STOP_REASON_MANUAL)
