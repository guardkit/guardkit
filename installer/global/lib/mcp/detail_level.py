"""
DetailLevel Enum for MCP Progressive Disclosure

This module defines the DetailLevel enum for controlling the level of detail
in MCP responses, particularly for Context7 library documentation.

Progressive disclosure allows fetching summary-level documentation during planning
phases (500-1000 tokens) and detailed documentation during implementation phases
(3500-5000 tokens), reducing token usage by 50-70% in planning.
"""

from enum import Enum
from typing import Tuple


class DetailLevel(Enum):
    """
    Enum for controlling MCP response detail level.

    Attributes:
        SUMMARY: High-level overview (500-1000 tokens)
            - Use in Phase 2 (Planning) for architectural overview
            - Provides API signatures, key concepts, patterns
            - Omits detailed examples and edge cases

        DETAILED: Full documentation with examples (3500-5000 tokens, default)
            - Use in Phase 3 (Implementation) for complete reference
            - Includes code examples, edge cases, best practices
            - Default mode for backward compatibility

    Example:
        >>> from installer.global.lib.mcp import DetailLevel
        >>> level = DetailLevel.SUMMARY
        >>> level.value
        'summary'
        >>> level.token_range()
        (500, 1000)
    """

    SUMMARY = "summary"
    DETAILED = "detailed"

    def token_range(self) -> Tuple[int, int]:
        """
        Get the expected token range for this detail level.

        Returns:
            Tuple[int, int]: (min_tokens, max_tokens) for this level

        Example:
            >>> DetailLevel.SUMMARY.token_range()
            (500, 1000)
            >>> DetailLevel.DETAILED.token_range()
            (3500, 5000)
        """
        if self == DetailLevel.SUMMARY:
            return (500, 1000)
        elif self == DetailLevel.DETAILED:
            return (3500, 5000)
        else:
            # Fallback for future detail levels
            return (1000, 3000)

    def default_tokens(self) -> int:
        """
        Get the default token count for this detail level (midpoint of range).

        Returns:
            int: Default token count for MCP requests

        Example:
            >>> DetailLevel.SUMMARY.default_tokens()
            750
            >>> DetailLevel.DETAILED.default_tokens()
            4250
        """
        min_tokens, max_tokens = self.token_range()
        return (min_tokens + max_tokens) // 2

    def __str__(self) -> str:
        """String representation for logging and debugging."""
        return self.value

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        min_tokens, max_tokens = self.token_range()
        return f"DetailLevel.{self.name} ({min_tokens}-{max_tokens} tokens)"
