# LOVE Developer Guide

## 1. Prerequisites & Tooling

To develop and test the LOVE backend, ensure you have:
- **Python:** Version 3.11 or newer (`python --version`)
- **Package Manager:** `uv` (recommended for ultra-fast installs) or standard `pip`
- **Shell:** PowerShell (Windows) or Bash/Zsh (Linux/macOS)

---

## 2. Environment Setup

### 1. Initialize Virtual Environment
Using `uv`:
```bash
uv venv .venv --python 3.11
```
Or using standard Python:
```bash
python -m venv .venv
```

### 2. Activate Virtual Environment
- **Windows (PowerShell):**
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
- **Windows (CMD):**
  ```cmd
  .\.venv\Scripts\activate.bat
  ```
- **macOS / Linux:**
  ```bash
  source .venv/bin/activate
  ```

### 3. Install Dependencies
```bash
uv pip install -r requirements.txt
```
Or:
```bash
pip install -r requirements.txt
```

---

## 3. Configuration Management

Configuration is handled dynamically via Pydantic Settings and loaded from `.env`.

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Key settings:
   - `DEBUG`: Set to `true` for auto-reloading and Swagger docs (`/docs`).
   - `HOST`: Set to `127.0.0.1` for local development.
   - `PORT`: Default is `8000`.
   - `DATABASE_URL`: Defaults to `sqlite+aiosqlite:///./database/love.db`.
   - `LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR`.

---

## 4. Running the Application

### Option A: Using the convenience runner script
```bash
python scripts/run_server.py
```

### Option B: Using Uvicorn CLI directly
```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Access the application in your browser:
- **API Status:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc API Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check Endpoint:** [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

---

## 5. Database Initialization & Utilities

To verify database connectivity and initialize tables:
```bash
python scripts/init_db.py
```

The script will report:
- Target database URL.
- Schema creation status.
- Connectivity status and round-trip query latency in milliseconds.

---

## 6. Automated Testing

Run the automated test suite with pytest:

```bash
# Run all tests verbosely
pytest -v

# Run only health check tests
pytest tests/test_health.py -v

# Run with coverage report
pytest --cov=backend tests/
```

### Test Design Principles:
- Tests run against an isolated **in-memory SQLite database** (`sqlite+aiosqlite:///:memory:`).
- Tests do not create, modify, or delete production/development database files.
- All async operations use `pytest-asyncio` with function-scoped event loops.

---

## 7. Adding New Endpoints

Follow these steps to add new endpoints to LOVE:
1. Define shared schemas in `shared/schemas/<feature>.py`.
2. Implement route logic in `backend/app/api/v1/endpoints/<feature>.py`.
3. Register the router in `backend/app/api/v1/api.py`.
4. Write unit and integration tests in `tests/test_<feature>.py`.
5. Run `pytest -v` to verify zero regressions.
