"""Health check response schema."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Health check response model."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "ok",
                    "version": "0.1.0",
                    "log_level": "INFO",
                    "log_format": "json",
                },
            ]
        }
    )

    status: str = Field(description="Service health status")
    version: str = Field(description="API version string")
    log_level: str = Field(
        description="Current configured log level (e.g., INFO, DEBUG)"
    )
    log_format: str = Field(
        description="Current configured log format (e.g., json, console)"
    )
    database: str = Field(
        description="Database connection status (e.g., connected, unavailable)"
    )


class ReadyResponse(BaseModel):
    """Readiness check response model."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"status": "ready", "service": "api"},
            ]
        }
    )

    status: str = Field(description="Service readiness status")
    service: str = Field(description="The name of the service")
