"""Parser and override-detector for Graphiti MCP ``add_memory`` responses.

The Graphiti MCP HTTP server at ``http://promaxgb10-41b1:8004/mcp`` accepts
``mcp__graphiti__add_memory`` calls with a ``group_id`` parameter but
silently overrides it with a server-side default (typically
``product_knowledge``). The actual group used is reported back in the
response message as ``"Episode '...' queued for processing in group
'<actual>'"``.

This module exposes pure functions used by ``/task-complete`` prose to
detect the override and trigger the CLI fallback path
(``guardkit graphiti capture-outcome``), which writes via the Python
client and respects the requested ``group_id``.

Pure stdlib only. No imports from ``guardkit/`` — keeping this module
free of the editable-install path keeps it importable in the same shape
no matter where it is invoked from (see
``.claude/rules/namespace-hygiene.md``).

See: TASK-FIX-B1F7.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


__all__ = [
    "GroupOverrideResult",
    "parse_queued_group",
    "detect_group_override",
]


# Anchors on the literal phrase the Graphiti MCP server emits, then
# captures everything up to the next single quote. Episode names earlier
# in the message can themselves contain quoted segments — the anchor
# avoids matching them.
_QUEUED_GROUP_PATTERN = re.compile(r"queued for processing in group '([^']+)'")


@dataclass
class GroupOverrideResult:
    """Outcome of comparing a requested ``group_id`` to what the server reported.

    Attributes:
        overridden: True when the server reported a group different from
            the one the caller asked for. False when the groups match, or
            when the response message could not be parsed (the safe
            default — assume no override rather than trigger a spurious
            fallback).
        requested: The ``group_id`` the caller passed to ``add_memory``.
        actual: The group the server reported. ``None`` if the response
            message did not match the expected pattern.
        warning: Human-readable warning string when ``overridden`` is
            True; ``None`` otherwise. Suitable for direct display.
    """

    overridden: bool
    requested: str
    actual: Optional[str]
    warning: Optional[str]


def parse_queued_group(response_message: str) -> Optional[str]:
    """Extract the actual group from a Graphiti MCP ``add_memory`` response.

    Parses the standard message format::

        Episode 'X' queued for processing in group '<group>'

    Args:
        response_message: The ``message`` field from the MCP response.

    Returns:
        The group name as a string, or ``None`` if the pattern is not
        found (empty input, malformed message, or upstream format change).
    """
    if not response_message:
        return None
    match = _QUEUED_GROUP_PATTERN.search(response_message)
    if match is None:
        return None
    return match.group(1)


def detect_group_override(
    requested_group_id: str,
    response_message: str,
) -> GroupOverrideResult:
    """Compare the requested ``group_id`` against the server-reported group.

    Used by ``/task-complete`` immediately after the MCP ``add_memory``
    call to decide whether to fire the CLI fallback path.

    Args:
        requested_group_id: The ``group_id`` the caller passed to
            ``mcp__graphiti__add_memory``.
        response_message: The ``message`` field from the MCP response.

    Returns:
        A ``GroupOverrideResult``. When the response message cannot be
        parsed, ``overridden`` is False and ``actual`` is None — callers
        treat this as "no observable override, proceed normally".
    """
    actual = parse_queued_group(response_message)

    if actual is None or actual == requested_group_id:
        return GroupOverrideResult(
            overridden=False,
            requested=requested_group_id,
            actual=actual,
            warning=None,
        )

    warning = (
        f"Graphiti MCP server overrode requested group "
        f"'{requested_group_id}' with '{actual}'. "
        f"Falling back to CLI write path."
    )
    return GroupOverrideResult(
        overridden=True,
        requested=requested_group_id,
        actual=actual,
        warning=warning,
    )
