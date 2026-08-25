"""Outer session guard + per-attempt stall detection -- unit tests."""
import os, sys, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest

import scheduler.config as config
from scheduler.worker import is_stall, STOP_REASON_TIME, STOP_REASON_TASKS
from scheduler.db import DataStore, init_db


def test_stall_requires_min_samples():
    assert is_stall(190.0, [], factor=10, min_samples=3) is False
    assert is_stall(190.0, [1.2, 1.3], factor=10, min_samples=3) is False


def test_stall_flagged_above_factor():
    # the measured thrash signature: 190s vs ~1.2s median
    assert is_stall(190.0, [1.2, 1.1, 1.3], factor=10, min_samples=3) is True


def test_stall_not_flagged_under_factor():
    assert is_stall(8.0, [1.2, 1.1, 1.3], factor=10, min_samples=3) is False


def test_stall_zero_median_never_flagged():
    assert is_stall(99.0, [0.0, 0.0, 0.0], factor=10, min_samples=3) is False


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_BACKEND", "sqlite")
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "g.db"))
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    init_db()
    return DataStore()


class _TinyWorker:
    """Bare stand-in exposing just the session pieces of Worker for these tests."""
    def __init__(self, store):
        self.store = store
        self.session_id = store.start_session()
        import time as _t
        self.session_started = _t.time()


def test_session_task_limit_engages(monkeypatch, store):
    monkeypatch.setattr(config, "SESSION_MAX_HOURS", 0.0)
    monkeypatch.setattr(config, "SESSION_MAX_TASKS", 2)
    w = _TinyWorker(store)
    for _ in range(2):
        store.bump_session_tasks(w.session_id)
    from scheduler.worker import Worker
    # reuse the real Worker._limit_reason against this store/session
    real = Worker(store=store)
    real.session_id = w.session_id
    real.session_started = w.session_started
    assert real._limit_reason() == STOP_REASON_TASKS


def test_session_time_limit_engages(monkeypatch, store):
    import time as _t
    monkeypatch.setattr(config, "SESSION_MAX_TASKS", 0)
    monkeypatch.setattr(config, "SESSION_MAX_HOURS", 8.0)
    from scheduler.worker import Worker
    real = Worker(store=store)
    real.session_id = store.start_session()
    real.session_started = _t.time() - 8 * 3600 - 1  # 8h+1s ago
    assert real._limit_reason() == STOP_REASON_TIME
    assert store.end_session(real.session_id, STOP_REASON_TIME) is None  # smoke: clean stop path


def test_session_end_marked_reviewable(monkeypatch, store):
    monkeypatch.setattr(config, "SESSION_MAX_TASKS", 0)
    monkeypatch.setattr(config, "SESSION_MAX_HOURS", 0.0)
    from scheduler.worker import Worker
    real = Worker(store=store)
    real.session_id = store.start_session()
    real._end_session(STOP_REASON_TIME)
    s = store.get_session(real.session_id)
    assert s["stop_reason"] == STOP_REASON_TIME
    assert s["stopped_at"] is not None
