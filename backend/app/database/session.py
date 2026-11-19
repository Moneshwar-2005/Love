"""
Database session management, engine lifecycle, and connectivity checks for LOVE.
"""

import time
from pathlib import Path
from typing import AsyncGenerator, Dict, Tuple
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

# SQLite-specific connection arguments (connect_args)
if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

# Async SQLAlchemy engine
engine: AsyncEngine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)


# Enable SQLite foreign key constraint enforcement
@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforces SQLite foreign key constraints and ON DELETE CASCADE behavior."""
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
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


async def close_database_connection() -> None:
    """Disposes engine pool connections on application shutdown."""
    logger.info("Closing database connections...")
    await engine.dispose()
    logger.info("Database connections closed.")
