"""Utilities for feature workflow operations."""
import re


def extract_feature_slug(title: str) -> str:
    """
    Extract feature slug from review task title.

    Converts a review task title into a URL/folder-safe slug by:
    1. Removing common prefixes (plan, review, investigate, analyze, assess)
    2. Removing "how to" phrases
    3. Converting to lowercase with hyphens
    4. Limiting length to 40 characters

    Args:
        title: The review task title to convert

    Returns:
        A URL/folder-safe slug, or "feature" if extraction fails

    Examples:
        >>> extract_feature_slug("Plan: implement dark mode")
        'implement-dark-mode'
        >>> extract_feature_slug("Review: user authentication system")
        'user-authentication-system'
        >>> extract_feature_slug("Investigate how to add caching")
        'add-caching'
        >>> extract_feature_slug("Plan: Add OAuth 2.0 Support!!!")
        'add-oauth-2-0-support'
        >>> extract_feature_slug("")
        'feature'
        >>> extract_feature_slug("Very long title that goes on and on about many things")
        'very-long-title-that-goes-on-and-on'
    """
    # Handle None input
    if title is None:
        return "feature"

    if not title or not title.strip():
        return "feature"

    # Remove common prefixes
    prefixes = ["plan:", "review:", "investigate:", "analyze:", "assess:"]
    lower_title = title.lower()

    for prefix in prefixes:
        if lower_title.startswith(prefix):
            title = title[len(prefix):].strip()
            break

    # Remove "how to" phrases
    title = re.sub(r'\bhow to\b', '', title, flags=re.IGNORECASE)

    # Convert to slug: replace non-alphanumeric chars with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower())

    # Remove leading/trailing hyphens
    slug = slug.strip('-')

    # Limit length to 40 characters, breaking at word boundary
    if len(slug) > 40:
        # Try to break at last hyphen before 40 chars
        truncated = slug[:40]
        last_hyphen = truncated.rfind('-')
        if last_hyphen > 0:
            slug = truncated[:last_hyphen]
        else:
            slug = truncated

    return slug or "feature"
