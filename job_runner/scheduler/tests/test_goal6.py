"""Goal 6 -- meta-orchestration control-loop tests (pure, no DB).

Verifies first that the decision functions are deterministic and bounded, then
that the stateful MetaController turns sustained telemetry into a cooldown /
temperature override without ever stopping anything itself.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest

from scheduler.controller import (
    MetaController, detect_collapse, recommend_temperature,
)


# ---------------------------------------------------------------------------
# Pure decision functions
# ---------------------------------------------------------------------------
def test_detect_collapse_needs_full_window():
    # one slow sample is not enough
    assert detect_collapse([100.0, 0.5, 100.0], threshold=5.0, n_samples=3) is False


def test_detect_collapse_sustained():
    assert detect_collapse([0.4, 0.5, 0.1], threshold=5.0, n_samples=3) is True


def test_detect_collapse_ignores_burst():
    # a single fast sample inside the window breaks the sustained signature
    assert detect_collapse([0.4, 90.0, 0.1], threshold=5.0, n_samples=3) is False


def test_detect_collapse_insufficient_history():
    assert detect_collapse([0.1], threshold=5.0, n_samples=3) is False


def test_recommend_keeps_base_when_unknown():
    assert recommend_temperature(None, base_temp=0.2, min_temp=0.1, max_temp=0.6) == 0.2


def test_recommend_raises_when_stuck():
    t = recommend_temperature(0.1, base_temp=0.2, min_temp=0.1, max_temp=0.6)
    assert t > 0.2
    assert 0.1 <= t <= 0.6


def test_recommend_lowers_when_passing():
    t = recommend_temperature(0.9, base_temp=0.2, min_temp=0.1, max_temp=0.6)
    assert t < 0.2


def test_recommend_clamps_to_range():
    t = recommend_temperature(0.9, base_temp=0.2, min_temp=0.25, max_temp=0.6)
    assert t >= 0.25, "must never drop below min even with high success ratio"
    t2 = recommend_temperature(0.1, base_temp=0.6, min_temp=0.1, max_temp=0.35)
    assert t2 <= 0.35, "must never exceed max"


# ---------- Stateful loop (hermetic: no DB, no model) ----------
def test_controller_no_action_when_healthy():
    c = MetaController(cooldown_s=30.0)
    action = c.record(1.2, 500.0, stall=False, passed=True)
    assert action.cooldown_s == 0.0
    assert action.reason == "no_adjustment"


def test_controller_emits_cooldown_on_sustained_collapse():
    # infuse a sustained slow tps window (collapse_samples=4) then record
    c = MetaController()
    for tps in (0.2, 0.2, 0.2, 0.2, 0.2):
        action = c.record(190.0, tps, stall=False, passed=False)
    # the last record sees the full sustained slow window -> cooldown
    assert action.cooldown_s > 0.0
    assert "collapse" in action.reason


def test_controller_temperature_override_present():
    # low success ratio should push temperature up slightly
    c = MetaController()
    for _ in range(6):
        c.record(1.2, 500.0, stall=False, passed=False)
    assert c.last_temp > c.base_temp
