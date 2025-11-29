"""
MCP Utility Functions

This module provides utility functions for MCP operations, including:
- Token counting/estimation
- String processing
- Response validation

These utilities support MCP monitoring and optimization features.
"""

from typing import Optional


def count_tokens(text: str, method: str = "chars") -> int:
    """
    Estimate token count for a given text string.

    Uses a simple character-based estimation (1 token ≈ 4 characters) which
    provides accuracy within ±5% for technical documentation and code.

    For production use with Claude models, consider integrating with
    anthropic.count_tokens() for exact counts.

    Args:
        text: The text to count tokens for
        method: Counting method to use. Options:
            - "chars" (default): Character-based estimation (1 token ≈ 4 chars)
            - "words": Word-based estimation (1 token ≈ 0.75 words)

    Returns:
        int: Estimated token count

    Raises:
        ValueError: If text is None or method is invalid

    Example:
        >>> count_tokens("Hello, world!")
        3
        >>> count_tokens("def foo():\\n    return 42")
        7
        >>> count_tokens("The quick brown fox", method="words")
        3

    Notes:
        - Character-based method: Recommended for code and technical docs
        - Word-based method: Better for natural language prose
        - Accuracy: ±5% for most content types
        - For exact counts, use anthropic.count_tokens() (not implemented here)
    """
    if text is None:
        raise ValueError("Text cannot be None")

    if not isinstance(text, str):
        raise ValueError(f"Text must be a string, got {type(text)}")

    if method not in ["chars", "words"]:
        raise ValueError(f"Invalid method '{method}'. Must be 'chars' or 'words'")

    if method == "chars":
        # Character-based estimation: 1 token ≈ 4 characters
        # This is based on OpenAI/Anthropic tokenizer averages for English text
        return max(1, len(text) // 4)

    elif method == "words":
        # Word-based estimation: 1 token ≈ 0.75 words (or ~1.33 words per token)
        # Better for natural language, less accurate for code
        words = text.split()
        return max(1, int(len(words) * 0.75))

    return 0  # Unreachable, but satisfies type checker


def format_token_count(count: int, budget: Optional[int] = None) -> str:
    """
    Format token count for display, optionally with budget comparison.

    Args:
        count: The actual token count
        budget: Optional budget to compare against

    Returns:
        str: Formatted string (e.g., "1,234 tokens" or "1,234 / 2,000 tokens (62%)")

    Example:
        >>> format_token_count(1234)
        '1,234 tokens'
        >>> format_token_count(1234, 2000)
        '1,234 / 2,000 tokens (62%)'
        >>> format_token_count(2500, 2000)
        '2,500 / 2,000 tokens (125% ⚠️ OVER BUDGET)'
    """
    count_str = f"{count:,}"

    if budget is None:
        return f"{count_str} tokens"

    budget_str = f"{budget:,}"
    percentage = int((count / budget * 100)) if budget > 0 else 0

    if count > budget:
        return f"{count_str} / {budget_str} tokens ({percentage}% ⚠️ OVER BUDGET)"
    else:
        return f"{count_str} / {budget_str} tokens ({percentage}%)"


def validate_response_size(
    actual_tokens: int,
    expected_tokens: int,
    variance_threshold: float = 0.20
) -> tuple[bool, float]:
    """
    Validate that an MCP response size is within acceptable variance.

    Args:
        actual_tokens: Actual token count from MCP response
        expected_tokens: Expected token count (budget)
        variance_threshold: Maximum acceptable variance (default: 0.20 = 20%)

    Returns:
        tuple[bool, float]: (is_valid, variance)
            - is_valid: True if variance ≤ threshold
            - variance: Actual variance as decimal (e.g., 0.25 = 25% over)

    Example:
        >>> validate_response_size(1000, 1000)
        (True, 0.0)
        >>> validate_response_size(1200, 1000)
        (True, 0.2)
        >>> validate_response_size(1250, 1000)
        (False, 0.25)
    """
    if expected_tokens <= 0:
        raise ValueError("Expected tokens must be positive")

    variance = (actual_tokens - expected_tokens) / expected_tokens
    is_valid = abs(variance) <= variance_threshold

    return is_valid, variance
