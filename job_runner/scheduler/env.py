"""Loads scheduler.env (gitignored secrets, e.g. the Postgres DSN) into os.environ
BEFORE config is imported. Called from server.py / worker main / run_once."""

import os


def load(env_file: str = "") -> None:
    path = env_file or os.environ.get(
        "SCHED_ENV_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "scheduler.env")
    )
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())
