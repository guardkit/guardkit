"""Shared Pydantic schema patterns and base classes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema class for shared patterns across all schemas.

    This class establishes the foundation for consistent schema definitions
    throughout the application. All response schemas should inherit from this
    base class to ensure uniform behavior for JSON schema generation and
    response examples.
    """

    model_config = ConfigDict(
        use_enum_values=True,
        validate_default=True,
    )
