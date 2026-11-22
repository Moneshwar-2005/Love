"""
Intelligence Engine — Primary Subsystem Entry Point for LOVE (Phase 03).
"""

from typing import List, Optional
from backend.app.config.settings import Settings, get_settings
from backend.app.intelligence.context import ContextManager
from backend.app.intelligence.conversation import ConversationManager
from backend.app.intelligence.model_registry import ModelRegistry
from backend.app.intelligence.model_router import ModelRouter
from backend.app.intelligence.orchestrator import IntelligenceOrchestrator
from backend.app.intelligence.provider_manager import ProviderManager
from backend.app.intelligence.schemas import (
    IntelligenceStatusResponse,
    ModelInfo,
    ProviderStatusResponse,
)
from backend.app.intelligence.streaming import StreamingManager
from backend.app.memory.service import MemoryService, get_memory_service


class IntelligenceEngine:
    """
    Unified facade coordinating models, providers, context, conversations, and routing.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.registry = ModelRegistry()
        self.provider_manager = ProviderManager(settings=self.settings, registry=self.registry)
        self.model_router = ModelRouter(
            provider_manager=self.provider_manager,
            registry=self.registry,
            settings=self.settings,
        )
        self.context_manager = ContextManager(settings=self.settings)
        self.conversation_manager = ConversationManager()
        self.streaming_manager = StreamingManager(conversation_manager=self.conversation_manager)
        self.memory_service = get_memory_service()
        
        from backend.app.work.service import get_work_service
        self.work_service = get_work_service()
        self.orchestrator = IntelligenceOrchestrator(
            context_manager=self.context_manager,
            conversation_manager=self.conversation_manager,
            model_router=self.model_router,
            provider_manager=self.provider_manager,
            streaming_manager=self.streaming_manager,
            memory_service=self.memory_service,
            work_service=self.work_service,
            settings=self.settings,
        )

    async def get_system_status(self) -> IntelligenceStatusResponse:
        """Collects live status across all registered AI providers and models."""
        provider_statuses: List[ProviderStatusResponse] = await self.provider_manager.list_providers_status()
        active_count = sum(1 for p in provider_statuses if p.is_available)
        total_models = sum(p.models_count for p in provider_statuses if p.is_available)

        hardware_profile = {
            "gpu": "NVIDIA GeForce GTX 1650 (4GB VRAM)",
            "local_vram_limit_gb": 4.0,
            "recommended_local_models": [
                "llama3.2:3b",
                "llama3.2:1b",
                "qwen2.5-coder:1.5b",
            ],
            "cpu_fallback_supported": True,
        }

        return IntelligenceStatusResponse(
            status="operational",
            default_provider=self.settings.DEFAULT_PROVIDER,
            default_model=self.settings.DEFAULT_MODEL,
            routing_preference=self.settings.ROUTING_PREFERENCE,
            local_only_mode=self.settings.LOCAL_ONLY_MODE,
            active_providers_count=active_count,
            total_available_models=total_models,
            providers=provider_statuses,
            hardware_profile=hardware_profile,
        )

    def list_known_models(self) -> List[ModelInfo]:
        """Returns catalog of known models and capability profiles."""
        return self.registry.list_models()


# Singleton Engine Instance
_engine_instance: Optional[IntelligenceEngine] = None


def get_intelligence_engine() -> IntelligenceEngine:
    """Dependency provider returning singleton IntelligenceEngine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = IntelligenceEngine()
    return _engine_instance
