"""
Response handling and formatting utilities for Universal Intelligence Layer (Phase 03).
"""

from backend.app.intelligence.schemas import (
    AssistantResponse,
    ChatResponse,
    TokenUsage,
)


class ResponseHandler:
    """
    Normalizes provider responses, computes fallback token usage, and constructs API payloads.
    """

    @staticmethod
    def format_chat_response(
        conversation_id: str,
        message_id: str,
        user_message: str,
        response: AssistantResponse,
    ) -> ChatResponse:
        """Constructs standardized ChatResponse."""
        usage = response.usage
        if usage.total_tokens == 0:
            prompt_t = max(1, len(user_message) // 4)
            comp_t = max(1, len(response.content) // 4)
            usage = TokenUsage(
                prompt_tokens=prompt_t,
                completion_tokens=comp_t,
                total_tokens=prompt_t + comp_t,
            )

        intent_str = response.intent.value if response.intent else "general"

        return ChatResponse(
            conversation_id=conversation_id,
            message_id=message_id,
            user_message=user_message,
            assistant_message=response.content,
            intent=intent_str,
            provider=response.provider,
            model=response.model,
            latency_ms=response.latency_ms,
            usage=usage,
        )
