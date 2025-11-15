"""Tests for configuration management."""

import pytest
from app.config import Settings


def test_settings_loads():
    """Test that settings can be instantiated."""
    settings = Settings()
    assert settings is not None
    assert settings.PROJECT_NAME == "Data Contract Engine"


def test_settings_has_database_url():
    """Test that database URL is configured."""
    settings = Settings()
    assert settings.DATABASE_URL is not None
    assert "postgresql://" in settings.DATABASE_URL


def test_is_development():
    """Test development environment detection."""
    settings = Settings(ENV="development")
    assert settings.is_development is True
    assert settings.is_production is False


def test_is_production():
    """Test production environment detection."""
    settings = Settings(ENV="production")
    assert settings.is_production is True
    assert settings.is_development is False