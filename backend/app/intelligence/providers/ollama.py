"""
Ollama Local Runtime Provider Adapter (Phase 03).
"""

import json
import time
from typing import AsyncGenerator, List, Optional
import httpx

from backend.app.core.logging import get_logger
from backend.app.intelligence.exceptions import (
    ModelNotFoundError,
    ProviderUnavailableError,
)
from backend.app.intelligence.providers.base import BaseModelProvider
from backend.app.intelligence.schemas import (
    AssistantResponse,
    ChatMessage,
    ModelCapabilities,
    Role,
    StreamChunk,
    TokenUsage,
)

logger = get_logger("intelligence.providers.ollama")


class OllamaProvider(BaseModelProvider):
    """
    Adapter for local LLM inference via Ollama REST API.
    Designed for hardware efficiency and compatibility with local GPUs (e.g. GTX 1650 4GB VRAM).
    Never automatically downloads models.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:11434", timeout_seconds: int = 60):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    @property
    def provider_id(self) -> str:
        return "ollama"

    @property
    def name(self) -> str:
        return "Ollama Local Runtime"

    @property
    def is_local(self) -> bool:
        return True

    def is_configured(self) -> bool:
        return bool(self.base_url)

    async def is_available(self) -> bool:
        """Checks if local Ollama daemon is reachable."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.base_url}/api/version")
                return res.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        """Queries local Ollama tags to list installed models."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                    return models
                return []
        except Exception as exc:
            logger.debug(f"Failed to query Ollama models: {exc}")
            return []

    async def generate(
        self,
        messages: List[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AssistantResponse:
        """Executes a chat completion request to local Ollama."""
        start_time = time.perf_counter()
        payload = {
            "model": model,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            async with httpx.AsyncClient(timeout=float(self.timeout_seconds)) as client:
                res = await client.post(f"{self.base_url}/api/chat", json=payload)

                if res.status_code == 404:
                    raise ModelNotFoundError(model=model, provider=self.provider_id)
                if res.status_code != 200:
                    raise ProviderUnavailableError(
                        provider=self.provider_id,
                        message=f"Ollama returned HTTP {res.status_code}: {res.text}"
                    )

                data = res.json()
                content = data.get("message", {}).get("content", "")
                prompt_tokens = data.get("prompt_eval_count", 0)
                completion_tokens = data.get("eval_count", 0)
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

                return AssistantResponse(
                    content=content,
                    role=Role.ASSISTANT,
                    provider=self.provider_id,
                    model=model,
                    finish_reason="stop" if data.get("done") else "unknown",
                    usage=TokenUsage(
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=prompt_tokens + completion_tokens,
                    ),
                    latency_ms=latency_ms,
                )

        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(
                provider=self.provider_id,
                message=f"Cannot connect to Ollama at {self.base_url}. Ensure the Ollama service is running."
            ) from exc
        except httpx.TimeoutException as exc:
            raise ProviderUnavailableError(
                provider=self.provider_id,
                message=f"Ollama inference timed out after {self.timeout_seconds} seconds."
            ) from exc

    async def generate_stream(
        self,
        messages: List[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Streams chat completion response from Ollama."""
        start_time = time.perf_counter()
        payload = {
            "model": model,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
            "stream": True,
            "options": {
                "temperature": temperature,
            }
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        accumulated = ""
        try:
            async with httpx.AsyncClient(timeout=float(self.timeout_seconds)) as client:
                async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                    if response.status_code == 404:
                        raise ModelNotFoundError(model=model, provider=self.provider_id)
                    if response.status_code != 200:
                        err_body = await response.aread()
                        raise ProviderUnavailableError(
                            provider=self.provider_id,
                            message=f"Ollama stream error {response.status_code}: {err_body.decode(errors='ignore')}"
                        )

                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            chunk_data = json.loads(line)
                            delta = chunk_data.get("message", {}).get("content", "")
                            is_done = chunk_data.get("done", False)
                            accumulated += delta
                            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

                            yield StreamChunk(
                                delta=delta,
                                accumulated=accumulated,
                                role=Role.ASSISTANT,
                                is_done=is_done,
                                finish_reason="stop" if is_done else None,
                                provider=self.provider_id,
                                model=model,
                                latency_ms=latency_ms,
                            )
                        except json.JSONDecodeError:
                            continue

        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(
                provider=self.provider_id,
                message=f"Cannot connect to Ollama at {self.base_url}."
            ) from exc
        except httpx.TimeoutException as exc:
            raise ProviderUnavailableError(
                provider=self.provider_id,
                message="Ollama streaming response timed out."
            ) from exc

    def get_model_capabilities(self, model: str) -> ModelCapabilities:
        """Infers capabilities based on known model tag conventions."""
        lower_name = model.lower()
        if "coder" in lower_name:
            return ModelCapabilities(coding_score=8, reasoning_score=7, creative_score=5, context_window=32768)
        if "1b" in lower_name:
            return ModelCapabilities(coding_score=5, reasoning_score=5, creative_score=6, context_window=8192)
        if "3b" in lower_name:
            return ModelCapabilities(coding_score=7, reasoning_score=7, creative_score=7, context_window=8192)
        if "7b" in lower_name:
            return ModelCapabilities(coding_score=8, reasoning_score=8, creative_score=7, context_window=8192)
        return ModelCapabilities(coding_score=6, reasoning_score=6, creative_score=6, context_window=4096)
