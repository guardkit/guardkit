"""Tests for LLM instrumentation helper module.

Pure function tests covering provider detection, token extraction,
latency measurement, error classification, prefix cache checking,
and tool name sanitisation.

TDD RED: Written before implementation to define expected behaviour.
"""

from __future__ import annotations

import asyncio
import re
import time
from unittest.mock import MagicMock

import pytest


# ============================================================================
# detect_provider tests
# ============================================================================


class TestDetectProvider:
    """Tests for detect_provider() function."""

    def test_none_url_returns_anthropic(self) -> None:
        """None base_url defaults to anthropic."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            detect_provider,
        )

        assert detect_provider(None, None) == "anthropic"

    def test_anthropic_url(self) -> None:
        """api.anthropic.com URL returns anthropic."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            detect_provider,
        )

        assert detect_provider("https://api.anthropic.com/v1", None) == "anthropic"

    def test_openai_url(self) -> None:
        """URL containing 'openai' returns openai."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            detect_provider,
        )

        assert detect_provider("https://api.openai.com/v1", None) == "openai"

    def test_localhost_url(self) -> None:
        """URL containing 'localhost' returns local-vllm."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            detect_provider,
        )

        assert detect_provider("http://localhost:8000", None) == "local-vllm"

    def test_vllm_url(self) -> None:
        """URL containing 'vllm' returns local-vllm."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            detect_provider,
        )

        assert detect_provider("http://vllm-server:8000/v1", None) == "local-vllm"

    def test_unknown_url_defaults_anthropic(self) -> None:
        """Unknown URL defaults to anthropic."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            detect_provider,
        )

        assert detect_provider("https://my-custom-llm.example.com", None) == "anthropic"

    def test_empty_string_url_defaults_anthropic(self) -> None:
        """Empty string base_url defaults to anthropic."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            detect_provider,
        )

        assert detect_provider("", None) == "anthropic"

    def test_case_insensitive_openai(self) -> None:
        """OpenAI detection is case-insensitive."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            detect_provider,
        )

        assert detect_provider("https://API.OPENAI.COM/v1", None) == "openai"

    def test_case_insensitive_localhost(self) -> None:
        """Localhost detection is case-insensitive."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            detect_provider,
        )

        assert detect_provider("http://LOCALHOST:8080", None) == "local-vllm"

    def test_model_string_ignored_when_url_provided(self) -> None:
        """When base_url is provided, model string is not used for detection."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            detect_provider,
        )

        assert detect_provider("https://api.openai.com/v1", "claude-sonnet-4-20250514") == "openai"


# ============================================================================
# extract_token_usage tests
# ============================================================================


class TestExtractTokenUsage:
    """Tests for extract_token_usage() function."""

    def test_empty_list_returns_zeros(self) -> None:
        """Empty message list returns (0, 0)."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            extract_token_usage,
        )

        assert extract_token_usage([]) == (0, 0)

    def test_none_usage_returns_zeros(self) -> None:
        """Messages without usage data return (0, 0)."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            extract_token_usage,
        )

        msg = MagicMock()
        msg.usage = None
        assert extract_token_usage([msg]) == (0, 0)

    def test_valid_usage_extracted(self) -> None:
        """Messages with usage data return correct token counts."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            extract_token_usage,
        )

        msg = MagicMock()
        msg.usage = MagicMock()
        msg.usage.input_tokens = 1000
        msg.usage.output_tokens = 500
        assert extract_token_usage([msg]) == (1000, 500)

    def test_zero_tokens_is_valid(self) -> None:
        """Zero token counts are valid values, not errors."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            extract_token_usage,
        )

        msg = MagicMock()
        msg.usage = MagicMock()
        msg.usage.input_tokens = 0
        msg.usage.output_tokens = 0
        assert extract_token_usage([msg]) == (0, 0)

    def test_multiple_messages_uses_last_with_usage(self) -> None:
        """When multiple messages have usage, the last one with usage is used."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            extract_token_usage,
        )

        msg1 = MagicMock()
        msg1.usage = MagicMock()
        msg1.usage.input_tokens = 100
        msg1.usage.output_tokens = 50

        msg2 = MagicMock()
        msg2.usage = MagicMock()
        msg2.usage.input_tokens = 200
        msg2.usage.output_tokens = 150

        assert extract_token_usage([msg1, msg2]) == (200, 150)

    def test_messages_without_usage_attribute(self) -> None:
        """Messages without usage attribute return (0, 0)."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            extract_token_usage,
        )

        msg = MagicMock(spec=[])  # No attributes at all
        assert extract_token_usage([msg]) == (0, 0)

    def test_usage_missing_input_tokens(self) -> None:
        """Usage object missing input_tokens returns (0, 0)."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            extract_token_usage,
        )

        msg = MagicMock()
        msg.usage = MagicMock(spec=[])  # usage exists but no input_tokens
        assert extract_token_usage([msg]) == (0, 0)


# ============================================================================
# measure_latency tests
# ============================================================================


class TestMeasureLatency:
    """Tests for measure_latency() context manager."""

    def test_records_elapsed_time(self) -> None:
        """Latency result has positive millisecond value after context exits."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            measure_latency,
        )

        with measure_latency() as latency:
            time.sleep(0.01)  # Sleep 10ms

        assert latency.ms > 0
        # Should be at least ~10ms but allow some tolerance
        assert latency.ms >= 5.0

    def test_records_latency_on_exception(self) -> None:
        """Latency is recorded even when wrapped call raises an exception."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            measure_latency,
        )

        with pytest.raises(ValueError, match="test error"):
            with measure_latency() as latency:
                time.sleep(0.01)
                raise ValueError("test error")

        # Latency should still be recorded
        assert latency.ms > 0

    def test_latency_result_type(self) -> None:
        """LatencyResult has a ms attribute of type float."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            measure_latency,
        )

        with measure_latency() as latency:
            pass

        assert isinstance(latency.ms, float)

    def test_very_short_operation(self) -> None:
        """Very short operations still have non-negative latency."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            measure_latency,
        )

        with measure_latency() as latency:
            _ = 1 + 1

        assert latency.ms >= 0.0


# ============================================================================
# classify_error tests
# ============================================================================


class TestClassifyError:
    """Tests for classify_error() function."""

    def test_none_returns_none(self) -> None:
        """No exception returns None."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            classify_error,
        )

        assert classify_error(None) is None

    def test_asyncio_timeout_error(self) -> None:
        """asyncio.TimeoutError maps to 'timeout'."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            classify_error,
        )

        assert classify_error(asyncio.TimeoutError()) == "timeout"

    def test_sdk_timeout_error(self) -> None:
        """SDKTimeoutError maps to 'timeout'."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            classify_error,
        )
        from guardkit.orchestrator.exceptions import SDKTimeoutError

        assert classify_error(SDKTimeoutError("timed out")) == "timeout"

    def test_rate_limit_error(self) -> None:
        """RateLimitExceededError maps to 'rate_limited'."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            classify_error,
        )
        from guardkit.orchestrator.exceptions import RateLimitExceededError

        assert classify_error(RateLimitExceededError("429")) == "rate_limited"

    def test_process_error(self) -> None:
        """Exception with 'ProcessError' type name maps to 'tool_error'."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            classify_error,
        )

        # Simulate a ProcessError-like exception without importing the SDK
        class ProcessError(Exception):
            pass

        assert classify_error(ProcessError("tool failed")) == "tool_error"

    def test_generic_exception_returns_other(self) -> None:
        """Generic exception returns 'other'."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            classify_error,
        )

        assert classify_error(RuntimeError("something went wrong")) == "other"

    def test_value_error_returns_other(self) -> None:
        """ValueError returns 'other'."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            classify_error,
        )

        assert classify_error(ValueError("bad value")) == "other"

    def test_os_error_returns_other(self) -> None:
        """OSError returns 'other'."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            classify_error,
        )

        assert classify_error(OSError("disk full")) == "other"


# ============================================================================
# check_prefix_cache tests
# ============================================================================


class TestCheckPrefixCache:
    """Tests for check_prefix_cache() function."""

    def test_none_headers_returns_none_false(self) -> None:
        """None headers returns (None, False)."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            check_prefix_cache,
        )

        assert check_prefix_cache(None) == (None, False)

    def test_empty_headers_returns_none_false(self) -> None:
        """Empty headers dict returns (None, False)."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            check_prefix_cache,
        )

        assert check_prefix_cache({}) == (None, False)

    def test_headers_without_cache_info_returns_none_false(self) -> None:
        """Headers without cache-related keys return (None, False)."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            check_prefix_cache,
        )

        assert check_prefix_cache({"content-type": "application/json"}) == (None, False)

    def test_vllm_cache_hit_header(self) -> None:
        """vLLM-specific cache hit header returns (True, False)."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            check_prefix_cache,
        )

        headers = {"x-vllm-prefix-cache-hit": "true"}
        assert check_prefix_cache(headers) == (True, False)

    def test_vllm_cache_miss_header(self) -> None:
        """vLLM-specific cache miss header returns (False, False)."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            check_prefix_cache,
        )

        headers = {"x-vllm-prefix-cache-hit": "false"}
        assert check_prefix_cache(headers) == (False, False)


# ============================================================================
# sanitise_tool_name tests
# ============================================================================


class TestSanitiseToolName:
    """Tests for sanitise_tool_name() function."""

    def test_clean_name_unchanged(self) -> None:
        """Clean tool name is returned unchanged."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            sanitise_tool_name,
        )

        assert sanitise_tool_name("my-tool_v1.0") == "my-tool_v1.0"

    def test_strips_shell_metacharacters(self) -> None:
        """Shell metacharacters are stripped."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            sanitise_tool_name,
        )

        assert sanitise_tool_name("bash;rm -rf /") == "bashrm -rf "

    def test_strips_pipe(self) -> None:
        """Pipe character is stripped."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            sanitise_tool_name,
        )

        result = sanitise_tool_name("tool|malicious")
        assert "|" not in result

    def test_strips_ampersand(self) -> None:
        """Ampersand is stripped."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            sanitise_tool_name,
        )

        result = sanitise_tool_name("tool&background")
        assert "&" not in result

    def test_strips_backtick(self) -> None:
        """Backtick is stripped."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            sanitise_tool_name,
        )

        result = sanitise_tool_name("tool`cmd`")
        assert "`" not in result

    def test_strips_dollar(self) -> None:
        """Dollar sign is stripped."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            sanitise_tool_name,
        )

        result = sanitise_tool_name("tool$var")
        assert "$" not in result

    def test_keeps_alphanumeric_hyphens_underscores_dots(self) -> None:
        """Only alphanumeric, hyphens, underscores, and dots are kept."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            sanitise_tool_name,
        )

        result = sanitise_tool_name("a-b_c.d1;|&$`><()")
        assert result == "a-b_c.d1"

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            sanitise_tool_name,
        )

        assert sanitise_tool_name("") == ""

    def test_only_metacharacters(self) -> None:
        """String of only metacharacters returns empty string."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            sanitise_tool_name,
        )

        assert sanitise_tool_name(";|&$`><()") == ""


# ============================================================================
# Purity / No Side Effects Tests
# ============================================================================


class TestPurity:
    """Verify all functions are pure with no side effects."""

    def test_no_agent_invoker_import(self) -> None:
        """Module does NOT import agent_invoker."""
        import guardkit.orchestrator.instrumentation.llm_instrumentation as mod
        import inspect

        source = inspect.getsource(mod)
        assert "agent_invoker" not in source

    def test_detect_provider_is_deterministic(self) -> None:
        """detect_provider returns same result for same inputs."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            detect_provider,
        )

        result1 = detect_provider("https://api.openai.com", None)
        result2 = detect_provider("https://api.openai.com", None)
        assert result1 == result2

    def test_classify_error_is_deterministic(self) -> None:
        """classify_error returns same result for same input."""
        from guardkit.orchestrator.instrumentation.llm_instrumentation import (
            classify_error,
        )

        err = RuntimeError("test")
        result1 = classify_error(err)
        result2 = classify_error(err)
        assert result1 == result2
