"""
Abstract Base Vector Store Interface (Phase 04).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class BaseVectorStore(ABC):
    """
    Standard interface for vector indexing and approximate nearest-neighbor search.
    Completely decoupled from canonical SQLite memory storage.
    """

    @abstractmethod
    async def upsert(
        self,
        vector_id: str,
        vector: List[float],
        metadata: Dict[str, Any],
        user_id: str
    ) -> None:
        """Inserts or updates an embedding vector with associated metadata."""
        pass

    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        user_id: str,
        top_k: int = 5,
        min_score: float = 0.0,
        filter_category: Optional[str] = None
    ) -> List[Tuple[str, float]]:
        """
        Executes cosine similarity search for a specific user.
        Returns a list of tuples: (vector_id, similarity_score).
        """
        pass

    @abstractmethod
    async def delete(self, vector_id: str, user_id: str) -> bool:
        """Deletes a vector entry by ID for the specified user."""
        pass

    @abstractmethod
    async def clear(self, user_id: Optional[str] = None) -> None:
        """Clears all vector entries for a user, or all users if None."""
        pass

    @abstractmethod
    def count(self, user_id: Optional[str] = None) -> int:
        """Returns the total number of indexed vectors."""
        pass

    @abstractmethod
    async def rebuild(self, records: List[Tuple[str, List[float], Dict[str, Any], str]]) -> None:
        """Bulk re-indexes vectors from canonical SQLite memory records."""
        pass
