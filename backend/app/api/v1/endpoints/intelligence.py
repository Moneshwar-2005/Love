"""
API Endpoints for Universal Intelligence Layer (Phase 03).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.authentication.dependencies import (
    get_current_active_user,
    get_current_device_id,
)
from backend.app.database.models.user import User
from backend.app.database.session import get_db
from backend.app.intelligence.engine import IntelligenceEngine, get_intelligence_engine
from backend.app.intelligence.response import ResponseHandler
from backend.app.intelligence.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationCreateRequest,
    ConversationDetailResponse,
    ConversationResponse,
    IntelligenceStatusResponse,
    ModelInfo,
    ProviderStatusResponse,
)

router = APIRouter(prefix="/intelligence", tags=["Universal Intelligence"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Chat with Assistant (Synchronous)",
    description="Sends a natural language prompt to LOVE. Dynamically routes to the best available model, executes inference, and records the conversation turn."
)
async def chat_endpoint(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    engine: IntelligenceEngine = Depends(get_intelligence_engine),
) -> ChatResponse:
    """Synchronous chat completion."""
    conv, user_msg, assistant_msg, response = await engine.orchestrator.execute_chat(
        db=db,
        user=current_user,
        request=request,
    )
    return ResponseHandler.format_chat_response(
        conversation_id=conv.id,
        message_id=assistant_msg.id,
        user_message=user_msg.content,
        response=response,
    )


@router.post(
    "/chat/stream",
    status_code=status.HTTP_200_OK,
    summary="Chat with Assistant (Streaming SSE)",
    description="Streams the assistant's response chunk-by-chunk using Server-Sent Events (SSE). Client receives delta tokens in real-time."
)
async def chat_stream_endpoint(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    engine: IntelligenceEngine = Depends(get_intelligence_engine),
):
    """Server-Sent Events streaming chat completion."""
    conv_id, assistant_msg_id, chunk_gen = await engine.orchestrator.execute_chat_stream(
        db=db,
        user=current_user,
        request=request,
    )

    sse_stream = engine.streaming_manager.stream_sse_generator(
        chunk_generator=chunk_gen,
        message_id=assistant_msg_id,
        conversation_id=conv_id,
        db=db,
    )

    return StreamingResponse(
        sse_stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get(
    "/conversations",
    response_model=List[ConversationResponse],
    summary="List Conversations",
    description="Retrieves a paginated list of conversations owned by the authenticated user."
)
async def list_conversations_endpoint(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    include_archived: bool = Query(default=False),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    engine: IntelligenceEngine = Depends(get_intelligence_engine),
) -> List[ConversationResponse]:
    """List conversation threads for the current user."""
    convs = await engine.conversation_manager.list_conversations(
        db=db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        include_archived=include_archived,
    )
    return [ConversationResponse.model_validate(c) for c in convs]


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Conversation",
    description="Explicitly initializes a new conversation thread."
)
async def create_conversation_endpoint(
    request: ConversationCreateRequest,
    current_user: User = Depends(get_current_active_user),
    device_id: Optional[str] = Depends(get_current_device_id),
    db: AsyncSession = Depends(get_db),
    engine: IntelligenceEngine = Depends(get_intelligence_engine),
) -> ConversationResponse:
    """Create a new conversation thread."""
    conv = await engine.conversation_manager.create_conversation(
        db=db,
        user_id=current_user.id,
        title=request.title,
        origin_device_id=device_id,
    )
    return ConversationResponse.model_validate(conv)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get Conversation Detail",
    description="Retrieves the full conversation metadata and all historical message turns."
)
async def get_conversation_endpoint(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    engine: IntelligenceEngine = Depends(get_intelligence_engine),
) -> ConversationDetailResponse:
    """Get conversation with full message history."""
    conv = await engine.conversation_manager.get_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
        include_messages=True,
    )
    return ConversationDetailResponse.model_validate(conv)


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Conversation",
    description="Deletes a conversation and all its associated messages."
)
async def delete_conversation_endpoint(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    device_id: Optional[str] = Depends(get_current_device_id),
    db: AsyncSession = Depends(get_db),
    engine: IntelligenceEngine = Depends(get_intelligence_engine),
):
    """Delete a conversation thread."""
    await engine.conversation_manager.delete_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
        origin_device_id=device_id,
    )
    return {"message": f"Conversation '{conversation_id}' deleted successfully."}


@router.get(
    "/providers",
    response_model=List[ProviderStatusResponse],
    summary="List Providers",
    description="Returns configuration and live health status for all registered AI providers."
)
async def list_providers_endpoint(
    current_user: User = Depends(get_current_active_user),
    engine: IntelligenceEngine = Depends(get_intelligence_engine),
) -> List[ProviderStatusResponse]:
    """List provider statuses."""
    return await engine.provider_manager.list_providers_status()


@router.get(
    "/models",
    response_model=List[ModelInfo],
    summary="List Models",
    description="Returns all registered models and their capability ratings."
)
async def list_models_endpoint(
    provider: Optional[str] = Query(default=None),
    local_only: bool = Query(default=False),
    current_user: User = Depends(get_current_active_user),
    engine: IntelligenceEngine = Depends(get_intelligence_engine),
) -> List[ModelInfo]:
    """List registered models."""
    return engine.registry.list_models(provider=provider, local_only=local_only)


@router.get(
    "/status",
    response_model=IntelligenceStatusResponse,
    summary="Intelligence Layer Status",
    description="Returns global intelligence subsystem status, routing settings, and hardware profile."
)
async def intelligence_status_endpoint(
    current_user: User = Depends(get_current_active_user),
    engine: IntelligenceEngine = Depends(get_intelligence_engine),
) -> IntelligenceStatusResponse:
    """Get system intelligence status."""
    return await engine.get_system_status()
