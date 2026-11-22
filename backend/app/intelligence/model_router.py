"""
Intelligent Model Routing Engine for the Universal Intelligence Layer (Phase 03).
"""

from typing import List, Optional
from backend.app.config.settings import Settings, get_settings
from backend.app.core.logging import get_logger
from backend.app.intelligence.exceptions import (
    LocalOnlyViolationError,
    ModelNotFoundError,
    ProviderNotConfiguredError,
    ProviderUnavailableError,
)
from backend.app.intelligence.model_registry import ModelRegistry
from backend.app.intelligence.provider_manager import ProviderManager
from backend.app.intelligence.schemas import IntentResult, RoutingDecision, TaskIntent

logger = get_logger("intelligence.model_router")


class ModelRouter:
    """
    Intelligently routes conversational queries to the optimal available model based on:
    - Classified task intent and complexity
    - Capabilities (coding, reasoning, creative, context window)
    - Privacy constraints (local-only mode enforcement)
    - Hardware profile (4GB VRAM GPU awareness)
    - Configured routing preferences (auto, local_first, cloud_first, local_only)
    """

    def __init__(
        self,
        provider_manager: ProviderManager,
        registry: ModelRegistry,
        settings: Optional[Settings] = None,
    ):
        self.provider_manager = provider_manager
        self.registry = registry
        self.settings = settings or get_settings()

    async def route(
        self,
        intent_result: IntentResult,
        provider_override: Optional[str] = None,
        model_override: Optional[str] = None,
        local_only: Optional[bool] = None,
    ) -> RoutingDecision:
        """
        Determines the optimal provider and model to handle the incoming request.
        """
        # Determine effective local-only constraint
        effective_local_only = self.settings.LOCAL_ONLY_MODE or bool(local_only)

        # 1. Handle explicit user overrides
        if provider_override:
            return await self._handle_explicit_override(
                provider_id=provider_override,
                model_id=model_override,
                intent_result=intent_result,
                effective_local_only=effective_local_only,
            )

        # 2. Dynamic routing
        available_providers = await self.provider_manager.get_available_providers(
            local_only=effective_local_only
        )

        if not available_providers:
            if effective_local_only:
                raise LocalOnlyViolationError(
                    "Local-only mode is active, but no local AI runtime (Ollama) is currently reachable. "
                    "Please ensure Ollama is running at " + self.settings.OLLAMA_BASE_URL
                )
            raise ProviderUnavailableError(
                provider="none",
                message=(
                    "No AI model provider is currently active or configured. "
                    "To enable AI capabilities, either start local Ollama (http://127.0.0.1:11434) "
                    "or supply an API key for OpenAI, Anthropic, or Google Gemini in your configuration."
                )
            )

        # Check routing policy
        policy = self.settings.ROUTING_PREFERENCE.lower()

        # Group available providers
        local_providers = [p for p in available_providers if p.is_local]
        cloud_providers = [p for p in available_providers if not p.is_local]

        # Route by policy and task intent
        if effective_local_only or policy == "local_only":
            return await self._route_local(local_providers, intent_result, reason="Enforced by local-only policy")

        if policy == "local_first" and local_providers:
            return await self._route_local(local_providers, intent_result, reason="Selected by local-first preference")

        if policy == "cloud_first" and cloud_providers:
            return await self._route_cloud(cloud_providers, intent_result, reason="Selected by cloud-first preference")

        # Default: "auto" intelligent policy
        # If the task requires deep coding or complex multi-step reasoning, prefer capable cloud models if active
        if (intent_result.requires_coding or intent_result.requires_reasoning) and cloud_providers:
            return await self._route_cloud(
                cloud_providers,
                intent_result,
                reason=f"Selected high-capability cloud model for {intent_result.intent.value} task"
            )

        # For everyday general queries, writing, or when cloud is unconfigured, prioritize local if available
        if local_providers:
            return await self._route_local(
                local_providers,
                intent_result,
                reason="Selected efficient local model for conversation"
            )

        # Fallback to cloud
        return await self._route_cloud(cloud_providers, intent_result, reason="Cloud provider selected (no local model available)")

    async def _handle_explicit_override(
        self,
        provider_id: str,
        model_id: Optional[str],
        intent_result: IntentResult,
        effective_local_only: bool,
    ) -> RoutingDecision:
        """Handles explicit provider and model selections requested by the caller."""
        provider = self.provider_manager.get_provider(provider_id)
        if not provider:
            raise ProviderNotConfiguredError(provider=provider_id)

        if effective_local_only and not provider.is_local:
            raise LocalOnlyViolationError(
                f"Requested provider '{provider_id}' is a cloud provider, which violates the active local-only privacy constraint."
            )

        if not provider.is_configured():
            raise ProviderNotConfiguredError(provider=provider_id)

        if not await provider.is_available():
            raise ProviderUnavailableError(provider=provider_id)

        # Resolve model
        chosen_model = model_id
        if not chosen_model or chosen_model == "auto":
            models = await provider.list_models()
            if not models:
                # Fallback to catalog defaults
                best = self.registry.get_best_model_for_task(
                    provider_id=provider_id,
                    requires_coding=intent_result.requires_coding,
                    requires_reasoning=intent_result.requires_reasoning,
                )
                chosen_model = best.id if best else "default"
            else:
                chosen_model = models[0]

        return RoutingDecision(
            provider_id=provider.provider_id,
            model_id=chosen_model,
            is_local=provider.is_local,
            intent=intent_result.intent,
            reason=f"Explicitly requested provider '{provider_id}' and model '{chosen_model}'",
        )

    async def _route_local(
        self,
        local_providers: List,
        intent_result: IntentResult,
        reason: str
    ) -> RoutingDecision:
        """Selects the best available model on local runtimes."""
        if not local_providers:
            raise ProviderUnavailableError(
                provider="ollama",
                message="No local AI runtime is available."
            )

        provider = local_providers[0]
        models = await provider.list_models()

        chosen_model = None
        # Select best local model based on intent and 4GB VRAM friendliness
        if models:
            if intent_result.requires_coding:
                for m in models:
                    if "coder" in m.lower():
                        chosen_model = m
                        break
            if not chosen_model:
                chosen_model = models[0]
        else:
            # If Ollama has no tags yet, select default small model
            chosen_model = "llama3.2:3b"

        return RoutingDecision(
            provider_id=provider.provider_id,
            model_id=chosen_model,
            is_local=True,
            intent=intent_result.intent,
            reason=reason,
        )

    async def _route_cloud(
        self,
        cloud_providers: List,
        intent_result: IntentResult,
        reason: str
    ) -> RoutingDecision:
        """Selects the best available model on cloud providers."""
        if not cloud_providers:
            raise ProviderUnavailableError(
                provider="cloud",
                message="No cloud AI provider is currently reachable."
            )

        # Priority order for cloud providers: Anthropic -> OpenAI -> Gemini -> OpenAI-Compatible
        priority_order = ["anthropic", "openai", "gemini", "openai_compatible"]
        chosen_provider = None
        for p_id in priority_order:
            for p in cloud_providers:
                if p.provider_id == p_id:
                    chosen_provider = p
                    break
            if chosen_provider:
                break

        if not chosen_provider:
            chosen_provider = cloud_providers[0]

        # Pick appropriate model for chosen provider
        p_id = chosen_provider.provider_id
        if p_id == "anthropic":
            chosen_model = "claude-3-5-sonnet-20241022" if intent_result.requires_coding else "claude-3-5-haiku-20241022"
        elif p_id == "openai":
            chosen_model = "gpt-4o" if intent_result.requires_coding else "gpt-4o-mini"
        elif p_id == "gemini":
            models = await chosen_provider.list_models()
            if "gemini-flash-lite-latest" in models:
                chosen_model = "gemini-flash-lite-latest"
            elif "gemini-3.1-flash-lite" in models:
                chosen_model = "gemini-3.1-flash-lite"
            elif "gemini-3.8-flash" in models:
                chosen_model = "gemini-3.8-flash"
            elif models:
                chosen_model = models[0]
            else:
                chosen_model = "gemini-flash-lite-latest"
        else:
            models = await chosen_provider.list_models()
            chosen_model = models[0] if models else "default"

        return RoutingDecision(
            provider_id=chosen_provider.provider_id,
            model_id=chosen_model,
            is_local=False,
            intent=intent_result.intent,
            reason=reason,
        )
