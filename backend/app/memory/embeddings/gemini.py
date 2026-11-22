"""
Google Gemini Cloud Embedding Provider (Phase 04).
Subject to strict local-only privacy boundaries.
"""

from typing import Any, List, Optional
import httpx
import numpy as np

from backend.app.core.logging import get_logger
from backend.app.memory.embeddings.base import BaseEmbeddingProvider
from backend.app.memory.exceptions import EmbeddingUnavailableError, LocalOnlyViolationError

logger = get_logger("memory.embeddings.gemini")


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """
    Adapter for Google Gemini text-embedding-004 (768 dimensions).
    Strictly blocked if cloud embeddings are disabled or LOCAL_ONLY_MODE is active.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        model: str = "text-embedding-004",
        allow_cloud: Optional[bool] = None,
        local_only_mode: Optional[bool] = None,
        timeout_seconds: int = 30,
        settings: Optional[Any] = None,
    ):
        st = settings
        if st is None:
            try:
                from backend.app.config.settings import get_settings
                st = get_settings()
            except Exception:
                st = None

        self._api_key = (
            api_key if api_key is not None
            else (getattr(st, "GEMINI_API_KEY", "") if st else "")
        ).strip()
        self.base_url = base_url.rstrip("/")
        self.model = model.replace("models/", "")
        self.allow_cloud = (
            allow_cloud if allow_cloud is not None
            else (getattr(st, "MEMORY_ALLOW_CLOUD_EMBEDDINGS", False) if st else False)
        )
        self.local_only_mode = (
            local_only_mode if local_only_mode is not None
            else (getattr(st, "LOCAL_ONLY_MODE", False) if st else False)
        )
        self.timeout_seconds = timeout_seconds

    @property
    def provider_id(self) -> str:
        return "gemini"

    @property
    def dimension(self) -> int:
        return 768

    @property
    def is_local(self) -> bool:
        return False

    async def is_available(self) -> bool:
        """Available only when API key is set, cloud embeddings are permitted, and local-only mode is inactive."""
        if not self._api_key or not self.allow_cloud or self.local_only_mode:
            return False
        try:
            url = f"{self.base_url}/models/{self.model}:embedContent?key={self._api_key}"
            payload = {
                "model": f"models/{self.model}",
                "content": {"parts": [{"text": "health"}]}
            }
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.post(url, json=payload)
                return res.status_code == 200
        except Exception:
            return False

    async def embed_text(self, text: str) -> List[float]:
        """Generates a 768-dimensional normalized embedding using Gemini API."""
        if self.local_only_mode or not self.allow_cloud:
            raise LocalOnlyViolationError(
                "Cloud embeddings are disabled by privacy policy. Personal memories will not be transmitted to cloud services."
            )
        if not self._api_key:
            raise EmbeddingUnavailableError(provider=self.provider_id, message="Gemini API key is not configured.")

        url = f"{self.base_url}/models/{self.model}:embedContent?key={self._api_key}"
        payload = {
            "model": f"models/{self.model}",
            "content": {"parts": [{"text": text}]}
        }
        try:
            async with httpx.AsyncClient(timeout=float(self.timeout_seconds)) as client:
                res = await client.post(url, json=payload)
                if res.status_code != 200:
                    raise EmbeddingUnavailableError(
                        provider=self.provider_id,
                        message=f"Gemini embedding API error ({res.status_code}): {res.text}"
                    )
                vec = res.json().get("embedding", {}).get("values", [])
                if not vec:
                    raise EmbeddingUnavailableError(provider=self.provider_id, message="Empty embedding returned from Gemini")

                arr = np.array(vec, dtype=np.float32)
                norm = np.linalg.norm(arr)
                if norm > 0:
                    arr = arr / norm
                return arr.tolist()
        except httpx.HTTPError as exc:
            raise EmbeddingUnavailableError(
                provider=self.provider_id,
                message=f"Network error communicating with Gemini embedding API: {exc}"
            ) from exc
