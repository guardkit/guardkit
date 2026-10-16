"""Version endpoint response schema."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class VersionResponse(BaseModel):
    """Version information response model."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "version": "0.1.0",
                    "commit": "1b0f90ba3c7e5d6a9f2b1c4d8e0f3a5b7c9d1e2f",
                    "service": "api",
                },
            ]
        }
    )

    version: str = Field(description="Application version string")
    commit: str = Field(description="Git commit hash (40 characters)")
    service: str = Field(description="Service name")
