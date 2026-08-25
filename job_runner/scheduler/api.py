"""REST API -- the dispatch surface the Fusion debate team posts tasks to.

Endpoints
  POST   /api/v1/tasks          dispatch a task            -> 201 {task}
  GET    /api/v1/tasks          list (optional ?status=)   -> [task]
  GET    /api/v1/tasks/{id}     detail + attempts          -> {task, attempts}
  POST   /api/v1/tasks/{id}/retry   fresh cycle after human review
  POST   /api/v1/tasks/{id}/cancel  cancel queued / request cancel of running
  GET    /api/v1/session        current session + stop reason (morning review)
  GET    /api/v1/sessions       recent session history
  GET    /api/v1/health         service + Ornith + worker state

Task schema (the contract with the Fusion team):
  title        required, short imperative sentence
  description  free-form scope
  constraints  list[str], each applied verbatim in the prompt (Goal 1 test a)
  tools        list[str], ONLY these appear in the prompt (Goal 1 test b)
  verify_cmd   shell command run in the task workspace; rc==0 => pass
  target_file  file to write the solution to (default solution.py)
  priority     higher runs first (default 0)
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import config
from .db import DataStore, init_db


class TaskDispatch(BaseModel):
    title: str = Field(..., min_length=1, max_length=300,
                       description="Short imperative sentence naming ONE scoped task.")
    description: str = Field("", description="Free-form scope/context for the task.")
    constraints: List[str] = Field([], description="Applied verbatim in the prompt.")
    tools: List[str] = Field([], description="Only these tools appear in the prompt.")
    verify_cmd: Optional[str] = Field(None, description="Acceptance command; rc==0 means pass.")
    target_file: str = Field("solution.py", description="File the solution is written to.")
    priority: int = Field(0, description="Higher priority runs first.")


def build_app(store: Optional[DataStore] = None,
              worker_status: Optional[Callable[[], Dict[str, Any]]] = None) -> FastAPI:
    init_db()
    db = store or DataStore()
    app = FastAPI(title="Ornith Batch Scheduler", version="0.1.0")
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
    )

    @app.get("/api/v1/health")
    def health() -> Dict[str, Any]:
        from .executor import OrnithClient
        ws = worker_status() if worker_status else {"running": False, "session_id": None}
        return {"scheduler": "ok", "db_backend": config.DB_BACKEND,
                "worker": ws, "ornith": OrnithClient().health()}

    @app.post("/api/v1/tasks", status_code=201)
    def dispatch_task(t: TaskDispatch) -> Dict[str, Any]:
        task = db.create_task(
            title=t.title, description=t.description,
            constraints=t.constraints, tools=t.tools,
            verify_cmd=t.verify_cmd, target_file=t.target_file,
            priority=t.priority,
        )
        return {"task": task, "queued": True}

    @app.get("/api/v1/tasks")
    def list_tasks(status: Optional[str] = None) -> Dict[str, Any]:
        return {"tasks": db.list_tasks(status)}

    @app.get("/api/v1/tasks/{task_id}")
    def get_task(task_id: str) -> Dict[str, Any]:
        task = db.get_task(task_id)
        if task is None:
            raise HTTPException(404, "task not found")
        return {"task": task, "attempts": db.list_attempts(task_id)}

    @app.post("/api/v1/tasks/{task_id}/retry")
    def retry_task(task_id: str) -> Dict[str, Any]:
        if not db.mark_fresh_cycle(task_id):
            raise HTTPException(409, "task is not in a retryable state (needs_review/failed/aborted)")
        return {"task": db.get_task(task_id), "retried": True}

    @app.post("/api/v1/tasks/{task_id}/cancel")
    def cancel_task(task_id: str) -> Dict[str, Any]:
        ok = db.request_cancel(task_id)
        if not ok:
            raise HTTPException(404, "task not found")
        return {"task": db.get_task(task_id), "cancelled": True}

    @app.get("/api/v1/session")
    def current_session() -> Dict[str, Any]:
        """Active session, or the most recent one with its stop reason (morning review)."""
        sessions = db.list_sessions(limit=5)
        for s in sessions:
            if s.get("stop_reason") is None:
                return {"active": True, "session": s}
        last = sessions[0] if sessions else None
        return {"active": False, "session": last,
                "note": "worker is not running; tasks dispatched now will queue for the next session"}

    @app.get("/api/v1/sessions")
    def sessions(limit: int = 10) -> Dict[str, Any]:
        return {"sessions": db.list_sessions(limit=limit)}

    return app
