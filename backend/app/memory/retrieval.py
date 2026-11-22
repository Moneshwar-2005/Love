"""
Hybrid Memory Retrieval Engine for Persistent Personal Memory (Phase 04).
Combines dense semantic vector similarity with token-based lexical search and recency decay.
"""

from datetime import datetime, timezone
import json
import re
from typing import Dict, List, Optional, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import get_logger
from backend.app.database.models.memory import Memory
from backend.app.memory.embeddings.manager import EmbeddingManager
from backend.app.memory.schemas import (
    MemoryCategory,
    MemoryResponse,
    MemorySearchRequest,
    MemorySearchResult,
)
from backend.app.memory.vector_store.base import BaseVectorStore

logger = get_logger("memory.retrieval")


class MemoryRetrievalEngine:
    """
    Executes multi-strategy hybrid retrieval:
    - Semantic similarity via vector embeddings
    - Lexical matching via token overlap and tag filtering
    - Recency decay and importance weighting
    """

    def __init__(
        self,
        vector_store: BaseVectorStore,
        embedding_manager: EmbeddingManager,
    ):
        self.vector_store = vector_store
        self.embedding_manager = embedding_manager

    @staticmethod
    def _compute_lexical_score(query_tokens: Set[str], content: str, tags: List[str]) -> float:
        """Computes normalized keyword/token overlap score in [0.0, 1.0]."""
        if not query_tokens:
            return 0.0

        content_tokens = set(re.findall(r"\w+", content.lower()))
        tag_tokens = set(t.lower() for t in tags)

        all_text_tokens = content_tokens.union(tag_tokens)
        matched_tokens = query_tokens.intersection(all_text_tokens)

        if not matched_tokens:
            return 0.0

        # Jaccard / overlap fraction
        overlap_ratio = len(matched_tokens) / len(query_tokens)

        # Bonus for exact phrase match
        bonus = 0.2 if " ".join(query_tokens) in content.lower() else 0.0
        return min(1.0, overlap_ratio + bonus)

    async def search(
        self,
        db: AsyncSession,
        user_id: str,
        request: MemorySearchRequest,
    ) -> List[MemorySearchResult]:
        """
        Executes hybrid retrieval combining semantic vectors and canonical database records.
        Strictly partitions by user_id to enforce owner isolation.
        """
        query_text = request.query.strip()
        query_tokens = set(re.findall(r"\w+", query_text.lower()))

        # 1. Semantic Vector Search
        semantic_scores: Dict[str, float] = {}
        try:
            query_vector = await self.embedding_manager.embed_text(query_text)
            vector_results = await self.vector_store.search(
                query_vector=query_vector,
                user_id=user_id,
                top_k=request.top_k * 3,
                min_score=request.min_score * 0.7,
                filter_category=request.category.value if request.category else None,
            )
            for v_id, score in vector_results:
                semantic_scores[v_id] = max(0.0, min(1.0, score))
        except Exception as exc:
            logger.debug(f"Semantic search skipped or unavailable ({exc}); relying on lexical retrieval.")

        # 2. Fetch Candidate Memories from SQLite
        stmt = select(Memory).where(Memory.user_id == user_id)
        if not request.include_archived:
            stmt = stmt.where(Memory.is_archived == False)
        if request.category:
            stmt = stmt.where(Memory.category == request.category.value)

        db_result = await db.execute(stmt)
        candidates = list(db_result.scalars().all())

        now = datetime.now(timezone.utc)
        has_semantic = bool(semantic_scores)

        # 3. Hybrid Ranking
        results: List[MemorySearchResult] = []
        for mem in candidates:
            # Parse tags
            try:
                tags = json.loads(mem.tags_json) if mem.tags_json else []
            except Exception:
                tags = []

            # Tag filter check
            if request.tags:
                req_tags = set(t.lower() for t in request.tags)
                mem_tags = set(t.lower() for t in tags)
                if not req_tags.intersection(mem_tags):
                    continue

            # Compute individual score components
            s_semantic = semantic_scores.get(mem.id, 0.0)
            s_lexical = self._compute_lexical_score(query_tokens, mem.content, tags)

            # Importance factor: map 1..5 to 0.2..1.0
            s_importance = mem.importance / 5.0

            # Recency factor: linear decay over 30 days
            created_at = mem.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            age_days = (now - created_at).total_seconds() / 86400.0
            s_recency = max(0.0, 1.0 - (age_days / 30.0))

            # Dynamic weighting depending on semantic availability
            if has_semantic:
                hybrid_score = (
                    0.55 * s_semantic +
                    0.25 * s_lexical +
                    0.15 * s_importance +
                    0.05 * s_recency
                )
            else:
                hybrid_score = (
                    0.75 * s_lexical +
                    0.20 * s_importance +
                    0.05 * s_recency
                )

            if hybrid_score >= request.min_score:
                # Convert DB model to DTO
                metadata = {}
                try:
                    if mem.metadata_json:
                        metadata = json.loads(mem.metadata_json)
                except Exception:
                    pass

                mem_dto = MemoryResponse(
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
                results.append(
                    MemorySearchResult(
                        memory=mem_dto,
                        score=round(hybrid_score, 3),
                        semantic_score=round(s_semantic, 3),
                        lexical_score=round(s_lexical, 3),
                    )
                )

        # Sort descending by hybrid score
        results.sort(key=lambda r: r.score, reverse=True)
        top_results = results[:request.top_k]

        # Update access timestamps on retrieved memories in database
        if top_results:
            retrieved_ids = [r.memory.id for r in top_results]
            for mem in candidates:
                if mem.id in retrieved_ids:
                    mem.access_count += 1
                    mem.last_accessed_at = now
            await db.commit()

        return top_results
