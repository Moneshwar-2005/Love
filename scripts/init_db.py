"""
Database Initialization and Connectivity Verification Script.
Usage:
    python scripts/init_db.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config.settings import get_settings
from backend.app.database.session import (
    check_database_connection,
    close_database_connection,
    init_db,
)


async def main() -> None:
    settings = get_settings()
    print("=" * 70)
    print("  LOVE Database Initialization")
    print(f"  Target URL: {settings.DATABASE_URL}")
    print("=" * 70)

    print("[1/2] Initializing tables and schemas...")
    await init_db()
    print("      Schemas created successfully.")

    print("[2/2] Checking database connectivity and latency...")
    status, detail = await check_database_connection()
    print(f"      Status:     {status.value}")
    print(f"      Latency:    {detail.get('latency_ms')} ms")
    print(f"      Message:    {detail.get('message')}")

    await close_database_connection()
    print("=" * 70)
    print("  Database initialization completed.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
