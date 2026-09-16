"""Эмуляция отправки уведомлений: запись в консоль и в лог-файл."""

import logging
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from .models import Notification, Task

logger = logging.getLogger("notification_service")


class NotificationSender:
    def __init__(self, log_file: Path, dedup_capacity: int = 10_000, history_size: int = 100) -> None:
        self.log_file = log_file
        self._seen: OrderedDict[str, None] = OrderedDict()
        self._dedup_capacity = dedup_capacity
        self._history_size = history_size
        self.history: list[Notification] = []
        self._lock = Lock()

    def notify(self, task: Task, event_id: str) -> bool:
        """Зафиксировать уведомление. Возвращает False, если событие уже обработано.

        Бросает OSError, если лог-файл недоступен, — тогда событие не считается
        обработанным и Task Service сможет доставить его повторно.
        """
        with self._lock:
            if event_id in self._seen:
                logger.info("Дубликат события %s (задача %s) пропущен", event_id, task.id)
                return False

            notification = Notification(
                event_id=event_id,
                received_at=datetime.now(timezone.utc),
                message=f"Создана задача «{task.title}» (статус: {task.status.value})",
                task=task,
            )
            self._write(notification)
            logger.info("УВЕДОМЛЕНИЕ: %s [task=%s, event=%s]", notification.message, task.id, event_id)

            self._seen[event_id] = None
            if len(self._seen) > self._dedup_capacity:
                self._seen.popitem(last=False)
            self.history.append(notification)
            del self.history[:-self._history_size]
            return True

    def _write(self, n: Notification) -> None:
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(n.model_dump_json() + "\n")
