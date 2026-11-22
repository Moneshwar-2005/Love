"""
Request Orchestrator for the Universal Intelligence Layer (Phase 03).
"""

from typing import Any, AsyncGenerator, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config.settings import Settings, get_settings
from backend.app.core.logging import get_logger
from backend.app.database.models.conversation import Conversation, Message
from backend.app.database.models.user import User
from backend.app.intelligence.context import ContextManager
from backend.app.intelligence.conversation import ConversationManager
from backend.app.intelligence.exceptions import ProviderUnavailableError
from backend.app.intelligence.intent import IntentClassifier
from backend.app.intelligence.model_router import ModelRouter
from backend.app.intelligence.provider_manager import ProviderManager
from backend.app.intelligence.schemas import (
    AssistantResponse,
    ChatRequest,
    StreamChunk,
)
from backend.app.intelligence.streaming import StreamingManager

logger = get_logger("intelligence.orchestrator")


class IntelligenceOrchestrator:
    """
    Coordinates the end-to-end lifecycle of user conversational requests:
    Intent Classification -> Conversation & Message Persistence -> Memory Retrieval ->
    Context Assembly -> Model Routing -> Provider Execution -> Memory Ingestion -> Response Normalization.
    """

    def __init__(
        self,
        context_manager: ContextManager,
        conversation_manager: ConversationManager,
        model_router: ModelRouter,
        provider_manager: ProviderManager,
        streaming_manager: StreamingManager,
        memory_service: Optional[Any] = None,
        work_service: Optional[Any] = None,
        settings: Optional[Settings] = None,
    ):
        self.context_manager = context_manager
        self.conversation_manager = conversation_manager
        self.model_router = model_router
        self.provider_manager = provider_manager
        self.streaming_manager = streaming_manager
        self.memory_service = memory_service
        self.work_service = work_service
        if self.work_service is None:
            try:
                from backend.app.work.service import get_work_service
                self.work_service = get_work_service()
            except Exception:
                self.work_service = None
        self.settings = settings or get_settings()

    async def execute_chat(
        self,
        db: AsyncSession,
        user: User,
        request: ChatRequest,
    ) -> Tuple[Conversation, Message, Message, AssistantResponse]:
        """
        Executes a complete synchronous conversation turn.
        Returns: (conversation, user_message_db, assistant_message_db, assistant_response_dto)
        """
        # 1. Classify natural language intent
        intent_result = IntentClassifier.classify(request.message)

        # 2. Resolve or create conversation
        if request.conversation_id:
            conv = await self.conversation_manager.get_conversation(
                db=db,
                conversation_id=request.conversation_id,
                user_id=user.id,
            )
        else:
            title = self.conversation_manager.derive_title_from_prompt(request.message)
            conv = await self.conversation_manager.create_conversation(
                db=db,
                user_id=user.id,
                title=title,
            )

        # 3. Persist incoming user message
        user_msg = await self.conversation_manager.add_message(
            db=db,
            conversation_id=conv.id,
            user_id=user.id,
            role="user",
            content=request.message,
            intent=intent_result.intent,
            status="completed",
        )

        # Check for ambiguity
        if intent_result.is_ambiguous and intent_result.clarification_prompt:
            clarification_content = intent_result.clarification_prompt
            assistant_msg = await self.conversation_manager.add_message(
                db=db,
                conversation_id=conv.id,
                user_id=user.id,
                role="assistant",
                content=clarification_content,
                intent=intent_result.intent,
                provider="system",
                model="intent_classifier",
                status="completed",
            )
            response = AssistantResponse(
                content=clarification_content,
                provider="system",
                model="intent_classifier",
                intent=intent_result.intent,
            )
            return conv, user_msg, assistant_msg, response

        # Check for Work Intelligence tool action requirement
        if intent_result.requires_action and self.work_service:
            try:
                task = await self.work_service.create_task(
                    db=db,
                    user_id=user.id,
                    title=f"Task: {request.message[:60]}",
                    description=request.message,
                    conversation_id=conv.id,
                )
                task = await self.work_service.execute_task(
                    db=db,
                    task_id=task.id,
                    user_id=user.id,
                )

                if task.status == "awaiting_approval":
                    pending_action = next((a for a in task.actions if a.status == "awaiting_approval"), None)
                    act_title = pending_action.title if pending_action else "workspace action"
                    act_risk = pending_action.risk_level if pending_action else "medium"
                    content = (
                        f"This operation requires your confirmation or approval:\n\n"
                        f"- **Action:** {act_title}\n"
                        f"- **Risk Level:** {act_risk.upper()}\n\n"
                        f"You can review and approve this action to proceed."
                    )
                elif task.status == "completed":
                    content = task.result_summary or "Operation completed successfully."
                elif task.status == "failed":
                    content = f"The operation encountered an issue: {task.error_message}"
                else:
                    content = f"Task created with status: {task.status}"

                assistant_msg = await self.conversation_manager.add_message(
                    db=db,
                    conversation_id=conv.id,
                    user_id=user.id,
                    role="assistant",
                    content=content,
                    intent=intent_result.intent,
                    provider="work_intelligence",
                    model="safe_orchestrator",
                    status="completed",
                )
                response = AssistantResponse(
                    content=content,
                    provider="work_intelligence",
                    model="safe_orchestrator",
                    intent=intent_result.intent,
                )
                await self._auto_extract_memories(
                    db=db,
                    user_id=user.id,
                    prompt=request.message,
                    conversation_id=conv.id,
                )
                return conv, user_msg, assistant_msg, response
            except Exception as e:
                logger.warning(f"Work intelligence execution encountered error, continuing to inference: {e}")

        # 4. Retrieve persistent personal memories and assemble context
        retrieved_memories = await self._retrieve_memories(db=db, user_id=user.id, query=request.message)

        context = await self.context_manager.assemble_context(
            db=db,
            conversation_id=conv.id,
            user_query=request.message,
            intent=intent_result.intent,
            user_name=user.full_name or user.username,
            memories=retrieved_memories,
        )

        # 5. Route request to the appropriate model
        decision = await self.model_router.route(
            intent_result=intent_result,
            provider_override=request.provider,
            model_override=request.model,
            local_only=request.local_only,
        )

        provider = self.provider_manager.get_provider(decision.provider_id)
        if not provider:
            raise ProviderUnavailableError(
                provider=decision.provider_id,
                message=f"Provider '{decision.provider_id}' selected by router is not available."
            )

        temperature = request.temperature if request.temperature is not None else intent_result.suggested_temperature

        # 6. Invoke provider inference
        response = await provider.generate(
            messages=context,
            model=decision.model_id,
            temperature=temperature,
        )
        response.intent = intent_result.intent

        # 7. Persist assistant reply
        assistant_msg = await self.conversation_manager.add_message(
            db=db,
            conversation_id=conv.id,
            user_id=user.id,
            role="assistant",
            content=response.content,
            intent=intent_result.intent,
            provider=response.provider,
            model=response.model,
            status="completed",
            latency_ms=response.latency_ms,
            usage=response.usage,
        )

        # 8. Auto-extract potential durable memory facts if enabled
        await self._auto_extract_memories(
            db=db,
            user_id=user.id,
            prompt=request.message,
            conversation_id=conv.id,
        )

        return conv, user_msg, assistant_msg, response

    async def execute_chat_stream(
        self,
        db: AsyncSession,
        user: User,
        request: ChatRequest,
    ) -> Tuple[str, str, AsyncGenerator[StreamChunk, None]]:
        """
        Prepares a streaming conversation turn.
        Returns: (conversation_id, assistant_message_id, chunk_generator)
        """
        # 1. Classify intent
        intent_result = IntentClassifier.classify(request.message)

        # 2. Resolve or create conversation
        if request.conversation_id:
            conv = await self.conversation_manager.get_conversation(
                db=db,
                conversation_id=request.conversation_id,
                user_id=user.id,
            )
        else:
            title = self.conversation_manager.derive_title_from_prompt(request.message)
            conv = await self.conversation_manager.create_conversation(
                db=db,
                user_id=user.id,
                title=title,
            )

        # 3. Persist incoming user message
        await self.conversation_manager.add_message(
            db=db,
            conversation_id=conv.id,
            user_id=user.id,
            role="user",
            content=request.message,
            intent=intent_result.intent,
            status="completed",
        )

        # Check for ambiguity
        if intent_result.is_ambiguous and intent_result.clarification_prompt:
            clarification_content = intent_result.clarification_prompt
            assistant_msg = await self.conversation_manager.add_message(
                db=db,
                conversation_id=conv.id,
                user_id=user.id,
                role="assistant",
                content=clarification_content,
                intent=intent_result.intent,
                provider="system",
                model="intent_classifier",
                status="completed",
            )

            async def _clarification_gen():
                yield StreamChunk(
                    delta=clarification_content,
                    accumulated=clarification_content,
                    is_done=True,
                    finish_reason="stop",
                    provider="system",
                    model="intent_classifier",
                )

            return conv.id, assistant_msg.id, _clarification_gen()

        # Check for Work Intelligence tool action requirement
        if intent_result.requires_action and self.work_service:
            try:
                task = await self.work_service.create_task(
                    db=db,
                    user_id=user.id,
                    title=f"Task: {request.message[:60]}",
                    description=request.message,
                    conversation_id=conv.id,
                )
                task = await self.work_service.execute_task(
                    db=db,
                    task_id=task.id,
                    user_id=user.id,
                )

                if task.status == "awaiting_approval":
                    pending_action = next((a for a in task.actions if a.status == "awaiting_approval"), None)
                    act_title = pending_action.title if pending_action else "workspace action"
                    act_risk = pending_action.risk_level if pending_action else "medium"
                    content = (
                        f"This operation requires your confirmation or approval:\n\n"
                        f"- **Action:** {act_title}\n"
                        f"- **Risk Level:** {act_risk.upper()}\n\n"
                        f"You can review and approve this action to proceed."
                    )
                elif task.status == "completed":
                    content = task.result_summary or "Operation completed successfully."
                elif task.status == "failed":
                    content = f"The operation encountered an issue: {task.error_message}"
                else:
                    content = f"Task created with status: {task.status}"

                assistant_msg = await self.conversation_manager.add_message(
                    db=db,
                    conversation_id=conv.id,
                    user_id=user.id,
                    role="assistant",
                    content=content,
                    intent=intent_result.intent,
                    provider="work_intelligence",
                    model="safe_orchestrator",
                    status="completed",
                )
                await self._auto_extract_memories(
                    db=db,
                    user_id=user.id,
                    prompt=request.message,
                    conversation_id=conv.id,
                )

                async def _task_stream_gen():
                    yield StreamChunk(
                        delta=content,
                        accumulated=content,
                        is_done=True,
                        finish_reason="stop",
                        provider="work_intelligence",
                        model="safe_orchestrator",
                    )

                return conv.id, assistant_msg.id, _task_stream_gen()
            except Exception as e:
                logger.warning(f"Work intelligence stream encountered error, continuing stream inference: {e}")

        # 4. Retrieve persistent personal memories and assemble context
        retrieved_memories = await self._retrieve_memories(db=db, user_id=user.id, query=request.message)

        context = await self.context_manager.assemble_context(
            db=db,
            conversation_id=conv.id,
            user_query=request.message,
            intent=intent_result.intent,
            user_name=user.full_name or user.username,
            memories=retrieved_memories,
        )

        # 5. Route request
        decision = await self.model_router.route(
            intent_result=intent_result,
            provider_override=request.provider,
            model_override=request.model,
            local_only=request.local_only,
        )

        provider = self.provider_manager.get_provider(decision.provider_id)
        if not provider:
            raise ProviderUnavailableError(provider=decision.provider_id)

        # 6. Create initial placeholder message for the assistant
        assistant_msg = await self.conversation_manager.add_message(
            db=db,
            conversation_id=conv.id,
            user_id=user.id,
            role="assistant",
            content="",
            intent=intent_result.intent,
            provider=decision.provider_id,
            model=decision.model_id,
            status="streaming",
        )

        temperature = request.temperature if request.temperature is not None else intent_result.suggested_temperature

        # 7. Start stream from provider
        chunk_generator = provider.generate_stream(
            messages=context,
            model=decision.model_id,
            temperature=temperature,
        )

        # 8. Auto-extract potential durable memory facts if enabled
        await self._auto_extract_memories(
            db=db,
            user_id=user.id,
            prompt=request.message,
            conversation_id=conv.id,
        )

        return conv.id, assistant_msg.id, chunk_generator

    async def _retrieve_memories(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
    ) -> List[Any]:
        """Safely queries personal memory retrieval for relevant context."""
        if not self.memory_service:
            return []
        try:
            from backend.app.memory.schemas import MemorySearchRequest
            search_req = MemorySearchRequest(
                query=query,
                top_k=self.settings.MEMORY_RETRIEVAL_TOP_K,
                min_score=self.settings.MEMORY_RETRIEVAL_MIN_SCORE,
            )
            return await self.memory_service.search_memories(
                db=db,
                user_id=user_id,
                request=search_req,
            )
        except Exception as exc:
            logger.warning(f"Memory retrieval encountered non-fatal error: {exc}")
            return []

    async def _auto_extract_memories(
        self,
        db: AsyncSession,
        user_id: str,
        prompt: str,
        conversation_id: str,
    ) -> None:
        """
        Processes memory candidates extracted from user prompt.
        - Explicit directives ("Remember that...") are saved directly.
        - Independently identified facts are created as PENDING suggestions requiring explicit user consent.
        """
        if not (self.settings.MEMORY_AUTO_EXTRACT and self.memory_service):
            return
        try:
            from backend.app.memory.extraction import MemoryExtractionService
            from backend.app.memory.schemas import MemoryCreateRequest, SourceType
            candidates = MemoryExtractionService.extract_candidates(prompt)
            for cand in candidates:
                if not cand.needs_approval and cand.confidence >= 0.8:
                    # Explicit user directive: save directly to permanent memory
                    await self.memory_service.create_memory(
                        db=db,
                        user_id=user_id,
                        request=MemoryCreateRequest(
                            content=cand.content,
                            category=cand.category,
                            confidence=cand.confidence,
                            importance=cand.importance,
                            source_type=SourceType.EXPLICIT_USER,
                            source_id=conversation_id,
                            tags=["explicit_command"],
                        ),
                    )
                else:
                    # Independently identified fact: create a PENDING suggestion
                    # Requires explicit user consent; never silently persisted as permanent memory
                    await self.memory_service.create_suggestion(
                        db=db,
                        user_id=user_id,
                        candidate=cand,
                        source_id=conversation_id,
                    )
        except Exception as exc:
            logger.debug(f"Candidate memory auto-extraction completed with note: {exc}")
