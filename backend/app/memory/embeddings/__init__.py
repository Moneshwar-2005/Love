"""
Embeddings package for Persistent Personal Memory (Phase 04).
"""

from backend.app.memory.embeddings.base import BaseEmbeddingProvider
from backend.app.memory.embeddings.deterministic import DeterministicEmbeddingProvider
from backend.app.memory.embeddings.gemini import GeminiEmbeddingProvider
from backend.app.memory.embeddings.manager import EmbeddingManager
from backend.app.memory.embeddings.ollama import OllamaEmbeddingProvider

__all__ = [
    "BaseEmbeddingProvider",
    "DeterministicEmbeddingProvider",
    "GeminiEmbeddingProvider",
    "OllamaEmbeddingProvider",
    "EmbeddingManager",
]
