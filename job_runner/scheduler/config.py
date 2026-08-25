"""Scheduler configuration (constants + env overrides). CPU-only module.

Ornith's production server config is LOCKED (systemd unit ornith-1.5.service,
DOE-tuned) and is not touched here -- this process is only a client of the
OpenAI-compatible endpoint on :8082.
"""
from __future__ import annotations

import os

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.environ.get("SCHED_DATA_DIR", os.path.join(_THIS_DIR, "data"))
DB_PATH = os.environ.get("SCHED_DB_PATH", os.path.join(DATA_DIR, "jobs.db"))
WORKSPACE_ROOT = os.environ.get("SCHED_WORKSPACE_ROOT", "/var/lib/ornith-sandbox/workspaces")
REPORTS_DIR = os.environ.get("SCHED_REPORTS_DIR", os.path.join(DATA_DIR, "reports"))


# --- sandbox for model-generated code ----------------------------------------------
# verify_cmd runs code the model just wrote. v1: unprivileged user + setrlimit caps.
# SANDBOX_ENABLED=0 is for dev/offline ONLY -- never on a box with real data.
SANDBOX_USER = os.environ.get("SCHED_SANDBOX_USER", "ornith-sandbox")
SANDBOX_ENABLED = os.environ.get("SCHED_SANDBOX_ENABLED", "1") == "1"
SANDBOX_CPU_S = float(os.environ.get("SCHED_SANDBOX_CPU_S", "30"))
SANDBOX_MEM_MB = int(os.environ.get("SCHED_SANDBOX_MEM_MB", "1536"))
SANDBOX_FSIZE_MB = int(os.environ.get("SCHED_SANDBOX_FSIZE_MB", "16"))

# --- storage backend -------------------------------------------------------------
# sqlite   = default. Single node, single sequential worker: zero daemon, zero
#            network dependency, ACID+WAL. Postgres on n100 is an explicit opt-in
#            (SCHED_DB_BACKEND=postgres) for the day multi-worker dispatch is real --
#            it buys nothing today and adds a 2am network dependency.
DB_BACKEND = os.environ.get("SCHED_DB_BACKEND", "sqlite").lower()
PG_DSN = os.environ.get("SCHED_PG_DSN", "postgresql://ornith_sched@192.168.2.102:5432/ornith_scheduler")

# --- Ornith endpoint (production llama-server, OpenAI-compatible) -------------
ORNITH_BASE_URL = os.environ.get("ORNITH_BASE_URL", "http://127.0.0.1:8082")
ORNITH_MODEL = os.environ.get("ORNITH_MODEL", "ornith-1.5-35b")

# --- budgets / timeouts --------------------------------------------------------
# Stall watchdog: Piece-2 proved the 26 GiB thrash failure manifests as a
# silent ~0.1 tok/s collapse (190 s for what normally takes 1.2 s), NOT an
# error -- so every generation call gets a hard wall-clock timeout.
GENERATION_TIMEOUT_S = float(os.environ.get("SCHED_GEN_TIMEOUT_S", "300"))
VERIFY_TIMEOUT_S = float(os.environ.get("SCHED_VERIFY_TIMEOUT_S", "60"))
# Ornith-1.5 is a reasoning model: it emits reasoning_content and can burn the
# whole token budget on thinking. Short max_tokens starves the answer (measured
# in DOE Phase 3). Keep this large for code tasks.
MAX_TOKENS = int(os.environ.get("SCHED_MAX_TOKENS", "4096"))
# Production sampling (matches the DOE-locked server defaults; explicit for audit).
TEMP = float(os.environ.get("SCHED_TEMP", "0.2"))
TOP_P = float(os.environ.get("SCHED_TOP_P", "0.95"))
TOP_K = int(os.environ.get("SCHED_TOP_K", "20"))

# --- service --------------------------------------------------------------------
API_HOST = os.environ.get("SCHED_API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("SCHED_API_PORT", "8090"))
POLL_INTERVAL_S = float(os.environ.get("SCHED_POLL_S", "2.0"))
# --- session outer guard (independent of the circuit breaker) -----------------
# Limits the overnight run as a WHOLE, not per-task. Either limit is sufficient
# to stop the worker from claiming new tasks. <=0 disables that limit.
SESSION_MAX_HOURS = float(os.environ.get("SCHED_SESSION_MAX_HOURS", "8.0"))
SESSION_MAX_TASKS = int(os.environ.get("SCHED_SESSION_MAX_TASKS", "30"))

# --- per-attempt stall detection (the 190s-vs-1.2s thrash signature) ----------
# Distinct from the generation/verify timeouts: an attempt that COMPLETES but
# takes > STALL_FACTOR x the median of recent SUCCESSFUL attempt wall times is
# logged as a stall warning even though nothing errored. This is exactly what
# the memory-floor DOE measured (silent collapse, no crash, no error).
STALL_FACTOR = float(os.environ.get("SCHED_STALL_FACTOR", "10.0"))
STALL_MEDIAN_WINDOW = int(os.environ.get("SCHED_STALL_WINDOW", "10"))
STALL_MIN_SAMPLES = int(os.environ.get("SCHED_STALL_MIN_SAMPLES", "3"))

# --- safety caps -----------------------------------------------------------------
MAX_TOTAL_ATTEMPTS = int(os.environ.get("SCHED_MAX_ATTEMPTS", "12"))  # absolute ceiling
CANCEL_CHECK_INTERVAL = 1.0


def ensure_dirs() -> None:
    for d in (DATA_DIR, REPORTS_DIR, WORKSPACE_ROOT):
        os.makedirs(d, exist_ok=True)

# --- Goal 3: error distillation (known-fix cache + novel-error lessons) -----
# The distilled-lesson cache persists across worker restarts / sessions.
DISTILL_LESSONS_PATH = os.environ.get(
    "SCHED_DISTILL_LESSONS",
    os.path.join(DATA_DIR, "distill_lessons.json"),
)
# Default distiller: of the local locked Ornith endpoint on :8082. Set
# SCHED_DISTILL_OFFLINE=1 to force the deterministic (no-model) fallback.
DISTILL_OFFLINE = os.environ.get("SCHED_DISTILL_OFFLINE", "0") == "1"

# --- Goal 6: meta-orchestration control loop -------------------------------
# The loop watches a rolling window of per-attempt generation speeds and the
# recent pass/fail ratio, and adjusts (a) temperature within [min,max] and
# (b) a cooldown between tasks when a SUSTAINED collapse is detected. All
# bounded; the loop never stops or kills -- the session outer guard does that.
CONTROL_WINDOW = int(os.environ.get("SCHED_CONTROL_WINDOW", "32"))
CONTROL_RESULT_WINDOW = int(os.environ.get("SCHED_CONTROL_RESULT_WINDOW", "12"))
CONTROL_SLOW_TPS = float(os.environ.get("SCHED_CONTROL_SLOW_TPS", "5.0"))
CONTROL_COLLAPSE_SAMPLES = int(os.environ.get("SCHED_CONTROL_COLLAPSE_SAMPLES", "4"))
CONTROL_MIN_TEMP = float(os.environ.get("SCHED_CONTROL_MIN_TEMP", "0.1"))
CONTROL_MAX_TEMP = float(os.environ.get("SCHED_CONTROL_MAX_TEMP", "0.6"))
CONTROL_COOLDOWN_S = float(os.environ.get("SCHED_CONTROL_COOLDOWN_S", "30.0"))
