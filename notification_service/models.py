"""Схема Task, которую Notification Service принимает в вебхуке (API_CONTRACT.md, раздел 2)."""

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class Task(BaseModel):
    id: UUID
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(max_length=2000)
    status: TaskStatus
    created_at: datetime


class WebhookResponse(BaseModel):
    status: Literal["accepted", "duplicate"]


class Notification(BaseModel):
    event_id: str
    received_at: datetime
    message: str
    task: Task
