"""
Database Backup, Verification, and Restore Subsystem for LOVE.
Implements atomic, WAL-safe SQLite backups using SQLite's Online Backup API,
companion SHA-256 metadata generation, post-backup integrity validation,
and safe restoration into isolated target databases.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import threading
from typing import Any, Dict, List, Optional, Tuple

from backend.app.config.settings import get_settings
from backend.app.core.logging import get_logger

logger = get_logger("database.backup")
settings = get_settings()


def _get_clean_sqlite_path(db_url: Optional[str] = None) -> Optional[Path]:
    """Extract clean Path from sqlite:// URL."""
    url = db_url or settings.DATABASE_URL
    if not url.startswith("sqlite"):
        return None
    clean_path = url.split("///")[-1]
    if not clean_path or clean_path == ":memory:":
        return None
    return Path(clean_path).resolve()


def _calculate_sha256(file_path: Path) -> str:
    """Computes SHA-256 checksum of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _set_restricted_file_permissions(file_path: Path) -> None:
    """Sets owner-only read/write permissions where supported."""
    try:
        os.chmod(file_path, 0o600)
    except Exception:
        pass


def create_database_backup(
    source_db_path: Optional[Path] = None,
    backup_dir: Optional[Path] = None,
    keep_retention: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Creates an atomic, WAL-consistent backup of the database using SQLite Online Backup API.
    Guarantees consistent snapshots even while concurrent write operations are in flight.
    Runs PRAGMA integrity_check on the backup before committing metadata.
    """
    src_path = source_db_path or _get_clean_sqlite_path()
    if not src_path or not src_path.exists():
        # Fallback for in-memory environments (e.g. testing) where default file exists
        default_db = Path("database/love.db").resolve()
        if default_db.exists():
            src_path = default_db
        else:
            raise FileNotFoundError(f"Source database file not found at: {src_path or default_db}")

    b_dir = backup_dir or Path(settings.DATABASE_BACKUP_DIR).resolve()
    b_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(b_dir, 0o700)
    except Exception:
        pass

    now_utc = datetime.now(timezone.utc)
    timestamp_str = now_utc.strftime("%Y%m%d_%H%M%S")
    backup_filename = f"love_backup_{timestamp_str}.db"
    backup_path = b_dir / backup_filename
    meta_path = b_dir / f"love_backup_{timestamp_str}.json"

    logger.info(f"Starting atomic database backup: {src_path} -> {backup_path}")

    # 1. Execute online backup using SQLite's backup API
    src_conn = sqlite3.connect(str(src_path), timeout=settings.DATABASE_SQLITE_BUSY_TIMEOUT_MS / 1000.0)
    dst_conn = sqlite3.connect(str(backup_path))

    try:
        # con.backup safely copies pages, flushing in-memory WAL states
        with dst_conn:
            src_conn.backup(dst_conn, pages=0)
    finally:
        dst_conn.close()
        src_conn.close()

    _set_restricted_file_permissions(backup_path)

    # 2. Verify backup file integrity
    is_valid, integrity_msg, inspection = verify_database_backup(backup_path)
    if not is_valid:
        if backup_path.exists():
            backup_path.unlink()
        raise RuntimeError(f"Backup verification failed: {integrity_msg}")

    # 3. Compute checksum & metadata
    file_size = backup_path.stat().st_size
    sha256_hash = _calculate_sha256(backup_path)

    metadata: Dict[str, Any] = {
        "backup_id": f"backup_{timestamp_str}",
        "filename": backup_filename,
        "backup_path": str(backup_path.resolve()),
        "source_db": str(src_path.resolve()),
        "created_at": now_utc.isoformat(),
        "size_bytes": file_size,
        "size_mb": round(file_size / (1024 * 1024), 2),
        "sha256": sha256_hash,
        "is_valid": True,
        "integrity_status": integrity_msg,
        "alembic_revision": inspection.get("alembic_revision"),
        "tables_count": len(inspection.get("table_counts", {})),
        "table_counts": inspection.get("table_counts", {}),
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    _set_restricted_file_permissions(meta_path)

    logger.info(f"Database backup completed successfully: {backup_filename} ({metadata['size_mb']} MB, SHA: {sha256_hash[:8]}...)")

    # 4. Prune old backups per retention policy
    retention = keep_retention if keep_retention is not None else settings.DATABASE_BACKUP_RETENTION_COUNT
    pruned_count = prune_database_backups(keep_count=retention, backup_dir=b_dir)
    metadata["pruned_old_backups"] = pruned_count

    return metadata


def verify_database_backup(backup_path: Path) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Performs comprehensive health and integrity verification on a database backup file:
    - Verifies file exists and has non-zero size
    - PRAGMA integrity_check
    - PRAGMA foreign_key_check
    - Reads alembic_version revision
    - Gathers table row counts
    """
    if not backup_path.exists():
        return False, f"Backup file does not exist: {backup_path}", {}

    if backup_path.stat().st_size == 0:
        return False, "Backup file is empty (0 bytes)", {}

    inspection: Dict[str, Any] = {
        "size_bytes": backup_path.stat().st_size,
        "alembic_revision": None,
        "table_counts": {},
        "integrity_ok": False,
        "foreign_keys_ok": False,
    }

    try:
        con = sqlite3.connect(str(backup_path), timeout=5.0)
        cur = con.cursor()

        # 1. SQLite integrity check
        ic_res = cur.execute("PRAGMA integrity_check;").fetchone()
        if not ic_res or ic_res[0] != "ok":
            con.close()
            return False, f"Integrity check failed: {ic_res[0] if ic_res else 'None'}", inspection
        inspection["integrity_ok"] = True

        # 2. Foreign keys check
        fk_violations = cur.execute("PRAGMA foreign_key_check;").fetchall()
        if fk_violations:
            con.close()
            return False, f"Foreign key check violations detected: {fk_violations}", inspection
        inspection["foreign_keys_ok"] = True

        # 3. Alembic revision check
        try:
            rev_row = cur.execute("SELECT version_num FROM alembic_version LIMIT 1;").fetchone()
            if rev_row:
                inspection["alembic_revision"] = rev_row[0]
        except Exception:
            pass

        # 4. Gather table counts
        tables = [t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
        for tbl in tables:
            try:
                cnt = cur.execute(f"SELECT count(*) FROM \"{tbl}\";").fetchone()[0]
                inspection["table_counts"][tbl] = cnt
            except Exception:
                inspection["table_counts"][tbl] = 0

        con.close()
        return True, "ok", inspection

    except Exception as exc:
        return False, f"Database verification error: {str(exc)}", inspection


def list_database_backups(backup_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Returns sorted list of all available backups (newest first).
    Reads companion JSON metadata or falls back to file inspection.
    """
    b_dir = backup_dir or Path(settings.DATABASE_BACKUP_DIR).resolve()
    if not b_dir.exists():
        return []

    backups: List[Dict[str, Any]] = []

    for file_path in b_dir.glob("love_backup_*.db"):
        meta_path = file_path.with_suffix(".json")
        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                backups.append(meta)
                continue
            except Exception:
                pass

        # Fallback inspection if metadata file was missing
        stat = file_path.stat()
        created_at = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
        is_valid, msg, insp = verify_database_backup(file_path)
        backups.append({
            "backup_id": file_path.stem,
            "filename": file_path.name,
            "backup_path": str(file_path.resolve()),
            "source_db": "unknown",
            "created_at": created_at,
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "sha256": _calculate_sha256(file_path) if is_valid else "invalid",
            "is_valid": is_valid,
            "integrity_status": msg,
            "alembic_revision": insp.get("alembic_revision"),
            "tables_count": len(insp.get("table_counts", {})),
            "table_counts": insp.get("table_counts", {}),
        })

    # Sort newest first by created_at
    backups.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return backups


def restore_database_backup(
    backup_path: Path,
    target_path: Path,
    allow_overwrite: bool = False,
) -> Dict[str, Any]:
    """
    Restores an authenticated database backup into a target database path.
    Safety controls:
    - Never overwrites existing target file unless allow_overwrite is explicitly True
    - Validates source backup integrity BEFORE initiating restore
    - Uses SQLite's online backup API for crash-resilient restoration
    - Validates target database integrity post-restore
    """
    b_path = Path(backup_path).resolve()
    t_path = Path(target_path).resolve()

    if not b_path.exists():
        raise FileNotFoundError(f"Backup file not found: {b_path}")

    if t_path.exists() and not allow_overwrite:
        raise FileExistsError(
            f"Target database already exists at {t_path}. "
            "To prevent accidental data loss, provide a separate target path or pass allow_overwrite=True."
        )

    # 1. Pre-restore validation of source backup
    is_valid, msg, insp = verify_database_backup(b_path)
    if not is_valid:
        raise ValueError(f"Cannot restore from corrupt backup: {msg}")

    # Ensure parent directory of target exists
    t_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Restoring backup {b_path} -> {t_path}")

    # 2. Perform online restore
    src_conn = sqlite3.connect(str(b_path))
    dst_conn = sqlite3.connect(str(t_path))

    try:
        with dst_conn:
            src_conn.backup(dst_conn, pages=0)
    finally:
        dst_conn.close()
        src_conn.close()

    _set_restricted_file_permissions(t_path)

    # 3. Post-restore verification
    t_valid, t_msg, t_insp = verify_database_backup(t_path)
    if not t_valid:
        raise RuntimeError(f"Restored target database failed integrity validation: {t_msg}")

    logger.info(f"Database restoration successfully completed at: {t_path}")

    return {
        "success": True,
        "message": "Database restored successfully",
        "source_backup": str(b_path),
        "target_path": str(t_path),
        "restored_at": datetime.now(timezone.utc).isoformat(),
        "alembic_revision": t_insp.get("alembic_revision"),
        "tables_verified": list(t_insp.get("table_counts", {}).keys()),
        "record_counts": t_insp.get("table_counts", {}),
    }


def prune_database_backups(
    keep_count: int,
    backup_dir: Optional[Path] = None,
) -> int:
    """
    Prunes older backups when the number of backups exceeds keep_count.
    Deletes both the .db file and companion .json metadata file.
    Returns the number of pruned backup pairs.
    """
    if keep_count <= 0:
        return 0

    backups = list_database_backups(backup_dir)
    if len(backups) <= keep_count:
        return 0

    to_delete = backups[keep_count:]
    deleted = 0

    for item in to_delete:
        p = Path(item["backup_path"])
        m = p.with_suffix(".json")
        try:
            if p.exists():
                p.unlink()
            if m.exists():
                m.unlink()
            deleted += 1
            logger.info(f"Pruned older backup: {p.name}")
        except Exception as exc:
            logger.warning(f"Failed to prune backup file {p.name}: {exc}")

    return deleted
