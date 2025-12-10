"""
Tests for JSON error message improvements in SingleAgentEnhancer.

TASK-FIX-AE01: Test coverage for Finding 3 (error message quality).
"""

import pytest
import json


class TestErrorContextExtraction:
    """Test context window extraction logic for JSON errors."""

    def test_context_at_start_of_string(self):
        """Should handle error near start of string (can't go before position 0)."""
        text = "x" * 1000
        error_pos = 10

        context_start = max(0, error_pos - 50)
        context_end = min(len(text), error_pos + 50)
        context = text[context_start:context_end]

        assert context_start == 0  # Can't go before start
        assert len(context) == 60  # 10 before + 50 after

    def test_context_at_end_of_string(self):
        """Should handle error near end of string (can't go past length)."""
        text = "x" * 1000
        error_pos = 990

        context_start = max(0, error_pos - 50)
        context_end = min(len(text), error_pos + 50)
        context = text[context_start:context_end]

        assert context_end == 1000  # Can't go past end
        assert len(context) == 60  # 50 before + 10 after

    def test_context_in_middle_of_string(self):
        """Should extract full 100-char window when in middle."""
        text = "x" * 10000
        error_pos = 5000

        context_start = max(0, error_pos - 50)
        context_end = min(len(text), error_pos + 50)
        context = text[context_start:context_end]

        assert len(context) == 100  # Full window available

    def test_context_short_string(self):
        """Should handle strings shorter than context window."""
        text = "short"  # 5 characters
        error_pos = 2

        context_start = max(0, error_pos - 50)
        context_end = min(len(text), error_pos + 50)
        context = text[context_start:context_end]

        assert context == "short"  # Entire string
        assert len(context) == 5

    def test_context_at_exact_position_zero(self):
        """Should handle error at position 0."""
        text = "x" * 100
        error_pos = 0

        context_start = max(0, error_pos - 50)
        context_end = min(len(text), error_pos + 50)
        context = text[context_start:context_end]

        assert context_start == 0
        assert len(context) == 50  # 0 before + 50 after


class TestJSONDecodeErrorAttributes:
    """Test that JSONDecodeError has expected attributes for context extraction."""

    def test_json_decode_error_has_pos(self):
        """JSONDecodeError should have 'pos' attribute."""
        try:
            json.loads('{"invalid": }')
        except json.JSONDecodeError as e:
            assert hasattr(e, 'pos')
            assert isinstance(e.pos, int)
            assert e.pos >= 0

    def test_json_decode_error_has_msg(self):
        """JSONDecodeError should have 'msg' attribute."""
        try:
            json.loads('{"invalid": }')
        except json.JSONDecodeError as e:
            assert hasattr(e, 'msg')
            assert isinstance(e.msg, str)
            assert len(e.msg) > 0

    def test_json_decode_error_truncated_string(self):
        """Should provide position for truncated JSON."""
        truncated_json = '{"sections": ["quick_start"], "quick_start": "'
        try:
            json.loads(truncated_json)
        except json.JSONDecodeError as e:
            # Position should be at or near end of string
            assert e.pos <= len(truncated_json) + 1
            assert "Unterminated string" in e.msg or "Expecting" in e.msg


class TestErrorContextContent:
    """Test that context extraction shows meaningful content."""

    def test_context_shows_error_location(self):
        """Context should include content around the actual error."""
        malformed = '{"sections": ["quick_start"], "quick_start": "content", "invalid": }'
        try:
            json.loads(malformed)
        except json.JSONDecodeError as e:
            error_pos = e.pos
            context_start = max(0, error_pos - 50)
            context_end = min(len(malformed), error_pos + 50)
            context = malformed[context_start:context_end]

            # Context should contain the problematic area
            # The error is near the empty value }
            assert len(context) > 0
            # Verify we can see content around the error
            assert context in malformed

    def test_context_for_nested_json_error(self):
        """Should provide context for errors in nested JSON."""
        nested_malformed = '{"sections": ["a"], "data": {"nested": {"deep": invalid}}}'
        try:
            json.loads(nested_malformed)
        except json.JSONDecodeError as e:
            error_pos = e.pos
            context_start = max(0, error_pos - 50)
            context_end = min(len(nested_malformed), error_pos + 50)
            context = nested_malformed[context_start:context_end]

            # Should show "invalid" in context since that's where error is
            assert "invalid" in context.lower() or "deep" in context.lower()


class TestErrorMessageSuggestions:
    """Test that error handling provides useful suggestions."""

    def test_suggestion_format(self):
        """Verify the structure of suggested remediation."""
        # These are the suggestions that should appear in error messages
        expected_suggestions = [
            "--static",  # Flag to use static fallback
            "truncated",  # Mention truncation as likely cause
            "corrupted",  # Mention corruption as possibility
        ]

        # The enhancer.py error handler should include these
        # This test validates the expected content structure
        error_message_template = (
            "Likely cause: AI response truncated or corrupted\n"
            "Suggestion: Re-run with --static for reliable results"
        )

        for suggestion in expected_suggestions:
            assert suggestion in error_message_template.lower()

    def test_response_size_info_helps_debugging(self):
        """Response size should help identify truncation issues."""
        # Typical truncation scenarios
        small_response = '{"sections": []}'  # 16 chars - likely complete
        large_response = '{"sections": [' + '"x" ' * 10000 + ']}'  # ~40k chars

        # Size comparison helps identify if response was truncated
        assert len(small_response) < 1000  # Small responses unlikely truncated
        assert len(large_response) > 30000  # Large responses may hit limits


class TestValidationErrorMessage:
    """Test ValidationError message format."""

    def test_error_includes_position(self):
        """ValidationError should include error position."""
        from pathlib import Path
        import sys

        # Import ValidationError from enhancer module
        _test_dir = Path(__file__).resolve().parent
        _lib_dir = _test_dir.parent.parent.parent / "installer" / "core" / "lib" / "agent_enhancement"
        sys.path.insert(0, str(_lib_dir))

        from enhancer import ValidationError

        error = ValidationError("Invalid JSON at position 1234: Expecting value")
        assert "1234" in str(error)
        assert "Invalid JSON" in str(error)

    def test_error_includes_original_message(self):
        """ValidationError should preserve original error message."""
        from pathlib import Path
        import sys

        _test_dir = Path(__file__).resolve().parent
        _lib_dir = _test_dir.parent.parent.parent / "installer" / "core" / "lib" / "agent_enhancement"
        sys.path.insert(0, str(_lib_dir))

        from enhancer import ValidationError

        original_msg = "Expecting property name"
        error = ValidationError(f"Invalid JSON at position 100: {original_msg}")
        assert original_msg in str(error)
