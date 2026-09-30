import json
from collections import OrderedDict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.sse import EventSourceResponse
from pydantic_ai.messages import ModelMessage
from sqlalchemy.ext.asyncio import AsyncSession

from agents_service.agents import classify_query
from agents_service.agents.classifier_agent import classify_query_stream
from agents_service.models import IntentClassification, IntentEnum
from backend.api.deps import AuthenticatedUser, get_current_user
from backend.api.dto_models import (
    ChatHistory,
    ChatItem,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    NewChatResponse,
)
from backend.api.utils import db_messages_to_model_messages
from backend.celery_app.tasks import run_research_pipeline_task
from backend.db.services import message_service, reports_service
from backend.db.session import get_session
from custom_logger import get_logger

logger = get_logger()
router = APIRouter()


class MessageHistoryCache:
    """In-process LRU cache of converted model message history per conversation.

    Entries are keyed by ``(user_id, conversation_id)`` so a conversation's
    history can never be served to a different user. Values are always copied
    on read/write, so callers cannot mutate (or leak) a cached list.
    """

    def __init__(self, max_size: int = 256) -> None:
        self._store: OrderedDict[tuple[UUID, UUID], list[ModelMessage]] = OrderedDict()
        self._max_size = max_size

    @staticmethod
    def _key(user_id: UUID, conversation_id: UUID) -> tuple[UUID, UUID]:
        return (user_id, conversation_id)

    def get(self, user_id: UUID, conversation_id: UUID) -> list[ModelMessage] | None:
        key = self._key(user_id, conversation_id)
        history = self._store.get(key)
        if history is None:
            return None
        self._store.move_to_end(key)
        return list(history)

    def set(
        self, user_id: UUID, conversation_id: UUID, history: list[ModelMessage]
    ) -> None:
        key = self._key(user_id, conversation_id)
        self._store[key] = list(history)
        self._store.move_to_end(key)
        while len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def append(
        self,
        user_id: UUID,
        conversation_id: UUID,
        *messages: ModelMessage,
    ) -> None:
        """Append newly created messages to a cached conversation history."""
        key = self._key(user_id, conversation_id)
        history = self._store.setdefault(key, [])
        history.extend(messages)
        self._store.move_to_end(key)

    def invalidate(self, user_id: UUID, conversation_id: UUID) -> None:
        self._store.pop(self._key(user_id, conversation_id), None)


message_history_cache = MessageHistoryCache()


@router.post("/chat", response_class=EventSourceResponse)
async def send_message(
    payload: ChatRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    conversation_id = payload.conversation_id
    model_message_history = None
    if conversation_id is None:
        conversation_id = await message_service.create_new_conversation(
            session=session, user_id=user.user_id, title=payload.message
        )
    else:
        conversation_exists = await message_service.conversation_exists(
            session=session, conversation_id=conversation_id, user_id=user.user_id
        )
        if not conversation_exists:
            raise HTTPException(
                detail="Conversation not found", status_code=status.HTTP_404_NOT_FOUND
            )
        # Cache is keyed (user_id, conversation_id), so histories can never
        # be served across users; only fall back to the DB on a cache miss.
        model_message_history = message_history_cache.get(user.user_id, conversation_id)
        if model_message_history is None:
            conversation_history = await message_service.get_conversation_messages(
                session=session, conversation_id=conversation_id, user_id=user.user_id
            )
            model_message_history = db_messages_to_model_messages(conversation_history)
            message_history_cache.set(
                user.user_id, conversation_id, model_message_history
            )
    user_message = await message_service.add_message(
        session=session,
        conversation_id=conversation_id,
        role="User",
        message_content=payload.message,
    )
    # Keep the cache in sync so the next turn does not need to hit the DB.
    message_history_cache.append(
        user.user_id, conversation_id, *db_messages_to_model_messages([user_message])
    )
    # Tell frontend user_message is sent -> Show user chat bubble
    if payload.conversation_id is None:
        yield {
            "event": "conversation_created",
            "data": json.dumps(
                {
                    "conversation_id": str(conversation_id),
                }
            ),
        }
    yield {
        "event": "user_message_created",
        "data": ChatMessage(
            message_id=str(user_message.id),
            role=user_message.role,
            content=user_message.message_content,
            sequence_no=user_message.sequence_no,
            created_at=user_message.created_at,
        ),
    }
    yield {
        "event": "starting_response_stream",
        "data": "",
    }
    final_output: IntentClassification | None = None
    async for chunk in classify_query_stream(
        query=payload.message, message_history=model_message_history
    ):
        final_output = chunk
        yield {
            "event": "message_delta",
            "data": chunk.response,
        }
    if final_output is None:
        raise RuntimeError("No output from classification agent")
    assistant_message = await message_service.add_message(
        session=session,
        conversation_id=conversation_id,
        role="Agent",
        message_content=final_output.response,
    )
    message_history_cache.append(
        user.user_id,
        conversation_id,
        *db_messages_to_model_messages([assistant_message]),
    )
    yield {
        "event": "message_complete",
        "data": ChatMessage(
            message_id=str(assistant_message.id),
            role=assistant_message.role,
            content=assistant_message.message_content,
            sequence_no=assistant_message.sequence_no,
            created_at=assistant_message.created_at,
        ),
    }
    if final_output.intent == IntentEnum.RESEARCH_TOPIC:
        report = await reports_service.create_report(
            session,
            user.user_id,
            payload.message,
            assistant_message.id,
            intent=final_output.intent.value,
            categories=[c.value for c in final_output.categories],
            response=final_output.response,
        )
        run_research_pipeline_task.delay(str(report.id))
        yield {
            "event": "Starting research",
            "data": json.dumps(
                {"report_id": str(report.id), "title": report.report_title}
            ),
        }
    yield {
        "event": "done",
        "data": "",
    }


@router.get("/chat/{conversation_id}", response_model=ChatHistory)
async def get_conversation_messages(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: AuthenticatedUser = Depends(get_current_user),
):
    messages = await message_service.get_conversation_messages(
        session=session, conversation_id=conversation_id, user_id=user.user_id
    )
    return ChatHistory(
        messages=[
            ChatMessage(
                message_id=str(m.id),
                role=m.role,
                content=m.message_content,
                sequence_no=m.sequence_no,
                created_at=m.created_at,
            )
            for m in messages
        ]
    )


@router.get("/chats/all", response_model=list[ChatItem])
async def get_all_chats(
    session: AsyncSession = Depends(get_session),
    user: AuthenticatedUser = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """
    Return the caller's recent conversations, newest first.

    The limit is passed through explicitly — relying on the service default
    silently truncated the sidebar to five chats.
    """
    chats = await message_service.get_all_conversations(
        session=session, user_id=user.user_id, limit=limit, offset=offset
    )
    return [
        ChatItem(conversation_id=str(c.id), title=c.title, updated_at=c.updated_at)
        for c in chats
    ]
