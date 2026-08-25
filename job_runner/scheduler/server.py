"""Entrypoint: REST API + background worker in one process (one unit to supervise).

Loads scheduler.env (gitignored: Postgres DSN) BEFORE config is imported.

Usage:
  python -m scheduler.server            # API + worker thread
  python -m scheduler.server --no-worker     # API only (worker stops cleanly at session limits)
  SCHED_API_PORT=8091 python -m scheduler.server
"""
from __future__ import annotations

import argparse
import threading

import uvicorn

from . import env
env.load()  # must run before config import

from . import config  # noqa: E402
from .api import build_app  # noqa: E402
from .db import init_db  # noqa: E402
from .worker import Worker  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-worker", action="store_true")
    ap.add_argument("--host", default=config.API_HOST)
    ap.add_argument("--port", type=int, default=config.API_PORT)
    args = ap.parse_args()

    init_db()
    w = Worker()
    worker_status = lambda: {"running": w.active, "session_id": w.session_id}  # noqa: E731
    app = build_app(worker_status=worker_status)

    if not args.no_worker:
        t = threading.Thread(target=w.run_forever, name="scheduler-worker", daemon=True)
        t.start()
        print(f"[scheduler] worker thread started (poll {w.poll}s)")

    print(f"[scheduler] API on http://{args.host}:{args.port}  (docs: /docs)")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
