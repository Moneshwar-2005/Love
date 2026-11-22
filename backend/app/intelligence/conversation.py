"""
Conversation and Message persistence service for the Universal Intelligence Layer (Phase 03).
"""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import delete, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.logging import get_logger
from backend.app.database.models.conversation import Conversation, Message
from backend.app.intelligence.exceptions import ConversationNotFoundError
from backend.app.intelligence.schemas import TaskIntent, TokenUsage

logger = get_logger("intelligence.conversation")


class ConversationManager:
    """
    CRUD management and state persistence for conversation threads and individual messages.
    Enforces user ownership boundaries across all operations.
    """

    @staticmethod
    def derive_title_from_prompt(prompt: str) -> str:
        """Derives a concise conversation title from the opening prompt."""
        clean = " ".join(prompt.strip().split())
        if len(clean) <= 40:
            return clean.capitalize()
        # Truncate to nearest word
        truncated = clean[:40]
        last_space = truncated.rfind(" ")
        if last_space > 10:
            truncated = truncated[:last_space]
        return f"{truncated.capitalize()}..."

    async def create_conversation(
        self,
        db: AsyncSession,
        user_id: str,
        title: Optional[str] = None,
        origin_device_id: Optional[str] = None,
    ) -> Conversation:
        """Initializes a new persistent conversation thread."""
        conv = Conversation(
            user_id=user_id,
            title=title or "New Conversation",
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)

        # Record synchronization event
        try:
            from backend.app.sync.service import get_sync_service
            await get_sync_service().record_event(
                db=db,
                user_id=user_id,
                entity_type="conversation",
                entity_id=conv.id,
                action="created",
                payload={
                    "id": conv.id,
                    "title": conv.title,
                    "is_pinned": conv.is_pinned,
                    "is_archived": conv.is_archived,
                    "created_at": conv.created_at.isoformat() if conv.created_at else None,
                },
                origin_device_id=origin_device_id
            )
            await db.commit()
        except Exception as exc:
            logger.debug(f"Sync event recording skipped for conversation creation: {exc}")

        return conv

    async def get_conversation(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
        include_messages: bool = True,
    ) -> Conversation:
        """
        Retrieves a conversation by ID, strictly verifying user ownership.
        Raises ConversationNotFoundError if not found or unauthorized.
        """
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).execution_options(populate_existing=True)
        if include_messages:
            stmt = stmt.options(selectinload(Conversation.messages))

        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise ConversationNotFoundError(conversation_id=conversation_id)
        return conversation

    async def list_conversations(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        include_archived: bool = False,
    ) -> List[Conversation]:
        """Lists user's conversations ordered by recency."""
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(
                desc(Conversation.is_pinned),
                desc(Conversation.last_message_at),
                desc(Conversation.updated_at),
            )
            .limit(limit)
            .offset(offset)
        )
        if not include_archived:
            stmt = stmt.where(Conversation.is_archived == False)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def delete_conversation(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
        origin_device_id: Optional[str] = None,
    ) -> bool:
        """Permanently deletes a conversation and all its cascade-related messages."""
        conv = await self.get_conversation(db, conversation_id, user_id, include_messages=False)
        await db.delete(conv)
        await db.commit()

        # Record synchronization event
        try:
            from backend.app.sync.service import get_sync_service
            await get_sync_service().record_event(
                db=db,
                user_id=user_id,
                entity_type="conversation",
                entity_id=conversation_id,
                action="deleted",
                payload={"id": conversation_id},
                origin_device_id=origin_device_id
            )
            await db.commit()
        except Exception as exc:
            logger.debug(f"Sync event recording skipped for conversation deletion: {exc}")

        return True

    async def add_message(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        intent: Optional[TaskIntent] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        status: str = "completed",
        latency_ms: Optional[float] = None,
        usage: Optional[TokenUsage] = None,
        error_message: Optional[str] = None,
        origin_device_id: Optional[str] = None,
    ) -> Message:
        """Appends a message turn and updates the conversation's recency timestamp."""
        now = datetime.now(timezone.utc)
        msg = Message(
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,
            content=content,
            intent=intent.value if intent else None,
            provider=provider,
            model=model,
            status=status,
            latency_ms=latency_ms,
            tokens_prompt=usage.prompt_tokens if usage else None,
            tokens_completion=usage.completion_tokens if usage else None,
            tokens_total=usage.total_tokens if usage else None,
            error_message=error_message,
        )
        db.add(msg)

        # Update parent conversation recency
        await db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(last_message_at=now, updated_at=now)
        )

        await db.commit()
        await db.refresh(msg)

        # Record synchronization event
        try:
            from backend.app.sync.service import get_sync_service
            await get_sync_service().record_event(
                db=db,
                user_id=user_id,
                entity_type="message",
                entity_id=msg.id,
                action="created",
                payload={
                    "id": msg.id,
                    "conversation_id": conversation_id,
                    "role": role,
                    "content": content,
                    "intent": msg.intent,
                    "provider": provider,
                    "model": model,
                    "status": status,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                },
                origin_device_id=origin_device_id
            )
            await db.commit()
        except Exception as exc:
            logger.debug(f"Sync event recording skipped for message addition: {exc}")

        return msg

    async def update_message_content(
        self,
        db: AsyncSession,
        message_id: str,
        content: str,
        status: str = "completed",
        latency_ms: Optional[float] = None,
        error_message: Optional[str] = None,
    ) -> Optional[Message]:
        """Updates a message (e.g. at the conclusion of a streaming session)."""
        stmt = (
            update(Message)
            .where(Message.id == message_id)
            .values(
                content=content,
                status=status,
                latency_ms=latency_ms,
                error_message=error_message,
                updated_at=datetime.now(timezone.utc),
            )
        )
        await db.execute(stmt)
        await db.commit()

        res = await db.execute(select(Message).where(Message.id == message_id))
        msg = res.scalar_one_or_none()

        # Record synchronization event
        if msg:
            try:
                from backend.app.sync.service import get_sync_service
                await get_sync_service().record_event(
                    db=db,
                    user_id=msg.user_id,
                    entity_type="message",
                    entity_id=message_id,
                    action="updated",
                    payload={
                        "id": message_id,
                        "conversation_id": msg.conversation_id,
                        "content": content,
                        "status": status,
                        "latency_ms": latency_ms,
                        "error_message": error_message,
                    }
                )
                await db.commit()
            except Exception as exc:
                logger.debug(f"Sync event recording skipped for message update: {exc}")

        return msg
