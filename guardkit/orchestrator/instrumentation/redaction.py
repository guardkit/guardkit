"""Secret redaction pipeline for AutoBuild instrumentation events.

Sanitises secrets from ToolExecEvent fields before emission, preventing
API keys, tokens, and passwords from appearing in structured event logs.

Architecture:
    SecretRedactor         - Configurable regex-based secret detector/replacer
    sanitise_tool_name     - Shell metacharacter stripper for tool names
    redact_tool_exec_event - Integration function that applies both to ToolExecEvent

Usage:
    >>> from guardkit.orchestrator.instrumentation.redaction import (
    ...     SecretRedactor, redact_tool_exec_event,
    ... )
    >>> redactor = SecretRedactor()
    >>> redactor.redact("export API_KEY=sk-abc123456789")
    'export API_KEY=[REDACTED]'
"""

from __future__ import annotations

import re
from typing import List, Optional

from guardkit.orchestrator.instrumentation.schemas import ToolExecEvent

# Sentinel replacement for detected secrets
_REDACTED = "[REDACTED]"

# Shell metacharacters that must be stripped from tool names
_SHELL_METACHARACTERS = frozenset(";|&$`><()")

# ============================================================================
# Default Redaction Patterns
# ============================================================================

DEFAULT_REDACTION_PATTERNS: List[str] = [
    # OpenAI-style secret keys: sk- followed by alphanumeric (20+ chars)
    r"sk-[A-Za-z0-9_-]{10,}",
    # AWS access key IDs: AKIA followed by 16 uppercase alphanumeric
    r"AKIA[A-Z0-9]{12,}",
    # GitHub personal access tokens (ghp_) and server tokens (ghs_)
    r"gh[ps]_[A-Za-z0-9]{10,}",
    # Bearer tokens: "Bearer " followed by a JWT-like or opaque token
    r"(?i)bearer\s+[A-Za-z0-9._-]{10,}",
    # Password/secret environment variables: KEY=value patterns
    # Matches PASSWORD=, PASS=, SECRET=, _PASSWORD=, _PASS=, _SECRET=
    r"(?:PASSWORD|PASS|SECRET)=(\S+)",
    # Generic token= and api_key= query/env patterns
    r"(?:token|api_key)=(\S+)",
    # Credentials embedded in URLs: scheme://user:pass@host
    r"://([^/\s]+):([^@/\s]+)@",
]

# ============================================================================
# SecretRedactor
# ============================================================================


class SecretRedactor:
    """Configurable regex-based secret redactor.

    Applies a list of regex patterns to detect secrets in text and replaces
    matched content with ``[REDACTED]``.

    Args:
        patterns: List of regex pattern strings. Defaults to
            :data:`DEFAULT_REDACTION_PATTERNS` when *None*.

    Example:
        >>> r = SecretRedactor()
        >>> r.redact("token=my_secret")
        'token=[REDACTED]'
    """

    def __init__(self, patterns: Optional[List[str]] = None) -> None:
        if patterns is None:
            patterns = list(DEFAULT_REDACTION_PATTERNS)
        self.patterns: List[str] = patterns
        self._compiled: List[re.Pattern[str]] = [
            re.compile(p) for p in self.patterns
        ]

    def redact(self, text: str) -> str:
        """Replace all detected secrets in *text* with ``[REDACTED]``.

        Patterns are applied sequentially. Patterns with capture groups
        replace only the captured group(s); patterns without capture groups
        replace the full match.

        Args:
            text: Input string to scan for secrets.

        Returns:
            String with all detected secrets replaced.
        """
        if not text:
            return text

        result = text
        for compiled in self._compiled:
            if compiled.groups == 0:
                # No capture groups — replace the entire match
                result = compiled.sub(_REDACTED, result)
            else:
                # Has capture groups — replace only captured portions
                result = _replace_groups(compiled, result)
        return result


def _replace_groups(pattern: re.Pattern[str], text: str) -> str:
    """Replace captured groups in *text* while preserving non-captured parts.

    For each match, every non-None group is replaced with ``[REDACTED]``.
    The overall match structure (prefix, delimiters) is preserved.

    Args:
        pattern: Compiled regex with one or more capture groups.
        text: Input text to process.

    Returns:
        Text with captured group content replaced.
    """
    result_parts: list[str] = []
    last_end = 0

    for match in pattern.finditer(text):
        # Add text before this match
        result_parts.append(text[last_end:match.start()])

        # Build replacement for this match by replacing each group
        match_text = match.group(0)
        # Track offsets within the match string
        inner_parts: list[str] = []
        inner_last = 0

        for g_idx in range(1, pattern.groups + 1):
            group_text = match.group(g_idx)
            if group_text is None:
                continue
            g_start = match.start(g_idx) - match.start()
            g_end = match.end(g_idx) - match.start()
            inner_parts.append(match_text[inner_last:g_start])
            inner_parts.append(_REDACTED)
            inner_last = g_end

        inner_parts.append(match_text[inner_last:])
        result_parts.append("".join(inner_parts))
        last_end = match.end()

    result_parts.append(text[last_end:])
    return "".join(result_parts)


# ============================================================================
# Tool Name Sanitisation
# ============================================================================


def sanitise_tool_name(name: str) -> str:
    """Strip shell metacharacters from a tool name.

    Prevents injection via event data by removing characters that could
    be interpreted as shell operators: ``;  |  &  $  ``  >  <  (  )``.

    Args:
        name: Raw tool name string.

    Returns:
        Sanitised tool name with metacharacters removed.
    """
    return "".join(ch for ch in name if ch not in _SHELL_METACHARACTERS)


# ============================================================================
# Event Redaction Integration
# ============================================================================


def redact_tool_exec_event(
    event: ToolExecEvent,
    redactor: Optional[SecretRedactor] = None,
) -> ToolExecEvent:
    """Create a redacted copy of a :class:`ToolExecEvent`.

    Applies secret redaction to ``cmd``, ``stdout_tail``, and
    ``stderr_tail`` fields, and sanitises ``tool_name`` against shell
    metacharacters. All other fields are preserved unchanged.

    Args:
        event: Original event to redact.
        redactor: Optional custom :class:`SecretRedactor`. Uses default
            patterns when *None*.

    Returns:
        New :class:`ToolExecEvent` with redacted/sanitised fields.
    """
    if redactor is None:
        redactor = SecretRedactor()

    return ToolExecEvent(
        run_id=event.run_id,
        feature_id=event.feature_id,
        task_id=event.task_id,
        agent_role=event.agent_role,
        attempt=event.attempt,
        timestamp=event.timestamp,
        schema_version=event.schema_version,
        tool_name=sanitise_tool_name(event.tool_name),
        cmd=redactor.redact(event.cmd),
        exit_code=event.exit_code,
        latency_ms=event.latency_ms,
        stdout_tail=redactor.redact(event.stdout_tail),
        stderr_tail=redactor.redact(event.stderr_tail),
    )


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "DEFAULT_REDACTION_PATTERNS",
    "SecretRedactor",
    "sanitise_tool_name",
    "redact_tool_exec_event",
]
