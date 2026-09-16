"""Task Service: управление задачами."""

from uuid import UUID

from fastapi import FastAPI, HTTPException, Response, status

from .models import Task, TaskCreate, TaskUpdate
from .storage import TaskStorage


def create_app() -> FastAPI:
    app = FastAPI(title="Task Service", version="1.0")
    storage = TaskStorage()
    app.state.storage = storage

    def get_or_404(task_id: UUID) -> Task:
        task = storage.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    @app.post("/api/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
    async def create_task(data: TaskCreate) -> Task:
        return storage.create(data)

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

    return app


app = create_app()
