"""
Unit tests for Persistent Personal Memory Subsystem (Phase 04).
Covers sanitization, extraction, deterministic & managed embeddings,
vector storage, hybrid retrieval, and owner isolation.
"""

import math
import pytest
from unittest.mock import AsyncMock, patch

from backend.app.config.settings import Settings
from backend.app.database.models.memory import Memory, MemoryAuditLog
from backend.app.memory.embeddings.deterministic import DeterministicEmbeddingProvider
from backend.app.memory.embeddings.gemini import GeminiEmbeddingProvider
from backend.app.memory.embeddings.manager import EmbeddingManager
from backend.app.memory.embeddings.ollama import OllamaEmbeddingProvider
from backend.app.memory.exceptions import SensitiveDataBlockedError
from backend.app.memory.extraction import MemoryExtractionService
from backend.app.memory.retrieval import MemoryRetrievalEngine
from backend.app.memory.sanitizer import SensitiveDataSanitizer
from backend.app.memory.schemas import (
    MemoryCategory,
    MemoryCreateRequest,
    MemorySearchRequest,
    SourceType,
)
from backend.app.memory.vector_store.local_store import LocalVectorStore


# ============================================================================
# 1. Sensitive Data Sanitizer Tests
# ============================================================================

def test_sanitizer_detects_credentials_and_secrets():
    """Verifies that secrets, API keys, passwords, private keys, and cards are detected."""
    sensitive_samples = [
        ("My secret key is sk-1234567890abcdef1234567890abcdef", "OpenAI / Claude Secret Key"),
        ("Here is the token ghp_1234567890abcdefghijklmnopqrstuvwxyz", "GitHub Token"),
        ("-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA...", "Private Key"),
        ("Use header Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", "Bearer Token"),
        ("Payment card is 4532-0150-1234-5678 please bill it", "Payment Card Number"),
        ("My database password: superSecretPassword123!", "Password Credential"),
        ("export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", "Generic API Key/Secret"),
    ]

    for text, expected_name in sensitive_samples:
        is_sensitive, detected = SensitiveDataSanitizer.check_for_sensitive_data(text)
        assert is_sensitive is True, f"Failed to detect secret in: {text}"
        assert detected is not None


def test_sanitizer_permits_safe_natural_statements():
    """Verifies that normal preferences, technical discussions, and facts are permitted."""
    safe_samples = [
        "I prefer dark mode in all IDEs and user interfaces.",
        "We are building LOVE with FastAPI and SQLite.",
        "My favorite programming language is Python.",
        "The project uses an NVIDIA GTX 1650 with 4GB VRAM.",
        "I live in Bengaluru, India.",
        "Remember that the server runs on port 8000.",
    ]

    for text in safe_samples:
        is_sensitive, detected = SensitiveDataSanitizer.check_for_sensitive_data(text)
        assert is_sensitive is False, f"False positive detection for safe text: {text} ({detected})"


def test_sanitizer_redaction():
    """Verifies that sensitive data can be redacted into masked tokens."""
    raw = "My API key is sk-1234567890abcdef1234567890abcdef and my card is 4532-0150-1234-5678."
    redacted = SensitiveDataSanitizer.sanitize_for_prompt(raw)
    assert "sk-" not in redacted
    assert "4532-0150" not in redacted
    assert "[REDACTED" in redacted


# ============================================================================
# 2. Memory Extraction Service Tests
# ============================================================================

def test_extract_candidates_explicit_directives():
    """Verifies extraction of explicit 'Remember that...' and preference commands."""
    prompt = "Remember that I prefer PostgreSQL for production deployments."
    candidates = MemoryExtractionService.extract_candidates(prompt)

    assert len(candidates) >= 1
    cand = candidates[0]
    assert cand.needs_approval is False
    assert cand.confidence >= 0.8
    assert "Postgresql" in cand.content or "postgresql" in cand.content.lower()


def test_extract_candidates_project_decisions():
    """Verifies extraction of project architectural statements as suggestions requiring consent."""
    prompt = "We decided to use SQLite as our primary relational database."
    candidates = MemoryExtractionService.extract_candidates(prompt)

    assert len(candidates) >= 1
    assert candidates[0].category == MemoryCategory.PROJECT
    assert candidates[0].confidence >= 0.85
    assert candidates[0].needs_approval is True  # Requires consent; not silently saved


def test_extract_candidates_personal_facts():
    """Verifies extraction of user personal profile facts as suggestions requiring consent."""
    prompt = "I work as a senior AI systems engineer."
    candidates = MemoryExtractionService.extract_candidates(prompt)

    assert len(candidates) >= 1
    assert candidates[0].category == MemoryCategory.PERSONAL
    assert candidates[0].confidence >= 0.8
    assert candidates[0].needs_approval is True  # Requires consent; not silently saved


def test_extract_candidates_blocks_sensitive_content():
    """Verifies that prompts containing raw credentials produce zero extracted candidates."""
    prompt = "Remember that my API token is ghp_1234567890abcdefghijklmnopqrstuvwxyz"
    candidates = MemoryExtractionService.extract_candidates(prompt)
    assert len(candidates) == 0


# ============================================================================
# 3. Embedding Providers Tests
# ============================================================================

@pytest.mark.asyncio
async def test_deterministic_embedding_provider():
    """Verifies that DeterministicEmbeddingProvider generates stable unit-normalized vectors."""
    provider = DeterministicEmbeddingProvider(dimension=128)
    assert provider.dimension == 128
    assert await provider.is_available() is True

    text_a = "LOVE personal assistant"
    text_b = "LOVE personal assistant"
    text_c = "Completely different content about astrophysics"

    vec_a = await provider.embed(text_a)
    vec_b = await provider.embed(text_b)
    vec_c = await provider.embed(text_c)

    assert len(vec_a) == 128
    # Exact deterministic identity
    assert vec_a == vec_b
    assert vec_a != vec_c

    # Verify L2 unit norm
    norm_a = math.sqrt(sum(x * x for x in vec_a))
    assert math.isclose(norm_a, 1.0, rel_tol=1e-5)


@pytest.mark.asyncio
async def test_gemini_embedding_privacy_gating():
    """Verifies that Gemini embeddings are disabled when cloud embeddings are not permitted."""
    settings_no_cloud = Settings(
        MEMORY_ALLOW_CLOUD_EMBEDDINGS=False,
        LOCAL_ONLY_MODE=False,
    )
    provider_blocked = GeminiEmbeddingProvider(settings=settings_no_cloud)
    assert await provider_blocked.is_available() is False

    settings_local_only = Settings(
        MEMORY_ALLOW_CLOUD_EMBEDDINGS=True,
        LOCAL_ONLY_MODE=True,
    )
    provider_local_blocked = GeminiEmbeddingProvider(settings=settings_local_only)
    assert await provider_local_blocked.is_available() is False


@pytest.mark.asyncio
async def test_embedding_manager_fallback():
    """Verifies that EmbeddingManager falls back to Deterministic provider when primary is unavailable."""
    settings = Settings(
        MEMORY_EMBEDDING_PROVIDER="ollama",
        MEMORY_OLLAMA_EMBEDDING_MODEL="nonexistent-model",
        MEMORY_ALLOW_CLOUD_EMBEDDINGS=False,
    )
    manager = EmbeddingManager(settings=settings)

    # Mock Ollama provider availability check to return False
    with patch.object(OllamaEmbeddingProvider, "is_available", new_callable=AsyncMock) as mock_avail:
        mock_avail.return_value = False
        active = await manager.get_active_provider()
        assert isinstance(active, DeterministicEmbeddingProvider)

        vec = await manager.embed_text("Test fallback embedding generation")
        assert len(vec) == 128


# ============================================================================
# 4. Local Vector Store Tests
# ============================================================================

@pytest.mark.asyncio
async def test_local_vector_store_crud_and_isolation(tmp_path):
    """Verifies vector upsert, cosine search, count, deletion, and multi-user isolation."""
    store = LocalVectorStore(storage_dir=str(tmp_path))

    user_a = "user-alpha"
    user_b = "user-beta"

    # User A records
    vec_1 = [1.0, 0.0, 0.0]
    vec_2 = [0.0, 1.0, 0.0]
    vec_3 = [0.707, 0.707, 0.0]

    await store.upsert("v1", vec_1, {"category": "personal"}, user_id=user_a)
    await store.upsert("v2", vec_2, {"category": "project"}, user_id=user_a)
    await store.upsert("v3", vec_3, {"category": "personal"}, user_id=user_a)

    # User B record
    await store.upsert("vb1", vec_1, {"category": "personal"}, user_id=user_b)

    assert store.count(user_a) == 3
    assert store.count(user_b) == 1

    # Search for user A
    query_vec = [1.0, 0.0, 0.0]
    results = await store.search(query_vec, user_id=user_a, top_k=2)
    assert len(results) == 2
    assert results[0][0] == "v1"
    assert math.isclose(results[0][1], 1.0, rel_tol=1e-4)

    # Verify user isolation: User B's record vb1 is never returned for User A
    user_a_all = await store.search(query_vec, user_id=user_a, top_k=10)
    returned_ids = [r[0] for r in user_a_all]
    assert "vb1" not in returned_ids

    # Delete record
    del_res = await store.delete("v1", user_id=user_a)
    assert del_res is True
    assert store.count(user_a) == 2

    # Clear user A
    await store.clear(user_id=user_a)
    assert store.count(user_a) == 0
    # User B still has their record
    assert store.count(user_b) == 1


# ============================================================================
# 5. Hybrid Retrieval Engine Tests
# ============================================================================

@pytest.mark.asyncio
async def test_hybrid_retrieval_ranking_and_isolation(test_db_session, tmp_path):
    """
    Verifies that MemoryRetrievalEngine performs hybrid semantic + lexical scoring,
    applies importance and recency boosts, and enforces strict user isolation.
    """
    vector_store = LocalVectorStore(storage_dir=str(tmp_path))
    deterministic_embedder = DeterministicEmbeddingProvider(dimension=128)
    embedding_manager = EmbeddingManager(
        primary_provider=deterministic_embedder,
        settings=Settings(MEMORY_ALLOW_CLOUD_EMBEDDINGS=False)
    )

    retrieval_engine = MemoryRetrievalEngine(
        vector_store=vector_store,
        embedding_manager=embedding_manager,
    )

    user_1 = "owner-001"
    user_2 = "owner-002"

    # Seed User 1 memories
    mem1 = Memory(
        id="mem-1",
        user_id=user_1,
        category=MemoryCategory.PROJECT.value,
        content="LOVE is an independent personal AI assistant using FastAPI and SQLite.",
        importance=5,
        confidence=1.0,
        source_type="user",
        tags_json='["fastapi", "sqlite", "love"]',
        is_archived=False,
    )
    mem2 = Memory(
        id="mem-2",
        user_id=user_1,
        category=MemoryCategory.PERSONAL.value,
        content="I prefer concise Indian English spoken phrasing.",
        importance=3,
        confidence=0.9,
        source_type="user",
        tags_json='["persona", "voice"]',
        is_archived=False,
    )
    # Seed User 2 memory
    mem3 = Memory(
        id="mem-3",
        user_id=user_2,
        category=MemoryCategory.PROJECT.value,
        content="LOVE project confidential architectural notes for owner 2.",
        importance=5,
        confidence=1.0,
        source_type="user",
        tags_json='["fastapi"]',
        is_archived=False,
    )

    test_db_session.add_all([mem1, mem2, mem3])
    await test_db_session.commit()

    # Index vectors
    vec1 = await deterministic_embedder.embed(mem1.content)
    vec2 = await deterministic_embedder.embed(mem2.content)
    vec3 = await deterministic_embedder.embed(mem3.content)
    await vector_store.upsert(mem1.id, vec1, {"category": mem1.category}, user_id=user_1)
    await vector_store.upsert(mem2.id, vec2, {"category": mem2.category}, user_id=user_1)
    await vector_store.upsert(mem3.id, vec3, {"category": mem3.category}, user_id=user_2)

    # Search for User 1: "What database does LOVE use?"
    search_req = MemorySearchRequest(
        query="What database does LOVE use with FastAPI?",
        top_k=5,
        min_score=0.1,
    )
    results_user_1 = await retrieval_engine.search(
        db=test_db_session,
        user_id=user_1,
        request=search_req,
    )

    assert len(results_user_1) >= 1
    top_result = results_user_1[0]
    assert top_result.memory.id == "mem-1"
    assert "FastAPI" in top_result.memory.content
    assert top_result.lexical_score > 0.0

    # Strict isolation check: User 2's memory mem-3 MUST NEVER appear in User 1's results
    retrieved_ids = [r.memory.id for r in results_user_1]
    assert "mem-3" not in retrieved_ids


# ============================================================================
# 6. Memory Suggestion & Consent Lifecycle Tests (Phase 04.5)
# ============================================================================

@pytest.mark.asyncio
async def test_suggestion_lifecycle_approval_and_rejection(test_db_session, tmp_path):
    """
    Verifies the complete suggestion consent lifecycle:
    - Independent facts become pending suggestions.
    - Pending suggestions are NOT permanent memories and NOT indexed in vector store.
    - Rejection marks suggestion as rejected and never saves to memory.
    - Approval converts suggestion to permanent canonical memory and indexes vector.
    """
    from backend.app.memory.service import MemoryService
    from backend.app.memory.schemas import MemoryExtractionCandidate, SuggestionStatus

    store = LocalVectorStore(storage_dir=str(tmp_path))
    service = MemoryService(vector_store=store)

    user_id = "consent-owner-001"

    # 1. Create a pending suggestion
    candidate_1 = MemoryExtractionCandidate(
        content="User frequently works with async SQLite database transactions.",
        category=MemoryCategory.PROJECT,
        confidence=0.88,
        importance=4,
        source_statement="We decided to use async SQLite.",
        needs_approval=True,
        reasoning="Project architectural observation.",
    )
    sug_1 = await service.create_suggestion(
        db=test_db_session,
        user_id=user_id,
        candidate=candidate_1,
        source_id="conv-123",
    )
    assert sug_1.status == SuggestionStatus.PENDING
    assert sug_1.content == candidate_1.content

    # Confirm it is NOT in vector store
    assert store.count(user_id=user_id) == 0

    # Confirm it is NOT in permanent memories
    memories = await service.list_memories(db=test_db_session, user_id=user_id)
    assert len(memories) == 0

    # 2. Reject suggestion
    rejected_sug = await service.reject_suggestion(
        db=test_db_session,
        suggestion_id=sug_1.id,
        user_id=user_id,
    )
    assert rejected_sug.status == SuggestionStatus.REJECTED
    # Vector store remains 0
    assert store.count(user_id=user_id) == 0
    # Permanent memories remains 0
    memories = await service.list_memories(db=test_db_session, user_id=user_id)
    assert len(memories) == 0

    # 3. Create a second suggestion and APPROVE it
    candidate_2 = MemoryExtractionCandidate(
        content="User prefers strict Python typing with Pydantic V2.",
        category=MemoryCategory.PERSONAL,
        confidence=0.92,
        importance=5,
        source_statement="My preference is strict typing with Pydantic V2.",
        needs_approval=True,
        reasoning="Coding preference observation.",
    )
    sug_2 = await service.create_suggestion(
        db=test_db_session,
        user_id=user_id,
        candidate=candidate_2,
    )
    assert sug_2.status == SuggestionStatus.PENDING

    # Approve suggestion
    approved_memory = await service.approve_suggestion(
        db=test_db_session,
        suggestion_id=sug_2.id,
        user_id=user_id,
    )
    assert approved_memory.content == candidate_2.content
    assert approved_memory.category == MemoryCategory.PERSONAL

    # Now it IS in canonical permanent memories!
    memories = await service.list_memories(db=test_db_session, user_id=user_id)
    assert len(memories) == 1
    assert memories[0].id == approved_memory.id

    # And it IS indexed in the vector store!
    assert store.count(user_id=user_id) == 1

    # Verify retrieval
    search_res = await service.search_memories(
        db=test_db_session,
        user_id=user_id,
        request=MemorySearchRequest(query="What typing style does user prefer?", top_k=3),
    )
    assert len(search_res) >= 1
    assert search_res[0].memory.id == approved_memory.id

