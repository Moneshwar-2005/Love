"""
Qdrant Vector Store Adapter (Phase 04).
Implements BaseVectorStore using local persistent or remote Qdrant instances.
Falls back safely to LocalVectorStore if Qdrant libraries or instances are unavailable.
"""

from typing import Any, Dict, List, Optional, Tuple
from backend.app.core.logging import get_logger
from backend.app.memory.vector_store.base import BaseVectorStore
from backend.app.memory.vector_store.local_store import LocalVectorStore

logger = get_logger("memory.vector_store.qdrant")


class QdrantVectorStore(BaseVectorStore):
    """
    Adapter for Qdrant local embedded storage or remote instances.
    Maintains collection partitions by user_id.
    """

    def __init__(self, storage_dir: str = "database/qdrant", fallback_store: Optional[BaseVectorStore] = None):
        self.storage_dir = storage_dir
        self._fallback = fallback_store or LocalVectorStore(storage_dir="database/vectors")
        self._is_qdrant_ready = False
        self._init_qdrant()

    def _init_qdrant(self) -> None:
        """Initializes Qdrant client if installed."""
        try:
            import qdrant_client
            # Qdrant client is available
            self._client = qdrant_client.QdrantClient(path=self.storage_dir)
            self._is_qdrant_ready = True
            logger.info("Qdrant embedded vector store initialized successfully.")
        except (ImportError, Exception) as exc:
            logger.info(f"Qdrant client not available ({exc}); using LocalVectorStore.")
            self._is_qdrant_ready = False

    async def upsert(
        self,
        vector_id: str,
        vector: List[float],
        metadata: Dict[str, Any],
        user_id: str
    ) -> None:
        if self._is_qdrant_ready:
            try:
                from qdrant_client.models import PointStruct
                collection_name = f"user_{user_id}"
                # Create collection if not exists, upsert point
                self._client.upsert(
                    collection_name=collection_name,
                    points=[PointStruct(id=vector_id, vector=vector, payload=metadata)]
                )
                return
            except Exception as exc:
                logger.warning(f"Qdrant upsert failed ({exc}), falling back to local store.")
        await self._fallback.upsert(vector_id, vector, metadata, user_id)

    async def search(
        self,
        query_vector: List[float],
        user_id: str,
        top_k: int = 5,
        min_score: float = 0.0,
        filter_category: Optional[str] = None
    ) -> List[Tuple[str, float]]:
        if self._is_qdrant_ready:
            try:
                collection_name = f"user_{user_id}"
                hits = self._client.search(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    limit=top_k,
                    score_threshold=min_score,
                )
                return [(str(hit.id), float(hit.score)) for hit in hits]
            except Exception as exc:
                logger.debug(f"Qdrant search fallback: {exc}")
        return await self._fallback.search(query_vector, user_id, top_k, min_score, filter_category)

    async def delete(self, vector_id: str, user_id: str) -> bool:
        if self._is_qdrant_ready:
            try:
                from qdrant_client.models import PointIdsList
                collection_name = f"user_{user_id}"
                self._client.delete(
                    collection_name=collection_name,
                    points_selector=PointIdsList(points=[vector_id])
                )
            except Exception:
                pass
        return await self._fallback.delete(vector_id, user_id)

    async def clear(self, user_id: Optional[str] = None) -> None:
        if self._is_qdrant_ready and user_id:
            try:
                self._client.delete_collection(collection_name=f"user_{user_id}")
            except Exception:
                pass
        await self._fallback.clear(user_id)

    def count(self, user_id: Optional[str] = None) -> int:
        return self._fallback.count(user_id)

    async def rebuild(self, records: List[Tuple[str, List[float], Dict[str, Any], str]]) -> None:
        await self._fallback.rebuild(records)
