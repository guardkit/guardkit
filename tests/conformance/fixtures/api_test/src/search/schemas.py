"""Search API response schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SearchResponse(BaseModel):
    """Response model for search queries."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "query": "test",
                    "results": [],
                    "total": 0,
                },
            ]
        }
    )

    query: str = Field(description="The search query string")
    results: list[str] = Field(
        default_factory=list,
        description="List of matching results",
    )
    total: int = Field(
        default=0,
        description="Total number of results found",
    )
