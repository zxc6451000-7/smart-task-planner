"""Доставка события task.created в Notification Service.

События кладутся в очередь в памяти и отправляются фоновым воркером,
поэтому недоступность Notification Service не влияет на ответ POST /api/tasks.
Временные ошибки (сеть, таймаут, 429, 5xx) повторяются с экспоненциальной
задержкой; после исчерпания попыток событие попадает в список failed и в лог.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import httpx

from .config import Settings
from .models import Task

logger = logging.getLogger("task_service.notifier")

EVENT_TYPE = "task.created"


@dataclass
class Delivery:
    task: Task
    event_id: UUID = field(default_factory=uuid4)
    attempt: int = 0
    last_error: str = ""


class WebhookNotifier:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self._client = client
        self._owns_client = client is None
        self._queue: asyncio.Queue[Delivery] = asyncio.Queue(maxsize=settings.webhook_queue_size)
        self._worker: asyncio.Task | None = None
        self._pending_retries: set[asyncio.Task] = set()
        self._in_flight = 0
        self.delivered: list[Delivery] = []
        self.failed: list[Delivery] = []

    async def start(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.settings.webhook_timeout)
        self._worker = asyncio.create_task(self._run())

    async def stop(self) -> None:
        for t in [self._worker, *self._pending_retries]:
            if t is not None:
                t.cancel()
        await asyncio.gather(
            *(t for t in [self._worker, *self._pending_retries] if t), return_exceptions=True
        )
        undelivered = self._queue.qsize() + len(self._pending_retries)
        if undelivered:
            logger.warning("Остановка: %d событий не доставлено и будут потеряны", undelivered)
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    def enqueue(self, task: Task) -> None:
        """Поставить событие в очередь. Никогда не бросает исключений."""
        delivery = Delivery(task=task)
        try:
            self._queue.put_nowait(delivery)
        except asyncio.QueueFull:
            delivery.last_error = "queue is full"
            self.failed.append(delivery)
            logger.error("Очередь вебхуков переполнена, событие %s для задачи %s потеряно",
                         delivery.event_id, task.id)

    async def wait_idle(self, timeout: float = 5.0) -> None:
        """Дождаться, пока очередь и отложенные повторы опустеют (для тестов)."""
        async def _wait() -> None:
            while self._queue.qsize() or self._pending_retries or self._in_flight:
                await asyncio.sleep(0.01)
        await asyncio.wait_for(_wait(), timeout)

    async def _run(self) -> None:
        while True:
            delivery = await self._queue.get()
            self._in_flight += 1
            try:
                await self._process(delivery)
            except Exception:  # воркер не должен умирать ни при каких ошибках
                logger.exception("Непредвиденная ошибка при доставке %s", delivery.event_id)
            finally:
                self._in_flight -= 1

    async def _process(self, delivery: Delivery) -> None:
        delivery.attempt += 1
        retryable, error = await self._send(delivery)
        if error is None:
            self.delivered.append(delivery)
            logger.info("Вебхук %s доставлен (задача %s, попытка %d)",
                        delivery.event_id, delivery.task.id, delivery.attempt)
            return

        delivery.last_error = error
        if retryable and delivery.attempt < self.settings.webhook_max_attempts:
            delay = min(
                self.settings.webhook_retry_base_delay * 2 ** (delivery.attempt - 1),
                self.settings.webhook_retry_max_delay,
            )
            logger.warning("Вебхук %s не доставлен (%s), попытка %d/%d, повтор через %.1f c",
                           delivery.event_id, error, delivery.attempt,
                           self.settings.webhook_max_attempts, delay)
            retry = asyncio.create_task(self._requeue_later(delivery, delay))
            self._pending_retries.add(retry)
            retry.add_done_callback(self._pending_retries.discard)
        else:
            self.failed.append(delivery)
            logger.error("Вебхук %s для задачи %s окончательно не доставлен после %d попыток: %s",
                         delivery.event_id, delivery.task.id, delivery.attempt, error)

    async def _requeue_later(self, delivery: Delivery, delay: float) -> None:
        await asyncio.sleep(delay)
        await self._queue.put(delivery)

    async def _send(self, delivery: Delivery) -> tuple[bool, str | None]:
        """Возвращает (можно_повторить, текст_ошибки или None при успехе)."""
        headers = {
            "X-Event-Type": EVENT_TYPE,
            "X-Event-Id": str(delivery.event_id),
            "X-Delivery-Attempt": str(delivery.attempt),
        }
        try:
            resp = await self._client.post(
                self.settings.webhook_url,
                json=delivery.task.model_dump(mode="json"),
                headers=headers,
            )
        except httpx.TimeoutException:
            return True, "timeout"
        except httpx.HTTPError as exc:
            return True, f"{type(exc).__name__}: {exc}"

        if resp.is_success:
            return False, None
        error = f"HTTP {resp.status_code}"
        return resp.status_code == 429 or resp.status_code >= 500, error
