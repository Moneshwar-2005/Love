# LOVE — Personal AI Assistant

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%2B%20(Async)-red.svg)](https://www.sqlalchemy.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Phase%2001.5-Audit%20%26%20Cleanup%20Completed-brightgreen.svg)]()

> **LOVE** is an independent, modular, extensible, multi-platform personal AI assistant ecosystem inspired by the capabilities of Iron Man's JARVIS and FRIDAY.

LOVE is engineered as a general-purpose, persistent, and intelligent companion capable of operating seamlessly across **Windows, macOS, Linux, Android, iOS, and Web**.

---

## 1. Permanent Capability Pillars

LOVE is designed around 14 permanent core capabilities:

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

## 2. Universal Intelligence Layer (UIL)

The cognitive core of LOVE features a dedicated **Universal Intelligence Layer** responsible for orchestrating intelligence:
- **Intent Recognition:** Categorizes input queries and dispatches specialized execution paths.
- **Model Routing:** Intelligently routes tasks to local GGUF models (privacy/offline) or frontier cloud models (reasoning/scale).
- **Reasoning & Planning:** Formulates multi-step execution plans with self-refining feedback loops.
- **Specialized Agent Orchestration:** Coordinates specialized agents (coding, debugging, research, automation).
- **Tool Integration & Sandbox:** Safely executes system tools within secure sandbox boundaries.
- **Project Workspace Management:** Tracks project workspaces, file trees, and git working states.
- **Human Approval Controls:** Enforces interactive permission gates for privileged or destructive operations.
- **Action History & Audit Logger:** Maintains an immutable action ledger for full accountability and rollback.

---

## 3. Official Voice Specification

- **Name:** LOVE
- **Identity Style:** Hybrid Cinematic + Natural (JARVIS/FRIDAY poise combined with human warmth).
- **Gender:** Female
- **Accent:** Indian English (articulate, elegant, cultured)
- **Personality:** Intelligent, elegant, calm, confident, and proactive.
- **Implementation Strategy:**
  - *Cloud TTS (Primary):* Azure Speech Services (`en-IN-NeerjaNeural` / `en-IN-KavyaNeural`).
  - *Cloud TTS (Alternative):* ElevenLabs expressive voice cloning.
  - *Offline Local TTS:* Piper neural TTS engine.
  - *Speech-to-Text (STT):* `faster-whisper` on-device speech recognition.
  - *Wake-Word:* `openWakeWord` ("Hey Love") for instant on-device activation.
  - *Coupling Guarantee:* The voice engine is completely decoupled from the LLM core.

*See [documentation/VOICE_SPECIFICATION.md](documentation/VOICE_SPECIFICATION.md) for full acoustic specifications.*

---

## 4. Project Structure

```text
LOVE/
├── backend/                  # Backend application source code
│   ├── app/
│   │   ├── api/              # Versioned API routes (v1)
│   │   │   └── v1/
│   │   │       ├── endpoints/
│   │   │       │   └── health.py
│   │   │       └── api.py
│   │   ├── authentication/   # Auth & device pairing (Phase 02)
│   │   ├── automation/       # Desktop automation (Phase 07)
│   │   ├── config/           # Pydantic settings & environment manager
│   │   ├── core/             # Logging, exceptions, and middlewares
│   │   ├── database/         # Async engine, sessionmaker, and Base
│   │   ├── intelligence/     # Universal Intelligence Layer (Phase 03)
│   │   ├── memory/           # Persistent vector memory (Phase 04)
│   │   ├── productivity/     # Tasks & reminders (Phase 06)
│   │   ├── security/         # Cryptography & sandboxing (Phase 08)
│   │   ├── synchronization/  # Cross-device sync (Phase 09)
│   │   ├── voice/            # Wake-word & TTS engine (Phase 05)
│   │   └── main.py           # FastAPI entrypoint
│   └── requirements.txt
├── desktop/                  # Tauri desktop application (future)
├── web/                      # React + TypeScript web application (future)
├── mobile/                   # Flutter iOS/Android application (future)
├── shared/                   # Schemas and constants shared across platforms
│   ├── constants.py
│   └── schemas/
│       └── health.py
├── models/                   # Local GGUF, tokenizer, and acoustic model weights
├── database/                 # SQLite storage and Alembic migrations
│   ├── migrations/
│   │   └── .gitkeep
│   └── README.md
├── scripts/                  # Operational utility scripts
│   ├── init_db.py            # Database initialization and connectivity test
│   └── run_server.py         # Development server launcher
├── tests/                    # Automated pytest suite
│   ├── conftest.py           # Test fixtures and in-memory DB configuration
│   ├── test_config.py        # Settings and environment variable tests
│   ├── test_database.py      # Database session and query tests
│   └── test_health.py        # Health API validation tests
├── documentation/            # Comprehensive documentation
│   ├── ARCHITECTURE.md       # Full architecture specification
│   ├── DEVELOPMENT_GUIDE.md  # Local setup & developer workflow
│   ├── PROJECT_STATUS.md     # Roadmap, status & verification logs
│   └── VOICE_SPECIFICATION.md# Official voice pipeline architecture
├── archive/                  # Preserved legacy experimental artifacts
├── .env.example              # Environment configuration template
├── .gitignore                # Git ignore rules
├── pyproject.toml            # Project build configuration & pytest settings
└── requirements.txt          # Root Python dependencies
```

---

## 5. Quickstart Guide

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

### 3. Initialize Database & Run
```bash
# Initialize local SQLite database
python scripts/init_db.py

# Launch development server
python scripts/run_server.py
```

- **API Base:** `http://127.0.0.1:8000`
- **Interactive Swagger Docs:** `http://127.0.0.1:8000/docs`
- **Health Check Endpoint:** `http://127.0.0.1:8000/api/v1/health`

### 4. Run Automated Tests
```bash
pytest -v
```

---

## 6. Project Independence Guarantee

LOVE is an entirely standalone, greenfield ecosystem:
- Completely isolated from legacy projects (including KURO and FRIDAY).
- Dedicated namespace (`love.*`), isolated database (`database/love.db`), and distinct configuration environment.
- All secrets and API credentials reside strictly in local `.env` variables and are never committed.
