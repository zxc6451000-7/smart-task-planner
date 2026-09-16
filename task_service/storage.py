"""Хранилище задач в памяти процесса."""

from threading import Lock
from uuid import UUID

from .models import Task, TaskCreate, TaskUpdate


class TaskStorage:
    def __init__(self) -> None:
        self._tasks: dict[UUID, Task] = {}
        self._lock = Lock()

    def create(self, data: TaskCreate) -> Task:
        task = Task(**data.model_dump())
        with self._lock:
            self._tasks[task.id] = task
        return task

    def list(self) -> list[Task]:
        with self._lock:
            return sorted(self._tasks.values(), key=lambda t: t.created_at)

    def get(self, task_id: UUID) -> Task | None:
        with self._lock:
            return self._tasks.get(task_id)

    def update(self, task_id: UUID, data: TaskUpdate) -> Task | None:
        changes = data.model_dump(exclude_none=True)
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            updated = task.model_copy(update=changes)
            self._tasks[task_id] = updated
            return updated

    def delete(self, task_id: UUID) -> bool:
        with self._lock:
            return self._tasks.pop(task_id, None) is not None
