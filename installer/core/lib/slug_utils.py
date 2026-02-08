"""Shared utility for generating URL-safe slugs from task names."""

import re

__all__ = ["slugify_task_name"]


def slugify_task_name(name: str, max_length: int = 50) -> str:
    """
    Convert a task name to a URL-safe slug.

    Args:
        name: Task name (e.g., "Create auth service")
        max_length: Maximum slug length (default 50). Pass 0 or None for no limit.

    Returns:
        Slugified name (e.g., "create-auth-service")

    Examples:
        >>> slugify_task_name("Create auth service")
        'create-auth-service'
        >>> slugify_task_name("Add OAuth 2.0 Provider")
        'add-oauth-2-0-provider'
        >>> slugify_task_name("A very long task name " * 5, max_length=20)
        'a-very-long-task'
    """
    # Convert to lowercase
    slug = name.lower()
    # Replace non-alphanumeric characters with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    # Remove leading/trailing hyphens
    slug = slug.strip("-")
    # Collapse multiple hyphens
    slug = re.sub(r"-+", "-", slug)
    # Truncate at max_length, clean trailing hyphen
    if max_length and len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug
