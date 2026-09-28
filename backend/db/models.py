import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from agents_service.models import IntentEnum, TaskStatus


class Base(DeclarativeBase):
    pass


class RunStatus:
    PENDING = "pending"
    CLASSIFYING = "classifying"
    PLANNING = "planning"
    RESEARCHING = "researching"
    SYNTHESIZING = "synthesizing"
    DONE = "done"
    FAILED = "failed"


RUN_STATUS_VALUES = [
    RunStatus.PENDING,
    RunStatus.CLASSIFYING,
    RunStatus.PLANNING,
    RunStatus.RESEARCHING,
    RunStatus.SYNTHESIZING,
    RunStatus.DONE,
    RunStatus.FAILED,
]

ROLE_VALUES = ["User", "Agent"]


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    reports: Mapped[list["UserReport"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserReport(Base):
    __tablename__ = "user_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False, unique=True
    )
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(
        SAEnum(*[e.value for e in IntentEnum], name="intent_enum"), nullable=True
    )
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    categories: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    status: Mapped[str] = mapped_column(
        SAEnum(*RUN_STATUS_VALUES, name="run_status_enum"),
        nullable=False,
        default=RunStatus.PENDING,
    )

    strategy_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="reports")
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )
    message: Mapped["Messages"] = relationship(
        back_populates="report",
    )


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_reports.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )

    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    depends_on: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    status: Mapped[str] = mapped_column(
        SAEnum(*[e.value for e in TaskStatus], name="task_status_enum"),
        nullable=False,
        default=TaskStatus.PENDING.value,
    )
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    report: Mapped["UserReport"] = relationship(back_populates="tasks")


class Conversations(Base):
    __tablename__ = "conversations"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    messages: Mapped[list["Messages"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class Messages(Base):
    __tablename__ = "messages"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
    )
    role: Mapped[str] = mapped_column(
        SAEnum(*ROLE_VALUES, name="message_roles_enum"),
        nullable=False,
    )
    message_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    conversation: Mapped["Conversations"] = relationship(
        back_populates="messages",
    )
    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "sequence_no",
            name="uq_message_conversation_sequence",
        ),
    )
    report: Mapped["UserReport"] = relationship(
        back_populates="message",
    )
