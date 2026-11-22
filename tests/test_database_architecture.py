"""
Phase 10 Comprehensive Database Architecture, Integrity & Reliability Test Suite.
Tests:
 1. Fresh SQLite initialization
 2. Existing database upgrade
 3. Migration upgrade and downgrade
 4. Foreign-key enforcement
 5. Transaction rollback
 6. Concurrent writes & reads (WAL mode + busy timeout)
 7. Database restart persistence
 8. Backup creation (online backup API)
 9. Backup integrity verification
10. Restore into a separate database copy
11. Owner data isolation
12. Cascade behaviour & historical preservation (ON DELETE SET NULL vs CASCADE)
13. Index and query performance (EXPLAIN QUERY PLAN)
14. Vector dimension verification (128-d deterministic vs 768-d Gemini)
15. PostgreSQL static compatibility (DDL compilation & dialect types)
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.schema import CreateIndex, CreateTable

from alembic.config import Config
from alembic import command

from backend.app.config.settings import Settings, get_settings
from backend.app.database.base import Base
import backend.app.database.models  # Register all models on Base.metadata
from backend.app.database.models.conversation import Conversation, Message
from backend.app.database.models.device import Device
from backend.app.database.models.memory import Memory, MemoryAuditLog
from backend.app.database.models.session import RefreshTokenSession
from backend.app.database.models.sync import DeviceSyncCursor, SyncEvent, UserSyncSettings
from backend.app.database.models.task import Task, TaskAction
from backend.app.database.models.user import User, UserCredential
from backend.app.database.backup import (
    create_database_backup,
    list_database_backups,
    restore_database_backup,
    verify_database_backup,
)
from backend.app.memory.embeddings.deterministic import DeterministicEmbeddingProvider
from backend.app.memory.embeddings.gemini import GeminiEmbeddingProvider
from backend.app.memory.vector_store.local_store import LocalVectorStore


@pytest.fixture
def temp_db_env():
    """Provides an isolated directory for temporary SQLite databases."""
    temp_dir = tempfile.mkdtemp()
    db_file = os.path.join(temp_dir, "test_isolated.db").replace("\\", "/")
    yield temp_dir, db_file
    time.sleep(0.3)
    try:
        shutil.rmtree(temp_dir)
    except Exception:
        pass


# ==============================================================================
# 1. Fresh SQLite Initialization
# ==============================================================================
def test_fresh_sqlite_initialization(temp_db_env):
    """Verifies fresh database initialization creates all 14 domain tables."""
    temp_dir, db_file = temp_db_env
    engine = create_engine(f"sqlite:///{db_file}")

    Base.metadata.create_all(bind=engine)
    insp = inspect(engine)
    tables = insp.get_table_names()

    expected_tables = {
        "users", "user_credentials", "devices", "refresh_token_sessions",
        "conversations", "messages", "memories", "memory_audit_logs",
        "memory_suggestions", "tasks", "task_actions", "sync_events",
        "user_sync_settings", "device_sync_cursors",
    }
    for tbl in expected_tables:
        assert tbl in tables, f"Expected table {tbl} missing from fresh initialization"

    engine.dispose()


# ==============================================================================
# 2. Existing Database Upgrade
# ==============================================================================
def test_existing_database_upgrade(temp_db_env):
    """Verifies upgrading from a previous revision to head preserves all existing records."""
    temp_dir, db_file = temp_db_env

    # Setup database at a30798731d0a
    cfg = Config(r"F:\LOVE\alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file}")
    command.upgrade(cfg, "a30798731d0a")

    # Insert seeded records
    con = sqlite3.connect(db_file)
    con.execute("""
        INSERT INTO users (id, email, username, is_active, is_verified, is_owner, created_at, updated_at)
        VALUES ('u_seed', 'seed@love.ai', 'seeduser', 1, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
    """)
    con.execute("""
        INSERT INTO conversations (id, user_id, title, is_pinned, is_archived, created_at, updated_at)
        VALUES ('c_seed', 'u_seed', 'Seeded Chat', 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
    """)
    con.commit()
    con.close()

    # Upgrade to head (c0e81b379d42)
    command.upgrade(cfg, "head")

    # Verify head revision and records preserved
    con2 = sqlite3.connect(db_file)
    rev = con2.execute("SELECT version_num FROM alembic_version;").fetchone()[0]
    assert rev == "c0e81b379d42"

    user_row = con2.execute("SELECT email, username FROM users WHERE id = 'u_seed';").fetchone()
    assert user_row == ("seed@love.ai", "seeduser")

    conv_row = con2.execute("SELECT title FROM conversations WHERE id = 'c_seed';").fetchone()
    assert conv_row == ("Seeded Chat",)

    # Check composite indexes present
    msg_idxs = [r[1] for r in con2.execute("PRAGMA index_list(messages);").fetchall()]
    assert "ix_messages_conv_created" in msg_idxs
    con2.close()


# ==============================================================================
# 3. Migration Upgrade and Downgrade
# ==============================================================================
def test_migration_upgrade_and_downgrade(temp_db_env):
    """Verifies clean reversible upgrade and downgrade operations."""
    temp_dir, db_file = temp_db_env
    cfg = Config(r"F:\LOVE\alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file}")

    # 1. Upgrade from base to head
    command.upgrade(cfg, "head")
    con = sqlite3.connect(db_file)
    assert con.execute("SELECT version_num FROM alembic_version;").fetchone()[0] == "c0e81b379d42"
    con.close()

    # 2. Downgrade to pre-Phase-10 head (a30798731d0a)
    command.downgrade(cfg, "a30798731d0a")
    con2 = sqlite3.connect(db_file)
    assert con2.execute("SELECT version_num FROM alembic_version;").fetchone()[0] == "a30798731d0a"
    idxs = [r[1] for r in con2.execute("PRAGMA index_list(messages);").fetchall()]
    assert "ix_messages_conv_created" not in idxs
    con2.close()

    # 3. Re-upgrade to head
    command.upgrade(cfg, "head")
    con3 = sqlite3.connect(db_file)
    assert con3.execute("SELECT version_num FROM alembic_version;").fetchone()[0] == "c0e81b379d42"
    con3.close()


# ==============================================================================
# 4. Foreign Key Enforcement
# ==============================================================================
def test_foreign_key_enforcement(temp_db_env):
    """Verifies SQLite strictly rejects orphaned child records when foreign_keys=ON."""
    temp_dir, db_file = temp_db_env
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(bind=engine)
    engine.dispose()

    con = sqlite3.connect(db_file)
    con.execute("PRAGMA foreign_keys = ON;")

    # Attempt inserting conversation with non-existent user_id
    with pytest.raises(sqlite3.IntegrityError) as exc_info:
        con.execute("""
            INSERT INTO conversations (id, user_id, title, is_pinned, is_archived, created_at, updated_at)
            VALUES ('c_bad', 'non_existent_user', 'Bad Conv', 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
        """)
    assert "FOREIGN KEY constraint failed" in str(exc_info.value)
    con.close()


# ==============================================================================
# 5. Transaction Rollback
# ==============================================================================
def test_transaction_rollback(temp_db_env):
    """Verifies uncommitted or errored transactions rollback completely."""
    temp_dir, db_file = temp_db_env
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(bind=engine)

    con = sqlite3.connect(db_file)
    con.execute("PRAGMA foreign_keys = ON;")

    # Insert valid user
    con.execute("""
        INSERT INTO users (id, email, username, is_active, is_verified, is_owner, created_at, updated_at)
        VALUES ('u_valid', 'valid@love.ai', 'validuser', 1, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
    """)
    con.commit()

    # Start atomic block that fails mid-way
    try:
        con.execute("BEGIN TRANSACTION;")
        con.execute("""
            INSERT INTO memories (id, user_id, category, content, source_type, confidence, importance, tags_json, metadata_json, is_archived, access_count)
            VALUES ('mem_1', 'u_valid', 'project', 'Valid memory', 'explicit_user', 1.0, 3, '[]', '{}', 0, 0);
        """)
        # Deliberate failure: foreign key violation
        con.execute("""
            INSERT INTO memories (id, user_id, category, content, source_type, confidence, importance, tags_json, metadata_json, is_archived, access_count)
            VALUES ('mem_2', 'ghost_user', 'project', 'Invalid memory', 'explicit_user', 1.0, 3, '[]', '{}', 0, 0);
        """)
        con.commit()
    except sqlite3.IntegrityError:
        con.rollback()

    # Verify mem_1 was rolled back and does not exist
    count = con.execute("SELECT count(*) FROM memories;").fetchone()[0]
    assert count == 0, "Partial transaction must be completely rolled back"
    con.close()
    engine.dispose()


# ==============================================================================
# 6. Concurrent Writes & Reads (WAL Mode & Busy Timeout)
# ==============================================================================
def test_concurrent_writes_and_reads(temp_db_env):
    """Verifies concurrent writers and readers operate without lock contention under WAL mode."""
    temp_dir, db_file = temp_db_env
    con = sqlite3.connect(db_file)
    con.execute("PRAGMA journal_mode = WAL;")
    con.execute("PRAGMA busy_timeout = 10000;")
    con.execute("CREATE TABLE counter (id INTEGER PRIMARY KEY, value INTEGER, writer TEXT);")
    con.execute("INSERT INTO counter VALUES (1, 0, 'init');")
    con.commit()
    con.close()

    errors = []
    writes_done = 0
    reads_done = 0

    def writer_task(writer_id: int):
        nonlocal writes_done
        try:
            c = sqlite3.connect(db_file, timeout=10.0)
            c.execute("PRAGMA busy_timeout = 10000;")
            for i in range(25):
                c.execute("UPDATE counter SET value = value + 1, writer = ? WHERE id = 1;", (f"w{writer_id}",))
                c.commit()
                writes_done += 1
                time.sleep(0.002)
            c.close()
        except Exception as exc:
            errors.append((f"writer_{writer_id}", str(exc)))

    def reader_task(reader_id: int):
        nonlocal reads_done
        try:
            c = sqlite3.connect(db_file, timeout=10.0)
            c.execute("PRAGMA busy_timeout = 10000;")
            for i in range(40):
                row = c.execute("SELECT value FROM counter WHERE id = 1;").fetchone()
                assert row is not None
                reads_done += 1
                time.sleep(0.001)
            c.close()
        except Exception as exc:
            errors.append((f"reader_{reader_id}", str(exc)))

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = []
        for r in range(4):
            futures.append(pool.submit(reader_task, r))
        for w in range(4):
            futures.append(pool.submit(writer_task, w))
        for f in futures:
            f.result()

    assert len(errors) == 0, f"Concurrent operations encountered errors: {errors}"
    assert writes_done == 100

    check_conn = sqlite3.connect(db_file)
    final_val = check_conn.execute("SELECT value FROM counter WHERE id = 1;").fetchone()[0]
    check_conn.close()
    assert final_val == 100


# ==============================================================================
# 7. Database Restart Persistence
# ==============================================================================
def test_database_restart_persistence(temp_db_env):
    """Verifies cold restarts re-read persisted data reliably across process boundaries."""
    temp_dir, db_file = temp_db_env

    # 1. First session
    engine1 = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(bind=engine1)
    with engine1.connect() as conn:
        conn.execute(text("""
            INSERT INTO users (id, email, username, is_active, is_verified, is_owner)
            VALUES ('u_persist', 'persist@love.ai', 'persistent', 1, 1, 1);
        """))
        conn.commit()
    engine1.dispose()

    # 2. Simulate cold restart: fresh connection handle
    engine2 = create_engine(f"sqlite:///{db_file}")
    with engine2.connect() as conn2:
        row = conn2.execute(text("SELECT email, username FROM users WHERE id = 'u_persist';")).fetchone()
        assert row is not None
        assert row[0] == "persist@love.ai"
        assert row[1] == "persistent"
    engine2.dispose()


# ==============================================================================
# 8. Backup Creation
# ==============================================================================
def test_backup_creation(temp_db_env):
    """Verifies atomic backup creation with SQLite online backup API."""
    temp_dir, db_file = temp_db_env
    backup_dir = Path(temp_dir) / "backups"

    # Seed test database
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO users (id, email, username, is_active, is_verified, is_owner)
            VALUES ('u_bak', 'bak@love.ai', 'bakuser', 1, 1, 1);
        """))
        conn.commit()
    engine.dispose()

    meta = create_database_backup(
        source_db_path=Path(db_file),
        backup_dir=backup_dir,
    )

    assert meta["is_valid"] is True
    assert meta["integrity_status"] == "ok"
    assert Path(meta["backup_path"]).exists()
    assert meta["size_bytes"] > 0
    assert len(meta["sha256"]) == 64


# ==============================================================================
# 9. Backup Integrity Verification
# ==============================================================================
def test_backup_integrity_verification(temp_db_env):
    """Verifies corrupted backups fail integrity validation."""
    temp_dir, db_file = temp_db_env
    backup_dir = Path(temp_dir) / "backups"

    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(bind=engine)
    engine.dispose()

    meta = create_database_backup(source_db_path=Path(db_file), backup_dir=backup_dir)
    bak_path = Path(meta["backup_path"])

    # 1. Valid backup verification
    is_valid, msg, insp = verify_database_backup(bak_path)
    assert is_valid is True
    assert msg == "ok"
    assert insp["integrity_ok"] is True

    # 2. Corrupt backup verification
    corrupt_path = Path(temp_dir) / "corrupt.db"
    with open(corrupt_path, "wb") as f:
        f.write(b"NOT A SQLITE FILE GARBAGE BYTES DATA")

    is_c_valid, c_msg, _ = verify_database_backup(corrupt_path)
    assert is_c_valid is False
    assert "file is not a database" in c_msg.lower() or "integrity" in c_msg.lower() or "error" in c_msg.lower()


# ==============================================================================
# 10. Restore into Separate Database
# ==============================================================================
def test_restore_into_separate_database(temp_db_env):
    """Verifies restoring into a separate target database restores all tables and records."""
    temp_dir, db_file = temp_db_env
    backup_dir = Path(temp_dir) / "backups"

    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO users (id, email, username, is_active, is_verified, is_owner)
            VALUES ('u_restored', 'restored@love.ai', 'restoreuser', 1, 1, 1);
        """))
        conn.commit()
    engine.dispose()

    meta = create_database_backup(source_db_path=Path(db_file), backup_dir=backup_dir)

    target_restore_db = Path(temp_dir) / "restored_destination.db"
    res = restore_database_backup(
        backup_path=Path(meta["backup_path"]),
        target_path=target_restore_db,
    )

    assert res["success"] is True
    assert target_restore_db.exists()

    # Query restored target
    con = sqlite3.connect(str(target_restore_db))
    user_row = con.execute("SELECT email, username FROM users WHERE id = 'u_restored';").fetchone()
    con.close()

    assert user_row == ("restored@love.ai", "restoreuser")


# ==============================================================================
# 11. Owner Data Isolation
# ==============================================================================
def test_owner_data_isolation(temp_db_env):
    """Verifies multi-user queries cannot leak or access another user's records."""
    temp_dir, db_file = temp_db_env
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO users (id, email, username, is_active, is_verified, is_owner)
            VALUES ('user_a', 'alice@love.ai', 'alice', 1, 1, 1),
                   ('user_b', 'bob@love.ai', 'bob', 1, 1, 0);
        """))
        conn.execute(text("""
            INSERT INTO memories (id, user_id, category, content, source_type, confidence, importance, tags_json, metadata_json, is_archived, access_count)
            VALUES ('mem_alice', 'user_a', 'personal', 'Alice secret note', 'explicit_user', 1.0, 5, '[]', '{}', 0, 0),
                   ('mem_bob', 'user_b', 'personal', 'Bob secret note', 'explicit_user', 1.0, 5, '[]', '{}', 0, 0);
        """))
        conn.commit()

        # Query isolated to user_a
        alice_mems = conn.execute(text("SELECT content FROM memories WHERE user_id = 'user_a';")).fetchall()
        assert len(alice_mems) == 1
        assert alice_mems[0][0] == "Alice secret note"

        # Query isolated to user_b
        bob_mems = conn.execute(text("SELECT content FROM memories WHERE user_id = 'user_b';")).fetchall()
        assert len(bob_mems) == 1
        assert bob_mems[0][0] == "Bob secret note"

    engine.dispose()


# ==============================================================================
# 12. Cascade Behaviour & Historical Preservation
# ==============================================================================
def test_cascade_behaviour_and_preservation(temp_db_env):
    """
    Verifies:
    - User deletion cascades to child records (ON DELETE CASCADE)
    - Conversation deletion preserves tasks with conversation_id set to NULL (ON DELETE SET NULL)
    """
    temp_dir, db_file = temp_db_env
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(bind=engine)
    engine.dispose()

    con = sqlite3.connect(db_file)
    con.execute("PRAGMA foreign_keys = ON;")

    con.execute("""
        INSERT INTO users (id, email, username, is_active, is_verified, is_owner)
        VALUES ('u1', 'owner@love.ai', 'owner', 1, 1, 1);
    """)
    con.execute("""
        INSERT INTO conversations (id, user_id, title, is_pinned, is_archived)
        VALUES ('conv1', 'u1', 'Test Conv', 0, 0);
    """)
    con.execute("""
        INSERT INTO tasks (id, user_id, conversation_id, title, description, status, plan_json, total_steps, completed_steps)
        VALUES ('task1', 'u1', 'conv1', 'Analyze Data', 'Task description', 'completed', '[]', 1, 1);
    """)
    con.execute("""
        INSERT INTO task_actions (id, task_id, title, tool_name, status, approval_state, step_index, risk_level, input_json)
        VALUES ('act1', 'task1', 'Action 1', 'file_reader', 'completed', 'approved', 0, 'low', '{}');
    """)
    con.commit()

    # 1. Test ON DELETE SET NULL on conversation deletion
    con.execute("DELETE FROM conversations WHERE id = 'conv1';")
    con.commit()

    # Task must still exist!
    task_row = con.execute("SELECT id, conversation_id, status FROM tasks WHERE id = 'task1';").fetchone()
    assert task_row is not None
    assert task_row[0] == "task1"
    assert task_row[1] is None, "conversation_id must be SET NULL when conversation is deleted"
    assert task_row[2] == "completed"

    # TaskAction must still exist!
    action_row = con.execute("SELECT id, task_id FROM task_actions WHERE id = 'act1';").fetchone()
    assert action_row is not None

    # 2. Test ON DELETE CASCADE on user deletion
    con.execute("DELETE FROM users WHERE id = 'u1';")
    con.commit()

    # Tasks and Actions must be deleted
    assert con.execute("SELECT count(*) FROM tasks WHERE id = 'task1';").fetchone()[0] == 0
    assert con.execute("SELECT count(*) FROM task_actions WHERE id = 'act1';").fetchone()[0] == 0
    con.close()


# ==============================================================================
# 13. Index and Query Performance (EXPLAIN QUERY PLAN)
# ==============================================================================
def test_index_and_query_performance(temp_db_env):
    """Verifies composite indexes eliminate temporary B-trees in SQLite query plans."""
    temp_dir, db_file = temp_db_env
    cfg = Config(r"F:\LOVE\alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file}")
    command.upgrade(cfg, "head")

    con = sqlite3.connect(db_file)

    # 1. Query: messages by conversation ordered by created_at
    plan1 = con.execute("""
        EXPLAIN QUERY PLAN
        SELECT * FROM messages WHERE conversation_id = 'c1' ORDER BY created_at ASC;
    """).fetchall()
    plan1_str = " ".join(r[3] for r in plan1)
    assert "ix_messages_conv_created" in plan1_str
    assert "USE TEMP B-TREE" not in plan1_str, "Composite index should order without temp b-tree"

    # 2. Query: tasks by user_id and status
    plan2 = con.execute("""
        EXPLAIN QUERY PLAN
        SELECT * FROM tasks WHERE user_id = 'u1' AND status = 'pending';
    """).fetchall()
    plan2_str = " ".join(r[3] for r in plan2)
    assert "ix_tasks_user_status" in plan2_str

    # 3. Query: memories by user_id and archived state
    plan3 = con.execute("""
        EXPLAIN QUERY PLAN
        SELECT * FROM memories WHERE user_id = 'u1' AND is_archived = 0;
    """).fetchall()
    plan3_str = " ".join(r[3] for r in plan3)
    assert "ix_memories_user_archived" in plan3_str

    con.close()


# ==============================================================================
# 14. Vector Dimension Verification
# ==============================================================================
@pytest.mark.asyncio
async def test_vector_dimension_verification():
    """
    Verifies actual vector store dimensions:
    - Deterministic local provider produces 128 dimensions
    - Gemini cloud provider produces 768 dimensions
    - LocalVectorStore handles dimension mismatch gracefully
    """
    det_provider = DeterministicEmbeddingProvider(dimension=128)
    assert det_provider.dimension == 128
    vec_128 = await det_provider.embed_text("Test memory query")
    assert len(vec_128) == 128

    gem_provider = GeminiEmbeddingProvider()
    assert gem_provider.dimension == 768

    # Test LocalVectorStore dimension mismatch tolerance
    temp_vdir = tempfile.mkdtemp()
    store = LocalVectorStore(storage_dir=temp_vdir)

    # Upsert a 128-dimensional vector
    await store.upsert(
        vector_id="v_128",
        vector=vec_128,
        metadata={"category": "project"},
        user_id="user_test"
    )

    # Query with a 768-dimensional vector (simulating model switch without rebuild)
    vec_768 = [0.1] * 768
    results = await store.search(query_vector=vec_768, user_id="user_test")
    # Must gracefully return empty list without crashing
    assert results == []

    # Query with matching 128-dimensional vector
    matched_results = await store.search(query_vector=vec_128, user_id="user_test")
    assert len(matched_results) == 1
    assert matched_results[0][0] == "v_128"

    time.sleep(0.2)
    try:
        shutil.rmtree(temp_vdir)
    except Exception:
        pass


# ==============================================================================
# 15. PostgreSQL Dialect & DDL Compatibility
# ==============================================================================
def test_postgresql_dialect_and_ddl_compatibility():
    """
    Verifies that all 14 SQLAlchemy ORM models compile cleanly into PostgreSQL DDL.
    Validates PostgreSQL SERIAL sequences, TIMESTAMPTZ, and constraints.
    """
    pg_dialect = postgresql.dialect()

    for table_name, table in Base.metadata.tables.items():
        # Compile CreateTable
        ddl = str(CreateTable(table).compile(dialect=pg_dialect)).strip()
        assert len(ddl) > 0, f"PostgreSQL DDL compilation failed for {table_name}"
        assert f"CREATE TABLE {table_name}" in ddl

        # Compile Indexes
        for idx in table.indexes:
            idx_ddl = str(CreateIndex(idx).compile(dialect=pg_dialect)).strip()
            assert len(idx_ddl) > 0, f"PostgreSQL index DDL failed for {idx.name}"

    # Verify specific PostgreSQL type conversions
    sync_table = Base.metadata.tables["sync_events"]
    sync_ddl = str(CreateTable(sync_table).compile(dialect=pg_dialect))
    assert "SERIAL" in sync_ddl, "Integer PK with autoincrement should compile to SERIAL in PostgreSQL"
    assert "TIMESTAMP WITH TIME ZONE" in sync_ddl

    user_table = Base.metadata.tables["users"]
    user_ddl = str(CreateTable(user_table).compile(dialect=pg_dialect))
    assert "BOOLEAN" in user_ddl
