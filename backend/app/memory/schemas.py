"""
Pydantic schemas and dataclasses for Persistent Personal Memory (Phase 04).
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MemoryCategory(str, Enum):
    """Canonical categories of personal memory."""
    PERSONAL = "personal"
    PROJECT = "project"
    CONVERSATIONAL = "conversational"
    KNOWLEDGE = "knowledge"


class SourceType(str, Enum):
    """Provenance origin of the memory record."""
    EXPLICIT_USER = "explicit_user"
    CONVERSATION_EXTRACTION = "conversation_extraction"
    SYSTEM_RULE = "system_rule"
    REFERENCE_DOC = "reference_doc"


class MemoryCreateRequest(BaseModel):
    """Request payload to create a new personal memory."""
    content: str = Field(..., min_length=3, description="Canonical memory statement or fact")
    category: MemoryCategory = Field(default=MemoryCategory.PERSONAL, description="Memory category")
    summary: Optional[str] = Field(default=None, max_length=255, description="Concise synopsis")
    source_type: SourceType = Field(default=SourceType.EXPLICIT_USER, description="Memory provenance")
    source_id: Optional[str] = Field(default=None, description="Optional conversation or reference UUID")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence/reliability score")
    importance: int = Field(default=3, ge=1, le=5, description="Priority weight (1 to 5)")
    tags: List[str] = Field(default_factory=list, description="Categorization and search tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary structured metadata")


class MemoryUpdateRequest(BaseModel):
    """Request payload to modify an existing memory record."""
    content: Optional[str] = Field(default=None, min_length=3, description="Updated memory text")
    category: Optional[MemoryCategory] = Field(default=None, description="Updated category")
    summary: Optional[str] = Field(default=None, max_length=255, description="Updated synopsis")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Updated confidence")
    importance: Optional[int] = Field(default=None, ge=1, le=5, description="Updated importance (1 to 5)")
    tags: Optional[List[str]] = Field(default=None, description="Updated search tags")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Updated metadata")


class MemoryResponse(BaseModel):
    """Serialized representation of a personal memory record."""
    id: str
    user_id: str
    category: MemoryCategory
    content: str
    summary: Optional[str] = None
    source_type: str
    source_id: Optional[str] = None
    confidence: float
    importance: int
    tags: List[str] = []
    metadata: Dict[str, Any] = {}
    is_archived: bool
    access_count: int
    last_accessed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MemorySearchRequest(BaseModel):
    """Search query payload for hybrid semantic and lexical memory retrieval."""
    query: str = Field(..., min_length=1, description="Natural language search query")
    category: Optional[MemoryCategory] = Field(default=None, description="Filter by category")
    tags: Optional[List[str]] = Field(default=None, description="Filter by tags")
    top_k: int = Field(default=5, ge=1, le=50, description="Maximum results to return")
    min_score: float = Field(default=0.25, ge=0.0, le=1.0, description="Minimum similarity score")
    include_archived: bool = Field(default=False, description="Whether to include archived memories")


class MemorySearchResult(BaseModel):
    """Individual retrieved memory with hybrid relevance ranking."""
    memory: MemoryResponse
    score: float = Field(..., description="Combined hybrid relevance score (0.0 to 1.0)")
    semantic_score: float = Field(default=0.0, description="Vector cosine similarity score")
    lexical_score: float = Field(default=0.0, description="Keyword / token matching score")


class MemoryExtractionCandidate(BaseModel):
    """Potential memory item extracted from a conversational turn."""
    content: str
    category: MemoryCategory
    confidence: float
    importance: int
    source_statement: str
    needs_approval: bool = False
    reasoning: str = ""


class SuggestionStatus(str, Enum):
    """Lifecycle status of a memory suggestion."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class MemorySuggestionResponse(BaseModel):
    """Serialized representation of a pending or processed memory suggestion."""
    id: str
    user_id: str
    category: MemoryCategory
    content: str
    summary: Optional[str] = None
    reasoning: Optional[str] = None
    source_statement: Optional[str] = None
    source_id: Optional[str] = None
    confidence: float
    importance: int
    tags: List[str] = []
    metadata: Dict[str, Any] = {}
    status: SuggestionStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MemoryStatsResponse(BaseModel):
    """Subsystem status and statistics for personal memory."""
    total_memories: int
    active_memories: int
    archived_memories: int
    categories_breakdown: Dict[str, int]
    vector_store_type: str
    vector_index_size: int
    embedding_provider: str
    embedding_dimension: int
    cloud_embeddings_permitted: bool
