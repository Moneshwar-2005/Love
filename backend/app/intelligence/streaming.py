"""
Streaming Generation and SSE Transport for the Universal Intelligence Layer (Phase 03).
"""

import json
import time
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import get_logger
from backend.app.database.models.conversation import Message
from backend.app.database.session import AsyncSessionLocal
from backend.app.intelligence.conversation import ConversationManager
from backend.app.intelligence.schemas import StreamChunk

logger = get_logger("intelligence.streaming")


class StreamingManager:
    """
    Orchestrates chunk delivery to HTTP Server-Sent Event (SSE) clients,
    tracks generation lifecycle, and persists streaming state to the database.
    """

    def __init__(self, conversation_manager: ConversationManager):
        self.conversation_manager = conversation_manager

    async def stream_sse_generator(
        self,
        chunk_generator: AsyncGenerator[StreamChunk, None],
        message_id: str,
        conversation_id: str,
        db: Optional[AsyncSession] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Wraps provider StreamChunk generator into standard SSE event-stream lines.
        Ensures message status in the database accurately reflects completion, interruption, or failure.
        """
        start_time = time.perf_counter()
        accumulated_text = ""
        is_completed = False
        error_msg = None

        try:
            async for chunk in chunk_generator:
                accumulated_text = chunk.accumulated or (accumulated_text + chunk.delta)

                payload = {
                    "conversation_id": conversation_id,
                    "message_id": message_id,
                    "delta": chunk.delta,
                    "role": chunk.role.value,
                    "provider": chunk.provider,
                    "model": chunk.model,
                    "is_done": chunk.is_done,
                    "finish_reason": chunk.finish_reason,
                    "status": "streaming" if not chunk.is_done else "completed",
                }
                yield f"data: {json.dumps(payload)}\n\n"

                if chunk.is_done:
                    is_completed = True
                    break

        except GeneratorExit:
            # Client disconnected prematurely
            logger.warning(f"Client disconnected during streaming for message {message_id}")
            error_msg = "Client disconnected before completion."
        except Exception as exc:
            logger.error(f"Error during streaming for message {message_id}: {exc}", exc_info=True)
            error_msg = str(exc)
            err_payload = {
                "conversation_id": conversation_id,
                "message_id": message_id,
                "error": error_msg,
                "status": "failed",
            }
            yield f"data: {json.dumps(err_payload)}\n\n"

        finally:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            final_status = "completed" if is_completed else ("interrupted" if error_msg == "Client disconnected before completion." else "failed")

            # Persist the final accumulated text and status to the database
            try:
                if db is not None:
                    await self.conversation_manager.update_message_content(
                        db=db,
                        message_id=message_id,
                        content=accumulated_text or ("Generation failed." if final_status == "failed" else ""),
                        status=final_status,
                        latency_ms=latency_ms,
                        error_message=error_msg,
                    )
                else:
                    async with AsyncSessionLocal() as session:
                        await self.conversation_manager.update_message_content(
                            db=session,
                            message_id=message_id,
                            content=accumulated_text or ("Generation failed." if final_status == "failed" else ""),
                            status=final_status,
                            latency_ms=latency_ms,
                            error_message=error_msg,
                        )
            except Exception as db_exc:
                logger.error(f"Failed to update message status after streaming: {db_exc}")
