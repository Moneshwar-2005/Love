"""
Universal Intelligence Layer Package for LOVE (Phase 03).
"""

from backend.app.intelligence.engine import IntelligenceEngine, get_intelligence_engine
from backend.app.intelligence.intent import IntentClassifier
from backend.app.intelligence.model_registry import ModelRegistry
from backend.app.intelligence.model_router import ModelRouter
from backend.app.intelligence.provider_manager import ProviderManager
from backend.app.intelligence.context import ContextManager
from backend.app.intelligence.conversation import ConversationManager
from backend.app.intelligence.streaming import StreamingManager
from backend.app.intelligence.identity import SystemIdentity
from backend.app.intelligence.schemas import (
    AssistantResponse,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    ConversationDetailResponse,
    IntentResult,
    ModelInfo,
    ProviderStatusResponse,
    Role,
    StreamChunk,
    TaskIntent,
)

__all__ = [
    "IntelligenceEngine",
    "get_intelligence_engine",
    "IntentClassifier",
    "ModelRegistry",
    "ModelRouter",
    "ProviderManager",
    "ContextManager",
    "ConversationManager",
    "StreamingManager",
    "SystemIdentity",
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "ConversationResponse",
    "ConversationDetailResponse",
    "AssistantResponse",
    "StreamChunk",
    "Role",
    "TaskIntent",
    "IntentResult",
    "ModelInfo",
    "ProviderStatusResponse",
]
