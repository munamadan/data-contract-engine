"""
Application configuration management using Pydantic Settings.
Loads configuration from environment variables.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    DATABASE_URL: str = "postgresql://dce_user:dce_password@localhost:5432/dce_db"
    
    # Application
    ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "debug"
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Data Contract Engine"
    VERSION: str = "0.1.0"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS
    CORS_ORIGINS: list[str] = ["*"]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENV == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENV == "production"


# Create global settings instance
settings = Settings()