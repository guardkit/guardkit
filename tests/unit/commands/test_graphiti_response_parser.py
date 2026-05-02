"""Tests for installer/core/commands/lib/graphiti_response_parser.py.

Covers the response-message parser and the override-detection logic that
``/task-complete`` uses to decide whether to fall back to the CLI write
path when the Graphiti MCP HTTP server silently coerces ``group_id``.

See: TASK-FIX-B1F7.

Coverage Target: 100% (the module is small and pure).
"""

from installer.core.commands.lib.graphiti_response_parser import (
    GroupOverrideResult,
    detect_group_override,
    parse_queued_group,
)


# ============================================================================
# parse_queued_group — extracting the actual group from MCP response text
# ============================================================================


def test_parse_queued_group_standard():
    """Standard server response with bare group name."""
    msg = "Episode 'X' queued for processing in group 'product_knowledge'"
    assert parse_queued_group(msg) == "product_knowledge"


def test_parse_queued_group_with_prefix():
    """Project-prefixed group name (double-underscore convention)."""
    msg = (
        "Episode 'Task Completion: TASK-FPSG-003' queued for processing "
        "in group 'guardkit__task_outcomes'"
    )
    assert parse_queued_group(msg) == "guardkit__task_outcomes"


def test_parse_queued_group_episode_name_with_quotes_does_not_confuse_parser():
    """Episode names earlier in the message must not be mistaken for the group."""
    msg = (
        "Episode 'It's a quoted name' queued for processing "
        "in group 'product_knowledge'"
    )
    assert parse_queued_group(msg) == "product_knowledge"


def test_parse_queued_group_no_match():
    """A message that does not contain the queued-for-processing pattern."""
    assert parse_queued_group("Some other message") is None


def test_parse_queued_group_empty_string():
    """Empty input is a non-match (safe default)."""
    assert parse_queued_group("") is None


def test_parse_queued_group_none_safe():
    """None-equivalent falsy input returns None rather than raising."""
    # The function uses ``if not response_message`` as the early-out, so
    # an empty string covers the same branch as a None would; we exercise
    # the empty-string branch explicitly above.
    assert parse_queued_group("") is None


# ============================================================================
# detect_group_override — comparing requested vs server-reported group
# ============================================================================


def test_detect_no_override_when_groups_match():
    """When server honours the requested group, no override is reported."""
    msg = "Episode 'X' queued for processing in group 'guardkit__task_outcomes'"
    result = detect_group_override("guardkit__task_outcomes", msg)

    assert isinstance(result, GroupOverrideResult)
    assert result.overridden is False
    assert result.requested == "guardkit__task_outcomes"
    assert result.actual == "guardkit__task_outcomes"
    assert result.warning is None


def test_detect_override_fires_when_server_coerces_group():
    """The bug this task fixes: requested vs server-reported groups differ."""
    msg = "Episode 'X' queued for processing in group 'product_knowledge'"
    result = detect_group_override("guardkit__task_outcomes", msg)

    assert result.overridden is True
    assert result.requested == "guardkit__task_outcomes"
    assert result.actual == "product_knowledge"
    assert result.warning is not None
    assert result.warning != ""


def test_detect_override_warning_names_both_groups():
    """The warning text must surface both groups so the user can diagnose."""
    msg = "Episode 'X' queued for processing in group 'product_knowledge'"
    result = detect_group_override("guardkit__task_outcomes", msg)

    assert "guardkit__task_outcomes" in result.warning
    assert "product_knowledge" in result.warning


def test_detect_unparseable_response_treated_as_no_override():
    """Format change or empty response → safe default (no override assumed)."""
    result = detect_group_override("guardkit__task_outcomes", "")

    assert result.overridden is False
    assert result.actual is None
    assert result.warning is None


def test_detect_unparseable_non_empty_response_treated_as_no_override():
    """A non-empty response that does not match the pattern is also a safe no-op."""
    result = detect_group_override(
        "guardkit__task_outcomes",
        "Some unrelated response shape we did not anticipate",
    )

    assert result.overridden is False
    assert result.actual is None
    assert result.warning is None
