"""
Conversation Context Manager for the Universal Intelligence Layer (Phase 03).
"""

from typing import Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config.settings import Settings, get_settings
from backend.app.database.models.conversation import Message
from backend.app.intelligence.identity import SystemIdentity
from backend.app.intelligence.schemas import ChatMessage, Role, TaskIntent


class ContextManager:
    """
    Assembles, token-budgets, and formats conversation history into model-ready context arrays.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Fast token estimation heuristic (~4 chars per token).
        Avoids heavyweight tokenizers while preserving safety margins.
        """
        return max(1, len(text) // 4)

    async def assemble_context(
        self,
        db: AsyncSession,
        conversation_id: Optional[str],
        user_query: str,
        intent: Optional[TaskIntent] = None,
        user_name: Optional[str] = None,
        max_messages: Optional[int] = None,
        token_budget: Optional[int] = None,
        memories: Optional[List[Any]] = None,
        custom_instructions: Optional[str] = None,
    ) -> List[ChatMessage]:
        """
        Retrieves recent conversation history from the database, applies token budgeting,
        prepends the central LOVE system prompt (including persistent personal memories if retrieved),
        and appends the user's latest query.
        """
        messages: List[ChatMessage] = []

        # 1. Format retrieved memories into system instructions if present
        extra_instructions: List[str] = []
        if custom_instructions:
            extra_instructions.append(custom_instructions)

        if memories:
            memory_lines = [
                "<relevant_memories>",
                "The following persistent personal memories and project contexts were retrieved based on the user's prompt. "
                "Use them naturally to maintain continuity, personal preferences, and accurate context without quoting internal IDs or metadata unless asked:"
            ]
            for m in memories:
                # Handle either MemorySearchResult or MemoryResponse
                mem_obj = getattr(m, "memory", m)
                category = getattr(mem_obj, "category", "")
                cat_val = category.value if hasattr(category, "value") else str(category)
                cat_tag = f"[{cat_val.upper()}] " if cat_val else ""
                content = getattr(mem_obj, "content", str(mem_obj))
                memory_lines.append(f"- {cat_tag}{content}")
            memory_lines.append("</relevant_memories>")
            extra_instructions.append("\n".join(memory_lines))

        combined_instructions = "\n\n".join(extra_instructions) if extra_instructions else None

        # 2. Generate system prompt
        system_prompt = SystemIdentity.build_system_prompt(
            intent=intent,
            user_name=user_name,
            custom_instructions=combined_instructions,
        )
        messages.append(ChatMessage(role=Role.SYSTEM, content=system_prompt))

        effective_max_msgs = max_messages or self.settings.INTELLIGENCE_CONTEXT_MAX_MESSAGES
        effective_budget = token_budget or self.settings.INTELLIGENCE_CONTEXT_MAX_TOKENS

        current_tokens = self.estimate_tokens(system_prompt) + self.estimate_tokens(user_query)

        # 2. Retrieve history if conversation_id provided
        history_turns: List[ChatMessage] = []
        if conversation_id:
            stmt = (
                select(Message)
                .where(
                    Message.conversation_id == conversation_id,
                    Message.status == "completed"
                )
                .order_by(Message.created_at.desc())
                .limit(effective_max_msgs)
            )
            result = await db.execute(stmt)
            db_messages = list(result.scalars().all())

            # Messages are retrieved newest-first; reverse to chronological order
            db_messages.reverse()

            for msg in db_messages:
                role = Role.USER if msg.role == "user" else Role.ASSISTANT
                msg_tokens = self.estimate_tokens(msg.content)
                if current_tokens + msg_tokens > effective_budget:
                    # Token budget reached, skip older history
                    continue
                current_tokens += msg_tokens
                history_turns.append(ChatMessage(role=role, content=msg.content))

        messages.extend(history_turns)

        # 3. Append current user query
        messages.append(ChatMessage(role=Role.USER, content=user_query))

        return messages
