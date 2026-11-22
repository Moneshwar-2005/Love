# LOVE — Database Backup and Disaster Recovery Guide

**Phase 10: Database Architecture, Integrity & Production Readiness**  
**Role:** Senior Database Architect, SQLAlchemy Engineer and Data Reliability Specialist  
**Canonical Datastore:** SQLite 3 (WAL Mode, `database/love.db`)  
**Backup Mechanism:** SQLite Online Backup API (`sqlite3.Connection.backup`)  
**Backup Location:** `database/backups/`  

---

## 1. Overview & Safety Principles

In SQLite Write-Ahead Logging (WAL) mode, transactions are written to `-wal` sidecar files before being checkpointed to the primary database file. Naive file copying (`cp`, `copy`, `shutil.copy`) of an active SQLite WAL database can produce corrupt backups or omit in-flight transactions.

### Core Safety Rules
1. **Never use blind file copying**: All backups must use the SQLite Online Backup API (`create_database_backup()`), which cooperatively coordinates page flushing and locks WAL states to output a single, self-contained, crash-resilient `.db` file.
2. **Never overwrite the active database during restore**: The restore procedure restores into an isolated target path and verifies data integrity before any replacement.
3. **Automated Post-Backup Verification**: Every backup runs `PRAGMA integrity_check` and `PRAGMA foreign_key_check` immediately after creation. Corrupted files are blocked and removed.
4. **Local Privacy**: Backups remain on local storage in `database/backups/` with restricted permissions (0o600). Backups are never uploaded to cloud services.

---

## 2. Backup File Format & Metadata

Each backup operation produces a paired `.db` snapshot and a companion `.json` metadata file:

```text
database/backups/
  ├── love_backup_20261120_095038.db       # Self-contained SQLite database
  └── love_backup_20261120_095038.json     # Cryptographic & structural metadata
```

### Metadata JSON Schema
```json
{
  "backup_id": "backup_20261120_095038",
  "filename": "love_backup_20261120_095038.db",
  "backup_path": "F:\\LOVE\\database\\backups\\love_backup_20261120_095038.db",
  "source_db": "F:\\LOVE\\database\\love.db",
  "created_at": "2026-11-20T09:50:38.123456+00:00",
  "size_bytes": 372736,
  "size_mb": 0.36,
  "sha256": "ab5322a3e0cded570c26be059c19b6c4848396aca89a1ca648ed2a26c6828dbd",
  "is_valid": true,
  "integrity_status": "ok",
  "alembic_revision": "c0e81b379d42",
  "tables_count": 15,
  "table_counts": {
    "alembic_version": 1,
    "users": 4,
    "user_credentials": 4,
    "devices": 15,
    "refresh_token_sessions": 36,
    "conversations": 9,
    "messages": 26,
    "memories": 2,
    "memory_audit_logs": 5,
    "memory_suggestions": 0,
    "tasks": 7,
    "task_actions": 7,
    "sync_events": 36,
    "user_sync_settings": 1,
    "device_sync_cursors": 4
  }
}
```

---

## 3. Command-Line Operations

LOVE includes a production CLI utility: `scripts/backup_db.py`.

### 3.1 Create a Manual Backup
```powershell
.venv\Scripts\python scripts/backup_db.py create
```
**Output:**
```text
============================================================
  LOVE Database Backup Creation
============================================================
[OK] Backup created successfully: love_backup_20261120_095038.db
     Path:             F:\LOVE\database\backups\love_backup_20261120_095038.db
     Size:             0.36 MB (372736 bytes)
     SHA-256 Checksum: ab5322a3e0cded570c26be059c19b6c4848396aca89a1ca648ed2a26c6828dbd
     Integrity Status: ok
     Alembic Revision: c0e81b379d42
     Tables Verified:  15
```

### 3.2 List All Existing Backups
```powershell
.venv\Scripts\python scripts/backup_db.py list
```

### 3.3 Verify a Backup's Integrity
```powershell
.venv\Scripts\python scripts/backup_db.py verify database/backups/love_backup_20261120_095038.db
```

### 3.4 Restore into an Isolated Target Database
```powershell
.venv\Scripts\python scripts/backup_db.py restore database/backups/love_backup_20261120_095038.db --target database/recovered.db
```

---

## 4. API & Command Dashboard Integration

Authenticated users can manage backups directly via HTTP API or the LOVE Command Dashboard:

- `POST /api/v1/system/database/backup`: Triggers an atomic backup snapshot.
- `GET /api/v1/system/database/backups`: Returns all available verified backups.
- `GET /api/v1/system/database`: Returns current database health, storage size, and last backup metadata.

In the Command Dashboard (`DatabaseHealthCard`), clicking **"Backup Database"** triggers the creation and immediately updates the latest backup receipt.

---

## 5. Disaster Recovery Procedures

### Scenario A: Accidental Data Deletion
1. Stop the backend server if running:
   ```powershell
   # Stop server process
   ```
2. Locate the most recent valid backup in `database/backups/`:
   ```powershell
   .venv\Scripts\python scripts/backup_db.py list
   ```
3. Verify the chosen backup:
   ```powershell
   .venv\Scripts\python scripts/backup_db.py verify database/backups/<backup_file>.db
   ```
4. Restore into a temporary verification database:
   ```powershell
   .venv\Scripts\python scripts/backup_db.py restore database/backups/<backup_file>.db --target database/verify_restore.db
   ```
5. Confirm contents in `database/verify_restore.db`, then replace active database:
   ```powershell
   Move-Item database/love.db database/love.db.bak_corrupt
   Move-Item database/verify_restore.db database/love.db
   # Clean up any stale WAL/SHM sidecars
   Remove-Item database/love.db-wal, database/love.db-shm -ErrorAction SilentlyContinue
   ```
6. Restart backend server.

### Scenario B: Database File Corruption
If SQLite raises `sqlite3.DatabaseError: file is not a database` or `database disk image is malformed`:
1. Quarantining the corrupt file:
   ```powershell
   Move-Item database/love.db database/love.db.malformed
   ```
2. Restore latest verified backup to `database/love.db`:
   ```powershell
   .venv\Scripts\python scripts/backup_db.py restore database/backups/<latest_backup>.db --target database/love.db
   ```
3. Verify new database:
   ```powershell
   .venv\Scripts\python -c "import sqlite3; con = sqlite3.connect('database/love.db'); print(con.execute('PRAGMA integrity_check').fetchall())"
   ```

### Scenario C: Complete Host or Disk Failure
1. Install LOVE on the new machine following `README.md`.
2. Copy the contents of `database/backups/` from your offline storage to the new installation's `database/backups/` directory.
3. Run restore to initialize `database/love.db`:
   ```powershell
   .venv\Scripts\python scripts/backup_db.py restore database/backups/<backup_file>.db --target database/love.db
   ```
4. Run migrations to ensure revision head compatibility:
   ```powershell
   .venv\Scripts\alembic upgrade head
   ```

---

## 6. Retention and Pruning Policy

By default, LOVE retains the **10 most recent backups** (`DATABASE_BACKUP_RETENTION_COUNT=10` in `.env`). Whenever a new backup is created, older backups beyond the retention threshold are pruned automatically along with their companion JSON files.
