"""
Phase 09.5 Migration Verification Script.
Tests:
1. Fresh database upgrade to pre-Phase-09 (322b6c8a37b0).
2. Upgrade to Phase 09 head (a30798731d0a).
3. Verify foreign keys, columns, unique constraints, and indexes.
4. Downgrade back to pre-Phase-09 head (322b6c8a37b0).
5. Re-upgrade to head (a30798731d0a).
6. Cold restart and data retrieval on migrated database.
Preserves database/love.db intact.
"""

import os
import shutil
import sqlite3
import tempfile
import time
from alembic.config import Config
from alembic import command


def test_migration_lifecycle():
    temp_dir = tempfile.mkdtemp()
    temp_db = os.path.join(temp_dir, "test_migration.db").replace("\\", "/")
    print(f"Testing migration on temporary database: {temp_db}")

    try:
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{temp_db}")

        # 1. Upgrade to pre-Phase-09 head
        print("1. Upgrading to pre-Phase-09 revision: 322b6c8a37b0...")
        command.upgrade(alembic_cfg, "322b6c8a37b0")

        conn = sqlite3.connect(temp_db)
        c = conn.cursor()
        tables_pre = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
        print(f"Tables at 322b6c8a37b0 ({len(tables_pre)} tables): {sorted(tables_pre)}")
        assert "sync_events" not in tables_pre, "sync_events should not exist in pre-phase 09"
        assert "user_sync_settings" not in tables_pre
        assert "device_sync_cursors" not in tables_pre

        # 2. Upgrade to Phase 09 head
        print("2. Upgrading to Phase 09 head: a30798731d0a...")
        command.upgrade(alembic_cfg, "a30798731d0a")

        conn = sqlite3.connect(temp_db)
        c = conn.cursor()
        tables_post = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print(f"Tables at a30798731d0a ({len(tables_post)} tables): {sorted(tables_post)}")
        assert "sync_events" in tables_post
        assert "user_sync_settings" in tables_post
        assert "device_sync_cursors" in tables_post

        # Verify columns of sync_events
        cols_sync = {r[1]: r[2] for r in c.execute("PRAGMA table_info(sync_events)").fetchall()}
        print(f"sync_events columns: {list(cols_sync.keys())}")
        assert "cursor" in cols_sync and "event_id" in cols_sync and "payload_json" in cols_sync
        assert "origin_device_id" in cols_sync and "entity_type" in cols_sync

        # Verify indexes on sync_events
        indices = [r[1] for r in c.execute("PRAGMA index_list(sync_events)").fetchall()]
        print(f"sync_events indexes: {indices}")
        assert any("user_cursor" in idx for idx in indices), "ix_sync_events_user_cursor must exist"
        assert any("event_id" in idx for idx in indices), "ix_sync_events_event_id must exist"

        # Verify foreign keys
        fks_events = c.execute("PRAGMA foreign_key_list(sync_events)").fetchall()
        print(f"sync_events foreign keys: {fks_events}")
        assert any(fk[2] == "users" for fk in fks_events), "sync_events must reference users"

        fks_cursors = c.execute("PRAGMA foreign_key_list(device_sync_cursors)").fetchall()
        print(f"device_sync_cursors foreign keys: {fks_cursors}")
        assert any(fk[2] == "devices" for fk in fks_cursors), "device_sync_cursors must reference devices"
        assert any(fk[2] == "users" for fk in fks_cursors), "device_sync_cursors must reference users"
        conn.close()

        # 3. Test downgrade back to 322b6c8a37b0
        print("3. Testing downgrade back to 322b6c8a37b0...")
        command.downgrade(alembic_cfg, "322b6c8a37b0")

        conn = sqlite3.connect(temp_db)
        c = conn.cursor()
        tables_down = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
        assert "sync_events" not in tables_down
        assert "user_sync_settings" not in tables_down
        assert "device_sync_cursors" not in tables_down
        print("Downgrade confirmed clean!")

        # 4. Re-upgrade to head
        print("4. Re-upgrading to head...")
        command.upgrade(alembic_cfg, "head")

        # 5. Cold restart & data insertion/retrieval test on migrated database
        print("5. Testing cold restart and data insertion on migrated database...")
        conn = sqlite3.connect(temp_db)
        c = conn.cursor()
        c.execute("""
            INSERT INTO users (id, email, username, is_active, is_verified, is_owner, created_at, updated_at)
            VALUES ('u1', 'owner@love.ai', 'owner', 1, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """)
        c.execute("""
            INSERT INTO user_sync_settings (user_id, sync_enabled, sync_mode, auto_sync_interval_seconds, conflict_resolution, updated_at)
            VALUES ('u1', 1, 'multi_device', 15, 'last_write_wins', CURRENT_TIMESTAMP)
        """)
        c.execute("""
            INSERT INTO sync_events (event_id, user_id, entity_type, entity_id, action, origin_device_id, payload_json, created_at)
            VALUES ('ev-uuid-1', 'u1', 'preference', 'theme', 'updated', 'dev-win-1', '{\"theme\":\"cyber\"}', CURRENT_TIMESTAMP)
        """)
        conn.commit()
        conn.close()

        # Simulate cold restart: open fresh connection
        conn2 = sqlite3.connect(temp_db)
        c2 = conn2.cursor()
        row = c2.execute("SELECT cursor, event_id, entity_type, payload_json FROM sync_events WHERE user_id = 'u1'").fetchone()
        assert row is not None
        assert row[0] == 1  # autoincrement cursor
        assert row[1] == "ev-uuid-1"
        assert row[2] == "preference"
        print(f"Cold restart query retrieved event: cursor={row[0]}, event_id={row[1]}, payload={row[3]}")
        conn2.close()

        print("\n=== ALL MIGRATION LIFECYCLE CHECKS PASSED SUCCESSFULLY ===")
    finally:
        # Give Windows a brief moment to release file handles before rmtree
        time.sleep(0.5)
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Note: temp_dir cleanup deferred: {e}")


if __name__ == "__main__":
    test_migration_lifecycle()
