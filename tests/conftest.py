"""
Pytest configuration, fixtures, and environment setup for LOVE tests.
"""

import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure project root and backend are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

# Force test environment variables before importing app modules
os.environ["APP_ENV"] = "testing"
os.environ["DEBUG"] = "true"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["ALLOW_OPEN_REGISTRATION"] = "false"
os.environ["FIRST_OWNER_SETUP_TOKEN"] = ""

from backend.app.config.settings import Settings
from backend.app.database.base import Base
import backend.app.database.models  # Ensure all models are registered on Base.metadata
from backend.app.database.session import get_db
from backend.app.main import create_application
from backend.app.security.rate_limiter import login_rate_limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Automatically reset rate limiter state between tests."""
    login_rate_limiter.clear()
    yield
    login_rate_limiter.clear()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Fixture providing settings configured for testing."""
    return Settings(
        APP_NAME="LOVE Personal AI Assistant (Test)",
        APP_ENV="testing",
        APP_VERSION="0.2.0-test",
        DEBUG=True,
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        DATABASE_ECHO=False,
    )


@pytest_asyncio.fixture(scope="function")
async def test_db_engine():
    """
    Create an isolated in-memory SQLite engine for each test function.
    Uses StaticPool so all connections and sessions in a test share the exact same in-memory DB.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a scoped async database session backed by the in-memory database."""
    session_maker = async_sessionmaker(
        bind=test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with session_maker() as session:
        yield session


@pytest.fixture(scope="function")
def test_app(test_db_engine):
    """Create a FastAPI application instance with overridden database session."""
    application = create_application()

    session_maker = async_sessionmaker(
        bind=test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async def override_get_db():
        async with session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    application.dependency_overrides[get_db] = override_get_db
    return application


@pytest.fixture(scope="function")
def client(test_app) -> Generator[TestClient, None, None]:
    """Synchronous test client for API endpoint testing."""
    with TestClient(test_app) as test_client:
        yield test_client


@pytest_asyncio.fixture(scope="function")
async def async_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """Asynchronous test client using httpx for async API endpoint testing."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
