"""Time endpoint response schema."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TimeResponse(BaseModel):
    """Time endpoint response model.

    Contains the current UTC time and the service name.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "time": "2026-07-31T12:34:56Z",
                    "service": "api_test",
                },
            ]
        },
    )

    time: str = Field(description="Current UTC time in ISO-8601 second precision with trailing Z")
    service: str = Field(description="Service name", default="api_test")
