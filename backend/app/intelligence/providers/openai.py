"""
OpenAI Cloud Provider Adapter (Phase 03).
"""

import json
import time
from typing import AsyncGenerator, List, Optional
import httpx

from backend.app.core.logging import get_logger
from backend.app.intelligence.exceptions import (
    ModelNotFoundError,
    ProviderNotConfiguredError,
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

logger = get_logger("intelligence.providers.openai")


class OpenAIProvider(BaseModelProvider):
    """
    Adapter for OpenAI official API (GPT-4o, GPT-4o-mini, etc.).
    Operates over standard async HTTP with streaming support.
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: int = 60,
        provider_id: str = "openai",
        name: str = "OpenAI",
    ):
        self._api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._provider_id = provider_id
        self._name = name

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_local(self) -> bool:
        return False

    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def is_available(self) -> bool:
        """Verifies API credentials against OpenAI /models endpoint."""
        if not self.is_configured():
            return False
        try:
            headers = {"Authorization": f"Bearer {self._api_key}"}
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/models", headers=headers)
                return res.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        """Lists chat models accessible via the API key."""
        if not self.is_configured():
            return []
        try:
            headers = {"Authorization": f"Bearer {self._api_key}"}
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/models", headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    models = [
                        m["id"] for m in data.get("data", [])
                        if "gpt" in m.get("id", "").lower() or "o1" in m.get("id", "").lower() or "o3" in m.get("id", "").lower()
                    ]
                    return models or ["gpt-4o", "gpt-4o-mini"]
                return ["gpt-4o", "gpt-4o-mini"]
        except Exception as exc:
            logger.debug(f"OpenAI model listing failed: {exc}")
            return ["gpt-4o", "gpt-4o-mini"]

    async def generate(
        self,
        messages: List[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AssistantResponse:
        """Executes a non-streaming chat completion request."""
        if not self.is_configured():
            raise ProviderNotConfiguredError(provider=self.provider_id)

        start_time = time.perf_counter()
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            async with httpx.AsyncClient(timeout=float(self.timeout_seconds)) as client:
                res = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )

                if res.status_code == 404:
                    raise ModelNotFoundError(model=model, provider=self.provider_id)
                if res.status_code == 401:
                    raise ProviderUnavailableError(
                        provider=self.provider_id,
                        message="OpenAI authentication failed: Invalid or expired API key."
                    )
                if res.status_code != 200:
                    raise ProviderUnavailableError(
                        provider=self.provider_id,
                        message=f"OpenAI API returned HTTP {res.status_code}: {res.text}"
                    )

                data = res.json()
                choice = data.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")
                finish_reason = choice.get("finish_reason", "stop")
                usage_data = data.get("usage", {})
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

                return AssistantResponse(
                    content=content,
                    role=Role.ASSISTANT,
                    provider=self.provider_id,
                    model=model,
                    finish_reason=finish_reason,
                    usage=TokenUsage(
                        prompt_tokens=usage_data.get("prompt_tokens", 0),
                        completion_tokens=usage_data.get("completion_tokens", 0),
                        total_tokens=usage_data.get("total_tokens", 0),
                    ),
                    latency_ms=latency_ms,
                )

        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise ProviderUnavailableError(
                provider=self.provider_id,
                message=f"Network error connecting to OpenAI API: {exc}"
            ) from exc

    async def generate_stream(
        self,
        messages: List[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Streams completion tokens via SSE."""
        if not self.is_configured():
            raise ProviderNotConfiguredError(provider=self.provider_id)

        start_time = time.perf_counter()
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        accumulated = ""
        try:
            async with httpx.AsyncClient(timeout=float(self.timeout_seconds)) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status_code == 404:
                        raise ModelNotFoundError(model=model, provider=self.provider_id)
                    if response.status_code != 200:
                        err_body = await response.aread()
                        raise ProviderUnavailableError(
                            provider=self.provider_id,
                            message=f"OpenAI stream error {response.status_code}: {err_body.decode(errors='ignore')}"
                        )

                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line or not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break

                        try:
                            chunk_json = json.loads(data_str)
                            choice = chunk_json.get("choices", [{}])[0]
                            delta = choice.get("delta", {}).get("content", "")
                            finish_reason = choice.get("finish_reason")
                            is_done = bool(finish_reason)
                            accumulated += delta
                            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

                            if delta or is_done:
                                yield StreamChunk(
                                    delta=delta,
                                    accumulated=accumulated,
                                    role=Role.ASSISTANT,
                                    is_done=is_done,
                                    finish_reason=finish_reason,
                                    provider=self.provider_id,
                                    model=model,
                                    latency_ms=latency_ms,
                                )
                        except json.JSONDecodeError:
                            continue

        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise ProviderUnavailableError(
                provider=self.provider_id,
                message=f"Network error during OpenAI streaming: {exc}"
            ) from exc

    def get_model_capabilities(self, model: str) -> ModelCapabilities:
        """Returns capabilities for OpenAI models."""
        return ModelCapabilities(
            coding_score=9,
            reasoning_score=9,
            creative_score=9,
            context_window=128000,
            supports_streaming=True,
            supports_tools=True,
            supports_vision=True,
        )
