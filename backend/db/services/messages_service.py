from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Sequence, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_404_NOT_FOUND

from backend.db.models import Conversations, Messages


class MessagesService:
    def __init__(self):
        pass

    async def conversation_exists(
        self, session: AsyncSession, conversation_id: UUID, user_id: UUID
    ) -> bool:
        """Check if a conversation exists"""
        result = await session.get(Conversations, conversation_id)
        if result is None:
            return False
        return result.user_id == user_id

    async def create_new_conversation(
        self, session: AsyncSession, user_id: UUID, title: str
    ) -> UUID:
        """Create a new conversation"""
        new_conversation = Conversations(user_id=user_id, title=title)
        session.add(new_conversation)
        await session.commit()
        await session.refresh(new_conversation)
        return new_conversation.id

    async def add_message(
        self,
        session: AsyncSession,
        conversation_id: UUID,
        role: str,
        message_content: str,
        sequence_no: int | None = None,
    ) -> Messages:
        """Add a message to an existing conversation."""

        # Make sure the conversation exists
        conversation = await session.get(Conversations, conversation_id)

        if conversation is None:
            raise HTTPException(
                detail=f"Conversation {conversation_id} not found",
                status_code=HTTP_404_NOT_FOUND,
            )

        # Get the latest sequence number
        if sequence_no is None:
            result = await session.execute(
                select(func.max(Messages.sequence_no)).where(
                    Messages.conversation_id == conversation_id
                )
            )

            sequence_no = result.scalar_one_or_none()

        # Start at 0 for the first message
        next_sequence = 0 if sequence_no is None else sequence_no + 1

        message = Messages(
            conversation_id=conversation_id,
            role=role,
            message_content=message_content,
            sequence_no=next_sequence,
        )

        session.add(message)

        # Keep conversation's activity timestamp up to date
        conversation.updated_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(message)

        return message

    async def get_conversation_messages(
        self, session: AsyncSession, conversation_id: UUID, user_id: UUID
    ) -> list[Messages]:
        """Get all messages in a conversation"""
        conversation = await session.get(Conversations, conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise HTTPException(
                detail=f"Conversation {conversation_id} not found",
                status_code=HTTP_404_NOT_FOUND,
            )
        result = await session.execute(
            select(Messages)
            .where(Messages.conversation_id == conversation_id)
            .order_by(Messages.sequence_no.asc())
        )

        return result.scalars().all()

    async def get_all_conversations(
        self, session: AsyncSession, user_id: UUID, limit: int = 5, offset: int = 0
    ) -> list[Conversations]:
        results = await session.execute(
            select(Conversations.id, Conversations.title, Conversations.updated_at)
            .where(Conversations.user_id == user_id)
            .order_by(Conversations.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(results.all())



message_service = MessagesService()
