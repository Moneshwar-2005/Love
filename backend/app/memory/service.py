"""
Memory Service layer managing canonical storage, vector indexing, and privacy auditing (Phase 04).
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
from sqlalchemy import delete, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config.settings import Settings, get_settings
from backend.app.core.logging import get_logger
from backend.app.database.models.memory import Memory, MemoryAuditLog, MemorySuggestion
from backend.app.memory.embeddings.manager import EmbeddingManager
from backend.app.memory.exceptions import (
    MemoryNotFoundError,
    SensitiveDataBlockedError,
)
from backend.app.memory.retrieval import MemoryRetrievalEngine
from backend.app.memory.sanitizer import SensitiveDataSanitizer
from backend.app.memory.schemas import (
    MemoryCategory,
    MemoryCreateRequest,
    MemoryExtractionCandidate,
    MemoryResponse,
    MemorySearchRequest,
    MemorySearchResult,
    MemoryStatsResponse,
    MemorySuggestionResponse,
    MemoryUpdateRequest,
    SourceType,
    SuggestionStatus,
)
from backend.app.memory.vector_store.base import BaseVectorStore
from backend.app.memory.vector_store.local_store import LocalVectorStore
from backend.app.memory.vector_store.qdrant_store import QdrantVectorStore

logger = get_logger("memory.service")


class MemoryService:
    """
    Core memory management service handling canonical persistence,
    vector synchronization, audit logging, and owner isolation.
    """

    def __init__(
        self,
        vector_store: Optional[BaseVectorStore] = None,
        embedding_manager: Optional[EmbeddingManager] = None,
        settings: Optional[Settings] = None,
    ):
        self.settings = settings or get_settings()
        self.embedding_manager = embedding_manager or EmbeddingManager(settings=self.settings)

        if vector_store:
            self.vector_store = vector_store
        else:
            if self.settings.MEMORY_VECTOR_STORE_TYPE == "qdrant":
                self.vector_store = QdrantVectorStore(storage_dir=self.settings.MEMORY_VECTOR_STORAGE_PATH)
            else:
                self.vector_store = LocalVectorStore(storage_dir=self.settings.MEMORY_VECTOR_STORAGE_PATH)

        self.retrieval_engine = MemoryRetrievalEngine(
            vector_store=self.vector_store,
            embedding_manager=self.embedding_manager,
        )

    def _serialize_dto(self, mem: Memory) -> MemoryResponse:
        """Converts ORM Memory entity to validated Pydantic DTO."""
        tags = []
        metadata = {}
        try:
            if mem.tags_json:
                tags = json.loads(mem.tags_json)
        except Exception:
            pass
        try:
            if mem.metadata_json:
                metadata = json.loads(mem.metadata_json)
        except Exception:
            pass

        return MemoryResponse(
            id=mem.id,
            user_id=mem.user_id,
            category=MemoryCategory(mem.category),
            content=mem.content,
            summary=mem.summary,
            source_type=mem.source_type,
            source_id=mem.source_id,
            confidence=mem.confidence,
            importance=mem.importance,
            tags=tags,
            metadata=metadata,
            is_archived=mem.is_archived,
            access_count=mem.access_count,
            last_accessed_at=mem.last_accessed_at,
            created_at=mem.created_at,
            updated_at=mem.updated_at,
        )

    def _serialize_suggestion_dto(self, sug: MemorySuggestion) -> MemorySuggestionResponse:
        """Converts ORM MemorySuggestion entity to validated Pydantic DTO."""
        tags = []
        metadata = {}
        try:
            if sug.tags_json:
                tags = json.loads(sug.tags_json)
        except Exception:
            pass
        try:
            if sug.metadata_json:
                metadata = json.loads(sug.metadata_json)
        except Exception:
            pass

        return MemorySuggestionResponse(
            id=sug.id,
            user_id=sug.user_id,
            category=MemoryCategory(sug.category),
            content=sug.content,
            summary=sug.summary,
            reasoning=sug.reasoning,
            source_statement=sug.source_statement,
            source_id=sug.source_id,
            confidence=sug.confidence,
            importance=sug.importance,
            tags=tags,
            metadata=metadata,
            status=SuggestionStatus(sug.status),
            created_at=sug.created_at,
            updated_at=sug.updated_at,
        )

    async def _log_audit(
        self,
        db: AsyncSession,
        user_id: str,
        action: str,
        memory_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Creates an audit trail record for memory operations."""
        audit = MemoryAuditLog(
            user_id=user_id,
            memory_id=memory_id,
            action=action,
            details_json=json.dumps(details or {}, ensure_ascii=False),
        )
        db.add(audit)

    async def create_memory(
        self,
        db: AsyncSession,
        user_id: str,
        request: MemoryCreateRequest,
    ) -> MemoryResponse:
        """
        Creates a new personal memory record.
        Enforces sensitive data sanitization and deduplication.
        """
        # 1. Sensitive Data Guard
        is_sensitive, detected = SensitiveDataSanitizer.check_for_sensitive_data(request.content)
        if is_sensitive:
            raise SensitiveDataBlockedError(detected_category=detected or "Secret")

        # 2. Deduplication check
        search_req = MemorySearchRequest(
            query=request.content,
            category=request.category,
            top_k=1,
            min_score=self.settings.MEMORY_DEDUPLICATION_THRESHOLD,
        )
        existing = await self.retrieval_engine.search(db=db, user_id=user_id, request=search_req)
        if existing and existing[0].score >= self.settings.MEMORY_DEDUPLICATION_THRESHOLD:
            # Memory already exists with high similarity; update it rather than creating a duplicate
            existing_id = existing[0].memory.id
            logger.info(f"Deduplication triggered: updating existing memory {existing_id}")
            return await self.update_memory(
                db=db,
                memory_id=existing_id,
                user_id=user_id,
                request=MemoryUpdateRequest(
                    content=request.content,
                    summary=request.summary or existing[0].memory.summary,
                    confidence=max(request.confidence, existing[0].memory.confidence),
                    importance=max(request.importance, existing[0].memory.importance),
                    tags=list(set(request.tags + existing[0].memory.tags)),
                )
            )

        # 3. Create Canonical Record
        mem = Memory(
            user_id=user_id,
            category=request.category.value,
            content=request.content.strip(),
            summary=request.summary,
            source_type=request.source_type.value,
            source_id=request.source_id,
            confidence=request.confidence,
            importance=request.importance,
            tags_json=json.dumps(request.tags, ensure_ascii=False),
            metadata_json=json.dumps(request.metadata, ensure_ascii=False),
            is_archived=False,
        )
        db.add(mem)
        await db.commit()
        await db.refresh(mem)

        # 4. Generate and Index Embedding Vector
        try:
            vec = await self.embedding_manager.embed_text(mem.content)
            await self.vector_store.upsert(
                vector_id=mem.id,
                vector=vec,
                metadata={"category": mem.category, "user_id": user_id},
                user_id=user_id,
            )
        except Exception as exc:
            logger.warning(f"Vector indexing skipped for memory {mem.id}: {exc}")

        # 5. Audit Log
        await self._log_audit(
            db=db,
            user_id=user_id,
            action="created",
            memory_id=mem.id,
            details={"category": mem.category, "source_type": mem.source_type},
        )

        # 6. Record Synchronization Event
        try:
            from backend.app.sync.service import get_sync_service
            await get_sync_service().record_event(
                db=db,
                user_id=user_id,
                entity_type="memory",
                entity_id=mem.id,
                action="created",
                payload={
                    "id": mem.id,
                    "category": mem.category,
                    "content": mem.content,
                    "summary": mem.summary,
                    "confidence": mem.confidence,
                    "importance": mem.importance,
                    "tags": json.loads(mem.tags_json) if mem.tags_json else [],
                    "metadata": json.loads(mem.metadata_json) if mem.metadata_json else {},
                    "is_archived": mem.is_archived,
                    "created_at": mem.created_at.isoformat() if mem.created_at else None,
                }
            )
        except Exception as exc:
            logger.debug(f"Sync event recording skipped for memory creation: {exc}")

        await db.commit()

        return self._serialize_dto(mem)

    async def get_memory(
        self,
        db: AsyncSession,
        memory_id: str,
        user_id: str,
    ) -> MemoryResponse:
        """Retrieves a memory record strictly verifying user ownership."""
        stmt = select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id)
        res = await db.execute(stmt)
        mem = res.scalar_one_or_none()
        if not mem:
            raise MemoryNotFoundError(memory_id=memory_id)
        return self._serialize_dto(mem)

    async def list_memories(
        self,
        db: AsyncSession,
        user_id: str,
        category: Optional[MemoryCategory] = None,
        tag: Optional[str] = None,
        is_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[MemoryResponse]:
        """Lists user's memories with pagination and filtering."""
        stmt = (
            select(Memory)
            .where(Memory.user_id == user_id, Memory.is_archived == is_archived)
            .order_by(desc(Memory.importance), desc(Memory.updated_at))
            .limit(limit)
            .offset(offset)
        )
        if category:
            stmt = stmt.where(Memory.category == category.value)

        res = await db.execute(stmt)
        memories = list(res.scalars().all())

        results = [self._serialize_dto(m) for m in memories]
        if tag:
            results = [m for m in results if tag.lower() in [t.lower() for t in m.tags]]
        return results

    async def search_memories(
        self,
        db: AsyncSession,
        user_id: str,
        request: MemorySearchRequest,
    ) -> List[MemorySearchResult]:
        """
        Searches user memories using hybrid vector + lexical retrieval.
        Enforces user isolation and updates access statistics.
        """
        return await self.retrieval_engine.search(db=db, user_id=user_id, request=request)

    async def update_memory(
        self,
        db: AsyncSession,
        memory_id: str,
        user_id: str,
        request: MemoryUpdateRequest,
    ) -> MemoryResponse:
        """Modifies an existing memory record and updates its vector index."""
        stmt = select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id)
        res = await db.execute(stmt)
        mem = res.scalar_one_or_none()
        if not mem:
            raise MemoryNotFoundError(memory_id=memory_id)

        content_changed = False
        if request.content is not None:
            is_sensitive, detected = SensitiveDataSanitizer.check_for_sensitive_data(request.content)
            if is_sensitive:
                raise SensitiveDataBlockedError(detected_category=detected or "Secret")
            if request.content.strip() != mem.content:
                mem.content = request.content.strip()
                content_changed = True

        if request.category is not None:
            mem.category = request.category.value
        if request.summary is not None:
            mem.summary = request.summary
        if request.confidence is not None:
            mem.confidence = request.confidence
        if request.importance is not None:
            mem.importance = request.importance
        if request.tags is not None:
            mem.tags_json = json.dumps(request.tags, ensure_ascii=False)
        if request.metadata is not None:
            mem.metadata_json = json.dumps(request.metadata, ensure_ascii=False)

        mem.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(mem)

        # Update vector if content or category changed
        if content_changed:
            try:
                vec = await self.embedding_manager.embed_text(mem.content)
                await self.vector_store.upsert(
                    vector_id=mem.id,
                    vector=vec,
                    metadata={"category": mem.category, "user_id": user_id},
                    user_id=user_id,
                )
            except Exception as exc:
                logger.warning(f"Vector update failed for memory {mem.id}: {exc}")

        await self._log_audit(
            db=db,
            user_id=user_id,
            action="updated",
            memory_id=mem.id,
            details={"content_changed": content_changed},
        )

        # Record Synchronization Event
        try:
            from backend.app.sync.service import get_sync_service
            await get_sync_service().record_event(
                db=db,
                user_id=user_id,
                entity_type="memory",
                entity_id=mem.id,
                action="updated",
                payload={
                    "id": mem.id,
                    "category": mem.category,
                    "content": mem.content,
                    "summary": mem.summary,
                    "confidence": mem.confidence,
                    "importance": mem.importance,
                    "tags": json.loads(mem.tags_json) if mem.tags_json else [],
                    "metadata": json.loads(mem.metadata_json) if mem.metadata_json else {},
                    "is_archived": mem.is_archived,
                }
            )
        except Exception as exc:
            logger.debug(f"Sync event recording skipped for memory update: {exc}")

        await db.commit()

        return self._serialize_dto(mem)

    async def delete_memory(
        self,
        db: AsyncSession,
        memory_id: str,
        user_id: str,
    ) -> bool:
        """Permanently deletes a memory record and its vector representation."""
        stmt = select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id)
        res = await db.execute(stmt)
        mem = res.scalar_one_or_none()
        if not mem:
            raise MemoryNotFoundError(memory_id=memory_id)

        await db.delete(mem)
        # Delete from vector index
        await self.vector_store.delete(vector_id=memory_id, user_id=user_id)

        await self._log_audit(
            db=db,
            user_id=user_id,
            action="deleted",
            memory_id=memory_id,
        )

        # Record Synchronization Event
        try:
            from backend.app.sync.service import get_sync_service
            await get_sync_service().record_event(
                db=db,
                user_id=user_id,
                entity_type="memory",
                entity_id=memory_id,
                action="deleted",
                payload={"id": memory_id}
            )
        except Exception as exc:
            logger.debug(f"Sync event recording skipped for memory deletion: {exc}")

        await db.commit()
        return True

    async def set_archived_status(
        self,
        db: AsyncSession,
        memory_id: str,
        user_id: str,
        is_archived: bool,
    ) -> MemoryResponse:
        """Archives or restores a memory record."""
        stmt = select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id)
        res = await db.execute(stmt)
        mem = res.scalar_one_or_none()
        if not mem:
            raise MemoryNotFoundError(memory_id=memory_id)

        mem.is_archived = is_archived
        mem.updated_at = datetime.now(timezone.utc)
        action = "archived" if is_archived else "restored"

        await self._log_audit(db=db, user_id=user_id, action=action, memory_id=mem.id)
        await db.commit()
        await db.refresh(mem)
        return self._serialize_dto(mem)

    async def rebuild_vector_index(self, db: AsyncSession, user_id: str) -> int:
        """
        Rebuilds vector index from canonical SQLite records for the specified user.
        """
        # Clear existing vectors for user
        await self.vector_store.clear(user_id=user_id)

        stmt = select(Memory).where(Memory.user_id == user_id, Memory.is_archived == False)
        res = await db.execute(stmt)
        memories = list(res.scalars().all())

        records = []
        for mem in memories:
            try:
                vec = await self.embedding_manager.embed_text(mem.content)
                records.append((mem.id, vec, {"category": mem.category, "user_id": user_id}, user_id))
            except Exception as exc:
                logger.warning(f"Failed to embed memory {mem.id} during rebuild: {exc}")

        if records:
            await self.vector_store.rebuild(records)

        await self._log_audit(
            db=db,
            user_id=user_id,
            action="reindexed",
            details={"rebuilt_count": len(records)},
        )
        await db.commit()
        return len(records)

    async def get_stats(self, db: AsyncSession, user_id: str) -> MemoryStatsResponse:
        """Collects memory subsystem health, counts, and embedding configuration."""
        stmt_total = select(func.count(Memory.id)).where(Memory.user_id == user_id)
        stmt_active = select(func.count(Memory.id)).where(Memory.user_id == user_id, Memory.is_archived == False)
        stmt_archived = select(func.count(Memory.id)).where(Memory.user_id == user_id, Memory.is_archived == True)

        total = (await db.execute(stmt_total)).scalar_one() or 0
        active = (await db.execute(stmt_active)).scalar_one() or 0
        archived = (await db.execute(stmt_archived)).scalar_one() or 0

        # Categories breakdown
        stmt_cats = (
            select(Memory.category, func.count(Memory.id))
            .where(Memory.user_id == user_id, Memory.is_archived == False)
            .group_by(Memory.category)
        )
        cat_rows = (await db.execute(stmt_cats)).all()
        categories_breakdown = {row[0]: row[1] for row in cat_rows}

        active_provider = await self.embedding_manager.get_active_provider()
        indexed_count = self.vector_store.count(user_id=user_id)

        return MemoryStatsResponse(
            total_memories=total,
            active_memories=active,
            archived_memories=archived,
            categories_breakdown=categories_breakdown,
            vector_store_type=self.vector_store.__class__.__name__,
            vector_index_size=indexed_count,
            embedding_provider=active_provider.provider_id,
            embedding_dimension=active_provider.dimension,
            cloud_embeddings_permitted=self.settings.MEMORY_ALLOW_CLOUD_EMBEDDINGS and not self.settings.LOCAL_ONLY_MODE,
        )

    async def export_memories(
        self,
        db: AsyncSession,
        user_id: str,
        include_archived: bool = True,
    ) -> List[MemoryResponse]:
        """Exports all memories owned by the user for backup."""
        stmt = select(Memory).where(Memory.user_id == user_id)
        if not include_archived:
            stmt = stmt.where(Memory.is_archived == False)
        stmt = stmt.order_by(desc(Memory.created_at))
        res = await db.execute(stmt)
        memories = list(res.scalars().all())
        return [self._serialize_dto(m) for m in memories]

    async def import_memories(
        self,
        db: AsyncSession,
        user_id: str,
        items: List[MemoryCreateRequest],
    ) -> int:
        """Imports a list of memory definitions with deduplication and sanitization."""
        imported_count = 0
        for item in items:
            try:
                await self.create_memory(db=db, user_id=user_id, request=item)
                imported_count += 1
            except Exception as exc:
                logger.warning(f"Skipping imported memory item due to error: {exc}")
        return imported_count

    async def clear_memories(
        self,
        db: AsyncSession,
        user_id: str,
        category: Optional[MemoryCategory] = None,
    ) -> int:
        """
        Clears memories for the user, optionally scoped to a single category.
        Synchronizes both SQLite storage and vector index.
        """
        stmt = select(Memory).where(Memory.user_id == user_id)
        if category:
            stmt = stmt.where(Memory.category == category.value)

        res = await db.execute(stmt)
        memories = list(res.scalars().all())
        count = len(memories)

        if count == 0:
            return 0

        # Delete from DB
        del_stmt = delete(Memory).where(Memory.user_id == user_id)
        if category:
            del_stmt = del_stmt.where(Memory.category == category.value)
        await db.execute(del_stmt)

        # Update vector store
        if category:
            for m in memories:
                await self.vector_store.delete(vector_id=m.id, user_id=user_id)
        else:
            await self.vector_store.clear(user_id=user_id)

        await self._log_audit(
            db=db,
            user_id=user_id,
            action="cleared",
            details={"category": category.value if category else "all", "cleared_count": count},
        )
        await db.commit()
        return count

    # =========================================================================
    # Memory Suggestion & Consent Lifecycle (Phase 04.5)
    # =========================================================================

    async def create_suggestion(
        self,
        db: AsyncSession,
        user_id: str,
        candidate: MemoryExtractionCandidate,
        source_id: Optional[str] = None,
    ) -> MemorySuggestionResponse:
        """
        Creates a pending memory suggestion for an independently identified fact.
        Guarantees that unapproved information is NEVER persisted as permanent memory
        and NEVER indexed in vector storage without explicit user consent.
        """
        # Sensitive Data Guard
        is_sensitive, detected = SensitiveDataSanitizer.check_for_sensitive_data(candidate.content)
        if is_sensitive:
            raise SensitiveDataBlockedError(detected_category=detected or "Secret")

        # Avoid redundant duplicate suggestions
        stmt = (
            select(MemorySuggestion)
            .where(
                MemorySuggestion.user_id == user_id,
                MemorySuggestion.content == candidate.content.strip(),
                MemorySuggestion.status.in_(["pending", "approved"]),
            )
        )
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            return self._serialize_suggestion_dto(existing)

        sug = MemorySuggestion(
            user_id=user_id,
            category=candidate.category.value,
            content=candidate.content.strip(),
            summary=candidate.content.strip()[:60],
            reasoning=candidate.reasoning,
            source_statement=candidate.source_statement,
            source_id=source_id,
            confidence=candidate.confidence,
            importance=candidate.importance,
            tags_json=json.dumps(["suggestion", candidate.category.value], ensure_ascii=False),
            metadata_json=json.dumps({}, ensure_ascii=False),
            status="pending",
        )
        db.add(sug)
        await db.commit()
        await db.refresh(sug)

        await self._log_audit(
            db=db,
            user_id=user_id,
            action="suggestion_created",
            memory_id=sug.id,
            details={"category": sug.category, "confidence": sug.confidence},
        )
        await db.commit()
        return self._serialize_suggestion_dto(sug)

    async def list_suggestions(
        self,
        db: AsyncSession,
        user_id: str,
        status: Optional[str] = "pending",
        limit: int = 50,
        offset: int = 0,
    ) -> List[MemorySuggestionResponse]:
        """Lists suggestions belonging to the user with optional status filter."""
        stmt = (
            select(MemorySuggestion)
            .where(MemorySuggestion.user_id == user_id)
            .order_by(desc(MemorySuggestion.created_at))
            .limit(limit)
            .offset(offset)
        )
        if status:
            stmt = stmt.where(MemorySuggestion.status == status)

        res = await db.execute(stmt)
        suggestions = list(res.scalars().all())
        return [self._serialize_suggestion_dto(s) for s in suggestions]

    async def get_suggestion(
        self,
        db: AsyncSession,
        suggestion_id: str,
        user_id: str,
    ) -> MemorySuggestionResponse:
        """Retrieves a specific suggestion enforcing user ownership."""
        stmt = select(MemorySuggestion).where(
            MemorySuggestion.id == suggestion_id,
            MemorySuggestion.user_id == user_id,
        )
        res = await db.execute(stmt)
        sug = res.scalar_one_or_none()
        if not sug:
            raise MemoryNotFoundError(memory_id=suggestion_id)
        return self._serialize_suggestion_dto(sug)

    async def approve_suggestion(
        self,
        db: AsyncSession,
        suggestion_id: str,
        user_id: str,
    ) -> MemoryResponse:
        """
        User grants explicit consent: promotes pending suggestion to canonical permanent memory
        and indexes it into the vector store.
        """
        stmt = select(MemorySuggestion).where(
            MemorySuggestion.id == suggestion_id,
            MemorySuggestion.user_id == user_id,
        )
        res = await db.execute(stmt)
        sug = res.scalar_one_or_none()
        if not sug:
            raise MemoryNotFoundError(memory_id=suggestion_id)

        # Promote to canonical permanent memory
        create_req = MemoryCreateRequest(
            content=sug.content,
            category=MemoryCategory(sug.category),
            summary=sug.summary,
            source_type=SourceType.CONVERSATION_EXTRACTION,
            source_id=sug.source_id,
            confidence=sug.confidence,
            importance=sug.importance,
            tags=json.loads(sug.tags_json) if sug.tags_json else [],
            metadata=json.loads(sug.metadata_json) if sug.metadata_json else {},
        )
        mem_dto = await self.create_memory(db=db, user_id=user_id, request=create_req)

        # Mark suggestion as approved
        sug.status = "approved"
        sug.updated_at = datetime.now(timezone.utc)
        await self._log_audit(
            db=db,
            user_id=user_id,
            action="approved_suggestion",
            memory_id=mem_dto.id,
            details={"suggestion_id": suggestion_id},
        )
        await db.commit()
        return mem_dto

    async def reject_suggestion(
        self,
        db: AsyncSession,
        suggestion_id: str,
        user_id: str,
    ) -> MemorySuggestionResponse:
        """
        User rejects a suggestion.
        Guarantees that rejected suggestions NEVER appear in permanent memory
        and are NEVER indexed or retrieved in vector search.
        """
        stmt = select(MemorySuggestion).where(
            MemorySuggestion.id == suggestion_id,
            MemorySuggestion.user_id == user_id,
        )
        res = await db.execute(stmt)
        sug = res.scalar_one_or_none()
        if not sug:
            raise MemoryNotFoundError(memory_id=suggestion_id)

        sug.status = "rejected"
        sug.updated_at = datetime.now(timezone.utc)
        await self._log_audit(
            db=db,
            user_id=user_id,
            action="rejected_suggestion",
            memory_id=suggestion_id,
        )
        await db.commit()
        await db.refresh(sug)
        return self._serialize_suggestion_dto(sug)

    async def delete_suggestion(
        self,
        db: AsyncSession,
        suggestion_id: str,
        user_id: str,
    ) -> bool:
        """Permanently deletes a suggestion record."""
        stmt = select(MemorySuggestion).where(
            MemorySuggestion.id == suggestion_id,
            MemorySuggestion.user_id == user_id,
        )
        res = await db.execute(stmt)
        sug = res.scalar_one_or_none()
        if not sug:
            raise MemoryNotFoundError(memory_id=suggestion_id)

        await db.delete(sug)
        await db.commit()
        return True


# Singleton Memory Service Instance
_memory_service_instance: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    """Dependency provider returning singleton MemoryService instance."""
    global _memory_service_instance
    if _memory_service_instance is None:
        _memory_service_instance = MemoryService()
    return _memory_service_instance
