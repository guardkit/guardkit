"""Security Detection Module for AutoBuild Security Gate (TASK-SEC-004).

This module provides pre-loop security tag and keyword detection to determine
whether a task requires full security review before implementation begins.

Detection is performed in the following priority order:
1. Configuration override (force_full_review flag)
2. Security level check (SKIP, STRICT, MINIMAL, STANDARD)
3. Tag-based detection (case-insensitive match against SECURITY_TAGS)
4. Keyword-based detection (title and description analysis)

Example:
    >>> from guardkit.orchestrator.security_config import SecurityConfig, SecurityLevel
    >>> from guardkit.orchestrator.quality_gates.security_detection import should_run_full_review
    >>>
    >>> task = {'id': 'TASK-001', 'title': 'Implement login', 'tags': ['auth']}
    >>> config = SecurityConfig(level=SecurityLevel.STANDARD)
    >>> should_run_full_review(task, config)
    True
"""

from typing import Any, Dict, Set

from guardkit.orchestrator.security_config import SecurityConfig, SecurityLevel


# =============================================================================
# Security Tags Constants
# =============================================================================

SECURITY_TAGS: Set[str] = {
    # Category: Injection Attacks
    "injection",
    "sql",
    "command",
    "ldap",
    "xpath",
    "xxe",
    # Category: Authentication & Authorization
    "authentication",
    "authorization",
    "security",
    "auth",
    "session",
    "token",
    "jwt",
    "oauth",
    "oauth2",
    "rbac",
    "acl",
    "permissions",
    "roles",
    # Category: Data Exposure
    "secrets",
    "credentials",
    "pii",
    "gdpr",
    # Category: Cryptography
    "crypto",
    "encryption",
    "hashing",
    # Category: Input Validation
    "validation",
    "input",
    "sanitization",
    # Category: Configuration Security
    "cors",
    "csrf",
    "headers",
    # Category: Code Execution
    "deserialization",
    "pickle",
    # Category: XSS
    "xss",
    # Sensitive Operations
    "payment",
    "checkout",
    "billing",
}

# High-risk categories that trigger full review even in MINIMAL mode
HIGH_RISK_CATEGORIES: Set[str] = {
    # Authentication & Authorization (critical security boundary)
    "authentication",
    "authorization",
    "auth",
    # Injection attacks (OWASP Top 10)
    "injection",
    "sql",
    "command",
    # Cryptography (requires expert review)
    "crypto",
    "encryption",
    # Sensitive data (compliance requirement)
    "secrets",
    "credentials",
}


# =============================================================================
# Security Keywords Constants
# =============================================================================

SECURITY_KEYWORDS: Set[str] = {
    # Authentication terms
    "login",
    "logout",
    "signup",
    "signin",
    "password",
    "credential",
    "authentication",
    # Authorization terms
    "permission",
    "access",
    "role",
    "privilege",
    "admin",
    # Token terms
    "jwt",
    "token",
    "refresh",
    "bearer",
    "api_key",
    "apikey",
    # Secrets terms
    "secret",
    "key",
    "certificate",
    "private",
    # Security feature terms
    "rate_limit",
    "rate-limit",
    "throttle",
    "cors",
    "csrf",
    # Sensitive data terms
    "pii",
    "gdpr",
    "encrypt",
    "decrypt",
    "hash",
    # Cryptography terms
    "encryption",
    "hashing",
}


# =============================================================================
# Detection Functions
# =============================================================================


def _extract_words(text: str) -> Set[str]:
    """Extract lowercase words from text for keyword matching.

    Args:
        text: Input text to extract words from.

    Returns:
        Set of lowercase words extracted from the text.
    """
    if not text:
        return set()

    # Convert to lowercase and replace common separators with spaces
    normalized = text.lower()
    for sep in ["-", "_", "/", ".", ","]:
        normalized = normalized.replace(sep, " ")

    # Split on whitespace and return unique words
    return {word.strip() for word in normalized.split() if word.strip()}


def _check_tags(tags: Any) -> bool:
    """Check if any task tags match security tags.

    Args:
        tags: Task tags (list or None).

    Returns:
        True if any tag matches SECURITY_TAGS (case-insensitive).
    """
    if not tags:
        return False

    for tag in tags:
        if isinstance(tag, str) and tag.lower() in SECURITY_TAGS:
            return True

    return False


def _check_high_risk_tags(tags: Any) -> bool:
    """Check if any task tags match high-risk categories.

    Args:
        tags: Task tags (list or None).

    Returns:
        True if any tag matches HIGH_RISK_CATEGORIES (case-insensitive).
    """
    if not tags:
        return False

    for tag in tags:
        if isinstance(tag, str) and tag.lower() in HIGH_RISK_CATEGORIES:
            return True

    return False


def _check_title_keywords(title: str) -> bool:
    """Check if title contains security keywords.

    A single keyword match in the title is sufficient to trigger review.

    Args:
        title: Task title string.

    Returns:
        True if title contains any security keyword.
    """
    if not title:
        return False

    words = _extract_words(title)
    return bool(words & SECURITY_KEYWORDS)


def _check_description_keywords(description: str) -> bool:
    """Check if description has sufficient security keyword density.

    Description requires at least 2 unique security keywords to trigger
    review (higher threshold than title to reduce false positives).

    Args:
        description: Task description string.

    Returns:
        True if description contains 2+ unique security keywords.
    """
    if not description:
        return False

    words = _extract_words(description)
    matching_keywords = words & SECURITY_KEYWORDS

    # Require at least 2 unique keywords in description
    return len(matching_keywords) >= 2


def should_run_full_review(task: Dict[str, Any], config: SecurityConfig) -> bool:
    """Determine whether a task requires full security review.

    Detection follows this priority order:
    1. force_full_review flag (always triggers if True)
    2. SKIP level (always skips)
    3. MINIMAL level (only HIGH_RISK_CATEGORIES trigger)
    4. STRICT level (always triggers)
    5. STANDARD level (tag and keyword detection)

    For STANDARD level:
    - Check tags against SECURITY_TAGS (any match triggers)
    - Check title for keywords (any match triggers)
    - Check description for keyword density (2+ matches triggers)

    Args:
        task: Task dictionary with optional keys:
            - tags: List of task tags
            - title: Task title string
            - description: Task description string
        config: SecurityConfig with level and force_full_review settings.

    Returns:
        True if task requires full security review, False otherwise.

    Example:
        >>> task = {'title': 'Implement JWT authentication', 'tags': []}
        >>> config = SecurityConfig(level=SecurityLevel.STANDARD)
        >>> should_run_full_review(task, config)
        True
    """
    # Priority 1: force_full_review flag always triggers
    if config.force_full_review:
        return True

    # Priority 2: SKIP level always skips
    if config.level == SecurityLevel.SKIP:
        return False

    # Priority 3: MINIMAL level - only high-risk categories trigger
    if config.level == SecurityLevel.MINIMAL:
        tags = task.get("tags")
        return _check_high_risk_tags(tags)

    # Priority 4: STRICT level always triggers
    if config.level == SecurityLevel.STRICT:
        return True

    # Priority 5: STANDARD level - full detection logic
    # Check tags first (highest priority for standard detection)
    tags = task.get("tags")
    if _check_tags(tags):
        return True

    # Check title keywords
    title = task.get("title", "")
    if _check_title_keywords(title):
        return True

    # Check description keyword density
    description = task.get("description", "")
    if _check_description_keywords(description):
        return True

    # No security indicators found
    return False


__all__ = [
    "SECURITY_TAGS",
    "HIGH_RISK_CATEGORIES",
    "SECURITY_KEYWORDS",
    "should_run_full_review",
]
