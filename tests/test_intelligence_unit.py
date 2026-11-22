"""
Unit tests for LOVE Universal Intelligence Layer core components (Phase 03).
"""

import pytest
from unittest.mock import AsyncMock, patch

from backend.app.config.settings import Settings
from backend.app.intelligence.context import ContextManager
from backend.app.intelligence.exceptions import (
    LocalOnlyViolationError,
    ModelNotFoundError,
    ProviderNotConfiguredError,
    ProviderUnavailableError,
)
from backend.app.intelligence.identity import SystemIdentity
from backend.app.intelligence.intent import IntentClassifier
from backend.app.intelligence.model_registry import ModelRegistry
from backend.app.intelligence.model_router import ModelRouter
from backend.app.intelligence.provider_manager import ProviderManager
from backend.app.intelligence.providers.anthropic import AnthropicProvider
from backend.app.intelligence.providers.gemini import GeminiProvider
from backend.app.intelligence.providers.ollama import OllamaProvider
from backend.app.intelligence.providers.openai import OpenAIProvider
from backend.app.intelligence.providers.openai_compatible import OpenAICompatibleProvider
from backend.app.intelligence.schemas import (
    ChatMessage,
    IntentResult,
    ModelCapabilities,
    ModelInfo,
    Role,
    TaskIntent,
)


# ==============================================================================
# Intent Classifier Tests
# ==============================================================================

def test_intent_classifier_debugging():
    prompt = "I'm getting a TypeError: NoneType object is not callable in my FastAPI endpoint. Can you help me fix this bug?"
    result = IntentClassifier.classify(prompt)
    assert result.intent == TaskIntent.DEBUGGING
    assert result.requires_coding is True
    assert result.suggested_temperature <= 0.3


def test_intent_classifier_coding():
    prompt = "Implement an async Python function that connects to SQLite using aiosqlite and runs a query."
    result = IntentClassifier.classify(prompt)
    assert result.intent == TaskIntent.CODING
    assert result.requires_coding is True


def test_intent_classifier_reasoning():
    prompt = "What is the difference between SQLite and PostgreSQL? Compare their architectural trade-offs."
    result = IntentClassifier.classify(prompt)
    assert result.intent == TaskIntent.REASONING
    assert result.requires_reasoning is True


def test_intent_classifier_writing():
    prompt = "Write a professional email to my engineering team summarizing our Phase 03 launch."
    result = IntentClassifier.classify(prompt)
    assert result.intent == TaskIntent.WRITING


def test_intent_classifier_creative():
    prompt = "Brainstorm 5 creative ideas and fictional plot concepts for an AI assistant sci-fi story."
    result = IntentClassifier.classify(prompt)
    assert result.intent == TaskIntent.CREATIVE
    assert result.suggested_temperature >= 0.8


def test_intent_classifier_productivity():
    prompt = "Help me organize my daily agenda and create a prioritized action checklist for today."
    result = IntentClassifier.classify(prompt)
    assert result.intent == TaskIntent.PRODUCTIVITY


def test_intent_classifier_math():
    prompt = "Calculate the integral of 3x^2 + 2x - 5 and solve for the roots of the polynomial equation."
    result = IntentClassifier.classify(prompt)
    assert result.intent == TaskIntent.MATHEMATICAL


def test_intent_classifier_general_fallback():
    prompt = "Good morning! How are you doing today?"
    result = IntentClassifier.classify(prompt)
    assert result.intent == TaskIntent.GENERAL
    assert result.confidence > 0.5


# ==============================================================================
# System Identity Tests
# ==============================================================================

def test_system_identity_prompt_construction():
    prompt = SystemIdentity.build_system_prompt(
        intent=TaskIntent.CODING,
        user_name="Tony Stark",
    )
    assert "LOVE" in prompt
    assert "Tony Stark" in prompt
    assert "Specialized Mode: Software Engineering" in prompt
    assert "Indian English" in prompt


# ==============================================================================
# Model Registry Tests
# ==============================================================================

def test_model_registry_initialization_and_lookup():
    registry = ModelRegistry()
    models = registry.list_models()
    assert len(models) >= 5

    # Check local models optimized for 4GB VRAM
    local_models = registry.list_models(local_only=True)
    assert any("llama3.2" in m.id for m in local_models)
    assert any("qwen2.5-coder" in m.id for m in local_models)

    # Check cloud flagship models
    gpt = registry.get_model("openai", "gpt-4o")
    assert gpt is not None
    assert gpt.capabilities.coding_score == 10

    claude = registry.get_model("anthropic", "claude-3-5-sonnet-20241022")
    assert claude is not None
    assert claude.capabilities.reasoning_score == 10


def test_model_registry_custom_registration():
    registry = ModelRegistry()
    custom_model = ModelInfo(
        id="custom-llm:latest",
        name="Custom Local Model",
        provider="ollama",
        is_local=True,
        capabilities=ModelCapabilities(coding_score=9),
    )
    registry.register_model(custom_model)
    retrieved = registry.get_model("ollama", "custom-llm:latest")
    assert retrieved is not None
    assert retrieved.name == "Custom Local Model"


# ==============================================================================
# Provider Adapter Contract Tests
# ==============================================================================

def test_provider_configuration_status():
    ollama = OllamaProvider(base_url="http://127.0.0.1:11434")
    assert ollama.is_configured() is True
    assert ollama.is_local is True

    openai_unconf = OpenAIProvider(api_key="")
    assert openai_unconf.is_configured() is False
    assert openai_unconf.is_local is False

    openai_conf = OpenAIProvider(api_key="sk-test-key")
    assert openai_conf.is_configured() is True

    anthropic_unconf = AnthropicProvider(api_key="")
    assert anthropic_unconf.is_configured() is False

    gemini_unconf = GeminiProvider(api_key="")
    assert gemini_unconf.is_configured() is False

    compat_unconf = OpenAICompatibleProvider(base_url="")
    assert compat_unconf.is_configured() is False

    compat_conf = OpenAICompatibleProvider(base_url="http://localhost:1234/v1")
    assert compat_conf.is_configured() is True


@pytest.mark.asyncio
async def test_unconfigured_cloud_providers_raise_error():
    openai = OpenAIProvider(api_key="")
    with pytest.raises(ProviderNotConfiguredError):
        await openai.generate(
            messages=[ChatMessage(role=Role.USER, content="Hello")],
            model="gpt-4o"
        )

    anthropic = AnthropicProvider(api_key="")
    with pytest.raises(ProviderNotConfiguredError):
        await anthropic.generate(
            messages=[ChatMessage(role=Role.USER, content="Hello")],
            model="claude-3-5-sonnet-20241022"
        )

    gemini = GeminiProvider(api_key="")
    with pytest.raises(ProviderNotConfiguredError):
        await gemini.generate(
            messages=[ChatMessage(role=Role.USER, content="Hello")],
            model="gemini-2.0-flash"
        )


@pytest.mark.asyncio
async def test_ollama_mocked_generation():
    ollama = OllamaProvider(base_url="http://127.0.0.1:11434")

    mock_response_data = {
        "model": "llama3.2:3b",
        "message": {"role": "assistant", "content": "I am LOVE, at your service."},
        "done": True,
        "prompt_eval_count": 12,
        "eval_count": 10,
    }

    from unittest.mock import MagicMock
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = mock_response_data
        mock_post.return_value = mock_res

        resp = await ollama.generate(
            messages=[ChatMessage(role=Role.USER, content="Who are you?")],
            model="llama3.2:3b"
        )
        assert resp.content == "I am LOVE, at your service."
        assert resp.provider == "ollama"
        assert resp.model == "llama3.2:3b"
        assert resp.usage.total_tokens == 22


# ==============================================================================
# Model Router Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_model_router_strict_local_only_enforcement():
    settings = Settings(
        LOCAL_ONLY_MODE=True,
        OPENAI_API_KEY="sk-fake-valid-key",
    )
    provider_mgr = ProviderManager(settings=settings)
    registry = ModelRegistry()
    router = ModelRouter(provider_manager=provider_mgr, registry=registry, settings=settings)

    # When Ollama is offline and local_only is active, cloud MUST NOT be used!
    with patch.object(OllamaProvider, "is_available", AsyncMock(return_value=False)):
        intent = IntentResult(intent=TaskIntent.CODING, requires_coding=True)
        with pytest.raises(LocalOnlyViolationError):
            await router.route(intent_result=intent, local_only=True)


@pytest.mark.asyncio
async def test_model_router_no_providers_available_clean_error():
    settings = Settings(
        LOCAL_ONLY_MODE=False,
        OPENAI_API_KEY="",
        ANTHROPIC_API_KEY="",
        GEMINI_API_KEY="",
    )
    provider_mgr = ProviderManager(settings=settings)
    registry = ModelRegistry()
    router = ModelRouter(provider_manager=provider_mgr, registry=registry, settings=settings)

    with patch.object(OllamaProvider, "is_available", AsyncMock(return_value=False)):
        intent = IntentResult(intent=TaskIntent.GENERAL)
        with pytest.raises(ProviderUnavailableError) as exc_info:
            await router.route(intent_result=intent)
        assert "No AI model provider is currently active" in str(exc_info.value.message)


@pytest.mark.asyncio
async def test_model_router_explicit_override_validation():
    settings = Settings(OPENAI_API_KEY="")
    provider_mgr = ProviderManager(settings=settings)
    registry = ModelRegistry()
    router = ModelRouter(provider_manager=provider_mgr, registry=registry, settings=settings)

    intent = IntentResult(intent=TaskIntent.GENERAL)
    # Requesting an unconfigured provider explicitly should raise ProviderNotConfiguredError
    with pytest.raises(ProviderNotConfiguredError):
        await router.route(intent_result=intent, provider_override="openai", model_override="gpt-4o")


# ==============================================================================
# Context Manager Tests
# ==============================================================================

def test_context_manager_token_estimation():
    text = "The quick brown fox jumps over the lazy dog."
    tokens = ContextManager.estimate_tokens(text)
    assert 5 <= tokens <= 15
