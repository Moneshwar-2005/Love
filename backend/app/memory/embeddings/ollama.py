"""
Local Ollama Embedding Provider (Phase 04).
"""

from typing import List
import httpx
import numpy as np

from backend.app.core.logging import get_logger
from backend.app.memory.embeddings.base import BaseEmbeddingProvider
from backend.app.memory.exceptions import EmbeddingUnavailableError

logger = get_logger("memory.embeddings.ollama")


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """
    Adapter for local embedding generation using Ollama.
    Communicates over async HTTP with zero cloud telemetry.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "qwen2.5:1.5b",
        dimension: int = 1536,
        timeout_seconds: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._dimension = dimension
        self.timeout_seconds = timeout_seconds

    @property
    def provider_id(self) -> str:
        return "ollama"

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def is_local(self) -> bool:
        return True

    async def is_available(self) -> bool:
        """Checks if Ollama daemon is reachable and supports embeddings for configured model."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": "health"},
                )
                if res.status_code == 200:
                    emb = res.json().get("embedding", [])
                    if emb:
                        self._dimension = len(emb)
                        return True
                return False
        except Exception:
            return False

    async def embed_text(self, text: str) -> List[float]:
        """Generates a normalized embedding vector for the supplied text."""
        payload = {
            "model": self.model,
            "prompt": text,
        }
        try:
            async with httpx.AsyncClient(timeout=float(self.timeout_seconds)) as client:
                res = await client.post(f"{self.base_url}/api/embeddings", json=payload)
                if res.status_code != 200:
                    raise EmbeddingUnavailableError(
                        provider=self.provider_id,
                        message=f"Ollama embedding request failed ({res.status_code}): {res.text}"
                    )
                vec = res.json().get("embedding", [])
                if not vec:
                    raise EmbeddingUnavailableError(provider=self.provider_id, message="Empty embedding returned")

                self._dimension = len(vec)
                arr = np.array(vec, dtype=np.float32)
                norm = np.linalg.norm(arr)
                if norm > 0:
                    arr = arr / norm
                return arr.tolist()
        except httpx.HTTPError as exc:
            raise EmbeddingUnavailableError(
                provider=self.provider_id,
                message=f"Network error communicating with Ollama embedding endpoint: {exc}"
            ) from exc
