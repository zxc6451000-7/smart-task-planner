from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from task_service.config import Settings
from task_service.main import create_app

# Вебхук уходит на закрытый порт: API-тесты не должны зависеть от Notification Service.
SETTINGS = Settings(webhook_url="http://127.0.0.1:9/hook", webhook_timeout=0.2, webhook_max_attempts=1)


@pytest.fixture
def client():
    with TestClient(create_app(SETTINGS)) as c:
        yield c


def test_create_task_returns_201_with_all_fields(client):
    resp = client.post(
        "/api/tasks",
        json={"title": "Подготовить отчёт", "description": "ЛР №2", "status": "new"},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert set(body) == {"id", "title", "description", "status", "created_at"}
    UUID(body["id"])
    assert body["title"] == "Подготовить отчёт"
    assert body["status"] == "new"
    assert body["created_at"].endswith("Z")


def test_create_task_defaults(client):
    body = client.post("/api/tasks", json={"title": "Минимум"}).json()

    assert body["description"] == ""
    assert body["status"] == "new"


def test_client_cannot_set_id_and_created_at(client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    body = client.post(
        "/api/tasks",
        json={"title": "x", "id": fake_id, "created_at": "2000-01-01T00:00:00Z"},
    ).json()

    assert body["id"] != fake_id
    assert not body["created_at"].startswith("2000")


@pytest.mark.parametrize(
    "payload",
    [{}, {"title": ""}, {"title": "x", "status": "archived"}, {"title": "x" * 201}],
)
def test_create_task_validation_error(client, payload):
    assert client.post("/api/tasks", json=payload).status_code == 422


def test_crud_scenario(client):
    task = client.post("/api/tasks", json={"title": "A"}).json()
    task_id = task["id"]

    assert [t["id"] for t in client.get("/api/tasks").json()] == [task_id]
    assert client.get(f"/api/tasks/{task_id}").json() == task

    updated = client.patch(f"/api/tasks/{task_id}", json={"status": "in_progress"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"
    assert updated.json()["title"] == "A"

    assert client.delete(f"/api/tasks/{task_id}").status_code == 204
    assert client.get(f"/api/tasks/{task_id}").status_code == 404
    assert client.get("/api/tasks").json() == []


def test_unknown_task_returns_404(client):
    missing = "11111111-1111-1111-1111-111111111111"
    assert client.get(f"/api/tasks/{missing}").json() == {"detail": "Task not found"}
    assert client.patch(f"/api/tasks/{missing}", json={"title": "y"}).status_code == 404
    assert client.delete(f"/api/tasks/{missing}").status_code == 404
