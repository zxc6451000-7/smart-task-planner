"""Сквозной тест: оба сервиса запускаются настоящими процессами uvicorn."""

import json
import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_until(check, timeout=10.0, interval=0.1):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if check():
                return
        except httpx.HTTPError:
            pass
        time.sleep(interval)
    raise AssertionError("условие не выполнилось за отведённое время")


@contextmanager
def service(module: str, port: int, env: dict):
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", f"{module}.main:app", "--port", str(port)],
        cwd=ROOT,
        env={**os.environ, **env},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        wait_until(lambda: httpx.get(f"{base}/health").status_code == 200)
        yield base
    finally:
        proc.terminate()
        proc.wait(timeout=10)


@pytest.fixture
def ports():
    return free_port(), free_port()


def task_service_env(notif_port: int) -> dict:
    return {
        "NOTIFICATION_WEBHOOK_URL": f"http://127.0.0.1:{notif_port}/api/webhooks/task_created",
        "WEBHOOK_RETRY_BASE_DELAY": "0.3",
        "WEBHOOK_MAX_ATTEMPTS": "10",
    }


def test_task_creation_triggers_notification(tmp_path, ports):
    task_port, notif_port = ports
    log_file = tmp_path / "notifications.log"

    with service("notification_service", notif_port, {"NOTIFICATION_LOG_FILE": str(log_file)}) as notif, \
         service("task_service", task_port, task_service_env(notif_port)) as tasks:
        resp = httpx.post(
            f"{tasks}/api/tasks",
            json={"title": "E2E задача", "description": "проверка вебхука", "status": "new"},
        )
        assert resp.status_code == 201
        task = resp.json()

        wait_until(lambda: len(httpx.get(f"{notif}/api/notifications").json()) == 1)
        notification = httpx.get(f"{notif}/api/notifications").json()[0]

        assert notification["task"] == task
        assert httpx.get(f"{tasks}/api/tasks/{task['id']}").json() == task
        assert httpx.get(f"{tasks}/health").json()["webhook_delivered"] == 1

    record = json.loads(log_file.read_text(encoding="utf-8").splitlines()[0])
    assert record["task"]["id"] == task["id"]


def test_notification_delivered_after_service_comes_back(tmp_path, ports):
    """Notification Service стартует позже — Task Service дожидается его повторами."""
    task_port, notif_port = ports
    log_file = tmp_path / "notifications.log"

    with service("task_service", task_port, task_service_env(notif_port)) as tasks:
        resp = httpx.post(f"{tasks}/api/tasks", json={"title": "Отложенная доставка"})
        assert resp.status_code == 201, "Task Service должен отвечать при недоступном получателе"
        time.sleep(0.5)
        assert httpx.get(f"{tasks}/health").json()["webhook_delivered"] == 0

        with service("notification_service", notif_port, {"NOTIFICATION_LOG_FILE": str(log_file)}) as notif:
            wait_until(lambda: len(httpx.get(f"{notif}/api/notifications").json()) == 1, timeout=30)
            assert httpx.get(f"{notif}/api/notifications").json()[0]["task"]["id"] == resp.json()["id"]
