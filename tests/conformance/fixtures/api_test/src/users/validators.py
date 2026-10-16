"""Validation utilities for users module."""

from __future__ import annotations

import re
from uuid import UUID

from fastapi import HTTPException

MAX_LIMIT = 100
MIN_COUNT_MAX = 10_000

# Allowed characters in a user ID: alphanumeric, hyphens, underscores
# This is stricter than UUID format to prevent special character injection
_VALID_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def validate_user_id(user_id: str) -> str:
    """Validate a user ID segment.

    Checks that the ID segment is non-empty and contains only valid
    characters (alphanumeric, hyphens, underscores). This prevents
    injection of special characters that could be used for attacks.

    Args:
        user_id: The user ID string to validate.

    Returns:
        The validated user ID string.

    Raises:
        ValueError: If the ID is empty or contains invalid characters.
    """
    if not user_id or not user_id.strip():
        raise ValueError("User ID must not be empty")

    if not _VALID_ID_PATTERN.match(user_id):
        raise ValueError(f"User ID contains invalid characters: '{user_id}'")

    # Also validate that it's a valid UUID format
    try:
        UUID(user_id)
    except ValueError:
        raise ValueError(f"User ID must be a valid UUID: '{user_id}'") from None

    return user_id


def get_validated_user_id(user_id: str) -> str:
    """FastAPI dependency that validates a user ID path parameter.

    This dependency runs before other dependencies (like database session)
    to ensure invalid IDs are caught early and return 400 Bad Request
    instead of propagating to database operations.

    Args:
        user_id: The user ID from the path parameter.

    Returns:
        The validated user ID string.

    Raises:
        HTTPException: 400 Bad Request if the ID is invalid.
    """
    try:
        return validate_user_id(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def validate_limit(limit_str: str) -> int:
    """Validate and parse a limit query parameter.

    Args:
        limit_str: The limit value as a string from the query parameter.

    Returns:
        The validated limit as an integer.

    Raises:
        ValueError: If the limit is not a positive integer or exceeds MAX_LIMIT.
    """
    try:
        limit = int(limit_str)
    except (ValueError, TypeError):
        raise ValueError("limit must be a positive integer") from None

    if limit <= 0:
        raise ValueError("limit must be a positive integer")

    if limit > MAX_LIMIT:
        raise ValueError(f"limit must not exceed {MAX_LIMIT}")

    return limit


def validate_min_count(min_count: str | None) -> int | None:
    """Validate and parse a min_count query parameter.

    Args:
        min_count: The min_count value as a string from the query parameter,
            or None if the parameter was omitted.

    Returns:
        The validated min_count as an integer, or None if the parameter
        was omitted (no filtering applied).

    Raises:
        ValueError: If the value is an empty string, not an integer, negative,
            or exceeds the maximum allowed value.
    """
    if min_count is None:
        return None

    if min_count == "":
        raise ValueError("min_count must not be empty")

    try:
        value = int(min_count)
    except (ValueError, TypeError):
        raise ValueError("min_count must be a valid integer") from None

    if value < 0:
        raise ValueError("min_count must not be negative")

    if value > MIN_COUNT_MAX:
        raise ValueError(f"min_count must not exceed {MIN_COUNT_MAX}")

    return value


def get_validated_min_count(min_count: str | None = None) -> int | None:
    """FastAPI dependency that validates a min_count query parameter.

    This dependency runs before the service layer to ensure invalid
    min_count values are caught early and return 400 Bad Request.

    Args:
        min_count: The min_count value from the query parameter,
            or None if the parameter was omitted.

    Returns:
        The validated min_count as an integer, or None if the parameter
        was omitted (no filtering applied).

    Raises:
        HTTPException: 400 Bad Request if the min_count is invalid.
    """
    try:
        return validate_min_count(min_count)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
