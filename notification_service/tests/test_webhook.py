import json

import pytest
from fastapi.testclient import TestClient

from notification_service.main import create_app

TASK = {
    "id": "3f1c2b8e-6a4d-4e7b-9a51-2d3c4b5a6f70",
    "title": "Подготовить отчёт",
    "description": "Лабораторная работа №2",
    "status": "new",
    "created_at": "2026-09-16T10:15:30.123456Z",
}
HEADERS = {"X-Event-Type": "task.created", "X-Event-Id": "9b2e6f1a-0c47-4d4e-8f0e-1a2b3c4d5e6f"}


@pytest.fixture
def log_file(tmp_path):
    return tmp_path / "logs" / "notifications.log"


@pytest.fixture
def client(log_file):
    with TestClient(create_app(log_file)) as c:
        yield c


def test_webhook_accepts_task_and_writes_log(client, log_file):
    resp = client.post("/api/webhooks/task_created", json=TASK, headers=HEADERS)

    assert resp.status_code == 200
    assert resp.json() == {"status": "accepted"}

    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event_id"] == HEADERS["X-Event-Id"]
    assert record["task"]["id"] == TASK["id"]
    assert "Подготовить отчёт" in record["message"]

    history = client.get("/api/notifications").json()
    assert [n["task"]["title"] for n in history] == ["Подготовить отчёт"]


def test_repeated_event_is_not_notified_twice(client, log_file):
    first = client.post("/api/webhooks/task_created", json=TASK, headers=HEADERS)
    second = client.post("/api/webhooks/task_created", json=TASK, headers=HEADERS)

    assert first.json() == {"status": "accepted"}
    assert second.status_code == 200
    assert second.json() == {"status": "duplicate"}
    assert len(log_file.read_text(encoding="utf-8").splitlines()) == 1


def test_without_event_id_task_id_is_used_for_dedup(client):
    assert client.post("/api/webhooks/task_created", json=TASK).json()["status"] == "accepted"
    assert client.post("/api/webhooks/task_created", json=TASK).json()["status"] == "duplicate"


@pytest.mark.parametrize(
    "patch",
    [
        {"id": "not-a-uuid"},
        {"status": "archived"},
        {"title": ""},
        {"created_at": "вчера"},
    ],
)
def test_invalid_task_returns_422(client, patch):
    resp = client.post("/api/webhooks/task_created", json={**TASK, **patch}, headers=HEADERS)
    assert resp.status_code == 422


def test_missing_field_returns_422(client):
    body = {k: v for k, v in TASK.items() if k != "created_at"}
    assert client.post("/api/webhooks/task_created", json=body).status_code == 422


def test_log_unavailable_returns_503_and_event_can_be_retried(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("это файл, а не каталог")
    app = create_app(blocker / "notifications.log")

    with TestClient(app) as client:
        resp = client.post("/api/webhooks/task_created", json=TASK, headers=HEADERS)
        assert resp.status_code == 503

        # после восстановления то же событие принимается, а не считается дублем
        app.state.sender.log_file = tmp_path / "ok.log"
        retry = client.post("/api/webhooks/task_created", json=TASK, headers=HEADERS)
        assert retry.json() == {"status": "accepted"}
