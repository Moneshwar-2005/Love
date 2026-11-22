"""
Provider Manager for the Universal Intelligence Layer (Phase 03).
"""

import asyncio
from typing import Dict, List, Optional
from backend.app.config.settings import Settings, get_settings
from backend.app.core.logging import get_logger
from backend.app.intelligence.model_registry import ModelRegistry
from backend.app.intelligence.providers.base import BaseModelProvider
from backend.app.intelligence.providers.ollama import OllamaProvider
from backend.app.intelligence.providers.openai import OpenAIProvider
from backend.app.intelligence.providers.anthropic import AnthropicProvider
from backend.app.intelligence.providers.gemini import GeminiProvider
from backend.app.intelligence.providers.openai_compatible import OpenAICompatibleProvider
from backend.app.intelligence.schemas import ModelInfo, ProviderStatusResponse

logger = get_logger("intelligence.provider_manager")


class ProviderManager:
    """
    Manages the lifecycle, health checking, and model discovery of all AI provider adapters.
    """

    def __init__(self, settings: Optional[Settings] = None, registry: Optional[ModelRegistry] = None):
        self.settings = settings or get_settings()
        self.registry = registry or ModelRegistry()
        self._providers: Dict[str, BaseModelProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Instantiates all supported provider adapters with current settings."""
        # 1. Ollama (Local)
        self.register_provider(
            OllamaProvider(
                base_url=self.settings.OLLAMA_BASE_URL,
                timeout_seconds=self.settings.OLLAMA_TIMEOUT_SECONDS,
            )
        )

        # 2. OpenAI (Cloud)
        self.register_provider(
            OpenAIProvider(
                api_key=self.settings.OPENAI_API_KEY,
                base_url=self.settings.OPENAI_BASE_URL,
                timeout_seconds=self.settings.INTELLIGENCE_REQUEST_TIMEOUT_SECONDS,
            )
        )

        # 3. Anthropic (Cloud)
        self.register_provider(
            AnthropicProvider(
                api_key=self.settings.ANTHROPIC_API_KEY,
                base_url=self.settings.ANTHROPIC_BASE_URL,
                timeout_seconds=self.settings.INTELLIGENCE_REQUEST_TIMEOUT_SECONDS,
            )
        )

        # 4. Google Gemini (Cloud)
        self.register_provider(
            GeminiProvider(
                api_key=self.settings.GEMINI_API_KEY,
                base_url=self.settings.GEMINI_BASE_URL,
                timeout_seconds=self.settings.INTELLIGENCE_REQUEST_TIMEOUT_SECONDS,
            )
        )

        # 5. OpenAI Compatible (Generic)
        if self.settings.OPENAI_COMPATIBLE_BASE_URL:
            self.register_provider(
                OpenAICompatibleProvider(
                    base_url=self.settings.OPENAI_COMPATIBLE_BASE_URL,
                    api_key=self.settings.OPENAI_COMPATIBLE_API_KEY,
                    timeout_seconds=self.settings.INTELLIGENCE_REQUEST_TIMEOUT_SECONDS,
                )
            )

    def register_provider(self, provider: BaseModelProvider) -> None:
        """Registers a provider adapter."""
        self._providers[provider.provider_id] = provider

    def get_provider(self, provider_id: str) -> Optional[BaseModelProvider]:
        """Retrieves a provider by its unique identifier."""
        return self._providers.get(provider_id)

    async def check_provider_status(self, provider: BaseModelProvider) -> ProviderStatusResponse:
        """Asynchronously checks configuration and live connectivity for an individual provider."""
        is_configured = provider.is_configured()
        is_available = False
        models = []
        error = None

        if is_configured:
            try:
                is_available = await provider.is_available()
                if is_available:
                    models = await provider.list_models()
                    # Sync discovered models into the registry
                    for m_id in models:
                        existing = self.registry.get_model(provider.provider_id, m_id)
                        if not existing:
                            caps = provider.get_model_capabilities(m_id)
                            self.registry.register_model(
                                ModelInfo(
                                    id=m_id,
                                    name=f"{m_id} ({provider.name})",
                                    provider=provider.provider_id,
                                    is_local=provider.is_local,
                                    is_available=True,
                                    capabilities=caps,
                                )
                            )
            except Exception as exc:
                error = str(exc)
                logger.debug(f"Error checking provider {provider.provider_id}: {exc}")
        else:
            error = "Provider is not configured (missing credentials or endpoint URL)"

        endpoint = getattr(provider, "base_url", "internal")
        return ProviderStatusResponse(
            provider_id=provider.provider_id,
            name=provider.name,
            is_configured=is_configured,
            is_available=is_available,
            is_local=provider.is_local,
            endpoint=endpoint,
            models_count=len(models),
            models=models,
            error=error if not is_available else None,
        )

    async def list_providers_status(self) -> List[ProviderStatusResponse]:
        """Returns the status and health of all registered providers concurrently."""
        tasks = [self.check_provider_status(p) for p in self._providers.values()]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results

    async def get_available_providers(self, local_only: bool = False) -> List[BaseModelProvider]:
        """Returns the subset of providers that are configured and currently available."""
        available = []
        for provider in self._providers.values():
            if local_only and not provider.is_local:
                continue
            if provider.is_configured() and await provider.is_available():
                available.append(provider)
        return available
