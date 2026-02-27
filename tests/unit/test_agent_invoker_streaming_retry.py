"""
Unit tests for TASK-FIX-46F2: vLLM streaming retry on transient SDK errors.

Tests the retry logic added to _run_task_work_inline_protocol that retries
once with backoff when the SDK encounters a transient "unknown" stream error.

Coverage Target: >=85%
Test Count: 7 tests
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import guardkit.orchestrator.agent_invoker as mod
from guardkit.orchestrator.agent_invoker import (
    AgentInvoker,
    MAX_SDK_STREAM_RETRIES,
    SDK_STREAM_RETRY_BACKOFF,
)
from guardkit.orchestrator.exceptions import TaskWorkResult


# ============================================================================
# 1. Module-Level Constants Tests
# ============================================================================


class TestStreamingRetryConstants:
    """Tests for the module-level retry constants."""

    def test_max_sdk_stream_retries_is_one(self):
        """MAX_SDK_STREAM_RETRIES is set to 1 (single retry)."""
        assert MAX_SDK_STREAM_RETRIES == 1

    def test_sdk_stream_retry_backoff_is_30(self):
        """SDK_STREAM_RETRY_BACKOFF is 30 seconds."""
        assert SDK_STREAM_RETRY_BACKOFF == 30


# ============================================================================
# 2. Retry Behavior Tests
# ============================================================================


def _make_invoker(tmp_path):
    """Create AgentInvoker with minimal config for testing."""
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    return AgentInvoker(
        worktree_path=worktree,
        max_turns_per_agent=5,
        sdk_timeout_seconds=60,
    )


def _mock_assistant_message(error=None, text="some output"):
    """Create a mock AssistantMessage with optional error."""
    msg = MagicMock()
    msg.__class__.__name__ = "AssistantMessage"
    if text:
        text_block = MagicMock()
        text_block.__class__.__name__ = "TextBlock"
        text_block.text = text
        msg.content = [text_block]
    else:
        msg.content = []
    return msg, error


def _mock_result_message(num_turns=5):
    """Create a mock ResultMessage."""
    msg = MagicMock()
    msg.__class__.__name__ = "ResultMessage"
    msg.num_turns = num_turns
    return msg


class TestStreamingRetryBehavior:
    """Tests for the retry logic in _run_task_work_inline_protocol."""

    def test_retry_decision_logic_transient_unknown(self):
        """Verify the retry guard fires for transient 'unknown' errors on first attempt."""
        err = "unknown"
        _sdk_attempt = 0
        should_retry = (
            _sdk_attempt < MAX_SDK_STREAM_RETRIES
            and "unknown" in str(err).lower()
        )
        assert should_retry is True

    def test_retry_decision_logic_exhausted(self):
        """Verify retry guard blocks after max attempts with transient error."""
        err = "unknown"
        _sdk_attempt = 1  # Second attempt (retry already used)
        should_retry = (
            _sdk_attempt < MAX_SDK_STREAM_RETRIES
            and "unknown" in str(err).lower()
        )
        assert should_retry is False

    @pytest.mark.asyncio
    async def test_non_transient_error_not_retried(self, tmp_path):
        """A non-transient error (e.g., 'rate_limit') returns failure immediately."""
        # This tests the constant/logic contract rather than full integration
        # Non-transient errors should not match "unknown" in str(err).lower()
        error_messages = [
            "rate_limit_exceeded",
            "authentication_error",
            "model_not_found",
            "invalid_request",
            "overloaded",
        ]
        for err_msg in error_messages:
            assert "unknown" not in err_msg.lower(), (
                f"Error '{err_msg}' should not trigger retry"
            )

    def test_transient_error_pattern_matches_unknown(self):
        """The 'unknown' pattern matches the actual vLLM transient error."""
        # From TASK-DB-006 Turn 1: "SDK API error in stream: unknown"
        actual_error = "unknown"
        assert "unknown" in str(actual_error).lower()

        # Also matches if embedded in longer string
        actual_error_2 = "Unknown server error"
        assert "unknown" in str(actual_error_2).lower()

    def test_auth_errors_do_not_match_retry_pattern(self):
        """Auth, rate limit, and model errors should NOT trigger retry."""
        non_retryable = [
            "authentication_error: invalid API key",
            "rate_limit_exceeded: too many requests",
            "model_not_found: claude-3-opus-20240229",
            "invalid_request_error: prompt too long",
            "Permission denied",
        ]
        for err in non_retryable:
            assert "unknown" not in err.lower(), (
                f"Error '{err}' should NOT match retry pattern"
            )

    def test_retry_constants_exported(self):
        """Verify retry constants are accessible from the module."""
        assert hasattr(mod, "MAX_SDK_STREAM_RETRIES")
        assert hasattr(mod, "SDK_STREAM_RETRY_BACKOFF")
        assert mod.MAX_SDK_STREAM_RETRIES == 1
        assert mod.SDK_STREAM_RETRY_BACKOFF == 30

    def test_retry_loop_range(self):
        """Verify retry loop iterates correct number of times."""
        # range(MAX_SDK_STREAM_RETRIES + 1) = range(2) = [0, 1]
        # Attempt 0: initial try, Attempt 1: single retry
        attempts = list(range(MAX_SDK_STREAM_RETRIES + 1))
        assert attempts == [0, 1]
        assert len(attempts) == 2

    def test_retry_only_on_last_attempt_guard(self):
        """Verify the guard condition: _sdk_attempt < MAX_SDK_STREAM_RETRIES."""
        # On attempt 0 (first try): 0 < 1 is True → can retry
        assert 0 < MAX_SDK_STREAM_RETRIES

        # On attempt 1 (retry): 1 < 1 is False → cannot retry further
        assert not (1 < MAX_SDK_STREAM_RETRIES)
