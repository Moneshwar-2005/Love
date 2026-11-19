"""
Centralized configuration management for the LOVE backend ecosystem.
Powered by Pydantic Settings.
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root directory resolution
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.
    All secrets must be provided via environment variables in production.
    """

    # Application Metadata
    APP_NAME: str = Field(default="LOVE Personal AI Assistant", description="Application name")
    APP_ENV: str = Field(default="development", description="Runtime environment: development, staging, production, testing")
    APP_VERSION: str = Field(default="0.1.0", description="Application version")
    DEBUG: bool = Field(default=True, description="Enable debug mode")

    # Server Configuration
    HOST: str = Field(default="127.0.0.1", description="Server bind host")
    PORT: int = Field(default=8000, description="Server port")
    WORKERS: int = Field(default=1, description="Number of Uvicorn worker processes")
    RELOAD: bool = Field(default=True, description="Enable Uvicorn auto-reload")

    # Security & Authentication
    SECRET_KEY: str = Field(
        default="love-dev-secret-key-replace-in-production-min-32-chars",
        description="Cryptographic secret key for signing tokens and sessions"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=1440,
        description="Access token lifespan in minutes (default: 24 hours)"
    )
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8080",
            "tauri://localhost",
        ],
        description="Allowed CORS origins"
    )

    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./database/love.db",
        description="Asynchronous database connection URL"
    )
    DATABASE_ECHO: bool = Field(
        default=False,
        description="Enable SQLAlchemy SQL query echo for debugging"
    )

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    LOG_FORMAT: str = Field(default="text", description="Log output format: text or json")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, tuple)):
            return list(v)
        return []

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Retrieve cached application settings instance.
    """
    return Settings()
