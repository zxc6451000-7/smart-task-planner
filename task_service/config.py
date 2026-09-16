"""Настройки Task Service из переменных окружения."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    webhook_url: str = "http://localhost:8001/api/webhooks/task_created"
    webhook_timeout: float = 2.0
    webhook_max_attempts: int = 5
    webhook_retry_base_delay: float = 0.5
    webhook_retry_max_delay: float = 10.0
    webhook_queue_size: int = 1000

    @classmethod
    def from_env(cls) -> "Settings":
        d = cls()
        return cls(
            webhook_url=os.getenv("NOTIFICATION_WEBHOOK_URL", d.webhook_url),
            webhook_timeout=float(os.getenv("WEBHOOK_TIMEOUT", d.webhook_timeout)),
            webhook_max_attempts=int(os.getenv("WEBHOOK_MAX_ATTEMPTS", d.webhook_max_attempts)),
            webhook_retry_base_delay=float(
                os.getenv("WEBHOOK_RETRY_BASE_DELAY", d.webhook_retry_base_delay)
            ),
            webhook_retry_max_delay=float(
                os.getenv("WEBHOOK_RETRY_MAX_DELAY", d.webhook_retry_max_delay)
            ),
            webhook_queue_size=int(os.getenv("WEBHOOK_QUEUE_SIZE", d.webhook_queue_size)),
        )
