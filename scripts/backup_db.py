"""
Command-line utility for LOVE Database Backup, Verification, and Recovery.

Usage:
    python scripts/backup_db.py create
    python scripts/backup_db.py list
    python scripts/backup_db.py verify [backup_path]
    python scripts/backup_db.py restore <backup_path> --target <target_db_path>
"""

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database.backup import (
    create_database_backup,
    list_database_backups,
    restore_database_backup,
    verify_database_backup,
)


def cmd_create(args):
    print("=" * 60)
    print("  LOVE Database Backup Creation")
    print("=" * 60)
    try:
        meta = create_database_backup()
        print(f"[OK] Backup created successfully: {meta['filename']}")
        print(f"     Path:             {meta['backup_path']}")
        print(f"     Size:             {meta['size_mb']} MB ({meta['size_bytes']} bytes)")
        print(f"     SHA-256 Checksum: {meta['sha256']}")
        print(f"     Integrity Status: {meta['integrity_status']}")
        print(f"     Alembic Revision: {meta['alembic_revision']}")
        print(f"     Tables Verified:  {meta['tables_count']}")
        if meta.get("pruned_old_backups"):
            print(f"     Pruned:           {meta['pruned_old_backups']} older backup(s)")
    except Exception as exc:
        print(f"[FAIL] Backup creation failed: {exc}")
        sys.exit(1)


def cmd_list(args):
    print("=" * 60)
    print("  LOVE Historical Database Backups")
    print("=" * 60)
    backups = list_database_backups()
    if not backups:
        print("  No backups found.")
        return

    print(f"  Found {len(backups)} backup(s):\n")
    for b in backups:
        status = "[VALID]" if b.get("is_valid") else "[CORRUPT]"
        print(f"  {status} {b['filename']}")
        print(f"          Created:  {b.get('created_at')}")
        print(f"          Size:     {b.get('size_mb', 0)} MB")
        print(f"          Alembic:  {b.get('alembic_revision', 'n/a')}")
        print(f"          SHA-256:  {b.get('sha256', 'n/a')[:16]}...")
        print()


def cmd_verify(args):
    path = Path(args.path).resolve()
    print("=" * 60)
    print(f"  Verifying Database Backup: {path.name}")
    print("=" * 60)
    is_valid, msg, insp = verify_database_backup(path)
    if is_valid:
        print(f"[OK] Backup is VALID. SQLite integrity check: {msg}")
        print(f"     Size:             {round(insp['size_bytes'] / (1024*1024), 2)} MB")
        print(f"     Alembic Revision: {insp.get('alembic_revision')}")
        print(f"     Tables:           {len(insp.get('table_counts', {}))}")
        for t, cnt in insp.get("table_counts", {}).items():
            print(f"       - {t}: {cnt} rows")
    else:
        print(f"[FAIL] Backup is INVALID: {msg}")
        sys.exit(1)


def cmd_restore(args):
    backup_path = Path(args.backup_path).resolve()
    target_path = Path(args.target).resolve()

    print("=" * 60)
    print("  LOVE Database Restoration")
    print(f"  Source: {backup_path}")
    print(f"  Target: {target_path}")
    print("=" * 60)

    try:
        res = restore_database_backup(
            backup_path=backup_path,
            target_path=target_path,
            allow_overwrite=args.force,
        )
        print(f"[OK] Database restored successfully to: {res['target_path']}")
        print(f"     Alembic Revision: {res.get('alembic_revision')}")
        print(f"     Verified Tables:  {len(res.get('tables_verified', []))}")
    except Exception as exc:
        print(f"[FAIL] Restoration failed: {exc}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="LOVE Database Backup & Recovery Utility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create
    p_create = subparsers.add_parser("create", help="Create a new atomic database backup")
    p_create.set_defaults(func=cmd_create)

    # list
    p_list = subparsers.add_parser("list", help="List all available backups")
    p_list.set_defaults(func=cmd_list)

    # verify
    p_verify = subparsers.add_parser("verify", help="Verify integrity of a backup file")
    p_verify.add_argument("path", help="Path to the backup .db file")
    p_verify.set_defaults(func=cmd_verify)

    # restore
    p_restore = subparsers.add_parser("restore", help="Restore a backup into a target database")
    p_restore.add_argument("backup_path", help="Path to source backup .db file")
    p_restore.add_argument("--target", required=True, help="Target path for restored database")
    p_restore.add_argument("--force", action="store_true", help="Allow overwriting target file if it exists")
    p_restore.set_defaults(func=cmd_restore)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
