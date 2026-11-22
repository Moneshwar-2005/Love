"""
Centralized configuration management for the LOVE backend ecosystem.
Powered by Pydantic Settings.
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Union
from pydantic import Field, field_validator, model_validator
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
    APP_VERSION: str = Field(default="0.2.0", description="Application version")
    DEBUG: bool = Field(default=True, description="Enable debug mode")

    # Server Configuration
    HOST: str = Field(default="127.0.0.1", description="Server bind host")
    PORT: int = Field(default=8000, description="Server port")
    WORKERS: int = Field(default=1, description="Number of Uvicorn worker processes")
    RELOAD: bool = Field(default=True, description="Enable Uvicorn auto-reload")
    SSL_KEYFILE: Optional[str] = Field(
        default=None,
        description="Path to SSL private key file for HTTPS (development or production)"
    )
    SSL_CERTFILE: Optional[str] = Field(
        default=None,
        description="Path to SSL certificate file for HTTPS (development or production)"
    )

    # Security & Cryptography
    SECRET_KEY: str = Field(
        default="love-dev-secret-key-replace-in-production-min-32-chars",
        description="Cryptographic secret key for signing tokens and sessions"
    )
    JWT_SECRET_KEY: str = Field(
        default="",
        description="Dedicated JWT secret key (falls back to SECRET_KEY if empty)"
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60,
        description="Access token lifespan in minutes (default: 1 hour)"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=14,
        description="Refresh token lifespan in days (default: 14 days)"
    )
    JWT_ISSUER: str = Field(default="love-assistant", description="JWT issuer claim (iss)")
    JWT_AUDIENCE: str = Field(default="love-client", description="JWT audience claim (aud)")

    # Registration & Initial Owner Setup
    ALLOW_OPEN_REGISTRATION: bool = Field(
        default=False,
        description="Whether to permit multi-user registrations after the primary owner account is created"
    )
    FIRST_OWNER_SETUP_TOKEN: str = Field(
        default="",
        description="Optional pre-shared setup token required for initial owner registration"
    )
    PASSWORD_MIN_LENGTH: int = Field(default=8, description="Minimum password length")

    # Rate Limiting
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS: int = Field(
        default=5,
        description="Maximum failed login attempts within the rate-limit window"
    )
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = Field(
        default=300,
        description="Login rate limit window in seconds (default: 5 minutes)"
    )

    # CORS & Cross-Origin Configuration
    DEV_CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://testserver",
            "tauri://localhost",
            "https://localhost",
            "http://localhost",
            "capacitor://localhost",
        ],
        description="Development CORS origins enabled only in non-production environments"
    )
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=[],
        description="Explicitly allowed CORS origins. If empty in development/testing, defaults to DEV_CORS_ORIGINS."
    )
    ALLOW_LOCALHOST_IN_PRODUCTION: bool = Field(
        default=False,
        description="Explicit override permitting localhost CORS origins in production"
    )

    # Auth Cookie Settings
    COOKIE_SECURE: Optional[bool] = Field(
        default=None,
        description="Enforce Secure flag on auth cookies. Defaults to True in production, False in dev/test."
    )
    COOKIE_SAMESITE: str = Field(
        default="lax",
        description="SameSite policy for auth cookies ('lax', 'strict', 'none')."
    )
    COOKIE_DOMAIN: Optional[str] = Field(
        default=None,
        description="Domain scope for auth cookies. None leaves domain unset for host-only cookies."
    )
    COOKIE_PATH: str = Field(
        default="/api/v1/auth",
        description="Path scope for auth refresh cookies."
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
    DATABASE_POOL_SIZE: int = Field(
        default=5,
        description="SQLAlchemy connection pool base size for client-server engines (PostgreSQL)"
    )
    DATABASE_MAX_OVERFLOW: int = Field(
        default=10,
        description="Maximum temporary connections above pool_size"
    )
    DATABASE_POOL_TIMEOUT: int = Field(
        default=30,
        description="Seconds to wait before giving up on obtaining a connection from the pool"
    )
    DATABASE_POOL_RECYCLE: int = Field(
        default=1800,
        description="Recycle connections after N seconds (prevents stale TCP connections)"
    )
    DATABASE_SQLITE_BUSY_TIMEOUT_MS: int = Field(
        default=10000,
        description="SQLite busy timeout in milliseconds (retries lock contention)"
    )
    DATABASE_SQLITE_WAL_MODE: bool = Field(
        default=True,
        description="Enable SQLite Write-Ahead Logging (WAL) for high concurrency"
    )
    DATABASE_BACKUP_DIR: str = Field(
        default="database/backups",
        description="Directory for local verified database backups"
    )
    DATABASE_BACKUP_RETENTION_COUNT: int = Field(
        default=10,
        description="Maximum number of historical backups to retain before pruning"
    )
    DATABASE_AUTO_BACKUP_ENABLED: bool = Field(
        default=False,
        description="Enable automatic periodic database backups"
    )

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    LOG_FORMAT: str = Field(default="text", description="Log output format: text or json")

    # Universal Intelligence Layer & Model Routing (Phase 03)
    DEFAULT_PROVIDER: str = Field(
        default="auto",
        description="Default AI provider identifier: auto, ollama, openai, anthropic, gemini, openai_compatible"
    )
    DEFAULT_MODEL: str = Field(
        default="auto",
        description="Default model identifier or 'auto' for task-based dynamic routing"
    )
    ROUTING_PREFERENCE: str = Field(
        default="auto",
        description="Routing policy: auto, local_first, cloud_first, local_only, cost_optimized"
    )
    LOCAL_ONLY_MODE: bool = Field(
        default=False,
        description="Strict privacy constraint: when True, requests are never routed to cloud providers"
    )
    OLLAMA_BASE_URL: str = Field(
        default="http://127.0.0.1:11434",
        description="Base HTTP URL for local Ollama service"
    )
    OLLAMA_TIMEOUT_SECONDS: int = Field(
        default=60,
        description="Timeout in seconds for local Ollama HTTP requests"
    )
    OPENAI_API_KEY: str = Field(
        default="",
        description="API key for OpenAI provider (disabled if empty)"
    )
    OPENAI_BASE_URL: str = Field(
        default="https://api.openai.com/v1",
        description="Base URL for OpenAI API"
    )
    ANTHROPIC_API_KEY: str = Field(
        default="",
        description="API key for Anthropic Claude provider (disabled if empty)"
    )
    ANTHROPIC_BASE_URL: str = Field(
        default="https://api.anthropic.com/v1",
        description="Base URL for Anthropic API"
    )
    GEMINI_API_KEY: str = Field(
        default="",
        description="API key for Google Gemini provider (disabled if empty)"
    )
    GEMINI_BASE_URL: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta",
        description="Base URL for Google Gemini API"
    )
    OPENAI_COMPATIBLE_API_KEY: str = Field(
        default="",
        description="API key for generic OpenAI-compatible provider"
    )
    OPENAI_COMPATIBLE_BASE_URL: str = Field(
        default="",
        description="Base URL for generic OpenAI-compatible provider (e.g. LocalAI, vLLM, LM Studio)"
    )
    INTELLIGENCE_CONTEXT_MAX_MESSAGES: int = Field(
        default=20,
        description="Maximum recent messages to include in conversation context window"
    )
    INTELLIGENCE_CONTEXT_MAX_TOKENS: int = Field(
        default=4096,
        description="Estimated token ceiling for context window budget"
    )
    INTELLIGENCE_REQUEST_TIMEOUT_SECONDS: int = Field(
        default=60,
        description="Global timeout in seconds for LLM inference requests"
    )

    # Persistent Personal Memory & Vector Retrieval (Phase 04)
    MEMORY_EMBEDDING_PROVIDER: str = Field(
        default="auto",
        description="Embedding provider identifier: auto, ollama, gemini, deterministic, none"
    )
    MEMORY_OLLAMA_EMBEDDING_MODEL: str = Field(
        default="qwen2.5:1.5b",
        description="Local Ollama model identifier to query for embeddings"
    )
    MEMORY_VECTOR_STORE_TYPE: str = Field(
        default="local",
        description="Vector storage backend: local (vectorized in-memory/disk) or qdrant"
    )
    MEMORY_VECTOR_STORAGE_PATH: str = Field(
        default="database/vectors",
        description="Directory path for local vector indices"
    )
    MEMORY_ALLOW_CLOUD_EMBEDDINGS: bool = Field(
        default=False,
        description="Strict privacy guard: whether to permit sending memory text to cloud embedding APIs (default False)"
    )
    MEMORY_RETRIEVAL_TOP_K: int = Field(
        default=5,
        description="Maximum relevant memory items to inject into conversation context"
    )
    MEMORY_RETRIEVAL_MIN_SCORE: float = Field(
        default=0.30,
        description="Minimum hybrid similarity threshold for retrieved memories"
    )
    MEMORY_AUTO_EXTRACT_ENABLED: bool = Field(
        default=True,
        description="Whether memory extraction service scans prompts for memory candidates"
    )
    MEMORY_DEDUPLICATION_THRESHOLD: float = Field(
        default=0.85,
        description="Similarity threshold above which memories are updated rather than duplicated"
    )

    # Universal Work Intelligence & Safe Tool Orchestration (Phase 05)
    WORKSPACE_ROOT: str = Field(
        default="workspace",
        description="Base directory path for workspace file and coding tools (relative or absolute)"
    )
    TOOL_EXECUTION_TIMEOUT_SECONDS: int = Field(
        default=30,
        description="Default timeout in seconds for individual tool execution"
    )
    TOOL_REQUIRE_CONFIRMATION_FOR_MEDIUM_RISK: bool = Field(
        default=True,
        description="Whether medium risk tool actions require user confirmation"
    )
    RESEARCH_PROVIDER: str = Field(
        default="mock",
        description="Research search provider: mock, searxng, tavily, duckduckgo (mock default when no API key)"
    )

    # Voice Engine, Speech Recognition & Wake Word (Phase 06)
    VOICE_ENABLED: bool = Field(
        default=True,
        description="Master toggle for the voice engine"
    )
    VOICE_STT_PROVIDER: str = Field(
        default="faster_whisper",
        description="Default speech-to-text provider: faster_whisper, mock"
    )
    VOICE_WHISPER_MODEL: str = Field(
        default="base",
        description="Faster-Whisper model size: tiny, base, small, medium, large-v3"
    )
    VOICE_WHISPER_DEVICE: str = Field(
        default="auto",
        description="Compute device for Whisper: auto, cuda, cpu"
    )
    VOICE_WHISPER_COMPUTE_TYPE: str = Field(
        default="int8",
        description="Whisper computation quantization type: int8, float16, float32"
    )
    VOICE_WHISPER_LANGUAGE: str = Field(
        default="en",
        description="Default language code for STT transcription (en for English, including Indian English)"
    )
    VOICE_STT_TIMEOUT_SECONDS: int = Field(
        default=30,
        description="Timeout in seconds for speech-to-text transcription"
    )
    VOICE_WAKE_WORD_ENABLED: bool = Field(
        default=False,
        description="Whether wake-word listening is enabled (opt-in only, never true by default)"
    )
    VOICE_WAKE_WORD_PROVIDER: str = Field(
        default="openwakeword",
        description="Wake-word engine provider: openwakeword, mock"
    )
    VOICE_WAKE_WORD_PHRASE: str = Field(
        default="Hey LOVE",
        description="Target wake phrase"
    )
    VOICE_WAKE_WORD_THRESHOLD: float = Field(
        default=0.5,
        description="Confidence threshold for wake-word activation (0.0 to 1.0)"
    )
    VOICE_TTS_PROVIDER: str = Field(
        default="auto",
        description="TTS provider: auto, azure, elevenlabs, piper, mock"
    )
    VOICE_TTS_LOCAL_FALLBACK: bool = Field(
        default=True,
        description="Whether to fall back to local/mock TTS provider if cloud provider fails or is unconfigured"
    )
    VOICE_AZURE_SPEECH_KEY: str = Field(
        default="",
        description="Azure Speech Services subscription key"
    )
    VOICE_AZURE_SPEECH_REGION: str = Field(
        default="",
        description="Azure Speech Services region (e.g. centralindia, eastus)"
    )
    VOICE_AZURE_VOICE_NAME: str = Field(
        default="en-IN-NeerjaNeural",
        description="Azure neural voice name (default: Indian English female voice Neerja)"
    )
    VOICE_ELEVENLABS_API_KEY: str = Field(
        default="",
        description="ElevenLabs API key"
    )
    VOICE_ELEVENLABS_VOICE_ID: str = Field(
        default="",
        description="ElevenLabs Voice ID"
    )
    VOICE_PIPER_BINARY_PATH: str = Field(
        default="",
        description="Path to local Piper TTS binary"
    )
    VOICE_PIPER_MODEL_PATH: str = Field(
        default="",
        description="Path to local Piper ONNX voice model"
    )
    VOICE_PIPER_CONFIG_PATH: str = Field(
        default="",
        description="Path to local Piper JSON model config"
    )
    VOICE_DEFAULT_PERSONALITY: str = Field(
        default="love_classic",
        description="Voice personality profile identifier"
    )
    VOICE_AUDIO_MAX_DURATION_SECONDS: int = Field(
        default=120,
        description="Maximum permissible audio recording duration in seconds"
    )
    VOICE_AUDIO_MAX_FILE_SIZE_BYTES: int = Field(
        default=15 * 1024 * 1024,
        description="Maximum permissible audio upload size in bytes (15 MB)"
    )
    VOICE_AUDIO_TEMP_DIR: str = Field(
        default="workspace/audio_temp",
        description="Temporary directory for audio conversion and buffering"
    )
    VOICE_RETAIN_AUDIO: bool = Field(
        default=False,
        description="Strict privacy constraint: whether to retain raw user audio files permanently (default: False)"
    )

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

    @property
    def effective_jwt_secret(self) -> str:
        """Returns JWT_SECRET_KEY if configured, otherwise falls back to SECRET_KEY."""
        return self.JWT_SECRET_KEY if self.JWT_SECRET_KEY else self.SECRET_KEY

    @property
    def effective_cookie_secure(self) -> bool:
        """Returns explicitly configured COOKIE_SECURE or True in production / when TLS is enabled."""
        if self.COOKIE_SECURE is not None:
            return self.COOKIE_SECURE
        if self.APP_ENV == "testing":
            return False
        return self.APP_ENV == "production" or bool(self.SSL_KEYFILE and self.SSL_CERTFILE)

    @property
    def effective_cors_origins(self) -> List[str]:
        """
        Returns active CORS origins:
        In production, uses explicit CORS_ORIGINS.
        In development/testing, falls back to DEV_CORS_ORIGINS if CORS_ORIGINS is empty.
        """
        if self.CORS_ORIGINS:
            origins = self.CORS_ORIGINS if isinstance(self.CORS_ORIGINS, list) else [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
            if origins:
                return origins
        if self.APP_ENV != "production":
            return list(self.DEV_CORS_ORIGINS)
        return []

    @property
    def MEMORY_AUTO_EXTRACT(self) -> bool:
        """Alias for MEMORY_AUTO_EXTRACT_ENABLED."""
        return self.MEMORY_AUTO_EXTRACT_ENABLED

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Enforces security rules when running in production environment."""
        if self.APP_ENV == "production":
            insecure_keys = {
                "love-dev-secret-key-replace-in-production-min-32-chars",
                "love-development-insecure-secret-key-replace-in-production-32c",
                "change-me-in-production-love-super-secret-key-32chars",
                "generate-a-secure-random-32-character-secret-key-for-production",
            }
            if self.effective_jwt_secret in insecure_keys or len(self.effective_jwt_secret) < 32:
                raise ValueError(
                    "CRITICAL SECURITY: Insecure or default SECRET_KEY detected in production environment. "
                    "You must provide a secure, unique SECRET_KEY or JWT_SECRET_KEY of at least 32 characters."
                )
            if self.DEBUG:
                raise ValueError("CRITICAL SECURITY: DEBUG mode must be disabled in production.")

            # Validate CORS policy in production
            active_origins = self.effective_cors_origins
            for origin in active_origins:
                if "*" in origin:
                    raise ValueError(
                        "CRITICAL SECURITY: Wildcard '*' CORS origin is strictly prohibited with credentialed requests in production."
                    )
                if ("localhost" in origin or "127.0.0.1" in origin) and not self.ALLOW_LOCALHOST_IN_PRODUCTION:
                    raise ValueError(
                        f"CRITICAL SECURITY: Localhost origin '{origin}' is not permitted in production CORS_ORIGINS without ALLOW_LOCALHOST_IN_PRODUCTION=True."
                    )
        return self

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
