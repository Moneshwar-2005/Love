# LOVE Developer Guide

## 1. Prerequisites & Tooling

To develop and test the LOVE backend, ensure you have:
- **Python:** Version 3.11 or newer (`python --version`)
- **Package Manager:** `uv` (recommended) or standard `pip`
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
- **macOS / Linux:**
  ```bash
  source .venv/bin/activate
  ```

### 3. Install Dependencies
```bash
uv pip install -r requirements.txt
```

---

## 3. Configuration Management

Configuration is handled dynamically via Pydantic Settings and loaded from `.env`.

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Key Authentication & Security Variables:
   - `SECRET_KEY`: Cryptographic secret key for signing sessions.
   - `JWT_SECRET_KEY`: Dedicated JWT secret (defaults to `SECRET_KEY` if empty).
   - `ACCESS_TOKEN_EXPIRE_MINUTES`: Access token lifespan (default: `60`).
   - `REFRESH_TOKEN_EXPIRE_DAYS`: Refresh token lifespan (default: `14`).
   - `ALLOW_OPEN_REGISTRATION`: Defaults to `false`. When false, only the first user can register (becoming Owner).
   - `FIRST_OWNER_SETUP_TOKEN`: Optional setup token required for initial owner registration.
   - `LOGIN_RATE_LIMIT_MAX_ATTEMPTS`: Failed attempt threshold before lockout (default: `5`).
   - `LOGIN_RATE_LIMIT_WINDOW_SECONDS`: Sliding window duration (default: `300`).

---

## 4. Database Migrations (Alembic)

Database schema evolution is managed via **Alembic**:

### Apply Migrations
```powershell
.\.venv\Scripts\alembic.exe upgrade head
```

### Generate New Migration
When ORM models are added or modified in `backend/app/database/models/`:
```powershell
.\.venv\Scripts\alembic.exe revision --autogenerate -m "describe_changes"
```

### Check Current Migration Status
```powershell
.\.venv\Scripts\alembic.exe current
```

---

## 5. Running the Application

### Option A: Using the convenience runner script
```bash
python scripts/run_server.py
```

### Option B: Using Uvicorn CLI directly
```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive API documentation:
- **Swagger Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check Endpoint:** [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

---

## 6. Authentication & Device API Usage

### A. Register First Owner
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "owner@love.ai",
    "username": "loveowner",
    "password": "StrongPassword123!",
    "full_name": "Assistant Owner"
  }'
```
*Response returns the created user profile with `is_owner: true`.*

### B. Login & Obtain Tokens
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email_or_username": "owner@love.ai",
    "password": "StrongPassword123!",
    "device_identifier": "win-workstation-uuid-1",
    "device_name": "Studio Windows Rig",
    "device_type": "windows"
  }'
```
*Response returns `access_token`, `refresh_token`, and user profile.*

### C. Access Protected Profile
```bash
curl -X GET http://127.0.0.1:8000/api/v1/auth/me \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### D. Rotate Refresh Token
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "<REFRESH_TOKEN>"
  }'
```

### E. Register Client Device
```bash
curl -X POST http://127.0.0.1:8000/api/v1/devices/register \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "device_identifier": "macbook-air-m2-uuid",
    "device_name": "Portable MacBook",
    "device_type": "macos",
    "client_version": "0.2.0"
  }'
```

### F. List Registered Devices
```bash
curl -X GET http://127.0.0.1:8000/api/v1/devices \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### G. Revoke Device
```bash
curl -X DELETE http://127.0.0.1:8000/api/v1/devices/<DEVICE_ID> \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

---

## 7. Automated Testing

Run the automated test suite with pytest:

```bash
# Run all tests verbosely
pytest -v

# Run only authentication tests
pytest tests/test_auth_api.py tests/test_auth_security.py -v

# Run only device tests
pytest tests/test_device_api.py -v
```
