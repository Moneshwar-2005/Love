# LOVE Database Storage & Migrations

## Overview
This directory holds the local SQLite database files (for development and standalone desktop operation) and Alembic schema migration scripts.

### Strategy:
1. **Development & Standalone Mode:**
   - Asynchronous SQLite (`sqlite+aiosqlite:///./database/love.db`).
   - Zero-configuration local database creation.
2. **Production Multi-User / Distributed Mode:**
   - PostgreSQL (`postgresql+asyncpg://...`).
   - Managed via Alembic migrations under `database/migrations/`.
