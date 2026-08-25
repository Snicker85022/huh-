"""Goal 3 (3a known-fix cache / 3b novel-error fallback) tests."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest

import scheduler.config as config
from scheduler.db import DataStore, init_db
from scheduler.error_distill import ErrorDistiller, KnownFixIndex


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_BACKEND", "sqlite")
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "g3.db"))
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(config, "WORKSPACE_ROOT", str(tmp_path / "ws"))
    init_db()
    return DataStore()


def sig(text):
    import circuit_breaker as cb
    return cb.normalize_error_signature(text)


def _succeed(store, title, fail_err, fix_code):
    t = store.create_task(title=title, verify_cmd="exit 1")
    store.add_attempt(t["id"], 1, "failed", "bad=1\n", fail_err, "a", sig(fail_err), "p")
    store.add_attempt(t["id"], 2, "passed", fix_code, None, "b", None, "p")
    store.finish(t["id"], "succeeded", {"attempts": 2, "freeze_cycles": 0}, "rep")
    return t


def test_known_fix_scan_learns_from_succeeded_task(store):
    """3a: an error that a past task eventually fixed maps to that fix."""
    _succeed(store, "Task A", "ValueError: boom", "def fix():\n    return 1\n")
    idx = KnownFixIndex.scan(store)
    fix = idx.lookup(sig("ValueError: boom"))
    assert fix is not None
    assert "def fix():" in fix.fix_code


def test_known_fix_ignores_tasks_that_never_succeeded(store):
    t = store.create_task(title="A", verify_cmd="exit 1")
    store.add_attempt(t["id"], 1, "failed", "bad=1\n", "ValueError: boom", "a", sig("ValueError: boom"), "p")
    store.finish(t["id"], "needs_review", {"attempts": 1, "freeze_cycles": 1}, "rep")
    idx = KnownFixIndex.scan(store)
    assert idx.lookup(sig("ValueError: boom")) is None


def test_guidance_returns_known_fix(store):
    _succeed(store, "Task B", "AttributeError: str", "def sol():\n    return 42\n")
    dist = ErrorDistiller(store=store)
    g = dist.guidance_for(sig("AttributeError: str"),
                          "AttributeError: 'str' object has no attribute 'x'", "bad=1\n")
    assert "KNOWN FIX CODE" in g
    assert "def sol():" in g


def test_novel_error_distills_once_and_caches(store):
    calls = {"n": 0}

    def fake_distiller(err_text, code):
        calls["n"] += 1
        return "root cause derived", "use a different API"

    dist = ErrorDistiller(store=store, distiller=fake_distiller)
    e = sig("ImportError: cannot import name 'lunar'")
    g1 = dist.guidance_for(e, "ImportError: cannot import name 'lunar'", "import lunar\n")
    g2 = dist.guidance_for(e, "ImportError: cannot import name 'lunar'", "import lunar\n")
    assert calls["n"] == 1, "distiller must run exactly once, then served from cache"
    assert "root cause derived" in g1
    assert g1 == g2


def test_offline_no_model_fallback(store):
    """Without a model distiller it still returns a deterministic lesson."""
    dist = ErrorDistiller(store=store)   # no distiller injected
    g = dist.guidance_for(sig("ZeroDivisionError: division by zero"),
                          "Traceback ...\nZeroDivisionError: division by zero", "x=1/0\n")
    assert "ZeroDivisionError" in g or "root cause" in g.lower()
