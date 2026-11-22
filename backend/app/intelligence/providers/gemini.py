"""
Google Gemini Cloud Provider Adapter (Phase 03).
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

logger = get_logger("intelligence.providers.gemini")


class GeminiProvider(BaseModelProvider):
    """
    Adapter for Google Gemini Developer API (Gemini 2.0 Flash, Gemini 1.5 Pro).
    Implements standard REST & SSE streaming protocols.
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout_seconds: int = 60,
    ):
        self._api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    @property
    def provider_id(self) -> str:
        return "gemini"

    @property
    def name(self) -> str:
        return "Google Gemini"

    @property
    def is_local(self) -> bool:
        return False

    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def is_available(self) -> bool:
        """Verifies API key validity by querying Gemini model list."""
        if not self.is_configured():
            return False
        try:
            url = f"{self.base_url}/models?key={self._api_key}"
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(url)
                return res.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        """Lists Gemini models capable of generateContent."""
        if not self.is_configured():
            return []
        try:
            url = f"{self.base_url}/models?key={self._api_key}"
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    models = [
                        m["name"].replace("models/", "")
                        for m in data.get("models", [])
                        if "generateContent" in m.get("supportedGenerationMethods", [])
                    ]
                    return models or ["gemini-2.0-flash", "gemini-1.5-pro"]
                return ["gemini-2.0-flash", "gemini-1.5-pro"]
        except Exception as exc:
            logger.debug(f"Gemini model listing failed: {exc}")
            return ["gemini-2.0-flash", "gemini-1.5-pro"]

    def _convert_messages(self, messages: List[ChatMessage]):
        """Converts ChatMessages into Gemini contents and systemInstruction structures."""
        system_instructions = []
        contents = []

        for m in messages:
            if m.role == Role.SYSTEM:
                system_instructions.append({"text": m.content})
            else:
                role = "user" if m.role == Role.USER else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": m.content}]
                })

        system_instruction_payload = None
        if system_instructions:
            system_instruction_payload = {"parts": system_instructions}

        return system_instruction_payload, contents

    async def generate(
        self,
        messages: List[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AssistantResponse:
        """Executes a generateContent call to Gemini."""
        if not self.is_configured():
            raise ProviderNotConfiguredError(provider=self.provider_id)

        start_time = time.perf_counter()
        clean_model = model.replace("models/", "")
        system_instruction, contents = self._convert_messages(messages)

        url = f"{self.base_url}/models/{clean_model}:generateContent?key={self._api_key}"
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
            }
        }
        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        try:
            async with httpx.AsyncClient(timeout=float(self.timeout_seconds)) as client:
                res = await client.post(url, json=payload)

                if res.status_code == 404:
                    raise ModelNotFoundError(model=clean_model, provider=self.provider_id)
                if res.status_code == 400 and "API_KEY_INVALID" in res.text:
                    raise ProviderUnavailableError(
                        provider=self.provider_id,
                        message="Google Gemini authentication failed: Invalid API key."
                    )
                if res.status_code != 200:
                    raise ProviderUnavailableError(
                        provider=self.provider_id,
                        message=f"Gemini API returned HTTP {res.status_code}: {res.text}"
                    )

                data = res.json()
                candidate = data.get("candidates", [{}])[0]
                parts = candidate.get("content", {}).get("parts", [])
                text_content = "".join(p.get("text", "") for p in parts)
                finish_reason = candidate.get("finishReason", "STOP").lower()
                usage_meta = data.get("usageMetadata", {})
                prompt_tokens = usage_meta.get("promptTokenCount", 0)
                completion_tokens = usage_meta.get("candidatesTokenCount", 0)
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

                return AssistantResponse(
                    content=text_content,
                    role=Role.ASSISTANT,
                    provider=self.provider_id,
                    model=clean_model,
                    finish_reason=finish_reason,
                    usage=TokenUsage(
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=prompt_tokens + completion_tokens,
                    ),
                    latency_ms=latency_ms,
                )

        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise ProviderUnavailableError(
                provider=self.provider_id,
                message=f"Network error connecting to Gemini API: {exc}"
            ) from exc

    async def generate_stream(
        self,
        messages: List[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Streams Gemini responses using streamGenerateContent with alt=sse."""
        if not self.is_configured():
            raise ProviderNotConfiguredError(provider=self.provider_id)

        start_time = time.perf_counter()
        clean_model = model.replace("models/", "")
        system_instruction, contents = self._convert_messages(messages)

        url = f"{self.base_url}/models/{clean_model}:streamGenerateContent?alt=sse&key={self._api_key}"
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
            }
        }
        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        accumulated = ""
        try:
            async with httpx.AsyncClient(timeout=float(self.timeout_seconds)) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code == 404:
                        raise ModelNotFoundError(model=clean_model, provider=self.provider_id)
                    if response.status_code != 200:
                        err_body = await response.aread()
                        raise ProviderUnavailableError(
                            provider=self.provider_id,
                            message=f"Gemini stream error {response.status_code}: {err_body.decode(errors='ignore')}"
                        )

                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()

                        try:
                            chunk_data = json.loads(data_str)
                            candidate = chunk_data.get("candidates", [{}])[0]
                            parts = candidate.get("content", {}).get("parts", [])
                            delta = "".join(p.get("text", "") for p in parts)
                            finish_reason = candidate.get("finishReason")
                            is_done = bool(finish_reason and finish_reason != "FINISH_REASON_UNSPECIFIED")
                            accumulated += delta
                            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

                            if delta or is_done:
                                yield StreamChunk(
                                    delta=delta,
                                    accumulated=accumulated,
                                    role=Role.ASSISTANT,
                                    is_done=is_done,
                                    finish_reason=finish_reason.lower() if finish_reason else None,
                                    provider=self.provider_id,
                                    model=clean_model,
                                    latency_ms=latency_ms,
                                )
                        except json.JSONDecodeError:
                            continue

        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise ProviderUnavailableError(
                provider=self.provider_id,
                message=f"Network error during Gemini streaming: {exc}"
            ) from exc

    def get_model_capabilities(self, model: str) -> ModelCapabilities:
        """Returns capabilities for Gemini models."""
        return ModelCapabilities(
            coding_score=9,
            reasoning_score=9,
            creative_score=9,
            context_window=1048576,
            supports_streaming=True,
            supports_tools=True,
            supports_vision=True,
        )
