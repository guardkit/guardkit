"""Core configuration module for the FastAPI application."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment and .env file."""

    model_config = SettingsConfigDict(env_file=".env")

    # Basic app info
    app_name: str = "api_test"
    app_env: str = "development"
    app_version: str = "0.1.0"
    debug: bool = False

    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "json"

    # Database configuration
    database_url: str = "postgresql+asyncpg://postgres:test@localhost:5432/test"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: float = 30.0
    db_pool_recycle: int = 3600
    db_echo: bool = False

    # Documentation / OpenAPI metadata
    app_description: str = (
        "A production-ready FastAPI backend template implementing best practices "
        "for scalable, maintainable APIs with async support, database integration, "
        "and comprehensive testing infrastructure."
    )
    app_summary: str = "Production-ready FastAPI backend template"
    app_contact_name: str = "API Support"
    app_contact_email: str = "support@example.com"
    app_contact_url: str = "https://example.com/support"
    app_license_name: str = "MIT"
    app_license_url: str = "https://opensource.org/licenses/MIT"
    app_terms_of_service: str = "https://example.com/terms"


settings = Settings()
