"""
Memory API Endpoints for Persistent Personal Memory and Vector Retrieval (Phase 04).
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.authentication.dependencies import get_current_active_user
from backend.app.database.models.user import User
from backend.app.database.session import get_db
from backend.app.memory.exceptions import (
    DuplicateMemoryError,
    MemoryNotFoundError,
    SensitiveDataBlockedError,
)
from backend.app.memory.schemas import (
    MemoryCategory,
    MemoryCreateRequest,
    MemoryResponse,
    MemorySearchRequest,
    MemorySearchResult,
    MemoryStatsResponse,
    MemorySuggestionResponse,
    MemoryUpdateRequest,
    SuggestionStatus,
)
from backend.app.memory.service import MemoryService, get_memory_service

router = APIRouter(prefix="/memory", tags=["Personal Memory"])


@router.post(
    "",
    response_model=MemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Memory",
    description="Stores a new canonical memory, indexes its vector embedding, and enforces privacy sanitization and deduplication."
)
async def create_memory_endpoint(
    request: MemoryCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Create a new memory record."""
    try:
        return await memory_service.create_memory(
            db=db,
            user_id=current_user.id,
            request=request,
        )
    except SensitiveDataBlockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except DuplicateMemoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


@router.get(
    "",
    response_model=List[MemoryResponse],
    summary="List Memories",
    description="Retrieves memories belonging to the authenticated user with optional category, tag, and archived status filters."
)
async def list_memories_endpoint(
    category: Optional[MemoryCategory] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    is_archived: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    memory_service: MemoryService = Depends(get_memory_service),
) -> List[MemoryResponse]:
    """List user memories with pagination and filters."""
    return await memory_service.list_memories(
        db=db,
        user_id=current_user.id,
        category=category,
        tag=tag,
        is_archived=is_archived,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/search",
    response_model=List[MemorySearchResult],
    summary="Hybrid Semantic & Lexical Search",
    description="Executes hybrid retrieval combining dense semantic similarity, token lexical overlap, importance weights, and recency decay."
)
async def search_memories_endpoint(
    request: MemorySearchRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    memory_service: MemoryService = Depends(get_memory_service),
) -> List[MemorySearchResult]:
    """Search user memories semantically and lexically."""
    return await memory_service.search_memories(
        db=db,
        user_id=current_user.id,
        request=request,
    )


@router.get(
    "/stats",
    response_model=MemoryStatsResponse,
    summary="Get Memory System Stats",
    description="Returns aggregate counts, category distributions, vector index health, and active embedding provider status."
)
async def get_memory_stats_endpoint(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryStatsResponse:
    """Collect memory system statistics."""
    return await memory_service.get_stats(
        db=db,
        user_id=current_user.id,
    )


@router.post(
    "/rebuild-index",
    summary="Rebuild Vector Index",
    description="Reconstructs user vector indices from canonical SQLite records."
)
async def rebuild_index_endpoint(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    memory_service: MemoryService = Depends(get_memory_service),
) -> Dict[str, Any]:
    """Rebuild user's vector embeddings."""
    count = await memory_service.rebuild_vector_index(
        db=db,
        user_id=current_user.id,
    )
    return {
        "status": "success",
        "rebuilt_count": count,
        "message": f"Successfully rebuilt {count} vector records."
    }


@router.get(
    "/export",
    response_model=List[MemoryResponse],
    summary="Export Memories",
    description="Exports all memories owned by the user for backup or migration."
)
async def export_memories_endpoint(
    include_archived: bool = Query(default=True),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    memory_service: MemoryService = Depends(get_memory_service),
) -> List[MemoryResponse]:
    """Export memories."""
    return await memory_service.export_memories(
        db=db,
        user_id=current_user.id,
        include_archived=include_archived,
    )


@router.post(
    "/import",
    summary="Import Memories",
    description="Imports a list of memory definitions into the user's personal memory store."
)
async def import_memories_endpoint(
    items: List[MemoryCreateRequest],
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    memory_service: MemoryService = Depends(get_memory_service),
) -> Dict[str, Any]:
    """Import memories."""
    count = await memory_service.import_memories(
        db=db,
        user_id=current_user.id,
        items=items,
    )
    return {
        "status": "success",
        "imported_count": count,
        "total_submitted": len(items),
    }


@router.delete(
    "/clear",
    summary="Clear Memories",
    description="Deletes memories for the authenticated user, optionally scoped to a single category. Requires explicit confirm=true."
)
async def clear_memories_endpoint(
    confirm: bool = Query(default=False, description="Explicit confirmation required to clear memories"),
    category: Optional[MemoryCategory] = Query(default=None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    memory_service: MemoryService = Depends(get_memory_service),
) -> Dict[str, Any]:
    """Clear user memories."""
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operation rejected. Pass ?confirm=true to confirm memory deletion."
        )

    cleared = await memory_service.clear_memories(
        db=db,
        user_id=current_user.id,
        category=category,
    )
    return {
        "status": "success",
        "cleared_count": cleared,
        "category": category.value if category else "all",
    }


# =============================================================================
# Memory Suggestion & Consent Endpoints (Phase 04.5)
# =============================================================================

@router.get(
    "/suggestions",
    response_model=List[MemorySuggestionResponse],
    summary="List Memory Suggestions",
    description="Lists pending or historical memory suggestions extracted from conversation turns."
)
async def list_suggestions_endpoint(
    status_filter: Optional[SuggestionStatus] = Query(default=SuggestionStatus.PENDING, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    memory_service: MemoryService = Depends(get_memory_service),
) -> List[MemorySuggestionResponse]:
    """List memory suggestions requiring user review or consent."""
    return await memory_service.list_suggestions(
        db=db,
        user_id=current_user.id,
        status=status_filter.value if status_filter else None,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/suggestions/{suggestion_id}",
    response_model=MemorySuggestionResponse,
    summary="Get Memory Suggestion",
    description="Retrieves a specific memory suggestion by ID, verifying user ownership."
)
async def get_suggestion_endpoint(
    suggestion_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemorySuggestionResponse:
    """Retrieve an individual memory suggestion."""
    try:
        return await memory_service.get_suggestion(
            db=db,
            suggestion_id=suggestion_id,
            user_id=current_user.id,
        )
    except MemoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.post(
    "/suggestions/{suggestion_id}/approve",
    response_model=MemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Approve Memory Suggestion",
    description="User grants explicit consent: promotes suggestion to permanent canonical memory and indexes vector."
)
async def approve_suggestion_endpoint(
    suggestion_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Approve a pending memory suggestion."""
    try:
        return await memory_service.approve_suggestion(
            db=db,
            suggestion_id=suggestion_id,
            user_id=current_user.id,
        )
    except MemoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except SensitiveDataBlockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/suggestions/{suggestion_id}/reject",
    response_model=MemorySuggestionResponse,
    summary="Reject Memory Suggestion",
    description="User rejects suggestion: marks as rejected so it is never saved to permanent memory or indexed."
)
async def reject_suggestion_endpoint(
    suggestion_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemorySuggestionResponse:
    """Reject a memory suggestion."""
    try:
        return await memory_service.reject_suggestion(
            db=db,
            suggestion_id=suggestion_id,
            user_id=current_user.id,
        )
    except MemoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.delete(
    "/suggestions/{suggestion_id}",
    summary="Delete Memory Suggestion",
    description="Permanently deletes a suggestion record."
)
async def delete_suggestion_endpoint(
    suggestion_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    memory_service: MemoryService = Depends(get_memory_service),
) -> Dict[str, Any]:
    """Delete a memory suggestion."""
    try:
        await memory_service.delete_suggestion(
            db=db,
            suggestion_id=suggestion_id,
            user_id=current_user.id,
        )
        return {
            "status": "deleted",
            "id": suggestion_id,
        }
    except MemoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="Get Memory",
    description="Retrieves a specific memory item by ID, verifying user ownership."
)
async def get_memory_endpoint(
    memory_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Retrieve individual memory."""
    try:
        return await memory_service.get_memory(
            db=db,
            memory_id=memory_id,
            user_id=current_user.id,
        )
    except MemoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.put(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="Update Memory",
    description="Updates content, tags, or metadata for a memory record and reindexes its vector."
)
async def update_memory_endpoint(
    memory_id: str,
    request: MemoryUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Update existing memory."""
    try:
        return await memory_service.update_memory(
            db=db,
            memory_id=memory_id,
            user_id=current_user.id,
            request=request,
        )
    except MemoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except SensitiveDataBlockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.delete(
    "/{memory_id}",
    summary="Delete Memory",
    description="Permanently deletes a memory record and removes it from the vector index."
)
async def delete_memory_endpoint(
    memory_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    memory_service: MemoryService = Depends(get_memory_service),
) -> Dict[str, Any]:
    """Delete memory."""
    try:
        await memory_service.delete_memory(
            db=db,
            memory_id=memory_id,
            user_id=current_user.id,
        )
        return {
            "status": "deleted",
            "id": memory_id,
        }
    except MemoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.post(
    "/{memory_id}/archive",
    response_model=MemoryResponse,
    summary="Archive Memory",
    description="Marks a memory as archived so it is excluded from standard retrieval while preserving history."
)
async def archive_memory_endpoint(
    memory_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Archive memory."""
    try:
        return await memory_service.set_archived_status(
            db=db,
            memory_id=memory_id,
            user_id=current_user.id,
            is_archived=True,
        )
    except MemoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.post(
    "/{memory_id}/restore",
    response_model=MemoryResponse,
    summary="Restore Memory",
    description="Restores an archived memory back into active retrieval."
)
async def restore_memory_endpoint(
    memory_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Restore memory."""
    try:
        return await memory_service.set_archived_status(
            db=db,
            memory_id=memory_id,
            user_id=current_user.id,
            is_archived=False,
        )
    except MemoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
