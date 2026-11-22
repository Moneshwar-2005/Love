# LOVE — Memory Architecture Specification (Phase 04)

This document specifies the persistent personal memory and vector retrieval architecture implemented for **LOVE** (Phase 04).

---

## 1. Architectural Philosophy

LOVE's memory system is designed as an **independent, durable cognitive layer**. 

Core design principles:
1. **Model Decoupling**: Memory exists independently of whichever language model is currently executing inference (Ollama, Gemini, OpenAI, Claude).
2. **Local-First & Privacy Preserving**:
   - Canonical memory records reside in SQLite on the user's host machine (`database/love.db`).
   - Vector indices are stored on the local filesystem (`database/vectors/`).
   - Personal memories are **never** transmitted to cloud embedding services without explicit user authorization (`MEMORY_ALLOW_CLOUD_EMBEDDINGS=False` by default).
   - Strict adherence to `LOCAL_ONLY_MODE`.
   - Sensitive credentials (passwords, API keys, private keys, payment cards, bearer tokens) are permanently blocked from memory persistence.
3. **Multi-Strategy Hybrid Retrieval**:
   - Dense semantic vector similarity (cosine metric).
   - Normalized token overlap and exact keyword/tag matching (lexical metric).
   - Recency decay over a 30-day half-life window.
   - User-defined importance boost (scale 1 to 5).
4. **Deterministic Resilience**:
   - Zero-dependency, zero-network fallback embedding engine (`DeterministicEmbeddingProvider`) generates stable 128-dimensional unit-norm vectors via token and n-gram feature hashing, ensuring memory functions even when local GPU neural embedding servers are offline.
5. **Rebuildability**:
   - The canonical SQLite database is the single source of truth. Vector indices can be wiped and completely rebuilt at any time via `POST /api/v1/memory/rebuild-index`.

```
                  +---------------------------------------------------+
                  |            Incoming User Message / Chat           |
                  +---------------------------------------------------+
                                            |
                         +------------------+------------------+
                         |                                     |
                         v                                     v
         +-------------------------------+     +-------------------------------+
         |     Memory Candidate Engine   |     |     Hybrid Retrieval Engine   |
         |  - Scans prompt for facts     |     |  - Queries semantic vectors   |
         |  - SensitiveDataSanitizer     |     |  - Lexical keyword match      |
         |  - Filters raw secrets        |     |  - Recency & importance boost |
         +-------------------------------+     +-------------------------------+
                         |                                     |
                         v                                     v
         +-------------------------------+     +-------------------------------+
         |   Deduplication & Storage     |     |       Context Manager         |
         |  - Deduplication check (0.85) |     |  - Injects <relevant_memories>|
         |  - Canonical SQLite write     |     |    into system prompt         |
         |  - Vector Index Upsert        |     +-------------------------------+
         |  - Audit Log write            |                     |
         +-------------------------------+                     v
                                               +-------------------------------+
                                               |     Model Router & LLM        |
                                               +-------------------------------+
```

---

## 2. Memory Categories

Memory is partitioned into four distinct operational categories:

| Category | Primary Scope | Typical Examples | Default Retention |
| :--- | :--- | :--- | :--- |
| `personal` | User preferences, communication style, facts | "I prefer dark mode", "My name is Moneshwar", "Keep responses concise" | Permanent |
| `project` | Technical decisions, repo details, architecture | "We use FastAPI and SQLite", "GTX 1650 4GB GPU limits", "Project name is LOVE" | Permanent |
| `conversational` | Multi-turn durable discussion facts | "We postponed Docker setup until Phase 06", "Task 3 was completed on Tuesday" | Dynamic / Expiring |
| `knowledge` | Domain guidelines, reference facts, algorithms | "KaTeX delimiters are $ and $$", "Alembic migrations head is 7083324f0a93" | Permanent |

---

## 3. Database Schema Design

The canonical data layer is backed by SQLite via SQLAlchemy 2.0 async ORM and tracked by Alembic migration revision `7083324f0a93`.

### 3.1 `memories` Table

| Column | Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `id` | VARCHAR(36) | No | Primary Key (UUID4) |
| `user_id` | VARCHAR(36) | No | Foreign Key -> `users.id` (ON DELETE CASCADE, Indexed) |
| `category` | VARCHAR(32) | No | Category enum (`personal`, `project`, `conversational`, `knowledge`, Indexed) |
| `content` | TEXT | No | Full natural language memory content |
| `summary` | VARCHAR(255)| Yes | Brief summary title |
| `source_type` | VARCHAR(32) | No | Source: `user`, `assistant`, `auto_extracted`, `system` |
| `source_id` | VARCHAR(64) | Yes | Optional originating message or conversation ID |
| `confidence` | FLOAT | No | Extraction confidence [0.0, 1.0] |
| `importance` | INTEGER | No | Priority weight 1 (trivial) to 5 (critical), default 3 (Indexed) |
| `tags_json` | TEXT | Yes | JSON-encoded string array (e.g. `["fastapi", "style"]`) |
| `metadata_json` | TEXT | Yes | JSON-encoded key-value dictionary |
| `is_archived` | BOOLEAN | No | Soft-delete / exclusion flag (default False, Indexed) |
| `access_count` | INTEGER | No | Number of times retrieved into prompt context |
| `last_accessed_at` | TIMESTAMP | Yes | Last time retrieved and injected into prompt |
| `created_at` | TIMESTAMP | No | Creation timestamp UTC (Indexed) |
| `updated_at` | TIMESTAMP | No | Last update timestamp UTC (Indexed) |

### 3.2 `memory_audit_logs` Table

Provides immutable auditability for memory modifications:

| Column | Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `id` | VARCHAR(36) | No | Primary Key (UUID4) |
| `user_id` | VARCHAR(36) | No | Foreign Key -> `users.id` (ON DELETE CASCADE, Indexed) |
| `memory_id` | VARCHAR(36) | Yes | Targeted memory ID (Indexed) |
| `action` | VARCHAR(32) | No | Action: `created`, `updated`, `deleted`, `archived`, `restored`, `cleared`, `reindexed` |
| `details_json` | TEXT | Yes | Detailed operation metadata |
| `created_at` | TIMESTAMP | No | Timestamp UTC (Indexed) |

---

## 4. Vector Storage Subsystem

### 4.1 Interface Contract (`BaseVectorStore`)

```python
class BaseVectorStore(ABC):
    async def upsert(self, vector_id: str, vector: List[float], metadata: dict, user_id: str) -> bool
    async def search(self, query_vector: List[float], user_id: str, top_k: int = 5, min_score: float = 0.0, filter_category: Optional[str] = None) -> List[Tuple[str, float]]
    async def delete(self, vector_id: str, user_id: str) -> bool
    async def clear(self, user_id: str) -> bool
    def count(self, user_id: str) -> int
    async def rebuild(self, records: List[Tuple[str, List[float], dict, str]]) -> int
```

### 4.2 Backends

1. **`LocalVectorStore` (Default)**:
   - High-performance, user-partitioned vector index stored on disk in `database/vectors/{user_id}.json`.
   - Computes cosine similarity across stored vectors in parallel using vectorized NumPy operations:
     $$\text{cosine\_similarity}(\mathbf{u}, \mathbf{v}) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \|\mathbf{v}\|_2}$$
   - Zero daemon requirement, zero network overhead, sub-millisecond retrieval latency for personal assistant workloads.
2. **`QdrantVectorStore` (Pluggable)**:
   - Client wrapper for local or remote Qdrant instances.
   - Gracefully falls back to `LocalVectorStore` if `qdrant-client` is not installed in the Python environment.

---

## 5. Embedding Provider Abstraction

The embedding layer decouples memory representation from any specific LLM or cloud API.

| Provider | Type | Dimensions | Characteristics |
| :--- | :--- | :--- | :--- |
| `DeterministicEmbeddingProvider` | Local / Offline | 128 | Feature hashing on word tokens & trigrams; 100% deterministic; zero network; L2 unit normalized. |
| `OllamaEmbeddingProvider` | Local Neural | Model-dependent (e.g. 1536 / 3584) | Communicates with local Ollama (`qwen2.5:1.5b` or custom embedding models). |
| `GeminiEmbeddingProvider` | Cloud Neural | 768 | Google Gemini `text-embedding-004`. Strictly blocked unless `MEMORY_ALLOW_CLOUD_EMBEDDINGS=True` and `LOCAL_ONLY_MODE=False`. |

### Embedding Fallback Hierarchy

The `EmbeddingManager` coordinates provider selection:
1. Provider specified by `MEMORY_EMBEDDING_PROVIDER` (if available and allowed).
2. Local Ollama instance if active and serving an embedding model.
3. Cloud Gemini API (only if explicitly permitted by configuration).
4. `DeterministicEmbeddingProvider` (guaranteed, zero-failure fallback).

---

## 6. Privacy & Sensitive Data Protection

### 6.1 `SensitiveDataSanitizer`

Before any memory candidate is accepted or persisted, it is inspected by the `SensitiveDataSanitizer`:
- **API Keys & Secrets**: OpenAI (`sk-...`), Anthropic (`sk-ant-...`), Google API (`AIzaSy...`), GitHub tokens (`ghp_...`, `gho_...`), AWS credentials (`AWS_SECRET_ACCESS_KEY`), and generic high-entropy secret patterns.
- **Passwords**: Explicit password patterns (`password = "..."`, `my password is ...`).
- **Private Key Blocks**: PEM headers (`-----BEGIN RSA PRIVATE KEY-----`, etc.).
- **Credit Card Numbers**: Validated 16-digit payment card sequences.
- **Bearer Tokens**: JWT signatures (`eyJ...`) and raw HTTP bearer tokens.

Any payload triggering these patterns raises `SensitiveDataBlockedError` (HTTP 400) and is refused entry into the permanent memory store.

### 6.2 Cloud Privacy Boundaries

```python
if settings.LOCAL_ONLY_MODE or not settings.MEMORY_ALLOW_CLOUD_EMBEDDINGS:
    # Cloud embedding APIs are completely disabled.
    # Memories are NEVER sent off-device.
```

---

## 7. Hybrid Memory Retrieval Algorithm

When LOVE retrieves memories for an incoming user query:

1. **Semantic Search**: The query text is converted to a vector embedding, and `LocalVectorStore.search` calculates cosine similarity scores $S_{\text{semantic}} \in [0.0, 1.0]$.
2. **Lexical Matching**: Tokenized Jaccard overlap between the query and canonical memory text and tags produces $S_{\text{lexical}} \in [0.0, 1.0]$.
3. **Importance Boost**: Memory importance (1 to 5) scales linearly:
   $$S_{\text{importance}} = \frac{\text{importance}}{5.0} \in [0.2, 1.0]$$
4. **Recency Decay**: Linear decay over a 30-day half-life:
   $$S_{\text{recency}} = \max\left(0.0, 1.0 - \frac{\text{age\_in\_days}}{30.0}\right)$$
5. **Dynamic Blended Score**:
   - If semantic vectors are available:
     $$\text{Score} = 0.55 \cdot S_{\text{semantic}} + 0.25 \cdot S_{\text{lexical}} + 0.15 \cdot S_{\text{importance}} + 0.05 \cdot S_{\text{recency}}$$
   - If semantic vectors are offline (lexical fallback mode):
     $$\text{Score} = 0.75 \cdot S_{\text{lexical}} + 0.20 \cdot S_{\text{importance}} + 0.05 \cdot S_{\text{recency}}$$
6. **Filtering**: Results where $\text{Score} \ge \text{MEMORY\_RETRIEVAL\_MIN\_SCORE}$ (default 0.30) are ranked and the top $K$ (default 5) are retrieved.
7. **Access Updating**: In SQLite, `access_count` increments and `last_accessed_at` updates to the current timestamp.

---

## 8. Intelligence Layer Context Injection

In `backend/app/intelligence/context.py` and `backend/app/intelligence/orchestrator.py`:

Retrieved memories are injected directly into the LLM system prompt:

```xml
<relevant_memories>
The following persistent personal memories and project contexts were retrieved based on the user's prompt. Use them naturally to maintain continuity, personal preferences, and accurate context without quoting internal IDs or metadata unless asked:
- [PERSONAL] User prefers concise Python code with strict typing and docstrings.
- [PROJECT] LOVE personal assistant runs on a GTX 1650 4GB GPU using Ollama local models.
</relevant_memories>
```

This ensures LOVE maintains cross-conversation continuity and naturally honors the owner's preferences without needing manual reminder prompts.

---

## 9. API Reference

All endpoints are mounted under `/api/v1/memory` and require Bearer token authentication.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/memory` | Create a new memory record (enforces sanitization & deduplication). |
| `GET` | `/api/v1/memory` | List memories with pagination and filters (`category`, `tag`, `is_archived`). |
| `GET` | `/api/v1/memory/{id}` | Retrieve individual memory by ID (enforces user isolation). |
| `PUT` | `/api/v1/memory/{id}` | Update memory content, tags, or metadata (re-indexes vector). |
| `DELETE` | `/api/v1/memory/{id}` | Permanently delete memory and vector record. |
| `POST` | `/api/v1/memory/search` | Execute hybrid semantic + lexical search. |
| `POST` | `/api/v1/memory/{id}/archive` | Archive memory (exclude from active retrieval). |
| `POST` | `/api/v1/memory/{id}/restore` | Restore archived memory back to active retrieval. |
| `GET` | `/api/v1/memory/stats` | Retrieve memory counts, category breakdown, and embedding provider status. |
| `POST` | `/api/v1/memory/rebuild-index` | Rebuild vector index from canonical SQLite records. |
| `GET` | `/api/v1/memory/export` | Export all user memories in JSON format for backup. |
| `POST` | `/api/v1/memory/import` | Import memories from JSON backup. |
| `DELETE` | `/api/v1/memory/clear` | Clear memories (requires `?confirm=true`, optionally scoped to category). |
