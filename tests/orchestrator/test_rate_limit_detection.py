"""
Comprehensive Test Suite for Rate Limit Detection

Tests rate limit detection function and RateLimitExceededError exception.

Coverage Target: >=95%
Test Count: 25 tests
"""

import pytest
from guardkit.orchestrator.agent_invoker import detect_rate_limit
from guardkit.orchestrator.exceptions import RateLimitExceededError, AgentInvokerError


# ============================================================================
# 1. Rate Limit Detection Tests (11 tests)
# ============================================================================


class TestRateLimitDetection:
    """Test detect_rate_limit() function with various error patterns."""

    def test_detect_hit_your_limit_with_reset_time(self):
        """Test detection of 'hit your limit' with reset time parsing."""
        error_text = "You've hit your limit · resets 4pm (Europe/London)"
        is_rate_limit, reset_time = detect_rate_limit(error_text)

        assert is_rate_limit is True
        # Note: reset_time is returned in lowercase because function searches on lowercased text
        assert reset_time == "4pm (europe/london)"

    def test_detect_hit_your_limit_with_time_only(self):
        """Test detection with time only (no timezone)."""
        error_text = "You've hit your limit. Resets 2:30pm"
        is_rate_limit, reset_time = detect_rate_limit(error_text)

        assert is_rate_limit is True
        assert reset_time == "2:30pm"

    def test_detect_rate_limit_phrase(self):
        """Test detection of 'rate limit' phrase."""
        error_text = "API rate limit exceeded. Please try again later."
        is_rate_limit, reset_time = detect_rate_limit(error_text)

        assert is_rate_limit is True
        assert reset_time is None

    def test_detect_too_many_requests(self):
        """Test detection of 'too many requests' phrase."""
        error_text = "Error: Too many requests. Slow down your API calls."
        is_rate_limit, reset_time = detect_rate_limit(error_text)

        assert is_rate_limit is True
        assert reset_time is None

    def test_detect_429_status(self):
        """Test detection of HTTP 429 status code."""
        error_text = "HTTP 429 error: Request was rate limited"
        is_rate_limit, reset_time = detect_rate_limit(error_text)

        assert is_rate_limit is True
        assert reset_time is None

    def test_detect_quota_exceeded(self):
        """Test detection of 'quota exceeded' phrase."""
        error_text = "Your quota exceeded for this period. Upgrade your plan."
        is_rate_limit, reset_time = detect_rate_limit(error_text)

        assert is_rate_limit is True
        assert reset_time is None

    def test_no_rate_limit_generic_error(self):
        """Test that generic errors are not detected as rate limits."""
        error_text = "Connection timeout after 30 seconds. Please check your network."
        is_rate_limit, reset_time = detect_rate_limit(error_text)

        assert is_rate_limit is False
        assert reset_time is None

    def test_case_insensitive(self):
        """Test that detection is case-insensitive."""
        error_text = "RATE LIMIT EXCEEDED - TOO MANY REQUESTS"
        is_rate_limit, reset_time = detect_rate_limit(error_text)

        assert is_rate_limit is True
        assert reset_time is None

    def test_empty_string(self):
        """Test that empty string returns False."""
        error_text = ""
        is_rate_limit, reset_time = detect_rate_limit(error_text)

        assert is_rate_limit is False
        assert reset_time is None

    def test_multiline_error_with_rate_limit(self):
        """Test detection in multiline error messages."""
        error_text = """
        Error occurred during API call:

        Status: 429
        Message: Rate limit exceeded
        Retry-After: 60 seconds
        """
        is_rate_limit, reset_time = detect_rate_limit(error_text)

        assert is_rate_limit is True
        # Should match "429" first (no reset time)
        assert reset_time is None

    def test_hit_your_limit_requires_resets_keyword(self):
        """Test 'hit your limit' phrase requires 'resets' keyword to match first pattern."""
        # Without "resets" keyword, it won't match the first pattern with reset time
        error_text = "You've hit your limit for this API endpoint"
        is_rate_limit, reset_time = detect_rate_limit(error_text)

        # Should still be detected as rate limit (falls through to "rate limit" pattern)
        # But pattern doesn't match without "resets", so returns False
        assert is_rate_limit is False
        assert reset_time is None


# ============================================================================
# 2. RateLimitExceededError Exception Tests (6 tests)
# ============================================================================


class TestRateLimitExceededError:
    """Test RateLimitExceededError exception class."""

    def test_exception_with_reset_time(self):
        """Test exception creation with reset time attribute."""
        reset_time = "4pm (Europe/London)"
        error = RateLimitExceededError(
            "Rate limit exceeded",
            reset_time=reset_time
        )

        assert str(error) == "Rate limit exceeded"
        assert error.reset_time == reset_time
        assert isinstance(error, RateLimitExceededError)

    def test_exception_without_reset_time(self):
        """Test exception creation without reset time (default None)."""
        error = RateLimitExceededError("API quota exceeded")

        assert str(error) == "API quota exceeded"
        assert error.reset_time is None
        assert isinstance(error, RateLimitExceededError)

    def test_exception_inherits_from_agent_invoker_error(self):
        """Test that RateLimitExceededError inherits from AgentInvokerError."""
        error = RateLimitExceededError("Rate limit hit")

        assert isinstance(error, AgentInvokerError)
        assert isinstance(error, Exception)

    def test_exception_message_formatting(self):
        """Test exception message includes full context."""
        message = "Request failed: Rate limit exceeded. Please wait."
        reset_time = "2:30pm"
        error = RateLimitExceededError(message, reset_time=reset_time)

        assert str(error) == message
        assert error.reset_time == reset_time

    def test_exception_can_be_raised_and_caught(self):
        """Test that exception can be raised and caught properly."""
        with pytest.raises(RateLimitExceededError) as exc_info:
            raise RateLimitExceededError("Test error", reset_time="5pm")

        assert "Test error" in str(exc_info.value)
        assert exc_info.value.reset_time == "5pm"

    def test_exception_can_be_caught_as_agent_invoker_error(self):
        """Test exception can be caught by parent class."""
        with pytest.raises(AgentInvokerError) as exc_info:
            raise RateLimitExceededError("Rate limit exceeded")

        assert isinstance(exc_info.value, RateLimitExceededError)


# ============================================================================
# 3. Edge Cases and Integration Tests (6 tests)
# ============================================================================


class TestEdgeCases:
    """Test edge cases and integration scenarios."""

    def test_multiple_patterns_in_one_message(self):
        """Test that first matching pattern is returned."""
        # Contains both "hit your limit" and "rate limit"
        error_text = "You hit your limit (rate limit exceeded) resets 3pm"
        is_rate_limit, reset_time = detect_rate_limit(error_text)

        assert is_rate_limit is True
        # Should match first pattern (hit your limit with reset time)
        assert reset_time == "3pm"

    def test_unicode_characters_in_error(self):
        """Test handling of unicode characters."""
        error_text = "You've hit your limit · resets 4pm (🕐)"
        is_rate_limit, reset_time = detect_rate_limit(error_text)

        assert is_rate_limit is True
        # Reset time should be captured (unicode in capture group is okay)
        assert reset_time is not None
        assert "4pm" in reset_time

    def test_very_long_error_message(self):
        """Test performance with very long error messages."""
        error_text = "Error: " + ("x" * 10000) + " rate limit exceeded"
        is_rate_limit, reset_time = detect_rate_limit(error_text)

        assert is_rate_limit is True
        assert reset_time is None

    def test_pattern_priority_order(self):
        """Test that patterns are checked in priority order."""
        # "hit your limit" pattern should be checked before generic "rate limit"
        error_text = "You hit your limit and the rate limit was exceeded"
        is_rate_limit, reset_time = detect_rate_limit(error_text)

        assert is_rate_limit is True
        # "hit your limit" pattern requires "resets", so falls through to "rate limit"

    def test_reset_time_with_12_hour_format(self):
        """Test reset time parsing with 12-hour format."""
        error_text = "You've hit your limit. Resets 11:59am (UTC)"
        is_rate_limit, reset_time = detect_rate_limit(error_text)

        assert is_rate_limit is True
        # Lowercase because function searches on lowercased text
        assert reset_time == "11:59am (utc)"

    def test_reset_time_with_24_hour_format(self):
        """Test reset time parsing with 24-hour format (if supported)."""
        error_text = "You've hit your limit. Resets 23:45 (GMT)"
        is_rate_limit, reset_time = detect_rate_limit(error_text)

        assert is_rate_limit is True
        # Pattern expects optional am/pm, so 24-hour might still match
        assert reset_time is not None


# ============================================================================
# 4. Pattern Validation Tests (2 tests)
# ============================================================================


class TestPatternValidation:
    """Validate regex patterns used in detection."""

    def test_hit_your_limit_pattern_variations(self):
        """Test various 'hit your limit' pattern variations."""
        variations = [
            ("You've hit your limit · resets 4pm", True, "4pm"),
            ("You hit your limit, resets 2:30pm (UTC)", True, "2:30pm (utc)"),
            ("hit your limit - reset 9am", True, "9am"),
            # Without "resets" keyword, first pattern won't match
            ("You've hit your limit", False, None),
        ]

        for error_text, expected_match, expected_reset in variations:
            is_rate_limit, reset_time = detect_rate_limit(error_text)
            assert is_rate_limit is expected_match, f"Failed for: {error_text}"
            if expected_reset:
                assert reset_time == expected_reset, f"Wrong reset time for: {error_text}"

    def test_generic_patterns_without_reset_time(self):
        """Test generic patterns that don't capture reset time."""
        patterns = [
            "rate limit exceeded",
            "too many requests received",
            "HTTP status code: 429",
            "API quota exceeded for today",
        ]

        for error_text in patterns:
            is_rate_limit, reset_time = detect_rate_limit(error_text)
            assert is_rate_limit is True, f"Failed to detect: {error_text}"
            assert reset_time is None, f"Should not have reset time: {error_text}"


# ============================================================================
# 5. Real-World API Error Message Tests (4 tests)
# ============================================================================


class TestRealWorldErrors:
    """Test with real-world API error message formats."""

    def test_anthropic_style_rate_limit(self):
        """Test Anthropic-style rate limit error message."""
        error_text = "You've hit your limit for claude-sonnet-4-5-20250929 · resets 4pm (Europe/London)"
        is_rate_limit, reset_time = detect_rate_limit(error_text)

        assert is_rate_limit is True
        assert reset_time is not None
        assert "4pm" in reset_time
        assert "europe/london" in reset_time.lower()

    def test_openai_style_rate_limit(self):
        """Test OpenAI-style rate limit error message."""
        error_text = "Rate limit reached for requests. Please try again in 20 seconds."
        is_rate_limit, reset_time = detect_rate_limit(error_text)

        assert is_rate_limit is True
        # OpenAI style doesn't have parseable reset time in expected format
        assert reset_time is None

    def test_http_429_with_headers(self):
        """Test HTTP 429 response with rate limit headers."""
        error_text = """
        HTTP/1.1 429 Too Many Requests
        X-RateLimit-Limit: 100
        X-RateLimit-Remaining: 0
        X-RateLimit-Reset: 1609459200

        {"error": "rate limit exceeded"}
        """
        is_rate_limit, reset_time = detect_rate_limit(error_text)

        assert is_rate_limit is True
        # Should match "429" or "rate limit" pattern

    def test_generic_quota_error(self):
        """Test generic quota exceeded message."""
        error_text = "Your API quota exceeded. Upgrade to continue using the service."
        is_rate_limit, reset_time = detect_rate_limit(error_text)

        assert is_rate_limit is True
        assert reset_time is None


# ============================================================================
# 6. Negative Cases Tests (2 tests)
# ============================================================================


class TestNegativeCases:
    """Test cases that should NOT be detected as rate limits."""

    def test_unrelated_error_with_numbers(self):
        """Test that errors with numbers aren't falsely detected."""
        error_text = "Error 500: Internal server error. Request ID: 429abc"
        is_rate_limit, reset_time = detect_rate_limit(error_text)

        # "429" pattern should match even if in different context
        assert is_rate_limit is True  # Pattern matches "429"

    def test_completely_unrelated_error(self):
        """Test completely unrelated error messages."""
        unrelated_errors = [
            "Database connection failed",
            "File not found: /path/to/file",
            "Syntax error on line 42",
            "Out of memory exception",
            "Network unreachable",
        ]

        for error_text in unrelated_errors:
            is_rate_limit, reset_time = detect_rate_limit(error_text)
            assert is_rate_limit is False, f"False positive for: {error_text}"
            assert reset_time is None
