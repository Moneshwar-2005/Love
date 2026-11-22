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
    import argparse
    settings = get_settings()

    parser = argparse.ArgumentParser(description="Run LOVE Backend Server")
    parser.add_argument("--host", default=settings.HOST, help="Host to bind to")
    parser.add_argument("--port", type=int, default=settings.PORT, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", default=settings.RELOAD, help="Enable reload")
    parser.add_argument("--no-reload", dest="reload", action="store_false", help="Disable reload")
    parser.add_argument("--ssl-keyfile", default=settings.SSL_KEYFILE, help="Path to SSL private key file")
    parser.add_argument("--ssl-certfile", default=settings.SSL_CERTFILE, help="Path to SSL certificate file")
    args, _ = parser.parse_known_args()

    bind_host = args.host
    bind_port = args.port
    do_reload = args.reload
    ssl_key = args.ssl_keyfile
    ssl_cert = args.ssl_certfile
    is_https = bool(ssl_key and ssl_cert)
    scheme = "https" if is_https else "http"

    print("=" * 70)
    print("  LOVE — Personal AI Assistant (Phase 01 Foundation)")
    print(f"  Version:     {settings.APP_VERSION}")
    print(f"  Environment: {settings.APP_ENV}")
    print(f"  Protocol:    {scheme.upper()} ({'TLS Enabled' if is_https else 'Cleartext HTTP'})")
    print(f"  Server URL:  {scheme}://{bind_host}:{bind_port}")
    print(f"  API Docs:    {scheme}://{bind_host}:{bind_port}/docs")
    print(f"  Health:      {scheme}://{bind_host}:{bind_port}/api/v1/health")
    print("=" * 70)

    uvicorn_kwargs = {
        "app": "backend.app.main:app",
        "host": bind_host,
        "port": bind_port,
        "reload": do_reload,
        "log_level": settings.LOG_LEVEL.lower(),
    }
    if is_https:
        uvicorn_kwargs["ssl_keyfile"] = str(ssl_key)
        uvicorn_kwargs["ssl_certfile"] = str(ssl_cert)

    uvicorn.run(**uvicorn_kwargs)


if __name__ == "__main__":
    main()
