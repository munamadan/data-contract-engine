import pytest
from app.config import Settings


def test_settings_loads():
    settings = Settings()
    assert settings is not None
    assert settings.PROJECT_NAME == "Data Contract Engine"


def test_settings_has_database_url():
    settings = Settings()
    assert settings.DATABASE_URL is not None
    assert "postgresql://" in settings.DATABASE_URL


def test_is_development():
    settings = Settings(ENV="development")
    assert settings.is_development is True
    assert settings.is_production is False


def test_is_production():
    settings = Settings(ENV="production")
    assert settings.is_production is True
    assert settings.is_development is False