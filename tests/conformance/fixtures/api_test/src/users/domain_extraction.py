"""Domain extraction utilities for email addresses.

Provides functions to extract email domains from email address strings,
with proper handling of malformed inputs and edge cases.
"""

from __future__ import annotations

import re

# Regex pattern for extracting domain from email address.
# Matches everything after the last '@' symbol.
# Domain must contain at least one dot and valid characters.
_EMAIL_DOMAIN_PATTERN = re.compile(
    r"^[^@\s]+@([a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?\.)*[a-zA-Z]{2,}$"
)


def extract_domain(email: str) -> str | None:
    """Extract the domain from a single email address.

    Validates the email format and extracts the domain portion (everything
    after the '@' symbol). Returns None for malformed or invalid emails.
    The returned domain is lowercased for case-insensitive matching.

    Args:
        email: The email address string to extract the domain from.

    Returns:
        The extracted domain in lowercase, or None if the email is invalid.
    """
    if not email or not isinstance(email, str):
        return None

    email_stripped = email.strip()
    if not email_stripped:
        return None

    # Check basic email format with domain validation
    if not _EMAIL_DOMAIN_PATTERN.match(email_stripped):
        return None

    # Extract domain: everything after the last '@'
    at_index = email_stripped.rfind("@")
    if at_index == -1:
        return None

    domain = email_stripped[at_index + 1 :]

    # Validate domain is not empty
    if not domain:
        return None

    # Validate domain has at least one dot
    if "." not in domain:
        return None

    return domain.lower()


def extract_domains(emails: list[str]) -> list[str]:
    """Extract domains from a list of email addresses.

    Filters out malformed emails and returns a list of extracted domains.
    Domains are lowercased for case-insensitive matching.

    Args:
        emails: A list of email address strings to extract domains from.

    Returns:
        A list of domain strings (lowercase) for valid emails only.
        Invalid emails are silently skipped.
    """
    domains: list[str] = []
    for email in emails:
        domain = extract_domain(email)
        if domain is not None:
            domains.append(domain)
    return domains
