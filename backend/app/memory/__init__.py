"""
Persistent Personal Memory Subsystem for LOVE (Phase 04).

Provides independent, persistent personal memory storage with semantic and lexical retrieval,
sensitive data protection, automatic candidate extraction, and multi-user isolation.
"""

from backend.app.memory.embeddings.base import BaseEmbeddingProvider
from backend.app.memory.embeddings.deterministic import DeterministicEmbeddingProvider
from backend.app.memory.embeddings.gemini import GeminiEmbeddingProvider
from backend.app.memory.embeddings.manager import EmbeddingManager
from backend.app.memory.embeddings.ollama import OllamaEmbeddingProvider
from backend.app.memory.exceptions import (
    DuplicateMemoryError,
    EmbeddingUnavailableError,
    MemoryError,
    MemoryNotFoundError,
    SensitiveDataBlockedError,
    VectorStoreError,
)
from backend.app.memory.extraction import MemoryExtractionService
from backend.app.memory.retrieval import MemoryRetrievalEngine
from backend.app.memory.sanitizer import SensitiveDataSanitizer
from backend.app.memory.schemas import (
    MemoryCategory,
    MemoryCreateRequest,
    MemoryExtractionCandidate,
    MemoryResponse,
    MemorySearchRequest,
    MemorySearchResult,
    MemoryStatsResponse,
    MemorySuggestionResponse,
    MemoryUpdateRequest,
    SourceType,
    SuggestionStatus,
)
from backend.app.memory.service import MemoryService, get_memory_service
from backend.app.memory.vector_store.base import BaseVectorStore
from backend.app.memory.vector_store.local_store import LocalVectorStore
from backend.app.memory.vector_store.qdrant_store import QdrantVectorStore

__all__ = [
    # Core Service
    "MemoryService",
    "get_memory_service",
    "MemoryRetrievalEngine",
    "MemoryExtractionService",
    "SensitiveDataSanitizer",
    # Embeddings
    "BaseEmbeddingProvider",
    "DeterministicEmbeddingProvider",
    "EmbeddingManager",
    "GeminiEmbeddingProvider",
    "OllamaEmbeddingProvider",
    # Vector Stores
    "BaseVectorStore",
    "LocalVectorStore",
    "QdrantVectorStore",
    # Schemas
    "MemoryCategory",
    "MemoryCreateRequest",
    "MemoryExtractionCandidate",
    "MemoryResponse",
    "MemorySearchRequest",
    "MemorySearchResult",
    "MemoryStatsResponse",
    "MemorySuggestionResponse",
    "MemoryUpdateRequest",
    "SourceType",
    "SuggestionStatus",
    # Exceptions
    "DuplicateMemoryError",
    "EmbeddingUnavailableError",
    "MemoryError",
    "MemoryNotFoundError",
    "SensitiveDataBlockedError",
    "VectorStoreError",
]
