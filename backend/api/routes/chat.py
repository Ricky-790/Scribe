import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.sse import EventSourceResponse
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
        conversation_history = await message_service.get_conversation_messages(
            session=session, conversation_id=conversation_id, user_id=user.user_id
        )
        model_message_history = db_messages_to_model_messages(conversation_history)
    user_message = await message_service.add_message(
        session=session,
        conversation_id=conversation_id,
        role="User",
        message_content=payload.message,
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
            session, user.user_id, payload.message, assistant_message.id
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
):
    chats = await message_service.get_all_conversations(session=session, user_id=user.user_id)
    # print(chats)
    return [ChatItem(conversation_id = str(c.id), title=c.title, updated_at=c.updated_at) for c in chats]
