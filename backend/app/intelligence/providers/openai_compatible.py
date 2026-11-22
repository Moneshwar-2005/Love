"""
OpenAI-Compatible Generic Provider Adapter (Phase 03).
Supports local and hosted drop-in runtimes (LM Studio, LocalAI, vLLM, Groq, OpenRouter).
"""

from backend.app.intelligence.providers.openai import OpenAIProvider


class OpenAICompatibleProvider(OpenAIProvider):
    """
    Adapter for any API adhering to the OpenAI v1 chat/completions specification.
    """

    def __init__(
        self,
        base_url: str = "",
        api_key: str = "",
        timeout_seconds: int = 60,
        provider_id: str = "openai_compatible",
        name: str = "OpenAI Compatible Runtime",
        is_local: bool = False,
    ):
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            provider_id=provider_id,
            name=name,
        )
        self._is_local = is_local

    @property
    def is_local(self) -> bool:
        return self._is_local

    def is_configured(self) -> bool:
        # For OpenAI compatible endpoints (like local LM Studio), base_url is required, but api_key may be optional
        return bool(self.base_url)
