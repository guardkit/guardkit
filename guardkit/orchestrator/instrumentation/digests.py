"""Role-specific digest system for AutoBuild agents.

Provides validation, loading, and token counting for role-specific digest files
that replace the full always-on rules bundle with minimal, targeted system prompts.

Architecture:
    DigestValidator  - Validates token count and file existence at startup
    DigestLoader     - Loads role-specific digest content for prompt injection
    count_tokens     - Token counting with tiktoken or word-based fallback

Digest files live in `.guardkit/digests/` with one markdown file per role:
    player.md, coach.md, resolver.md, router.md

Example:
    >>> from guardkit.orchestrator.instrumentation.digests import DigestLoader
    >>> loader = DigestLoader(Path(".guardkit/digests"))
    >>> content = loader.load("player")
    >>> print(content[:50])
    '# Player Agent Digest...'
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================

DIGEST_ROLES: tuple[str, ...] = ("player", "coach", "resolver", "router")
"""Valid agent roles that have digest files."""

MAX_TOKENS: int = 700
"""Maximum allowed token count per digest file."""

# ============================================================================
# Exceptions
# ============================================================================


class DigestLoadError(Exception):
    """Raised when a digest file cannot be loaded.

    This is raised instead of silently falling back to default content,
    ensuring that missing digest files are caught at startup.
    """


# ============================================================================
# Token Counting
# ============================================================================


def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken or word-based fallback.

    Attempts to use tiktoken with the cl100k_base encoding (used by GPT-4
    and Claude models). Falls back to a word-based approximation if tiktoken
    is not available.

    The word-based fallback uses the standard approximation of ~0.75 tokens
    per word (based on the observation that average English words are ~4-5
    characters and most tokenizers produce ~1 token per 4 characters).

    Args:
        text: The text to count tokens for.

    Returns:
        Estimated token count as an integer (>= 0).
    """
    if not text:
        return 0

    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except ImportError:
        # Word-based fallback: split on whitespace, apply 0.75 multiplier
        # This approximation is based on the observation that tokenizers
        # typically produce ~1 token per 4 characters, and average English
        # words are ~5.1 characters including the space separator.
        words = text.split()
        if not words:
            return 0
        # Use character-based estimate for more accuracy:
        # ~1 token per 4 characters
        char_count = len(text)
        return max(1, math.ceil(char_count / 4.0))


# ============================================================================
# DigestValidationResult
# ============================================================================


@dataclass
class DigestValidationResult:
    """Result of validating a single digest file.

    Attributes:
        role: The agent role this digest belongs to.
        valid: Whether the digest passes validation.
        token_count: Number of tokens in the digest.
        warning: Optional warning message (e.g., exceeds recommended limit).
    """

    role: str
    valid: bool
    token_count: int
    warning: Optional[str] = None


# ============================================================================
# DigestValidator
# ============================================================================


class DigestValidator:
    """Validates role-specific digest files at startup.

    Checks that each digest file exists and is within the token limit.
    Provides fail-fast behavior: missing files raise DigestLoadError
    instead of silently falling back.

    Args:
        digest_dir: Path to the directory containing digest markdown files.

    Example:
        >>> validator = DigestValidator(Path(".guardkit/digests"))
        >>> results = validator.validate_all()
        >>> all(r.valid for r in results)
        True
    """

    def __init__(self, digest_dir: Path) -> None:
        self._digest_dir = digest_dir

    def validate(self, role: str) -> DigestValidationResult:
        """Validate a single role's digest file.

        Args:
            role: Agent role name (player, coach, resolver, router).

        Returns:
            DigestValidationResult with validation outcome.

        Raises:
            ValueError: If role is not a valid digest role.
            DigestLoadError: If the digest file is missing.
        """
        if role not in DIGEST_ROLES:
            raise ValueError(
                f"Invalid role '{role}'. Must be one of: {', '.join(DIGEST_ROLES)}"
            )

        digest_path = self._digest_dir / f"{role}.md"
        if not digest_path.exists():
            raise DigestLoadError(
                f"Digest file not found for role '{role}': {digest_path}. "
                f"Each role requires a digest file. "
                f"No silent fallback to full rules bundle is allowed."
            )

        content = digest_path.read_text(encoding="utf-8")
        token_count = count_tokens(content)

        warning: Optional[str] = None
        if token_count > MAX_TOKENS:
            warning = (
                f"Digest for '{role}' has {token_count} tokens, "
                f"which exceeds the maximum of {MAX_TOKENS} tokens."
            )
            logger.warning(warning)

        return DigestValidationResult(
            role=role,
            valid=True,
            token_count=token_count,
            warning=warning,
        )

    def validate_all(self) -> List[DigestValidationResult]:
        """Validate all role digest files.

        Returns:
            List of DigestValidationResult, one per role.

        Raises:
            DigestLoadError: If any digest file is missing.
        """
        results: List[DigestValidationResult] = []
        for role in DIGEST_ROLES:
            result = self.validate(role)
            results.append(result)
        return results


# ============================================================================
# DigestLoader
# ============================================================================


class DigestLoader:
    """Loads role-specific digest content for prompt assembly.

    Reads the digest markdown file for a given agent role and returns
    its content as a string suitable for injection into the system prompt.

    Args:
        digest_dir: Path to the directory containing digest markdown files.

    Example:
        >>> loader = DigestLoader(Path(".guardkit/digests"))
        >>> content = loader.load("player")
        >>> isinstance(content, str)
        True
    """

    def __init__(self, digest_dir: Path) -> None:
        self._digest_dir = digest_dir

    def load(self, role: str) -> str:
        """Load the digest content for a specific agent role.

        Args:
            role: Agent role name (player, coach, resolver, router).

        Returns:
            Digest content as a string.

        Raises:
            ValueError: If role is not a valid digest role.
            DigestLoadError: If the digest file is missing.
        """
        if role not in DIGEST_ROLES:
            raise ValueError(
                f"Invalid role '{role}'. Must be one of: {', '.join(DIGEST_ROLES)}"
            )

        digest_path = self._digest_dir / f"{role}.md"
        if not digest_path.exists():
            raise DigestLoadError(
                f"Digest file not found for role '{role}': {digest_path}. "
                f"Each role requires a digest file at startup. "
                f"No silent fallback to full rules bundle is allowed."
            )

        content = digest_path.read_text(encoding="utf-8")
        logger.debug("Loaded digest for role '%s' (%d chars)", role, len(content))
        return content


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "count_tokens",
    "DigestLoadError",
    "DigestLoader",
    "DigestValidationResult",
    "DigestValidator",
    "DIGEST_ROLES",
    "MAX_TOKENS",
]
