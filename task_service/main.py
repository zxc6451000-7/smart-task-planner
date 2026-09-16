"""Task Service: управление задачами."""

import logging
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, HTTPException, Response, status

from .config import Settings
from .models import Task, TaskCreate, TaskUpdate
from .notifier import WebhookNotifier
from .storage import TaskStorage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app(settings: Settings | None = None, notifier: WebhookNotifier | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    notifier = notifier or WebhookNotifier(settings)
    storage = TaskStorage()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await notifier.start()
        yield
        await notifier.stop()

    app = FastAPI(title="Task Service", version="1.1", lifespan=lifespan)
    app.state.storage = storage
    app.state.notifier = notifier

    def get_or_404(task_id: UUID) -> Task:
        task = storage.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    @app.post("/api/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
    async def create_task(data: TaskCreate) -> Task:
        task = storage.create(data)
        notifier.enqueue(task)
        return task

    @app.get("/api/tasks", response_model=list[Task])
    async def list_tasks() -> list[Task]:
        return storage.list()

    @app.get("/api/tasks/{task_id}", response_model=Task)
    async def get_task(task_id: UUID) -> Task:
        return get_or_404(task_id)

    @app.patch("/api/tasks/{task_id}", response_model=Task)
    async def update_task(task_id: UUID, data: TaskUpdate) -> Task:
        task = storage.update(task_id, data)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    @app.delete("/api/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_task(task_id: UUID) -> Response:
        if not storage.delete(task_id):
            raise HTTPException(status_code=404, detail="Task not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/health")
    async def health() -> dict:
        return {
            "status": "ok",
            "webhook_delivered": len(notifier.delivered),
            "webhook_failed": len(notifier.failed),
        }

    return app


app = create_app()
