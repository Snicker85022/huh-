"""API tests: dispatch surface for the Fusion team."""
import pytest
from fastapi.testclient import TestClient

import scheduler.config as config
from scheduler.api import build_app
from scheduler.db import init_db


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_BACKEND", "sqlite")
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "api.db"))
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    init_db()
    return TestClient(build_app())


def test_dispatch_and_list(client):
    r = client.post("/api/v1/tasks", json={
        "title": "Add pagination to /venues",
        "description": "Add ?page and ?page_size to the venues endpoint.",
        "constraints": ["Keep the existing response shape", "No new deps"],
        "tools": ["run_python", "run_shell"],
        "verify_cmd": "pytest -q",
        "priority": 5,
    })
    assert r.status_code == 201
    task = r.json()["task"]
    assert task["status"] == "queued"
    assert task["constraints"] == ["Keep the existing response shape", "No new deps"]

    listing = client.get("/api/v1/tasks").json()["tasks"]
    assert len(listing) == 1
    assert listing[0]["id"] == task["id"]


def test_get_task_detail_includes_attempts(client):
    t = client.post("/api/v1/tasks", json={"title": "X"}).json()["task"]
    d = client.get(f"/api/v1/tasks/{t['id']}").json()
    assert d["task"]["id"] == t["id"]
    assert d["attempts"] == []


def test_retry_requires_stopped_state(client):
    t = client.post("/api/v1/tasks", json={"title": "X"}).json()["task"]
    r = client.post(f"/api/v1/tasks/{t['id']}/retry")
    assert r.status_code == 409, "queued tasks must not be retryable"


def test_cancel_queued(client):
    t = client.post("/api/v1/tasks", json={"title": "X"}).json()["task"]
    r = client.post(f"/api/v1/tasks/{t['id']}/cancel")
    assert r.status_code == 200
    assert client.get(f"/api/v1/tasks/{t['id']}").json()["task"]["status"] == "aborted"


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["scheduler"] == "ok"
