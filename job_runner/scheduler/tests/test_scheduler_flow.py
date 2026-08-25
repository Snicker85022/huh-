"""End-to-end worker state machine tests with a deterministic fake executor.

Covers (spec Section 8 item 8): a task that fails repeatedly must freeze,
distill (negative examples injected), reset, and hard-stop to
"needs human review" after 2 freeze cycles -- or succeed when it can.
"""
import os
import sys
import tempfile
import threading
from dataclasses import dataclass

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import circuit_breaker as cb_mod  # noqa: E402

import scheduler.config as config  # noqa: E402
from scheduler.db import DataStore, init_db  # noqa: E402
from scheduler.executor import AttemptResult  # noqa: E402
from scheduler.worker import Worker  # noqa: E402


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_BACKEND", "sqlite")
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    init_db()
    return DataStore()


class FakeExecutor:
    """Deterministic executor: fails until `pass_at` calls, then passes."""

    def __init__(self, pass_at=None, always_fail=False):
        self.pass_at = pass_at       # 1-indexed call number on which to pass
        self.always_fail = always_fail
        self.calls = []
        self.prompts = []

    def make_workspace(self, task):
        return tempfile.mkdtemp(prefix="sched-test-")

    def execute_once(self, task, system, user, temperature=None, **kwargs):
        self.calls.append(task["id"])
        self.prompts.append(user)
        n = len(self.calls)
        if not self.always_fail and self.pass_at is not None and n >= self.pass_at:
            return AttemptResult(code="def solution():\n    return 42\n", passed=True, wall_s=0.1, gen_tokens=50, gen_tps=500)
        return AttemptResult(
            code=f"def broken_{n}():\n    raise ValueError('boom')\n",
            passed=False,
            error=f"Traceback (most recent call last):\nValueError: boom",
            wall_s=0.1, gen_tokens=50, gen_tps=500,
        )


def make_task(db, **kw):
    d = dict(title="T", description="D", constraints=["C1"], tools=["t1"],
             verify_cmd="exit 1")
    d.update(kw)
    return db.create_task(**d)


def run(worker, task):
    worker.stop.set()  # make stop.wait() return immediately in tests
    worker.run_task(task)
    return db_task if False else None


def test_hard_stop_after_two_freeze_cycles(db):
    task = make_task(db)
    ex = FakeExecutor(always_fail=True)
    Worker(store=db, executor=ex).run_task(task)
    final = db.get_task(task["id"])
    attempts = db.list_attempts(task["id"])
    assert final["status"] == "needs_review"
    assert final["freeze_cycles"] == 2
    assert len(attempts) == 4, "2 identical error sigs per cycle -> freeze at 2,4"

    # Cycle 2 prompts must contain the negative examples (distillation works).
    assert "NEGATIVE EXAMPLE" in ex.prompts[2]
    assert "NEGATIVE EXAMPLE" in ex.prompts[3]
    # First-cycle prompts carry no negatives.
    assert "NEGATIVE EXAMPLE" not in ex.prompts[0]
    assert "NEGATIVE EXAMPLE" not in ex.prompts[1]


def test_succeeds_when_model_recovers(db):
    task = make_task(db)
    ex = FakeExecutor(pass_at=3)  # fail, fail, fail (freeze at 2), pass at 3? pass_at=3 -> pass on 3rd call
    Worker(store=db, executor=ex).run_task(task)
    final = db.get_task(task["id"])
    assert final["status"] == "succeeded"
    assert final["freeze_cycles"] == 1
    # attempt 3 prompt (post-freeze) included the negative example
    assert "NEGATIVE EXAMPLE" in ex.prompts[2]


def test_manual_retry_starts_fresh_cycle(db):
    task = make_task(db)
    Worker(store=db, executor=FakeExecutor(always_fail=True)).run_task(task)
    assert db.get_task(task["id"])["status"] == "needs_review"

    assert db.mark_fresh_cycle(task["id"]) is True
    t = db.get_task(task["id"])
    assert t["status"] == "queued" and t["fresh"] == 1

    ex2 = FakeExecutor(pass_at=1)  # now passes immediately
    Worker(store=db, executor=ex2).run_task(db.claim_next())
    final = db.get_task(task["id"])
    assert final["status"] == "succeeded"
    assert final["freeze_cycles"] == 0, "fresh cycle must not inherit prior freeze state"


def test_crash_replay_preserves_loop_detection(db):
    """Simulate a worker death: 4 identical failed attempts persisted, task re-queued fresh=0.
    Replay must re-freeze on its own and hard-stop WITHOUT calling the model again."""
    task = make_task(db)
    for i in range(4):
        db.add_attempt(task["id"], i + 1, "failed", "x=1\n", "ValueError: boom", "aa", "bb", "p")
    # re-queue via recovery semantics: fresh=0 (crash-replay path)
    db.requeue_recovery(task["id"])

    ex = FakeExecutor(always_fail=True)
    w = Worker(store=db, executor=ex)
    w.stop.set()
    w.run_task(db.claim_next())
    final = db.get_task(task["id"])
    assert final["status"] == "needs_review"
    assert ex.calls == [], "must hard-stop during replay without calling the model"
