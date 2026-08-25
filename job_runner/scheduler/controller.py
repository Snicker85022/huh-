"""Goal 6 -- meta-orchestration control loop.

The handoff noted: telemetry (gen_wall_s, gen_tps, stall_warning) was logged to
the DB on every attempt, but nothing read it back to adjust temperature,
throttling, or anything else -- it was a data log, not a control loop. This
module closes that loop. It watches the live per-attempt telemetry (fed to it
by the worker, which is the only writer of that stream) and reacts:

  * THERMOSTAT: an adaptive, bounded adjustment to the sampling temperature
    from the recent task success ratio -- more deterministic when the model is
    passing, slightly more exploratory when it is stuck.
  * THROTTLE: an infra-collapse cooldown. The memory-floor DOE measured a
    SUSTAINED silent collapse to ~0.1 tok/s (190 s for a 1.2 s generation, no
    error, no crash). That signature is a sustained run of very-low tps +
    stall warnings, NOT a one-off; the controller responds with a pause between
    tasks (throttling) so the overnight run does not burn hours on a thrashing
    KV cache. The session outer guard still does the hard stopping; the
    controller never stops or kills anything itself.

Architectural rules (consistent with the rest of the harness):
  * CPU-only, deterministic, stdlib-only: no model in the control path.
  * Pure decision functions (unit-testable) + a thin live state holder.
  * Everything bounded: temperature clamped to [min,max]; cooldown clamped to
    [0,max]. One bad sample never triggers a cooldown -- it needs the SUSTAINED
    signature, catching the measured thrash pattern (not a single timeout).
  * It is an ADVISOR to the worker: it never writes, never raises, never
    touches Ornith's locked server config.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Optional, Sequence

from . import config


# ---------------------------------------------------------------------------
# Pure decision functions (no state -> directly unit-testable)
# ---------------------------------------------------------------------------
def detect_collapse(tps_samples: Sequence[float],
                    threshold: float,
                    n_samples: int) -> bool:
    """True iff the last `n_samples` tps values are ALL <= threshold.

    Requires a sustained run, so a single transient blip never triggers it --
    exactly the measured thrash signature (collapse to ~0.1 tok/s lasted many
    attempts), not a one-off timeout.
    """
    if n_samples <= 0:
        return False
    recent = list(tps_samples)[-n_samples:]
    if len(recent) < n_samples:
        return False
    return all(t <= threshold for t in recent)


def recommend_temperature(recent_success_ratio: Optional[float],
                          base_temp: float,
                          min_temp: float,
                          max_temp: float) -> float:
    """Small, clamped temperature adjustment from recent success ratio.

      None (not enough data) -> keep base.
      ratio >= 0.6  -> working well; ease 0.06 toward deterministic.
      ratio <= 0.3  -> stuck; nudge 0.06 toward exploration (circuit-breaker
                       negatives still discipline the search).
      else          -> keep base.
    Change magnitude is tiny (never stomps the DOE-locked sampling), hard-
    clamped to [min_temp, max_temp].
    """
    if recent_success_ratio is None:
        return base_temp
    if recent_success_ratio >= 0.6:
        target = base_temp - 0.06
    elif recent_success_ratio <= 0.3:
        target = base_temp + 0.08
    else:
        target = base_temp
    return max(min_temp, min(max_temp, target))


# ---------------------------------------------------------------------------
# Live state holder + actions
# ---------------------------------------------------------------------------
@dataclass
class ControlAction:
    cooldown_s: float = 0.0
    temperature: Optional[float] = None
    reason: str = "no_adjustment"


class MetaController:
    """Stateful control loop. Feed it each completed attempt's metrics, get back
    the action for the worker to apply (cooldown delay + temperature override)."""

    def __init__(
        self,
        window: int = config.CONTROL_WINDOW,
        slow_threshold_tps: float = config.CONTROL_SLOW_TPS,
        collapse_samples: int = config.CONTROL_COLLAPSE_SAMPLES,
        base_temp: float = config.TEMP,
        min_temp: float = config.CONTROL_MIN_TEMP,
        max_temp: float = config.CONTROL_MAX_TEMP,
        cooldown_s: float = config.CONTROL_COOLDOWN_S,
    ) -> None:
        self.slow_threshold_tps = slow_threshold_tps
        self.collapse_samples = collapse_samples
        self.base_temp = base_temp
        self.min_temp = min_temp
        self.max_temp = max_temp
        self.cooldown_s = cooldown_s
        self.tps_window: Deque[float] = deque(maxlen=window)
        self.results_window: Deque[int] = deque(maxlen=config.CONTROL_RESULT_WINDOW)
        self.last_temp: float = base_temp
        self.in_cooldown = False
        self.actions: List[dict] = []

    # -- feed one attempt -------------------------------------------------
    def record(self, wall_s: float, tps: float, stall: bool, passed: bool,
               now: Optional[float] = None) -> ControlAction:
        self.tps_window.append(float(tps))
        self.results_window.append(1 if passed else 0)

        reason = "no_adjustment"
        cooldown = 0.0
        temp: Optional[float] = None

        # Thermostat.
        sr = self._success_ratio()
        new_temp = recommend_temperature(sr, self.base_temp, self.min_temp, self.max_temp)
        if abs(new_temp - self.last_temp) > 1e-9:
            temp = new_temp
            self.last_temp = new_temp

        # Infra-collapse throttle (sustained condition AND a stall signal seen).
        if detect_collapse(self.tps_window, self.slow_threshold_tps, self.collapse_samples):
            cooldown = min(self.cooldown_s, 300.0)
            self.in_cooldown = True
            reason = "cooldown_sustained_collapse"
        else:
            self.in_cooldown = False

        self.actions.append({
            "ts": now if now is not None else time.time(),
            "reason": reason,
            "cooldown_s": cooldown,
            "temperature": temp,
            "passed": passed,
            "recent_success_ratio": sr,
        })
        return ControlAction(cooldown_s=cooldown, temperature=temp, reason=reason)

    # -- helpers ------------------------------------------------------------
    def _success_ratio(self) -> Optional[float]:
        if not self.results_window:
            return None
        return sum(self.results_window) / len(self.results_window)

    def persist(self, store, task_id: Optional[str] = None) -> None:
        """Persist the latest control action to the store telemetry (metric prefix
        'adjust_'). Non-fatal if the store is unavailable."""
        if not self.actions:
            return
        a = self.actions[-1]
        try:
            store.telemetry(task_id, f"adjust_{a['reason']}", float(a['cooldown_s']))
        except Exception:  # noqa: BLE001 -- control-loop logging must never break the worker
            pass
