"""LLM instrumentation helper functions.

Pure, side-effect-free functions for extracting instrumentation data from
SDK responses. This module provides building blocks for TASK-INST-005b
(hook integration) and TASK-INST-005c (event construction).

**No imports of the invocation layer** — this module is intentionally
decoupled and has zero dependencies on the SDK invocation module.

Functions:
    detect_provider      - Classify LLM provider from base URL / model
    extract_token_usage  - Pull (input_tokens, output_tokens) from SDK messages
    measure_latency      - Context manager for wall-clock timing in milliseconds
    classify_error       - Map SDK exceptions to controlled vocabulary
    check_prefix_cache   - Inspect vLLM headers for prefix cache indicators
    sanitise_tool_name   - Strip unsafe characters from tool names
"""

from __future__ import annotations

import asyncio
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Generator, Optional

from guardkit.orchestrator.exceptions import RateLimitExceededError, SDKTimeoutError


# ============================================================================
# LatencyResult dataclass
# ============================================================================


@dataclass
class LatencyResult:
    """Container for wall-clock latency measurement.

    Attributes:
        ms: Elapsed time in milliseconds. Set to 0.0 initially and
            populated when the ``measure_latency`` context manager exits.
    """

    ms: float = 0.0


# ============================================================================
# Allowed characters for tool name sanitisation
# ============================================================================

_ALLOWED_TOOL_NAME = re.compile(r"[^A-Za-z0-9\-_. ]")


# ============================================================================
# Provider Detection
# ============================================================================


def detect_provider(base_url: Optional[str], model: Optional[str]) -> str:
    """Detect LLM provider from base URL or model string.

    Classification rules (applied in order):
    1. *None* or empty ``base_url`` → ``"anthropic"`` (default)
    2. Contains ``api.anthropic.com`` → ``"anthropic"``
    3. Contains ``openai`` → ``"openai"``
    4. Contains ``localhost`` or ``vllm`` → ``"local-vllm"``
    5. Otherwise → ``"anthropic"`` (safe default)

    Args:
        base_url: API base URL, or *None* for default Anthropic endpoint.
        model: Model identifier string (currently unused; reserved for
            future heuristic expansion).

    Returns:
        One of ``"anthropic"``, ``"openai"``, or ``"local-vllm"``.
    """
    if not base_url:
        return "anthropic"

    url_lower = base_url.lower()

    if "api.anthropic.com" in url_lower:
        return "anthropic"
    if "openai" in url_lower:
        return "openai"
    if "localhost" in url_lower or "vllm" in url_lower:
        return "local-vllm"

    return "anthropic"


# ============================================================================
# Token Extraction
# ============================================================================


def extract_token_usage(response_messages: list[Any]) -> tuple[int, int]:
    """Extract input_tokens and output_tokens from SDK response messages.

    Iterates through *response_messages* looking for objects with a
    ``usage`` attribute containing ``input_tokens`` and ``output_tokens``.
    Returns the values from the **last** message that has valid usage data.

    Args:
        response_messages: List of SDK response message objects.

    Returns:
        ``(input_tokens, output_tokens)`` tuple. Defaults to ``(0, 0)``
        if no usage data is found.
    """
    input_tokens = 0
    output_tokens = 0

    for msg in response_messages:
        usage = getattr(msg, "usage", None)
        if usage is None:
            continue
        i_tok = getattr(usage, "input_tokens", None)
        o_tok = getattr(usage, "output_tokens", None)
        if i_tok is None or o_tok is None:
            continue
        input_tokens = i_tok
        output_tokens = o_tok

    return (input_tokens, output_tokens)


# ============================================================================
# Latency Measurement
# ============================================================================


@contextmanager
def measure_latency() -> Generator[LatencyResult, None, None]:
    """Context manager that measures wall-clock latency in milliseconds.

    Uses ``time.perf_counter()`` for high-precision timing. The latency
    is recorded even if the wrapped block raises an exception.

    Yields:
        A :class:`LatencyResult` whose ``ms`` attribute is populated
        when the context exits.

    Example::

        with measure_latency() as latency:
            await sdk_call()
        print(latency.ms)  # float, e.g. 1234.5
    """
    result = LatencyResult()
    start = time.perf_counter()
    try:
        yield result
    finally:
        elapsed = time.perf_counter() - start
        result.ms = elapsed * 1000.0


# ============================================================================
# Error Classification
# ============================================================================


def classify_error(exception: Optional[Exception]) -> Optional[str]:
    """Classify an SDK exception into controlled vocabulary.

    Mapping rules:
    - ``None`` → ``None`` (no error)
    - ``asyncio.TimeoutError`` / ``SDKTimeoutError`` → ``"timeout"``
    - ``RateLimitExceededError`` → ``"rate_limited"``
    - Exception whose class name is ``"ProcessError"`` → ``"tool_error"``
    - Any other exception → ``"other"``

    The ``ProcessError`` check uses class name matching to avoid a hard
    import dependency on ``claude_agent_sdk``.

    Args:
        exception: The exception to classify, or *None* if no error.

    Returns:
        One of ``"rate_limited"``, ``"timeout"``, ``"tool_error"``,
        ``"other"``, or ``None``.
    """
    if exception is None:
        return None

    # Timeout errors
    if isinstance(exception, (asyncio.TimeoutError, SDKTimeoutError)):
        return "timeout"

    # Rate limit errors
    if isinstance(exception, RateLimitExceededError):
        return "rate_limited"

    # ProcessError from claude_agent_sdk (matched by class name to avoid
    # hard dependency on the SDK package)
    if type(exception).__name__ == "ProcessError":
        return "tool_error"

    return "other"


# ============================================================================
# Prefix Cache Estimation
# ============================================================================


def check_prefix_cache(
    response_headers: Optional[dict[str, str]],
) -> tuple[Optional[bool], bool]:
    """Check vLLM response for prefix cache hit indicator.

    Inspects the ``x-vllm-prefix-cache-hit`` header. If the header is
    absent or headers are *None*, returns ``(None, False)``.

    Args:
        response_headers: HTTP response headers dict, or *None*.

    Returns:
        ``(prefix_cache_hit, prefix_cache_estimated)`` where:
        - ``(True, False)``  — direct cache hit confirmed by server
        - ``(False, False)`` — direct cache miss confirmed by server
        - ``(None, False)``  — no cache info available
    """
    if not response_headers:
        return (None, False)

    cache_header = response_headers.get("x-vllm-prefix-cache-hit")
    if cache_header is None:
        return (None, False)

    hit = cache_header.lower() == "true"
    return (hit, False)


# ============================================================================
# Tool Name Sanitisation
# ============================================================================


def sanitise_tool_name(raw_name: str) -> str:
    """Sanitise tool name by removing disallowed characters.

    Keeps only alphanumeric characters, hyphens, underscores, dots,
    and spaces. All other characters (including shell metacharacters
    like ``;  |  &  $  ``  >  <  (  )``) are stripped.

    Args:
        raw_name: Raw tool name string.

    Returns:
        Sanitised tool name.
    """
    return _ALLOWED_TOOL_NAME.sub("", raw_name)


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "LatencyResult",
    "detect_provider",
    "extract_token_usage",
    "measure_latency",
    "classify_error",
    "check_prefix_cache",
    "sanitise_tool_name",
]
