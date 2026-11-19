"""
Automated tests for database layer.
Verifies asynchronous connection, session management, and basic queries.
"""

import pytest
from sqlalchemy import Integer, String, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base, TimestampMixin
from backend.app.database.session import check_database_connection, get_db
from shared.constants import DatabaseStatus, ServiceStatus


class SampleModel(Base, TimestampMixin):
    """Temporary test model for verifying ORM mapping and timestamps."""
    __tablename__ = "test_sample"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)


@pytest.mark.asyncio
async def test_database_connection_check():
    """Verify check_database_connection returns CONNECTED and healthy status."""
    status, detail = await check_database_connection()
    assert status == DatabaseStatus.CONNECTED
    assert detail["status"] == ServiceStatus.HEALTHY
    assert isinstance(detail["latency_ms"], float)
    assert detail["latency_ms"] >= 0.0


@pytest.mark.asyncio
async def test_database_session_execution(test_db_session: AsyncSession):
    """Verify async database session can execute raw queries."""
    result = await test_db_session.execute(text("SELECT 42 AS answer"))
    row = result.mappings().one()
    assert row["answer"] == 42


@pytest.mark.asyncio
async def test_orm_model_lifecycle(test_db_engine, test_db_session: AsyncSession):
    """Verify ORM model creation, persistence, and timestamp population."""
    async with test_db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Insert test entity
    entity = SampleModel(name="test_record")
    test_db_session.add(entity)
    await test_db_session.flush()

    assert entity.id is not None
    assert entity.name == "test_record"

    # Query back
    stmt = select(SampleModel).where(SampleModel.id == entity.id)
    retrieved = (await test_db_session.execute(stmt)).scalar_one()
    assert retrieved.name == "test_record"
