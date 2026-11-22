"""
Providers package for Universal Intelligence Layer.
"""

from backend.app.intelligence.providers.base import BaseModelProvider
from backend.app.intelligence.providers.ollama import OllamaProvider
from backend.app.intelligence.providers.openai import OpenAIProvider
from backend.app.intelligence.providers.anthropic import AnthropicProvider
from backend.app.intelligence.providers.gemini import GeminiProvider
from backend.app.intelligence.providers.openai_compatible import OpenAICompatibleProvider

__all__ = [
    "BaseModelProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "OpenAICompatibleProvider",
]
