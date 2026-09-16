"""Notification Service: приём события о создании задачи."""

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException

from .models import Notification, Task, WebhookResponse
from .sender import NotificationSender

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("notification_service")

DEFAULT_LOG_FILE = "logs/notifications.log"


def create_app(log_file: Path | None = None) -> FastAPI:
    log_file = log_file or Path(os.getenv("NOTIFICATION_LOG_FILE", DEFAULT_LOG_FILE))
    sender = NotificationSender(log_file)

    app = FastAPI(title="Notification Service", version="1.1")
    app.state.sender = sender

    @app.post("/api/webhooks/task_created", response_model=WebhookResponse)
    def task_created(
        task: Task,
        x_event_id: str | None = Header(default=None),
        x_event_type: str | None = Header(default=None),
    ) -> WebhookResponse:
        if x_event_type not in (None, "task.created"):
            logger.warning("Неожиданный X-Event-Type=%s для задачи %s", x_event_type, task.id)
        event_id = x_event_id or str(task.id)
        try:
            accepted = sender.notify(task, event_id)
        except OSError as exc:
            logger.error("Не удалось записать уведомление в %s: %s", sender.log_file, exc)
            raise HTTPException(status_code=503, detail="Notification log is unavailable")
        return WebhookResponse(status="accepted" if accepted else "duplicate")

    @app.get("/api/notifications", response_model=list[Notification])
    def list_notifications() -> list[Notification]:
        return sender.history

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "notifications": len(sender.history)}

    return app


app = create_app()
