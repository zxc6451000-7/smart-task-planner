import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from task_service.config import Settings
from task_service.main import create_app
from task_service.models import Task
from task_service.notifier import WebhookNotifier

URL = "http://notifications.test/api/webhooks/task_created"
FAST = Settings(webhook_url=URL, webhook_max_attempts=3, webhook_retry_base_delay=0.01)


def run_notifier(handler, tasks, settings=FAST):
    """Прогнать события через notifier с подменённым HTTP-транспортом."""

    async def scenario():
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        notifier = WebhookNotifier(settings, client=client)
        await notifier.start()
        for t in tasks:
            notifier.enqueue(t)
        await notifier.wait_idle()
        await notifier.stop()
        await client.aclose()
        return notifier

    return asyncio.run(scenario())


def test_sends_task_json_with_event_headers():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"status": "accepted"})

    task = Task(title="Задача", description="d")
    notifier = run_notifier(handler, [task])

    assert len(notifier.delivered) == 1 and notifier.failed == []
    req = requests[0]
    assert req.method == "POST" and str(req.url) == URL
    assert Task.model_validate_json(req.content) == task
    assert req.headers["X-Event-Type"] == "task.created"
    assert req.headers["X-Event-Id"] == str(notifier.delivered[0].event_id)
    assert req.headers["X-Delivery-Attempt"] == "1"


def test_retries_on_server_error_with_same_event_id():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(503 if len(requests) < 3 else 200)

    notifier = run_notifier(handler, [Task(title="x")])

    assert len(notifier.delivered) == 1
    assert [r.headers["X-Delivery-Attempt"] for r in requests] == ["1", "2", "3"]
    assert len({r.headers["X-Event-Id"] for r in requests}) == 1


def test_gives_up_after_max_attempts_when_service_is_down():
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("connection refused", request=request)

    notifier = run_notifier(handler, [Task(title="x")])

    assert calls == FAST.webhook_max_attempts
    assert notifier.delivered == []
    assert len(notifier.failed) == 1
    assert "ConnectError" in notifier.failed[0].last_error


def test_client_error_is_not_retried():
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(422)

    notifier = run_notifier(handler, [Task(title="x")])

    assert calls == 1
    assert notifier.failed[0].last_error == "HTTP 422"


def test_queue_overflow_does_not_raise():
    async def scenario():
        notifier = WebhookNotifier(Settings(webhook_url=URL, webhook_queue_size=1))
        notifier.enqueue(Task(title="1"))
        notifier.enqueue(Task(title="2"))  # воркер не запущен — очередь переполнена
        return notifier

    notifier = asyncio.run(scenario())
    assert len(notifier.failed) == 1
    assert notifier.failed[0].last_error == "queue is full"


def test_create_task_returns_201_when_notification_service_is_down():
    settings = Settings(
        webhook_url="http://127.0.0.1:9/api/webhooks/task_created",  # закрытый порт
        webhook_timeout=0.2,
        webhook_max_attempts=1,
    )
    with TestClient(create_app(settings)) as client:
        resp = client.post("/api/tasks", json={"title": "Сервис уведомлений лежит"})
        assert resp.status_code == 201
        assert client.get("/api/tasks").status_code == 200


@pytest.mark.parametrize("status", [200, 500])
def test_create_task_enqueues_webhook(status):
    received = []

    def handler(request):
        received.append(request)
        return httpx.Response(status)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    notifier = WebhookNotifier(FAST, client=client)
    with TestClient(create_app(FAST, notifier)) as api:
        task = api.post("/api/tasks", json={"title": "Вебхук"}).json()
        api.portal.call(notifier.wait_idle)
        api.portal.call(client.aclose)

    assert received, "вебхук не отправлен"
    assert Task.model_validate_json(received[0].content).model_dump(mode="json") == task
