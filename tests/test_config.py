"""
Automated tests for configuration management.
Verifies environment variables, default settings, and schema validations.
"""

import os
from backend.app.config.settings import Settings, get_settings


def test_default_settings():
    """Verify default configuration attributes are correctly populated."""
    settings = Settings()
    assert settings.APP_NAME == "LOVE Personal AI Assistant"
    assert settings.APP_VERSION == "0.1.0"
    assert isinstance(settings.PORT, int)
    assert isinstance(settings.DEBUG, bool)
    assert settings.DATABASE_URL.startswith("sqlite")


def test_settings_environment_override(monkeypatch):
    """Verify environment variables take precedence over defaults."""
    monkeypatch.setenv("APP_NAME", "LOVE Custom Assistant")
    monkeypatch.setenv("PORT", "9090")
    monkeypatch.setenv("APP_ENV", "staging")

    custom_settings = Settings()
    assert custom_settings.APP_NAME == "LOVE Custom Assistant"
    assert custom_settings.PORT == 9090
    assert custom_settings.APP_ENV == "staging"


def test_cors_origins_parsing():
    """Verify CORS origins string is parsed into a list."""
    settings_str = Settings(CORS_ORIGINS="http://test.local, https://app.love.ai")
    assert "http://test.local" in settings_str.CORS_ORIGINS
    assert "https://app.love.ai" in settings_str.CORS_ORIGINS

    settings_list = Settings(CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"])
    assert len(settings_list.CORS_ORIGINS) == 2


def test_cached_get_settings():
    """Verify get_settings() returns a singleton Settings instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
