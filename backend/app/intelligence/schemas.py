"""
Pydantic schemas and dataclasses for the Universal Intelligence Layer (Phase 03).
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class TaskIntent(str, Enum):
    GENERAL = "general"
    CODING = "coding"
    DEBUGGING = "debugging"
    REASONING = "reasoning"
    RESEARCH = "research"
    WRITING = "writing"
    CREATIVE = "creative"
    PRODUCTIVITY = "productivity"
    MATHEMATICAL = "mathematical"
    DOCUMENT_ASSISTANCE = "document_assistance"
    DATA_ANALYSIS = "data_analysis"
    PLANNING = "planning"
    MULTI_STEP = "multi_step"


class ModelCapabilities(BaseModel):
    """Capabilities and architectural attributes of an LLM."""
    supports_streaming: bool = True
    supports_tools: bool = False
    supports_vision: bool = False
    context_window: int = 4096
    coding_score: int = Field(default=5, ge=1, le=10, description="1-10 capability scale")
    reasoning_score: int = Field(default=5, ge=1, le=10, description="1-10 capability scale")
    creative_score: int = Field(default=5, ge=1, le=10, description="1-10 capability scale")
    speed_tier: str = Field(default="medium", description="fast, medium, slow")


class ModelInfo(BaseModel):
    """Normalized metadata for an available model."""
    id: str
    name: str
    provider: str
    is_local: bool
    is_available: bool = True
    context_window: int = 4096
    capabilities: ModelCapabilities = Field(default_factory=ModelCapabilities)
    description: Optional[str] = None


class IntentResult(BaseModel):
    """Output of the intent classification engine."""
    intent: TaskIntent = TaskIntent.GENERAL
    confidence: float = 0.8
    requires_coding: bool = False
    requires_reasoning: bool = False
    requires_action: bool = False
    suggested_temperature: float = 0.7
    summary: str = "General assistant request"
    detected_capabilities: List[str] = Field(default_factory=list)
    suggested_tools: List[str] = Field(default_factory=list)
    is_ambiguous: bool = False
    clarification_prompt: Optional[str] = None


class RoutingDecision(BaseModel):
    """Model router selection decision."""
    provider_id: str
    model_id: str
    is_local: bool
    intent: TaskIntent
    reason: str
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None


class ChatMessage(BaseModel):
    """Single normalized conversational turn."""
    role: Role = Role.USER
    content: str
    name: Optional[str] = None


class TokenUsage(BaseModel):
    """Token consumption statistics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class AssistantResponse(BaseModel):
    """Normalized completion result returned by provider adapters."""
    content: str
    role: Role = Role.ASSISTANT
    provider: str
    model: str
    finish_reason: str = "stop"
    usage: TokenUsage = Field(default_factory=TokenUsage)
    latency_ms: float = 0.0
    intent: Optional[TaskIntent] = None


class StreamChunk(BaseModel):
    """Individual streamed delta token from a provider."""
    delta: str
    accumulated: str = ""
    role: Role = Role.ASSISTANT
    is_done: bool = False
    finish_reason: Optional[str] = None
    provider: str = ""
    model: str = ""
    latency_ms: float = 0.0


# ==============================================================================
# API Request / Response Schemas
# ==============================================================================

class ChatRequest(BaseModel):
    """User prompt request payload for chat completion."""
    message: str = Field(..., min_length=1, description="User natural language prompt")
    conversation_id: Optional[str] = Field(default=None, description="Existing conversation UUID or null for new")
    provider: Optional[str] = Field(default=None, description="Explicit provider override or null for auto routing")
    model: Optional[str] = Field(default=None, description="Explicit model override or null for auto routing")
    local_only: Optional[bool] = Field(default=None, description="Enforce strict local-only routing for this query")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0, description="Sampling temperature override")


class ChatResponse(BaseModel):
    """Successful conversation turn response payload."""
    conversation_id: str
    message_id: str
    user_message: str
    assistant_message: str
    intent: str
    provider: str
    model: str
    latency_ms: float
    usage: TokenUsage


class ConversationCreateRequest(BaseModel):
    """Request payload to create a new conversation."""
    title: Optional[str] = Field(default=None, max_length=255, description="Optional custom conversation title")


class MessageResponse(BaseModel):
    """Serialized message model for API responses."""
    id: str
    conversation_id: str
    role: str
    content: str
    intent: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    latency_ms: Optional[float] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    """Summary representation of a conversation thread."""
    id: str
    user_id: str
    title: str
    summary: Optional[str] = None
    is_pinned: bool
    is_archived: bool
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(ConversationResponse):
    """Detailed conversation representation including message history."""
    messages: List[MessageResponse] = []


class ProviderStatusResponse(BaseModel):
    """Status metadata for an individual AI provider."""
    provider_id: str
    name: str
    is_configured: bool
    is_available: bool
    is_local: bool
    endpoint: str
    models_count: int
    models: List[str] = []
    error: Optional[str] = None


class IntelligenceStatusResponse(BaseModel):
    """Global system status for the Universal Intelligence Layer."""
    status: str = "operational"
    default_provider: str
    default_model: str
    routing_preference: str
    local_only_mode: bool
    active_providers_count: int
    total_available_models: int
    providers: List[ProviderStatusResponse]
    hardware_profile: Dict[str, Any]
