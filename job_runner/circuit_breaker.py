#!/usr/bin/env python3
"""circuit_breaker.py -- deterministic confirmation-bias loop breaker.

Part of the Fusion harness batch job scheduler.

HARDWARE CONTRACT (do not break):
  * This is a CPU-side guardrail. It imports ONLY the Python standard
    library and must NEVER touch the iGPU / Vulkan generation path.
  * The Radeon 780M iGPU runs Ornith and only Ornith (pure generation,
    --n-cpu-moe 0). This module does lint/test/loop-detection/hard-stop
    bookkeeping on the CPU and makes zero model calls.

BEHAVIOR (spec):
  1. Hashing is normalized-AST. Raw line text is never hashed, so
     reformatting a broken fix does NOT count as a new attempt.
  2. Freeze -> status "frozen", judgment marked "Compromised Judgment" when:
       - 3 identical code-hash attempts within a cycle, OR
       - 2 identical CONSECUTIVE error signatures.
  3. 2 freeze cycles on the same task -> hard stop "needs human review".
     No further retries are accepted.
  4. After a freeze, retry_context() returns the failed attempts as
     labeled NEGATIVE EXAMPLES, not just a request for a new fix.
"""

from __future__ import annotations

import ast
import hashlib
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ---- tunable thresholds ----------------------------------------------------
FREEZE_CODE_HASH_THRESHOLD = 3     # identical code hashes within a cycle
FREEZE_ERROR_SIG_THRESHOLD = 2     # identical consecutive error signatures
HARD_STOP_FREEZE_CYCLES = 2        # freeze cycles before hard stop

STATUS_ACTIVE = "active"
STATUS_FROZEN = "frozen"
STATUS_HARD_STOP = "needs human review"
COMPROMISED_JUDGMENT = "Compromised Judgment"

REASON_CODE_HASH = "3 identical code-hash attempts"
REASON_ERROR_SIG = "2 identical consecutive error signatures"
REASON_HARD_STOP = "2 freeze cycles on the same task -> needs human review"


def _normalize_whitespace(text: str) -> str:
    """Collapse all runs of whitespace to a single space."""
    return re.sub(r"\s+", " ", text).strip()


def normalize_ast_hash(code: str) -> str:
    """Deterministic structural hash of code, insensitive to reformatting.

    Parses to an AST and hashes the structural dump, so whitespace, line
    breaks, tabs, and comment placement do not affect the hash. Genuinely
    different semantics produce different hashes.

    Syntactically invalid code cannot be parsed; we fall back to a
    whitespace-normalized digest so the SAME broken code with different
    formatting still collides, while genuinely different broken fixes do not.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return hashlib.sha256(
            _normalize_whitespace(code).encode("utf-8")
        ).hexdigest()
    canonical = ast.dump(tree, include_attributes=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def normalize_error_signature(error_text: str) -> str:
    """Stable signature for an error, ignoring volatile details.

    Strips line/column numbers, hex addresses, and timestamps so the same
    underlying failure across runs maps to one signature.
    """
    text = _normalize_whitespace(error_text)
    text = re.sub(r"\bline\s+\d+", "line N", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcolumn\s+\d+", "column N", text, flags=re.IGNORECASE)
    text = re.sub(r"\b0x[0-9a-fA-F]+\b", "0xADDR", text)
    text = re.sub(
        r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?\b",
        "TIMESTAMP",
        text,
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class Attempt:
    code: str
    code_hash: str
    error: Optional[str]                 # raw error text (for negative examples)
    error_signature: Optional[str]       # normalized (for loop detection)
    timestamp: float = field(default_factory=time.time)


@dataclass
class Outcome:
    accepted: bool
    status: str
    attempt_index: int
    freeze_reason: Optional[str] = None
    hard_stop: bool = False


class CircuitBreakerError(RuntimeError):
    """Raised when retries are attempted after a hard stop."""


class CircuitBreaker:
    """Tracks attempts on one task and deterministically breaks loops."""

    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        self.attempts: List[Attempt] = []
        self.freeze_cycles = 0
        self.status = STATUS_ACTIVE
        self.last_freeze_reason: Optional[str] = None
        self._code_hash_counts: Dict[str, int] = {}
        self._last_err_sig: Optional[str] = None
        self._err_sig_run = 0

    # -- recording --------------------------------------------------------

    def record_attempt(self, code: str, error: Optional[str] = None) -> Outcome:
        """Record one attempt (code plus optional error output).

        Attempts are rejected (accepted=False) once the task is hard-stopped.
        """
        if self.status == STATUS_HARD_STOP:
            return Outcome(
                accepted=False,
                status=self.status,
                attempt_index=len(self.attempts),
                hard_stop=True,
            )

        code_hash = normalize_ast_hash(code)
        err_sig = normalize_error_signature(error) if error else None

        self.attempts.append(
            Attempt(
                code=code,
                code_hash=code_hash,
                error=error,
                error_signature=err_sig,
            )
        )
        idx = len(self.attempts) - 1

        # Check 1: 3 identical code hashes within this cycle (not consecutive).
        self._code_hash_counts[code_hash] = (
            self._code_hash_counts.get(code_hash, 0) + 1
        )
        if self._code_hash_counts[code_hash] >= FREEZE_CODE_HASH_THRESHOLD:
            return self._freeze(REASON_CODE_HASH, idx)

        # Check 2: 2 identical CONSECUTIVE error signatures.
        if err_sig is not None:
            if err_sig == self._last_err_sig:
                self._err_sig_run += 1
            else:
                self._err_sig_run = 1
            self._last_err_sig = err_sig
            if self._err_sig_run >= FREEZE_ERROR_SIG_THRESHOLD:
                return self._freeze(REASON_ERROR_SIG, idx)

        return Outcome(accepted=True, status=self.status, attempt_index=idx)

    def _freeze(self, trigger_reason: str, attempt_index: int) -> Outcome:
        self.freeze_cycles += 1
        if self.freeze_cycles >= HARD_STOP_FREEZE_CYCLES:
            self.status = STATUS_HARD_STOP
            self.last_freeze_reason = REASON_HARD_STOP
        else:
            self.status = STATUS_FROZEN
            self.last_freeze_reason = trigger_reason

        # Per-cycle counters reset: a new retry cycle starts clean.
        self._code_hash_counts = {}
        self._last_err_sig = None
        self._err_sig_run = 0

        return Outcome(
            accepted=True,
            status=self.status,
            attempt_index=attempt_index,
            freeze_reason=self.last_freeze_reason,
            hard_stop=(self.status == STATUS_HARD_STOP),
        )

    # -- retry context ----------------------------------------------------

    def retry_context(self, base_prompt: str = "") -> str:
        """Prompt context for the next attempt.

        After a freeze, returns the failed attempts as labeled NEGATIVE
        EXAMPLES (code + error), not just a request for a new fix.
        After a hard stop, raises CircuitBreakerError -- no further retries.
        """
        if self.status == STATUS_HARD_STOP:
            raise CircuitBreakerError(
                f"task {self.task_id!r}: {STATUS_HARD_STOP} "
                f"(freeze cycles={self.freeze_cycles}); no further retries"
            )

        lines = []
        if base_prompt:
            lines.append(base_prompt)
        lines.append(f"TASK: {self.task_id}")

        if self.freeze_cycles == 0:
            lines.append("No prior attempts recorded.")
            return "\n".join(lines)

        lines.append(
            "Previous attempts on this task all FAILED. Do NOT repeat them. "
            "Each labeled negative example below is a concrete failure to "
            "avoid -- study the error and change the approach."
        )
        for i, att in enumerate(self.attempts, start=1):
            lines.append(f"--- NEGATIVE EXAMPLE #{i} (attempt {i}) ---")
            lines.append("CODE (do not reuse):")
            lines.append(att.code.rstrip())
            if att.error is not None:
                lines.append("ERROR (do not reproduce):")
                lines.append(att.error.rstrip())
            else:
                lines.append("ERROR: none recorded")
            lines.append(f"--- END NEGATIVE EXAMPLE #{i} ---")
        return "\n".join(lines)

    # -- inspection -------------------------------------------------------

    @property
    def judgment(self) -> str:
        return COMPROMISED_JUDGMENT if self.freeze_cycles > 0 else "OK"

    def summary(self) -> dict:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "judgment": self.judgment,
            "freeze_cycles": self.freeze_cycles,
            "last_freeze_reason": self.last_freeze_reason,
            "attempts": len(self.attempts),
        }
