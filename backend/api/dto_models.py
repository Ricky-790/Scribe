from typing import Literal, Optional
from uuid import UUID
from datetime import datetime
from fastapi import WebSocket
from pydantic import BaseModel

from agents_service.models import IntentEnum, TaskStatus
from backend.db.models import RunStatus


# Chat route
class ChatRequest(BaseModel):
    message: str
    conversation_id: UUID | None = None


class NewChatResponse(BaseModel):
    conversation_id: UUID


class ChatResponse(BaseModel):
    message: str
    intent: IntentEnum
    report_id: UUID | None = None


class ChatMessage(BaseModel):
    message_id: str
    role: str
    content: str
    sequence_no: int
    created_at: datetime


class ChatHistory(BaseModel):
    messages: list[ChatMessage]


class ChatItem(BaseModel):
    conversation_id: str
    title: str
    updated_at: datetime


# Reports route


class ReportStatusResponse(BaseModel):
    """Returned when the report is still in progress."""

    report_id: UUID
    status: str


class ReportResponse(BaseModel):
    """Returned when the report has completed successfully."""

    report_id: UUID
    goal: str
    intent: str | None
    categories: list[str] | None
    strategy_summary: str | None
    title: str | None
    content: str | None
    created_at: str
    updated_at: str


class ReportSummary(BaseModel):
    report_id: UUID
    title: str | None
    status: str | None


class ReportsListResponse(BaseModel):
    reports: list[ReportSummary]
    limit: int
    offset: int


class PublishMessage(BaseModel):
    phase: str
    status: str
    done: bool = False
    task_id: Optional[str] = None
    task_name: Optional[str] = None
    task_status: Optional[str] = None
    msg: Optional[str] = None
    # task_result: Optional[dict] = None


class ConnectionManager:
    """Wrapper class to handle Ws connections"""

    def __init__(self):
        self.connections: dict[UUID, WebSocket] = {}

    async def connect(self, report_id: UUID, websocket: WebSocket):
        await websocket.accept()
        self.connections[report_id] = websocket

    def disconnect(self, report_id: UUID):
        self.connections.pop(report_id, None)

    async def send(self, report_id, message: PublishMessage):
        websocket = self.connections.get(report_id)
        if websocket:
            await websocket.send_json(message.model_dump(mode="json"))
