"""
Development Server Runner for LOVE Personal AI Assistant.
Usage:
    python scripts/run_server.py
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn
from backend.app.config.settings import get_settings


def main() -> None:
    settings = get_settings()

    print("=" * 70)
    print("  LOVE — Personal AI Assistant (Phase 01 Foundation)")
    print(f"  Version:     {settings.APP_VERSION}")
    print(f"  Environment: {settings.APP_ENV}")
    print(f"  Server URL:  http://{settings.HOST}:{settings.PORT}")
    print(f"  API Docs:    http://{settings.HOST}:{settings.PORT}/docs")
    print(f"  Health:      http://{settings.HOST}:{settings.PORT}/api/v1/health")
    print("=" * 70)

    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
