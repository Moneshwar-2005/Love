# LOVE — Database Migration & Schema Evolution Guide

**Phase 10: Database Architecture, Integrity & Production Readiness**  
**Role:** Senior Database Architect, SQLAlchemy Engineer and Data Reliability Specialist  
**Tooling:** Alembic & SQLAlchemy Async  
**Current Migration Head:** `c0e81b379d42`  

---

## 1. Alembic Architecture & Configuration

LOVE manages schema evolutions using Alembic configured for asynchronous database engines (`sqlite+aiosqlite` and future `postgresql+asyncpg`).

### Configuration Structure
- `alembic.ini`: Primary configuration defining script locations and logging.
- `database/migrations/env.py`: Execution environment. Imports all SQLAlchemy models via `backend.app.database.models` so `target_metadata = Base.metadata` accurately tracks all domain entities.
- `render_as_batch=True`: Configured in `env.py` to support SQLite's table alter limitations by safely recreating tables with constraints during column or constraint alterations.

---

## 2. Complete Migration History Graph

The migration graph is strictly linear with a single head:

```text
  05fabba69f6e (Base: Users, UserCredentials, Devices, RefreshTokenSessions)
       │
       ▼
  b272d69a2753 (Conversations, Messages)
       │
       ▼
  7083324f0a93 (Memories, MemoryAuditLogs)
       │
       ▼
  deddca6e0023 (MemorySuggestions)
       │
       ▼
  322b6c8a37b0 (Tasks, TaskActions)
       │
       ▼
  a30798731d0a (SyncEvents, UserSyncSettings, DeviceSyncCursors)
       │
       ▼
  c0e81b379d42 [HEAD] (Performance Composite Indexes & Sync Cursor Index Hardening)
```

### Detailed Revision Ledger

| Revision ID | Parent Revision | Description & Key Schema Additions |
| :--- | :--- | :--- |
| `05fabba69f6e` | `<base>` | Initial authentication and device architecture: `users`, `user_credentials`, `devices`, `refresh_token_sessions`. |
| `b272d69a2753` | `05fabba69f6e` | Universal Intelligence conversation layer: `conversations`, `messages`. Foreign keys to `users.id` with `ON DELETE CASCADE`. |
| `7083324f0a93` | `b272d69a2753` | Persistent Personal Memory: `memories`, `memory_audit_logs`. Added indexes on category, archived state, and access frequency. |
| `deddca6e0023` | `7083324f0a93` | Memory suggestion queue: `memory_suggestions` table with extraction status (`pending`, `approved`, `rejected`). |
| `322b6c8a37b0` | `deddca6e0023` | Universal Work Intelligence: `tasks`, `task_actions`. Added `conversation_id` with `ON DELETE SET NULL` and action idempotency keys. |
| `a30798731d0a` | `322b6c8a37b0` | Cross-Device Synchronization: `sync_events` with integer sequence cursor, `user_sync_settings`, and `device_sync_cursors`. |
| `c0e81b379d42` | `a30798731d0a` | Database hardening: added composite indexes `ix_messages_conv_created`, `ix_tasks_user_status`, `ix_memories_user_archived`, and verified `ix_sync_events_user_cursor`. |

---

## 3. Migration Commands & Workflows

### 3.1 Check Current Revision Status
```powershell
.venv\Scripts\alembic current
```
**Expected Output:**
```text
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
c0e81b379d42 (head)
```

### 3.2 View Migration History
```powershell
.venv\Scripts\alembic history --verbose
```

### 3.3 Upgrade to Latest Head
```powershell
.venv\Scripts\alembic upgrade head
```

### 3.4 Rollback (Downgrade)
To rollback the latest migration:
```powershell
.venv\Scripts\alembic downgrade -1
```
To rollback to a specific revision (e.g. `a30798731d0a`):
```powershell
.venv\Scripts\alembic downgrade a30798731d0a
```

---

## 4. Development Best Practices for New Migrations

1. **Never edit applied migrations**: Once a migration has been applied or committed, create a new forward migration rather than altering historical files.
2. **Never test migrations destructively on `database/love.db`**: Always test migrations using a temporary copy or isolated test database (`tempfile.mkdtemp()`).
3. **Always write reversible downgrades**: Every `upgrade()` function must have an exact inverse `downgrade()` function.
4. **Use Idempotent Index Checks**: When creating indexes on tables that might already exist in some environments, check if the index exists before invoking `create_index`.
5. **Preserve User Data**: Ensure foreign keys and nullable column additions specify defaults or nullable states so existing records are never invalidated or truncated.

---

## 5. Future PostgreSQL Migration Roadmap

When deploying LOVE with PostgreSQL in a multi-tenant enterprise or cloud setting:

1. **Connection String**: Change `DATABASE_URL` in `.env`:
   ```env
   DATABASE_URL=postgresql+asyncpg://love_user:secure_password@postgres_host:5432/love_db
   ```
2. **Execute Migrations**: Run Alembic against the new PostgreSQL database:
   ```powershell
   alembic upgrade head
   ```
   Alembic will automatically generate all tables, sequences (`SERIAL`), and indexes according to PostgreSQL DDL specifications.
3. **Data Transfer**:
   - Use a script (`scripts/migrate_sqlite_to_pg.py`) reading records from `database/love.db` in dependency order:
     1. `users`
     2. `user_credentials`
     3. `devices`
     4. `refresh_token_sessions`
     5. `conversations`
     6. `messages`
     7. `memories`
     8. `memory_audit_logs`
     9. `memory_suggestions`
     10. `tasks`
     11. `task_actions`
     12. `sync_events`
     13. `user_sync_settings`
     14. `device_sync_cursors`
   - Reset the PostgreSQL sequence for `sync_events.cursor`:
     ```sql
     SELECT setval('sync_events_cursor_seq', (SELECT max(cursor) FROM sync_events));
     ```
4. **Verification**: Execute `pytest tests/test_database_architecture.py` against the PostgreSQL database to confirm live compatibility.
