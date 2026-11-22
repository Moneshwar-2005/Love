"""
Anthropic Claude Cloud Provider Adapter (Phase 03).
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

logger = get_logger("intelligence.providers.anthropic")


class AnthropicProvider(BaseModelProvider):
    """
    Adapter for Anthropic Messages API (Claude 3.5 Sonnet, Claude 3.5 Haiku, Claude 3 Opus).
    Conforms to official Anthropic Messages specification.
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.anthropic.com/v1",
        timeout_seconds: int = 60,
    ):
        self._api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    @property
    def provider_id(self) -> str:
        return "anthropic"

    @property
    def name(self) -> str:
        return "Anthropic"

    @property
    def is_local(self) -> bool:
        return False

    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def is_available(self) -> bool:
        """Checks API reachability with a minimal messages request."""
        if not self.is_configured():
            return False
        try:
            # Send a 1-token test probe
            headers = {
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            payload = {
                "model": "claude-3-5-haiku-20241022",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "ping"}],
            }
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.post(f"{self.base_url}/messages", headers=headers, json=payload)
                return res.status_code in (200, 400)  # 200 is valid; 400 implies reached API with valid auth
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        """Returns standard verified Claude models."""
        return [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
        ]

    def _prepare_messages(self, messages: List[ChatMessage]):
        """Separates system prompt from conversational user/assistant messages."""
        system_prompt = ""
        chat_turns = []
        for m in messages:
            if m.role == Role.SYSTEM:
                system_prompt += f"{m.content}\n"
            else:
                chat_turns.append({"role": m.role.value, "content": m.content})
        return system_prompt.strip(), chat_turns

    async def generate(
        self,
        messages: List[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AssistantResponse:
        """Executes a completion request via Anthropic Messages API."""
        if not self.is_configured():
            raise ProviderNotConfiguredError(provider=self.provider_id)

        start_time = time.perf_counter()
        system_prompt, chat_turns = self._prepare_messages(messages)

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": model,
            "messages": chat_turns,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=float(self.timeout_seconds)) as client:
                res = await client.post(f"{self.base_url}/messages", headers=headers, json=payload)

                if res.status_code == 404:
                    raise ModelNotFoundError(model=model, provider=self.provider_id)
                if res.status_code == 401:
                    raise ProviderUnavailableError(
                        provider=self.provider_id,
                        message="Anthropic authentication failed: Invalid or expired API key."
                    )
                if res.status_code != 200:
                    raise ProviderUnavailableError(
                        provider=self.provider_id,
                        message=f"Anthropic returned HTTP {res.status_code}: {res.text}"
                    )

                data = res.json()
                content_blocks = data.get("content", [])
                text_content = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
                usage_data = data.get("usage", {})
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

                return AssistantResponse(
                    content=text_content,
                    role=Role.ASSISTANT,
                    provider=self.provider_id,
                    model=model,
                    finish_reason=data.get("stop_reason", "end_turn"),
                    usage=TokenUsage(
                        prompt_tokens=usage_data.get("input_tokens", 0),
                        completion_tokens=usage_data.get("output_tokens", 0),
                        total_tokens=usage_data.get("input_tokens", 0) + usage_data.get("output_tokens", 0),
                    ),
                    latency_ms=latency_ms,
                )

        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise ProviderUnavailableError(
                provider=self.provider_id,
                message=f"Network error connecting to Anthropic API: {exc}"
            ) from exc

    async def generate_stream(
        self,
        messages: List[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Streams Anthropic Messages events."""
        if not self.is_configured():
            raise ProviderNotConfiguredError(provider=self.provider_id)

        start_time = time.perf_counter()
        system_prompt, chat_turns = self._prepare_messages(messages)

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": model,
            "messages": chat_turns,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
            "stream": True,
        }
        if system_prompt:
            payload["system"] = system_prompt

        accumulated = ""
        try:
            async with httpx.AsyncClient(timeout=float(self.timeout_seconds)) as client:
                async with client.stream("POST", f"{self.base_url}/messages", headers=headers, json=payload) as response:
                    if response.status_code == 404:
                        raise ModelNotFoundError(model=model, provider=self.provider_id)
                    if response.status_code != 200:
                        err_body = await response.aread()
                        raise ProviderUnavailableError(
                            provider=self.provider_id,
                            message=f"Anthropic stream error {response.status_code}: {err_body.decode(errors='ignore')}"
                        )

                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()

                        try:
                            event_data = json.loads(data_str)
                            event_type = event_data.get("type")

                            delta = ""
                            is_done = False
                            finish_reason = None

                            if event_type == "content_block_delta":
                                delta = event_data.get("delta", {}).get("text", "")
                            elif event_type == "message_delta":
                                finish_reason = event_data.get("delta", {}).get("stop_reason")
                            elif event_type == "message_stop":
                                is_done = True

                            accumulated += delta
                            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

                            if delta or is_done or finish_reason:
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
                message=f"Network error during Anthropic streaming: {exc}"
            ) from exc

    def get_model_capabilities(self, model: str) -> ModelCapabilities:
        """Returns capability profile for Claude models."""
        return ModelCapabilities(
            coding_score=10,
            reasoning_score=10,
            creative_score=10,
            context_window=200000,
            supports_streaming=True,
            supports_tools=True,
            supports_vision=True,
        )
