# LOVE — Personal AI Assistant

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%2B%20(Async)-red.svg)](https://www.sqlalchemy.org/)
[![Alembic](https://img.shields.io/badge/Alembic-1.13%2B-8A2BE2.svg)](https://alembic.sqlalchemy.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Phase%2002-Authentication%20%26%20Security%20Completed-brightgreen.svg)]()

> **LOVE** is an independent, modular, extensible, multi-platform personal AI assistant ecosystem inspired by the capabilities of Iron Man's JARVIS and FRIDAY.

LOVE is engineered as a general-purpose, persistent, and intelligent companion capable of operating seamlessly across **Windows, macOS, Linux, Android, iOS, and Web**.

---

## 1. Permanent Capability Pillars

1. **General Intelligent Conversations:** High-context, fluid multi-turn natural dialogue.
2. **Software Development & Programming:** Multi-language code authoring, refactoring, and architecture.
3. **Website & Application Development:** Full-stack development across web, desktop, and mobile.
4. **Debugging & Code Analysis:** Automated diagnostics, syntax auditing, and optimization.
5. **Image & Creative Assistance:** Multimodal generation, editing, SVG design, and wireframing.
6. **Document Creation & Analysis:** Comprehensive synthesis and generation of Markdown, PDF, and reports.
7. **Research & Problem Solving:** Deep-dive literature retrieval, citation validation, and analytical synthesis.
8. **Personal Productivity:** Contextual task management, reminders, scheduling, and morning briefings.
9. **File Operations:** Intelligent file search, workspace organization, and bulk content manipulation.
10. **Desktop Automation:** Multi-platform OS interaction, window management, and controlled scripting.
11. **Local & Cloud AI Models:** Dynamic routing between on-device GGUF models and frontier cloud LLMs.
12. **Persistent Personal Memory:** Working context, episodic recall, and semantic vector embeddings.
13. **Voice Interaction:** Ultra-low latency voice loop with "Hey Love" wake-word activation.
14. **Cross-Device Availability:** Synchronized state across desktop, web, and mobile with E2EE.

---

## 2. Authentication, User Identity & Device Security (Phase 02)

- **Argon2id Password Hashing:** OWASP-compliant parameter profile with random per-credential salt.
- **Dual-Token Lifecycle:** Cryptographically signed JWT access tokens paired with **hashed refresh tokens (SHA-256)**.
- **Refresh Token Rotation & Reuse Detection:** Immediate revocation of all active sessions if an already rotated token is presented.
- **Brute Force Protection:** In-memory sliding-window rate limiting on login attempts.
- **First-Owner Bootstrap Architecture:** The first registered account automatically becomes Owner; public signup automatically closes.
- **Multi-Platform Device Security:** Client installation UUID identification, device authorization, and remote session termination across Windows, macOS, Linux, Android, iOS, and Web.
- **Database Migrations:** Automated schema versioning via **Alembic** supporting async SQLite and PostgreSQL.

---

## 3. Implemented API Endpoints

### Authentication & Identity
- `POST /api/v1/auth/register` — Register primary owner / user
- `POST /api/v1/auth/login` — Authenticate and obtain JWT token pair
- `POST /api/v1/auth/refresh` — Rotate refresh token and obtain new access token
- `POST /api/v1/auth/logout` — Revoke active session (Authenticated)
- `GET /api/v1/auth/me` — Retrieve current authenticated user profile (Authenticated)

### Device Security
- `POST /api/v1/devices/register` — Register or update client device (Authenticated)
- `GET /api/v1/devices` — List user's registered devices (Authenticated)
- `DELETE /api/v1/devices/{device_id}` — Revoke device authorization and terminate sessions (Authenticated)

### System & Health
- `GET /health` / `GET /api/v1/health` — Subsystem liveness, uptime, and DB latency
- `GET /` — Basic application identity

---

## 4. Quickstart Guide

### 1. Setup Virtual Environment
```bash
# Navigate to LOVE root
cd LOVE

# Create virtual environment with uv or python -m venv
uv venv .venv --python 3.11

# Activate virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
uv pip install -r requirements.txt
```

### 3. Run Database Migrations
```bash
.\.venv\Scripts\alembic.exe upgrade head
```

### 4. Launch Server
```bash
python scripts/run_server.py
```

- **API Base:** `http://127.0.0.1:8000`
- **Interactive Swagger Docs:** `http://127.0.0.1:8000/docs`
- **Health Check Endpoint:** `http://127.0.0.1:8000/api/v1/health`

### 5. Run Automated Tests
```bash
pytest -v
```
*(All 33 tests execute in-memory with zero side effects).*

---

## 5. Official Voice Specification

- **Assistant Name:** LOVE
- **Vocal Style:** Hybrid Cinematic + Natural (JARVIS/FRIDAY poise + human warmth and cadence).
- **Gender:** Female
- **Accent:** Indian English (articulate, cultured, urban Indian English).
- **Implementation:** Azure Speech Services (primary cloud), ElevenLabs (secondary cloud), Piper (local offline), `faster-whisper` (STT), `openWakeWord` ("Hey Love").
