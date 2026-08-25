"""Goal 3 -- error distillation (3a known-fix cache / 3b novel-error fallback).

What was missing (handoff 2026-08-25): the circuit breaker only does *in-task*
loop detection. There was no CROSS-TASK cache of known fixes (3a) and no
working novel-error-distillation path (3b). This module supplies both, CPU-only
(no iGPU), deterministic, zero new runtime dependencies.

3a  KNOWN-FIX CACHE (cross-task). Learned from PAST SUCCEEDED tasks already in
    the store database. The invariant: if task T failed with error signature E
    and T *eventually* succeeded, then the error fixed by T's final successful
    code is a *known fix for E*. Next time any fresh task fails with the same E,
    we inject that prior fix as a positive hint BEFORE Ornith wastes attempts
    re-deriving it -- a cross-task cache, not the in-task loop detection the
    circuit breaker already does. Derived from the attempts table at runtime,
    so it is always self-consistent with what actually succeeded -- no separate
    bookkeeping to drift.

3b  NOVEL-ERROR DISTILLATION (fallback path). An error signature NOT in the
    known-fix cache is *novel*. We distill it into a portable, cached lesson
    (root cause + fix hint) via an injectable distiller callable. Default
    distiller uses the same locked local Ornith endpoint (client of :8082, same
    discipline as executor.py -- never touches the iGPU directly). The lesson is
    persisted to a small JSON cache (config.DISTILL_LESSONS_PATH) so the same
    novel error never pays for distillation twice, even across worker restarts.
    If no model/distiller is available the module degrades to a deterministic
    dry-run lesson (root cause = normalized error head) -- it never hard-fails
    the worker loop.

    Why local Ornith instead of an off-box model? The end-goal is an autonomous
    over-night harness; adding a network+key dependency into the failure path
    violates the "no blind trust in infrastructure" rule. Local Ornith is already
    running and already the model the whole harness is built around. The
    distillation callable is injected through a seam, so a cheaper/remote model
    (DeepSeek V4 Flash, GPT-5.6 Luna, a quantized local draft) can be swapped in
    without touching the loop.
"""
from __future__ import annotations

import json
import os
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from . import config


# ---------------------------------------------------------------------------
# 3a -- Known-fix cache, derived from the attempts table
# ---------------------------------------------------------------------------
@dataclass
class KnownFix:
    """A fix known to resolve a specific (normalized) error signature."""
    error_signature: str
    fix_code: str                       # the code that finally succeeded
    root_cause: str = ""                # head of the error it resolved
    source_task_id: str = ""
    occurrences: int = 1
    fix_hint: str = ""

    def to_prompt(self) -> str:
        """Positive guidance block injected when this signature recurs on a new task."""
        lines = [
            "A PREVIOUS task on this machine hit THIS EXACT error signature and",
            "eventually resolved it. The following is a KNOWN FIX -- study it and",
            "adapt it rather than re-deriving from scratch:",
            "--- KNOWN FIX CODE (from past task) ---",
            self.fix_code.rstrip(),
        ]
        if self.fix_hint:
            lines.insert(1, f"NOTE FROM PAST RESOLUTION: {self.fix_hint}")
        return "\n".join(lines)


class KnownFixIndex:
    """Cross-task map error_signature -> KnownFix, rebuilt from the store DB.

    Built cheaply on demand (a couple of indexed queries over the attempts and
    tasks tables), so it always reflects what HAS actually succeeded and needs
    no separate persistence -- the successes live in the DB and this is a pure
    read projection.
    """

    def __init__(self) -> None:
        self._by_sig: Dict[str, KnownFix] = {}
        self._lock = threading.Lock()

    def lookup(self, error_signature: str) -> Optional[KnownFix]:
        with self._lock:
            return self._by_sig.get(error_signature)

    def add(self, fix: KnownFix) -> None:
        with self._lock:
            cur = self._by_sig.get(fix.error_signature)
            if cur is None:
                self._by_sig[fix.error_signature] = fix
            else:
                cur.occurrences += 1
                if not cur.fix_hint and fix.fix_hint:
                    cur.fix_hint = fix.fix_hint

    def __len__(self) -> int:
        return len(self._by_sig)

    # -- construction ------------------------------------------------------
    @classmethod
    def scan(cls, store: Any) -> "KnownFixIndex":
        """Build from all tasks that FINALLY SUCCEEDED.

        For each succeeded task we read every failure it logged before the
        success. Each such failure's error_signature is a bug that the task's
        own eventual success fixed, so we record that fix for ANY future task
        that hits the same signature.
        """
        idx = cls()
        for t in store.list_tasks("succeeded"):
            attempts = store.list_attempts(t["id"])
            # Last attempt in the list is the successful one (attempt_no ASC).
            success = None
            for a in reversed(attempts):
                if a.get("status") == "passed":
                    success = a
                    break
            if success is None:
                continue
            for a in attempts:
                sig = a.get("error_signature")
                if not sig:
                    continue
                idx.add(KnownFix(
                    error_signature=sig,
                    fix_code=success.get("code") or "",
                    root_cause=a.get("error") or "",
                    source_task_id=t["id"],
                    fix_hint="",
                ))
        return idx


# ---------------------------------------------------------------------------
# 3b. Novel-error distillation + JSON lesson cache
# ---------------------------------------------------------------------------
@dataclass
class DistillLesson:
    error_signature: str
    root_cause: str
    fix_hint: str
    source_task_id: str = ""
    distilled_at: str = ""

    def to_prompt(self) -> str:
        return (
            "A previous occurrence of this error on this machine was analyzed. "
            f"DISTILLED ROOT CAUSE: {self.root_cause}\n"
            f"DISTILLED FIX HINT: {self.fix_hint}"
        )


def normalize_error_head(error_text: str, n_lines: int = 2) -> str:
    """Cheap, deterministic fallback 'root cause': the first lines of the error."""
    lines = [l.strip() for l in (error_text or "").splitlines() if l.strip()]
    return " | ".join(lines[:n_lines]) or "(no error text)"


class LessonCache:
    """On-disk JSON cache of distilled lessons (cross-session persistence).

    Thread-safe with a lock; writes atomically via temp-file + rename so a
    crash mid-write never corrupts the cache.
    """

    def __init__(self, path: Optional[str] = None) -> None:
        self.path = path or os.path.join(config.DATA_DIR, "distill_lessons.json")
        self._lock = threading.Lock()
        self._data: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        with self._lock:
            if not os.path.exists(self.path):
                return
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (OSError, ValueError):
                # Corrupt / unreadable cache is not fatal: rebuild from scratch.
                self._data = {}

    def get(self, error_signature: str) -> Optional[DistillLesson]:
        with self._lock:
            d = self._data.get(error_signature)
        if not d:
            return None
        return DistillLesson(
            error_signature=error_signature,
            root_cause=d.get("root_cause", ""),
            fix_hint=d.get("fix_hint", ""),
            source_task_id=d.get("source", ""),
            distilled_at=d.get("distilled_at", ""),
        )

    def put(self, lesson: DistillLesson) -> None:
        with self._lock:
            self._data[lesson.error_signature] = {
                "root_cause": lesson.root_cause,
                "fix_hint": lesson.fix_hint,
                "source": lesson.source_task_id,
                "distilled_at": lesson.distilled_at,
            }
            self._flush_locked()

    def _flush_locked(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=1)
        os.replace(tmp, self.path)


def distill_lesson(error_text: str) -> DistillLesson:
    """Default no-model distiller: deterministic head of the error.

    Used when no LLM distiller is injected (dev/offline/tests) and is the
    always-safe fallback if a real distiller raises. It never blocks the loop.
    """
    root = normalize_error_head(error_text)
    return DistillLesson(
        error_signature="",
        root_cause=root,
        fix_hint="No auto-fix derivable; review the error in context.",
    )


# distiller signature: (error_text, code) -> (root_cause, fix_hint)
DistillerFn = Callable[[str, str], "tuple[str, str]"]


class ErrorDistiller:
    """Facade the worker uses to turn a failed attempt into next-attempt guidance.

    Pipeline for a failed attempt with signature S:
      1. Known-fix cache hit  -> return the known fix (positive hint), no distiller.
      2. Novel, already distilled -> return the cached lesson.
      3. Novel, never distilled  -> run the model distiller (injected), persist
         the lesson to the JSON cache so we never pay twice, return it.
    Returns the prompt text to inject, or "" if there is nothing useful.
    """

    def __init__(
        self,
        store: Any,
        lesson_path: Optional[str] = None,
        distiller: Optional[DistillerFn] = None,
    ) -> None:
        self.store = store
        self.known = KnownFixIndex.scan(store)
        self.lessons = LessonCache(lesson_path)
        self.distiller = distiller

    def guidance_for(self, error_signature: str, error_text: str,
                     code: str) -> str:
        if not error_signature:
            return ""
        fix = self.known.lookup(error_signature)
        if fix is not None:
            return fix.to_prompt()
        cached = self.lessons.get(error_signature)
        if cached is not None:
            return cached.to_prompt()
        # Novel error: distill and cache.
        root, hint = self._distill(error_text, code)
        lesson = DistillLesson(
            error_signature=error_signature,
            root_cause=root,
            fix_hint=hint,
            source_task_id="",
            distilled_at=__import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
        )
        self.lessons.put(lesson)
        return lesson.to_prompt()

    def _distill(self, error_text: str, code: str):
        if self.distiller is not None:
            try:
                root, hint = self.distiller(error_text, code)
                if root:
                    return root, hint
            except Exception:  # noqa: BLE001 -- never let distillation break the loop
                pass
        fallback = distill_lesson(error_text)
        return fallback.root_cause, fallback.fix_hint
