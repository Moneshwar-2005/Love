"""
Local Persistent Vector Store (Phase 04).
Employs vectorized NumPy cosine similarity with local file persistence.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from backend.app.core.logging import get_logger
from backend.app.memory.vector_store.base import BaseVectorStore

logger = get_logger("memory.vector_store.local")


class LocalVectorStore(BaseVectorStore):
    """
    High-performance on-device vector store with zero external server dependencies.
    Partitions indices strictly by user_id and persists to local JSON snapshots.
    """

    def __init__(self, storage_dir: str = "database/vectors"):
        self.storage_dir = Path(storage_dir).resolve()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        # In-memory index structure: { user_id: { vector_id: (np.ndarray, metadata) } }
        self._indices: Dict[str, Dict[str, Tuple[np.ndarray, Dict[str, Any]]]] = {}
        self._load_all_indices()

    def _get_user_file(self, user_id: str) -> Path:
        return self.storage_dir / f"{user_id}.json"

    def _load_all_indices(self) -> None:
        """Loads persistent vector files from disk into memory."""
        try:
            for file_path in self.storage_dir.glob("*.json"):
                user_id = file_path.stem
                self._load_user_index(user_id)
        except Exception as exc:
            logger.error(f"Error loading vector store indices: {exc}")

    def _load_user_index(self, user_id: str) -> None:
        file_path = self._get_user_file(user_id)
        if not file_path.exists():
            self._indices[user_id] = {}
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            user_idx = {}
            for v_id, item in data.items():
                vec = np.array(item["vector"], dtype=np.float32)
                user_idx[v_id] = (vec, item.get("metadata", {}))
            self._indices[user_id] = user_idx
        except Exception as exc:
            logger.error(f"Failed to load vector index for user {user_id}: {exc}")
            self._indices[user_id] = {}

    def _save_user_index(self, user_id: str) -> None:
        """Saves a user's index to disk snapshot."""
        file_path = self._get_user_file(user_id)
        user_idx = self._indices.get(user_id, {})
        data = {}
        for v_id, (vec, meta) in user_idx.items():
            data[v_id] = {
                "vector": vec.tolist(),
                "metadata": meta,
            }
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as exc:
            logger.error(f"Failed to persist vector index for user {user_id}: {exc}")

    async def upsert(
        self,
        vector_id: str,
        vector: List[float],
        metadata: Dict[str, Any],
        user_id: str
    ) -> None:
        """Inserts or updates an embedding vector for a user."""
        if user_id not in self._indices:
            self._indices[user_id] = {}

        arr = np.array(vector, dtype=np.float32)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm

        self._indices[user_id][vector_id] = (arr, metadata)
        self._save_user_index(user_id)

    async def search(
        self,
        query_vector: List[float],
        user_id: str,
        top_k: int = 5,
        min_score: float = 0.0,
        filter_category: Optional[str] = None
    ) -> List[Tuple[str, float]]:
        """
        Executes vectorized cosine similarity search across the user's vectors.
        """
        user_idx = self._indices.get(user_id, {})
        if not user_idx:
            return []

        q_arr = np.array(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q_arr)
        if q_norm > 0:
            q_arr = q_arr / q_norm

        candidate_ids = []
        candidate_vecs = []

        for v_id, (vec, meta) in user_idx.items():
            if filter_category and meta.get("category") != filter_category:
                continue
            if len(vec) != len(q_arr):
                # Dimension mismatch (e.g. embedding model was switched), skip gracefully
                continue
            candidate_ids.append(v_id)
            candidate_vecs.append(vec)

        if not candidate_vecs:
            return []

        # Vectorized dot product (cosine similarity since vectors are L2-normalized)
        matrix = np.stack(candidate_vecs)  # shape: (N, D)
        similarities = np.dot(matrix, q_arr)  # shape: (N,)

        results: List[Tuple[str, float]] = []
        for i, score in enumerate(similarities):
            float_score = float(score)
            if float_score >= min_score:
                results.append((candidate_ids[i], float_score))

        # Sort descending by score
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    async def delete(self, vector_id: str, user_id: str) -> bool:
        """Deletes a vector from memory and persists changes."""
        user_idx = self._indices.get(user_id, {})
        if vector_id in user_idx:
            del user_idx[vector_id]
            self._save_user_index(user_id)
            return True
        return False

    async def clear(self, user_id: Optional[str] = None) -> None:
        """Clears vectors for a specific user, or all users."""
        if user_id:
            self._indices[user_id] = {}
            self._save_user_index(user_id)
        else:
            self._indices = {}
            for f in self.storage_dir.glob("*.json"):
                f.unlink(missing_ok=True)

    def count(self, user_id: Optional[str] = None) -> int:
        """Returns the number of indexed vectors."""
        if user_id:
            return len(self._indices.get(user_id, {}))
        return sum(len(idx) for idx in self._indices.values())

    async def rebuild(self, records: List[Tuple[str, List[float], Dict[str, Any], str]]) -> None:
        """Rebuilds the index from canonical records."""
        affected_users = set()
        for v_id, vector, metadata, u_id in records:
            if u_id not in self._indices:
                self._indices[u_id] = {}
            arr = np.array(vector, dtype=np.float32)
            norm = np.linalg.norm(arr)
            if norm > 0:
                arr = arr / norm
            self._indices[u_id][v_id] = (arr, metadata)
            affected_users.add(u_id)

        for u_id in affected_users:
            self._save_user_index(u_id)
