"""Uptime response schema."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UptimeResponse(BaseModel):
    """Uptime response model.

    Provides the service name, start time, and current uptime in seconds.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "service": "api",
                    "started_at": "2024-01-01T00:00:00+00:00",
                    "uptime_seconds": 0.0,
                },
            ]
        }
    )

    service: str = Field(description="The name of the service")
    started_at: datetime = Field(
        description="ISO-8601 timestamp when the service started (with UTC offset)"
    )
    uptime_seconds: float = Field(
        description="Seconds elapsed since the service started"
    )
