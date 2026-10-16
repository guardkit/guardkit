"""Whoami response schema."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WhoamiResponse(BaseModel):
    """Whoami response model."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"service": "api_test"},
            ]
        }
    )

    service: str = Field(description="The name of the API service")
