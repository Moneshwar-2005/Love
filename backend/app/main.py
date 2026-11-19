"""
FastAPI Application Entry Point for LOVE Personal AI Assistant.
"""

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.v1.api import api_v1_router
from backend.app.api.v1.endpoints import health
from backend.app.config.settings import get_settings
from backend.app.core.exceptions import register_exception_handlers
from backend.app.core.logging import get_logger, setup_logging
from backend.app.database.session import close_database_connection, init_db

settings = get_settings()
setup_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager managing startup and shutdown routines.
    """
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.APP_ENV}]...")
    try:
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception as exc:
        logger.critical(f"Database initialization failed during startup: {exc}", exc_info=True)
        # In development, we allow the app to boot so the health check endpoint can report the degraded status

    yield

    logger.info(f"Shutting down {settings.APP_NAME}...")
    await close_database_connection()
    logger.info("Shutdown sequence completed.")


def create_application() -> FastAPI:
    """
    Application factory initializing the FastAPI instance with middleware, routes, and error handlers.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="LOVE — Modular, extensible, multi-platform personal AI assistant ecosystem.",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request Timing and Logging Middleware
    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.debug(
            f"{request.method} {request.url.path} -> {response.status_code} ({process_time_ms}ms)"
        )
        response.headers["X-Process-Time-Ms"] = str(process_time_ms)
        return response

    # Exception Handlers
    register_exception_handlers(app)

    # Root route
    @app.get("/", tags=["Root"], summary="Application Info")
    async def root_info() -> JSONResponse:
        return JSONResponse(
            content={
                "app_name": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "environment": settings.APP_ENV,
                "status": "online",
                "documentation": "/docs" if settings.DEBUG else "disabled in production",
            }
        )

    # Mount API routers
    # Root level health endpoint (for health probes)
    app.include_router(health.router)

    # Versioned API router (/api/v1/...)
    app.include_router(api_v1_router, prefix="/api")

    return app


app = create_application()
