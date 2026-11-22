"""
Database session management, engine lifecycle, and connectivity checks for LOVE.
"""

import os
import time
from pathlib import Path
from typing import AsyncGenerator, Dict, Optional, Tuple
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.config.settings import get_settings
from backend.app.core.logging import get_logger
from backend.app.database.base import Base
from shared.constants import DatabaseStatus, ServiceStatus

logger = get_logger("database")
settings = get_settings()


def _ensure_sqlite_directory(db_url: str) -> None:
    """Ensure directory exists if using a local file-based SQLite database."""
    if db_url.startswith("sqlite"):
        # Strip scheme to get file path
        clean_path = db_url.split("///")[-1]
        if clean_path and clean_path != ":memory:":
            db_file = Path(clean_path).resolve()
            db_file.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_directory(settings.DATABASE_URL)

# Configure engine arguments
engine_kwargs: dict = {
    "echo": settings.DATABASE_ECHO,
    "future": True,
}

# SQLite vs PostgreSQL connection & pooling configuration
if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {
        "check_same_thread": False,
        "timeout": settings.DATABASE_SQLITE_BUSY_TIMEOUT_MS / 1000.0,
    }
else:
    # Client-server engines (e.g. PostgreSQL)
    engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW
    engine_kwargs["pool_timeout"] = settings.DATABASE_POOL_TIMEOUT
    engine_kwargs["pool_recycle"] = settings.DATABASE_POOL_RECYCLE
    engine_kwargs["pool_pre_ping"] = True

# Async SQLAlchemy engine
engine: AsyncEngine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)


# SQLite Hardening & PRAGMA configuration
@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Enforces SQLite production reliability settings on every physical connection:
    - Foreign keys ON (referential integrity & cascade)
    - Busy timeout (prevents immediate 'database is locked' errors)
    - WAL mode (concurrent read/write isolation)
    - Synchronous NORMAL (crash-safe with high write throughput)
    - Memory cache & temporary store optimization
    """
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute(f"PRAGMA busy_timeout={settings.DATABASE_SQLITE_BUSY_TIMEOUT_MS}")
        if settings.DATABASE_SQLITE_WAL_MODE:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-64000")  # 64 MB page cache
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()


# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an active database session.
    Automatically handles commit and rollback on exception.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initializes database tables defined in SQLAlchemy Base metadata.
    In production with PostgreSQL, migrations should be handled via Alembic.
    """
    logger.info("Initializing database schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized successfully.")


async def check_database_connection() -> Tuple[DatabaseStatus, Dict[str, any]]:
    """
    Executes a lightweight query to verify active database connectivity and measure latency.
    """
    start_time = time.perf_counter()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return DatabaseStatus.CONNECTED, {
            "status": ServiceStatus.HEALTHY,
            "message": "Database connection verified",
            "latency_ms": latency_ms,
        }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.error(f"Database health check failed: {exc}")
        return DatabaseStatus.ERROR, {
            "status": ServiceStatus.UNHEALTHY,
            "message": f"Connection error: {str(exc)}",
            "latency_ms": latency_ms,
        }


async def get_database_diagnostics() -> Dict[str, any]:
    """
    Gathers detailed operational health metrics without exposing secrets:
    - Dialect / engine name
    - Connectivity & latency
    - Journal mode & foreign key status (SQLite)
    - Integrity check status
    - Current Alembic revision
    - Database file size (bytes & MB)
    - Table counts
    - Last successful backup status
    """
    start_time = time.perf_counter()
    dialect = engine.sync_engine.dialect.name
    diagnostics: Dict[str, any] = {
        "engine": dialect,
        "status": "connected",
        "latency_ms": 0.0,
        "is_sqlite": dialect == "sqlite",
        "is_postgresql": dialect == "postgresql",
        "journal_mode": None,
        "foreign_keys_enabled": False,
        "integrity_status": "unknown",
        "alembic_revision": None,
        "database_size_bytes": 0,
        "database_size_mb": 0.0,
        "table_counts": {},
        "wal_file_present": False,
        "last_backup": None,
    }

    try:
        async with engine.connect() as conn:
            # Latency ping
            await conn.execute(text("SELECT 1"))
            diagnostics["latency_ms"] = round((time.perf_counter() - start_time) * 1000, 2)

            # SQLite specific pragmas
            if dialect == "sqlite":
                jm_res = await conn.execute(text("PRAGMA journal_mode;"))
                diagnostics["journal_mode"] = str(jm_res.scalar()).upper()

                fk_res = await conn.execute(text("PRAGMA foreign_keys;"))
                diagnostics["foreign_keys_enabled"] = bool(fk_res.scalar() == 1)

                ic_res = await conn.execute(text("PRAGMA integrity_check;"))
                diagnostics["integrity_status"] = str(ic_res.scalar())

            # Alembic revision
            try:
                rev_res = await conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1;"))
                diagnostics["alembic_revision"] = rev_res.scalar()
            except Exception:
                diagnostics["alembic_revision"] = "not_tracked"

            # Table counts
            table_names = [
                "users",
                "devices",
                "conversations",
                "messages",
                "memories",
                "memory_audit_logs",
                "memory_suggestions",
                "tasks",
                "task_actions",
                "sync_events",
                "user_sync_settings",
                "device_sync_cursors",
            ]
            counts = {}
            for tbl in table_names:
                try:
                    c_res = await conn.execute(text(f"SELECT count(*) FROM {tbl};"))
                    counts[tbl] = int(c_res.scalar() or 0)
                except Exception:
                    counts[tbl] = 0
            diagnostics["table_counts"] = counts

        # File size calculation for SQLite
        if dialect == "sqlite":
            clean_path = settings.DATABASE_URL.split("///")[-1]
            if clean_path and clean_path != ":memory:":
                db_file = Path(clean_path).resolve()
                if db_file.exists():
                    size = db_file.stat().st_size
                    diagnostics["database_size_bytes"] = size
                    diagnostics["database_size_mb"] = round(size / (1024 * 1024), 2)
                wal_file = Path(str(db_file) + "-wal")
                diagnostics["wal_file_present"] = wal_file.exists()

        # Last backup metadata check
        try:
            from backend.app.database.backup import list_database_backups
            backups = list_database_backups()
            if backups:
                latest = backups[0]
                diagnostics["last_backup"] = {
                    "filename": latest.get("filename"),
                    "created_at": latest.get("created_at"),
                    "size_bytes": latest.get("size_bytes"),
                    "is_valid": latest.get("is_valid"),
                    "total_backups": len(backups),
                }
        except Exception:
            pass

    except Exception as exc:
        diagnostics["status"] = "error"
        diagnostics["error"] = str(exc)
        diagnostics["latency_ms"] = round((time.perf_counter() - start_time) * 1000, 2)

    return diagnostics


async def close_database_connection() -> None:
    """Disposes engine pool connections on application shutdown."""
    logger.info("Closing database connections...")
    await engine.dispose()
    logger.info("Database connections closed.")
