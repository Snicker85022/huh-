"""Persistence for the batch scheduler -- dual backend.

Storage decision (reviewed 2026-08-25):
  * PRODUCTION backend: PostgreSQL on n100 (192.168.2.102, DB `ornith_scheduler`).
    Postgres is already part of this stack (langgraph checkpoints live there), it is
    REMOTE so its writes cost gflip nothing on the DRAM/memory-bus resource that the
    whole hardware philosophy protects, and its FOR UPDATE SKIP LOCKED gives a safe
    concurrent claim primitive (two workers could even run).
  * SQLITE backend (SCHED_DB_BACKEND=sqlite): kept for hermetic unit tests and as an
    offline/emergency mode if n100 is unreachable. Same schema, same interface.

The two backends share one schema so switching is a config change, not a rewrite.
"""
from __future__ import annotations

import contextlib
import json
import os
import time
import uuid
from typing import Any, Dict, Iterable, List, Optional

from . import config

# --------------------------------------------------------------------------
# Schema (both backends). Postgres: BIGSERIAL ids; SQLite: AUTOINCREMENT.
# --------------------------------------------------------------------------
_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id              TEXT PRIMARY KEY,
    status          TEXT NOT NULL DEFAULT 'queued',
    priority        INTEGER NOT NULL DEFAULT 0,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    constraints     TEXT NOT NULL DEFAULT '[]',
    tools           TEXT NOT NULL DEFAULT '[]',
    verify_cmd      TEXT,
    target_file     TEXT NOT NULL DEFAULT 'solution.py',
    workspace       TEXT,
    fresh           INTEGER NOT NULL DEFAULT 1,
    cancel_requested INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL,
    started_at      TEXT,
    finished_at     TEXT,
    attempts        INTEGER NOT NULL DEFAULT 0,
    freeze_cycles   INTEGER NOT NULL DEFAULT 0,
    final_report    TEXT,
    error           TEXT
);
CREATE TABLE IF NOT EXISTS attempts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id          TEXT NOT NULL REFERENCES tasks(id),
    attempt_no       INTEGER NOT NULL,
    status           TEXT NOT NULL,
    code_hash        TEXT,
    error_signature  TEXT,
    code             TEXT,
    error            TEXT,
    prompt           TEXT,
    freeze_reason    TEXT,
    wall_s           REAL,
    gen_tokens       INTEGER,
    gen_tps          REAL,
    stall_warning    INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status, priority, created_at);
CREATE INDEX IF NOT EXISTS idx_attempts_task ON attempts(task_id, attempt_no);
CREATE TABLE IF NOT EXISTS telemetry (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id  TEXT,
    ts       TEXT NOT NULL,
    metric   TEXT NOT NULL,
    value    REAL
);
CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY,
    started_at      TEXT NOT NULL,
    stopped_at      TEXT,
    stop_reason     TEXT,
    tasks_processed INTEGER NOT NULL DEFAULT 0,
    stall_warnings  INTEGER NOT NULL DEFAULT 0,
    notes           TEXT
);
"""

_PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id              TEXT PRIMARY KEY,
    status          TEXT NOT NULL DEFAULT 'queued',
    priority        INTEGER NOT NULL DEFAULT 0,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    constraints     TEXT NOT NULL DEFAULT '[]',
    tools           TEXT NOT NULL DEFAULT '[]',
    verify_cmd      TEXT,
    target_file     TEXT NOT NULL DEFAULT 'solution.py',
    workspace       TEXT,
    fresh           INTEGER NOT NULL DEFAULT 1,
    cancel_requested INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL,
    started_at      TEXT,
    finished_at     TEXT,
    attempts        INTEGER NOT NULL DEFAULT 0,
    freeze_cycles   INTEGER NOT NULL DEFAULT 0,
    final_report    TEXT,
    error           TEXT
);
CREATE TABLE IF NOT EXISTS attempts (
    id               BIGSERIAL PRIMARY KEY,
    task_id          TEXT NOT NULL REFERENCES tasks(id),
    attempt_no       INTEGER NOT NULL,
    status           TEXT NOT NULL,
    code_hash        TEXT,
    error_signature  TEXT,
    code             TEXT,
    error            TEXT,
    prompt           TEXT,
    freeze_reason    TEXT,
    wall_s           REAL,
    gen_tokens       INTEGER,
    gen_tps          REAL,
    stall_warning    INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status, priority, created_at);
CREATE INDEX IF NOT EXISTS idx_attempts_task ON attempts(task_id, attempt_no);
CREATE TABLE IF NOT EXISTS telemetry (
    id       BIGSERIAL PRIMARY KEY,
    task_id  TEXT,
    ts       TEXT NOT NULL,
    metric   TEXT NOT NULL,
    value    REAL
);
CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY,
    started_at      TEXT NOT NULL,
    stopped_at      TEXT,
    stop_reason     TEXT,
    tasks_processed INTEGER NOT NULL DEFAULT 0,
    stall_warnings  INTEGER NOT NULL DEFAULT 0,
    notes           TEXT
);
"""


def _now() -> str:
    # Microsecond precision: created_at is the tiebreaker for equal-priority queue
    # order. Second precision caused same-second dispatches to claim in arbitrary
    # (rowid) order -- measured in the first live run.
    base = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    micro = int((time.time() % 1.0) * 1_000_000)
    return f"{base}.{micro:06d}Z"


def _iso_to_epoch(iso: str) -> float:
    return time.mktime(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))


# --------------------------------------------------------------------------
# SQLite backend
# --------------------------------------------------------------------------
class _SqliteStore:
    def init(self) -> None:
        config.ensure_dirs()
        with self._conn() as c:
            c.executescript(_SQLITE_SCHEMA)
            # idempotent migration: stall_warning column on pre-existing DBs
            cols = [r[1] for r in c.execute("PRAGMA table_info(attempts)").fetchall()]
            if cols and "stall_warning" not in cols:
                c.execute("ALTER TABLE attempts ADD COLUMN stall_warning INTEGER NOT NULL DEFAULT 0")

    @staticmethod
    def _conn():
        config.ensure_dirs()
        c = __import__("sqlite3").connect(config.DB_PATH, timeout=30.0, isolation_level=None)
        c.row_factory = __import__("sqlite3").Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA busy_timeout=30000")
        c.execute("PRAGMA foreign_keys=ON")
        return c

    def create_task(self, title, description="", constraints=None, tools=None,
                    verify_cmd=None, target_file="solution.py", priority=0, workspace=None):
        task_id = str(uuid.uuid4())
        with self._conn() as c:
            c.execute(
                """INSERT INTO tasks
                   (id, status, priority, title, description, constraints, tools,
                    verify_cmd, target_file, workspace, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (task_id, "queued", int(priority), title, description,
                 json.dumps(list(constraints or [])), json.dumps(list(tools or [])),
                 verify_cmd, target_file, workspace, _now()),
            )
        return self.get_task(task_id)

    def get_task(self, task_id):
        with self._conn() as c:
            row = c.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return self._decode(row) if row else None

    def list_tasks(self, status=None):
        with self._conn() as c:
            if status:
                rows = c.execute("SELECT * FROM tasks WHERE status=? ORDER BY created_at DESC", (status,)).fetchall()
            else:
                rows = c.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
        return [self._decode(r) for r in rows]

    def list_tasks_since(self, start_iso):
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM tasks WHERE started_at IS NOT NULL AND started_at >= ? ORDER BY started_at",
                (start_iso,),
            ).fetchall()
        return [self._decode(r) for r in rows]

    def claim_next(self):
        with self._conn() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute(
                "SELECT * FROM tasks WHERE status='queued' "
                "ORDER BY priority DESC, created_at ASC LIMIT 1"
            ).fetchone()
            if row is None:
                c.execute("COMMIT")
                return None
            c.execute("UPDATE tasks SET status='running', started_at=? WHERE id=?", (_now(), row["id"]))
            c.execute("COMMIT")
        return self._decode(row)

    def set_status(self, task_id, status, error=None):
        finished = _now() if status in ("succeeded", "needs_review", "failed", "aborted") else None
        with self._conn() as c:
            c.execute("UPDATE tasks SET status=?, error=?, finished_at=? WHERE id=?",
                      (status, error, finished, task_id))

    def request_cancel(self, task_id):
        with self._conn() as c:
            row = c.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row is None:
                return False
            if row["status"] == "queued":
                c.execute("UPDATE tasks SET status='aborted', finished_at=? WHERE id=?", (_now(), task_id))
                return True
            if row["status"] == "running":
                c.execute("UPDATE tasks SET cancel_requested=1 WHERE id=?", (task_id,))
            return False

    def mark_fresh_cycle(self, task_id):
        with self._conn() as c:
            row = c.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row is None:
                return False
            if row["status"] not in ("needs_review", "failed", "aborted"):
                return False
            c.execute(
                "UPDATE tasks SET status='queued', fresh=1, cancel_requested=0, "
                "started_at=NULL, finished_at=NULL, error=NULL WHERE id=?", (task_id,))
            return True

    def finish(self, task_id, status, summary, report, error=None):
        with self._conn() as c:
            c.execute(
                """UPDATE tasks SET status=?, final_report=?, error=?,
                   attempts=?, freeze_cycles=?, finished_at=? WHERE id=?""",
                (status, report, error, int(summary.get("attempts", 0)),
                 int(summary.get("freeze_cycles", 0)), _now(), task_id))

    def add_attempt(self, task_id, attempt_no, status, code, error, code_hash,
                    error_signature, prompt, freeze_reason=None, wall_s=None,
                    gen_tokens=None, gen_tps=None, stall_warning=0):
        with self._conn() as c:
            c.execute(
                """INSERT INTO attempts
                   (task_id, attempt_no, status, code_hash, error_signature, code, error,
                    prompt, freeze_reason, wall_s, gen_tokens, gen_tps, stall_warning, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (task_id, attempt_no, status, code_hash, error_signature, code, error,
                 prompt, freeze_reason, wall_s, gen_tokens, gen_tps, int(stall_warning), _now()))

    def list_attempts(self, task_id):
        # ORDER BY attempt_no ASC is LOAD-BEARING: crash-recovery replay reconstructs
        # exact circuit-breaker state only if the original order is preserved.
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM attempts WHERE task_id=? ORDER BY attempt_no", (task_id,)).fetchall()
        return [dict(r) for r in rows]

    def telemetry(self, task_id, metric, value):
        with self._conn() as c:
            c.execute("INSERT INTO telemetry (task_id, ts, metric, value) VALUES (?,?,?,?)",
                      (task_id, _now(), metric, float(value)))

    def recover_stale_running(self):
        with self._conn() as c:
            c.execute("BEGIN IMMEDIATE")
            n = c.execute(
                "UPDATE tasks SET status='queued', fresh=0, cancel_requested=0, started_at=NULL "
                "WHERE status='running'").rowcount
            c.execute("COMMIT")
        return n

    def requeue_recovery(self, task_id):
        """Re-queue ONE task with fresh=0 so crash-replay engages (tests/ops)."""
        with self._conn() as c:
            c.execute(
                "UPDATE tasks SET status='queued', fresh=0, cancel_requested=0, "
                "started_at=NULL WHERE id=?", (task_id,))


    # -- sessions ---------------------------------------------------------
    def start_session(self):
        sid = str(uuid.uuid4())
        with self._conn() as c:
            c.execute("INSERT INTO sessions (id, started_at) VALUES (?,?)", (sid, _now()))
        return sid

    def get_session(self, sid):
        with self._conn() as c:
            row = c.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
        return dict(row) if row else None

    def list_sessions(self, limit=10):
        with self._conn() as c:
            rows = c.execute("SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?", (int(limit),)).fetchall()
        return [dict(r) for r in rows]

    def bump_session_tasks(self, sid):
        with self._conn() as c:
            c.execute("UPDATE sessions SET tasks_processed = tasks_processed + 1 WHERE id=?", (sid,))

    def add_session_stall(self, sid):
        with self._conn() as c:
            c.execute("UPDATE sessions SET stall_warnings = stall_warnings + 1 WHERE id=?", (sid,))

    def end_session(self, sid, reason, notes=None):
        with self._conn() as c:
            c.execute("UPDATE sessions SET stopped_at=?, stop_reason=?, notes=? WHERE id=?",
                      (_now(), reason, notes, sid))

    @staticmethod
    def _decode(row):
        d = dict(row)
        d["constraints"] = json.loads(d.get("constraints") or "[]")
        d["tools"] = json.loads(d.get("tools") or "[]")
        return d


# --------------------------------------------------------------------------
# PostgreSQL backend (n100)
# --------------------------------------------------------------------------
class _PostgresStore:
    def init(self):
        with self._conn() as c:
            c.execute(_PG_SCHEMA)

    @staticmethod
    def _conn():
        try:
            import psycopg
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "psycopg is required for the postgres backend; install it in the venv "
                "(pip install 'psycopg[binary]') or set SCHED_DB_BACKEND=sqlite"
            ) from e
        return psycopg.connect(config.PG_DSN, connect_timeout=5)

    def create_task(self, title, description="", constraints=None, tools=None,
                    verify_cmd=None, target_file="solution.py", priority=0, workspace=None):
        task_id = str(uuid.uuid4())
        with self._conn() as c:
            c.execute(
                """INSERT INTO tasks
                   (id, status, priority, title, description, constraints, tools,
                    verify_cmd, target_file, workspace, created_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (task_id, "queued", int(priority), title, description,
                 json.dumps(list(constraints or [])), json.dumps(list(tools or [])),
                 verify_cmd, target_file, workspace, _now()),
            )
        return self.get_task(task_id)

    def get_task(self, task_id):
        with self._conn() as c:
            row = c.execute("SELECT * FROM tasks WHERE id=%s", (task_id,)).fetchone()
        return self._decode(row) if row else None

    def list_tasks(self, status=None):
        with self._conn() as c:
            if status:
                rows = c.execute("SELECT * FROM tasks WHERE status=%s ORDER BY created_at DESC", (status,)).fetchall()
            else:
                rows = c.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
        return [self._decode(r) for r in rows]

    def list_tasks_since(self, start_iso):
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM tasks WHERE started_at IS NOT NULL AND started_at >= %s ORDER BY started_at",
                (start_iso,)).fetchall()
        return [self._decode(r) for r in rows]

    def claim_next(self):
        with self._conn() as c:
            with c.cursor() as cur:
                cur.execute(
                    "SELECT * FROM tasks WHERE status='queued' "
                    "ORDER BY priority DESC, created_at ASC LIMIT 1 FOR UPDATE SKIP LOCKED")
                row = cur.fetchone()
                if row is None:
                    return None
                cur.execute("UPDATE tasks SET status='running', started_at=%s WHERE id=%s",
                            (_now(), row["id"]))
        return self._decode(row)

    def set_status(self, task_id, status, error=None):
        finished = _now() if status in ("succeeded", "needs_review", "failed", "aborted") else None
        with self._conn() as c:
            c.execute("UPDATE tasks SET status=%s, error=%s, finished_at=%s WHERE id=%s",
                      (status, error, finished, task_id))

    def request_cancel(self, task_id):
        with self._conn() as c:
            row = c.execute("SELECT status FROM tasks WHERE id=%s", (task_id,)).fetchone()
            if row is None:
                return False
            if row["status"] == "queued":
                c.execute("UPDATE tasks SET status='aborted', finished_at=%s WHERE id=%s", (_now(), task_id))
                return True
            if row["status"] == "running":
                c.execute("UPDATE tasks SET cancel_requested=1 WHERE id=%s", (task_id,))
            return False

    def mark_fresh_cycle(self, task_id):
        with self._conn() as c:
            row = c.execute("SELECT status FROM tasks WHERE id=%s", (task_id,)).fetchone()
            if row is None:
                return False
            if row["status"] not in ("needs_review", "failed", "aborted"):
                return False
            c.execute(
                "UPDATE tasks SET status='queued', fresh=1, cancel_requested=0, "
                "started_at=NULL, finished_at=NULL, error=NULL WHERE id=%s", (task_id,))
            return True

    def finish(self, task_id, status, summary, report, error=None):
        with self._conn() as c:
            c.execute(
                """UPDATE tasks SET status=%s, final_report=%s, error=%s,
                   attempts=%s, freeze_cycles=%s, finished_at=%s WHERE id=%s""",
                (status, report, error, int(summary.get("attempts", 0)),
                 int(summary.get("freeze_cycles", 0)), _now(), task_id))

    def add_attempt(self, task_id, attempt_no, status, code, error, code_hash,
                    error_signature, prompt, freeze_reason=None, wall_s=None,
                    gen_tokens=None, gen_tps=None, stall_warning=0):
        with self._conn() as c:
            c.execute(
                """INSERT INTO attempts
                   (task_id, attempt_no, status, code_hash, error_signature, code, error,
                    prompt, freeze_reason, wall_s, gen_tokens, gen_tps, stall_warning, created_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (task_id, attempt_no, status, code_hash, error_signature, code, error,
                 prompt, freeze_reason, wall_s, gen_tokens, gen_tps, int(stall_warning), _now()))

    def list_attempts(self, task_id):
        # ORDER BY attempt_no ASC is LOAD-BEARING: crash-recovery replay reconstructs
        # exact circuit-breaker state only if the original order is preserved.
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM attempts WHERE task_id=%s ORDER BY attempt_no", (task_id,)).fetchall()
        return [dict(r) for r in rows]

    def telemetry(self, task_id, metric, value):
        with self._conn() as c:
            c.execute("INSERT INTO telemetry (task_id, ts, metric, value) VALUES (%s,%s,%s,%s)",
                      (task_id, _now(), metric, float(value)))

    def recover_stale_running(self):
        with self._conn() as c:
            cur = c.execute(
                "UPDATE tasks SET status='queued', fresh=0, cancel_requested=0, started_at=NULL "
                "WHERE status='running'")
        return cur.rowcount

    def requeue_recovery(self, task_id):
        """Re-queue ONE task with fresh=0 so crash-replay engages (tests/ops)."""
        with self._conn() as c:
            c.execute(
                "UPDATE tasks SET status='queued', fresh=0, cancel_requested=0, "
                "started_at=NULL WHERE id=%s", (task_id,))


    # -- sessions ---------------------------------------------------------
    def start_session(self):
        sid = str(uuid.uuid4())
        with self._conn() as c:
            c.execute("INSERT INTO sessions (id, started_at) VALUES (%s,%s)", (sid, _now()))
        return sid

    def get_session(self, sid):
        with self._conn() as c:
            row = c.execute("SELECT * FROM sessions WHERE id=%s", (sid,)).fetchone()
        return dict(row) if row else None

    def list_sessions(self, limit=10):
        with self._conn() as c:
            rows = c.execute("SELECT * FROM sessions ORDER BY started_at DESC LIMIT %s", (int(limit),)).fetchall()
        return [dict(r) for r in rows]

    def bump_session_tasks(self, sid):
        with self._conn() as c:
            c.execute("UPDATE sessions SET tasks_processed = tasks_processed + 1 WHERE id=%s", (sid,))

    def add_session_stall(self, sid):
        with self._conn() as c:
            c.execute("UPDATE sessions SET stall_warnings = stall_warnings + 1 WHERE id=%s", (sid,))

    def end_session(self, sid, reason, notes=None):
        with self._conn() as c:
            c.execute("UPDATE sessions SET stopped_at=%s, stop_reason=%s, notes=%s WHERE id=%s",
                      (_now(), reason, notes, sid))

    @staticmethod
    def _decode(row):
        d = dict(row)
        d["constraints"] = json.loads(d.get("constraints") or "[]")
        d["tools"] = json.loads(d.get("tools") or "[]")
        return d


# --------------------------------------------------------------------------
# Public facade
# --------------------------------------------------------------------------
class DataStore:
    """Delegates to the configured backend. Backend chosen once at construction."""

    def __init__(self, backend: Optional[str] = None) -> None:
        self.backend = (backend or config.DB_BACKEND).lower()
        if self.backend == "sqlite":
            self._impl = _SqliteStore()
        elif self.backend == "postgres":
            self._impl = _PostgresStore()
        else:
            raise ValueError(f"unknown DB backend: {self.backend!r}")

    def __getattr__(self, name: str):
        return getattr(self._impl, name)

    def init(self) -> None:
        self._impl.init()


def init_db(backend: Optional[str] = None) -> DataStore:
    store = DataStore(backend)
    store.init()
    return store
