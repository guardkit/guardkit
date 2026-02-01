"""
Tests for Graphiti query command output formatting utilities.
"""

import json
from io import StringIO
from unittest.mock import patch

import pytest
from rich.console import Console

from guardkit.cli.graphiti_query_commands import (
    BOX_CHARS,
    _detect_knowledge_type,
    _format_detail,
    _get_score_color,
    _truncate_text,
    format_search_results,
    format_show_output,
    format_status_box,
)


class TestScoreColor:
    """Tests for _get_score_color function."""

    def test_high_relevance_green(self):
        """High relevance scores (>0.8) should return green."""
        assert _get_score_color(0.9) == "green"
        assert _get_score_color(0.85) == "green"
        assert _get_score_color(1.0) == "green"

    def test_medium_relevance_yellow(self):
        """Medium relevance scores (>0.5, <=0.8) should return yellow."""
        assert _get_score_color(0.7) == "yellow"
        assert _get_score_color(0.6) == "yellow"
        assert _get_score_color(0.51) == "yellow"

    def test_low_relevance_white(self):
        """Low relevance scores (<=0.5) should return white."""
        assert _get_score_color(0.5) == "white"
        assert _get_score_color(0.3) == "white"
        assert _get_score_color(0.0) == "white"

    def test_boundary_values(self):
        """Test exact boundary values."""
        # Exactly 0.8 should be yellow (not green)
        assert _get_score_color(0.8) == "yellow"
        # Just above 0.8 should be green
        assert _get_score_color(0.8001) == "green"
        # Exactly 0.5 should be white
        assert _get_score_color(0.5) == "white"
        # Just above 0.5 should be yellow
        assert _get_score_color(0.5001) == "yellow"


class TestTruncateText:
    """Tests for _truncate_text function."""

    def test_short_text_unchanged(self):
        """Short text should not be truncated."""
        text = "Hello world"
        assert _truncate_text(text, 20) == text

    def test_exact_length_unchanged(self):
        """Text exactly at max_length should not be truncated."""
        text = "Hello"
        assert _truncate_text(text, 5) == text

    def test_long_text_truncated(self):
        """Long text should be truncated with ellipsis."""
        text = "This is a very long text that should be truncated"
        result = _truncate_text(text, 20)
        assert len(result) == 23  # 20 + "..."
        assert result.endswith("...")
        assert result == "This is a very long ..."

    def test_truncation_preserves_prefix(self):
        """Truncation should preserve the beginning of the text."""
        text = "Important information here and more"
        result = _truncate_text(text, 10)
        assert result.startswith("Important")

    def test_empty_text(self):
        """Empty text should remain empty."""
        assert _truncate_text("", 10) == ""

    def test_single_character(self):
        """Single character within limit should be unchanged."""
        assert _truncate_text("A", 10) == "A"


class TestDetectKnowledgeType:
    """Tests for _detect_knowledge_type function."""

    def test_feature_detection(self):
        """FEAT- prefix should be detected as feature."""
        assert _detect_knowledge_type("FEAT-001") == "feature"
        assert _detect_knowledge_type("FEAT-GR-001") == "feature"
        assert _detect_knowledge_type("feat-test") == "feature"

    def test_adr_detection(self):
        """ADR- prefix should be detected as adr."""
        assert _detect_knowledge_type("ADR-001") == "adr"
        assert _detect_knowledge_type("ADR-FB-001") == "adr"
        assert _detect_knowledge_type("adr-test") == "adr"

    def test_pattern_detection(self):
        """Pattern in name should be detected."""
        assert _detect_knowledge_type("singleton-pattern") == "pattern"
        assert _detect_knowledge_type("pattern-factory") == "pattern"
        assert _detect_knowledge_type("PATTERN-001") == "pattern"

    def test_default_detection(self):
        """Unknown types should default to 'default'."""
        assert _detect_knowledge_type("project-overview") == "default"
        assert _detect_knowledge_type("some-guide") == "default"
        assert _detect_knowledge_type("random-id") == "default"


class TestFormatSearchResults:
    """Tests for format_search_results function."""

    def test_empty_results(self):
        """Empty results should display no results message."""
        with patch("guardkit.cli.graphiti_query_commands.console") as mock_console:
            format_search_results([], "test query")

            # Should print "No results found" message
            mock_console.print.assert_called()
            call_args = str(mock_console.print.call_args)
            assert "No results found" in call_args
            assert "test query" in call_args

    def test_single_result(self):
        """Single result should be formatted correctly."""
        results = [
            {
                "score": 0.9,
                "fact": "This is a test fact",
            }
        ]

        with patch("guardkit.cli.graphiti_query_commands.console") as mock_console:
            format_search_results(results, "test")

            # Should show result count
            calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("Found 1 results" in call for call in calls)

    def test_multiple_results(self):
        """Multiple results should be numbered."""
        results = [
            {"score": 0.9, "fact": "First fact"},
            {"score": 0.6, "fact": "Second fact"},
            {"score": 0.3, "fact": "Third fact"},
        ]

        with patch("guardkit.cli.graphiti_query_commands.console") as mock_console:
            format_search_results(results, "test")

            calls = [str(call) for call in mock_console.print.call_args_list]
            # Should show numbered results
            assert any("1." in call for call in calls)
            assert any("2." in call for call in calls)
            assert any("3." in call for call in calls)

    def test_score_color_coding(self):
        """Results should be color-coded by score."""
        results = [
            {"score": 0.9, "fact": "High score"},
            {"score": 0.6, "fact": "Medium score"},
            {"score": 0.3, "fact": "Low score"},
        ]

        with patch("guardkit.cli.graphiti_query_commands.console") as mock_console:
            format_search_results(results, "test")

            calls = [str(call) for call in mock_console.print.call_args_list]
            # Should include color formatting
            output = " ".join(calls)
            assert "green" in output or "0.90" in output
            assert "yellow" in output or "0.60" in output

    def test_long_fact_truncation(self):
        """Long facts should be truncated."""
        long_fact = "A" * 150  # 150 characters
        results = [{"score": 0.8, "fact": long_fact}]

        with patch("guardkit.cli.graphiti_query_commands.console") as mock_console:
            format_search_results(results, "test")

            calls = [str(call) for call in mock_console.print.call_args_list]
            # Should truncate to 100 chars + "..."
            # Check that the full 150-char string isn't in output
            output = " ".join(calls)
            assert long_fact not in output


class TestFormatShowOutput:
    """Tests for format_show_output function."""

    def test_empty_results(self):
        """Empty results should show not found message."""
        with patch("guardkit.cli.graphiti_query_commands.console") as mock_console:
            format_show_output([], "FEAT-001")

            calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("Not found" in call for call in calls)

    def test_single_result_with_name(self):
        """Single result should display name and details."""
        results = [
            {
                "name": "Test Feature",
                "fact": "Feature description",
                "score": 0.9,
                "uuid": "test-uuid-123",
            }
        ]

        with patch("guardkit.cli.graphiti_query_commands.console") as mock_console:
            format_show_output(results, "FEAT-001")

            calls = [str(call) for call in mock_console.print.call_args_list]
            output = " ".join(calls)
            assert "Test Feature" in output

    def test_structured_json_fact(self):
        """Structured JSON facts should be parsed and displayed."""
        fact_data = {
            "id": "FEAT-001",
            "description": "Test feature",
            "status": "active",
        }
        results = [
            {
                "name": "Feature",
                "fact": json.dumps(fact_data),
                "score": 0.9,
            }
        ]

        with patch("guardkit.cli.graphiti_query_commands.console") as mock_console:
            format_show_output(results, "FEAT-001")

            calls = [str(call) for call in mock_console.print.call_args_list]
            output = " ".join(calls)
            # Should display parsed fields
            assert "FEAT-001" in output or "Test feature" in output

    def test_multiple_results(self):
        """Multiple results should all be displayed."""
        results = [
            {"name": "Result 1", "fact": "Fact 1", "score": 0.9},
            {"name": "Result 2", "fact": "Fact 2", "score": 0.8},
        ]

        with patch("guardkit.cli.graphiti_query_commands.console") as mock_console:
            format_show_output(results, "test-id")

            calls = [str(call) for call in mock_console.print.call_args_list]
            output = " ".join(calls)
            assert "Result 1" in output
            assert "Result 2" in output


class TestFormatDetail:
    """Tests for _format_detail function."""

    def test_plain_text_fact(self):
        """Plain text facts should be displayed as-is."""
        result = {
            "name": "Test Item",
            "fact": "This is plain text",
            "score": 0.7,
        }

        with patch("guardkit.cli.graphiti_query_commands.console") as mock_console:
            _format_detail(result, "default")

            calls = [str(call) for call in mock_console.print.call_args_list]
            output = " ".join(calls)
            assert "Test Item" in output
            assert "This is plain text" in output

    def test_json_fact_parsing(self):
        """JSON facts should be parsed and formatted."""
        fact_data = {"id": "TEST-001", "description": "Test description"}
        result = {
            "name": "Test",
            "fact": json.dumps(fact_data),
            "score": 0.8,
        }

        with patch("guardkit.cli.graphiti_query_commands.console") as mock_console:
            _format_detail(result, "default")

            calls = [str(call) for call in mock_console.print.call_args_list]
            output = " ".join(calls)
            assert "TEST-001" in output or "Test description" in output

    def test_metadata_display(self):
        """Metadata fields should be displayed."""
        result = {
            "name": "Test",
            "fact": "Fact",
            "score": 0.95,
            "uuid": "uuid-123",
            "created_at": "2024-01-01",
        }

        with patch("guardkit.cli.graphiti_query_commands.console") as mock_console:
            _format_detail(result, "default")

            calls = [str(call) for call in mock_console.print.call_args_list]
            output = " ".join(calls)
            assert "uuid-123" in output
            assert "0.95" in output
            assert "2024-01-01" in output

    def test_feature_knowledge_type(self):
        """Feature type should display feature-specific fields."""
        fact_data = {
            "id": "FEAT-001",
            "title": "Feature Title",
            "description": "Description",
            "success_criteria": ["Criterion 1", "Criterion 2"],
        }
        result = {
            "name": "Feature",
            "fact": json.dumps(fact_data),
            "score": 0.9,
        }

        with patch("guardkit.cli.graphiti_query_commands.console") as mock_console:
            _format_detail(result, "feature")

            calls = [str(call) for call in mock_console.print.call_args_list]
            output = " ".join(calls)
            # Should show success criteria
            assert "Criterion 1" in output or "Success" in output


class TestFormatStatusBox:
    """Tests for format_status_box function."""

    def test_basic_box_formatting(self):
        """Status box should be formatted with borders."""
        items = [
            ("Status", "Active"),
            ("Version", "1.0"),
        ]

        with patch("guardkit.cli.graphiti_query_commands.console") as mock_console:
            format_status_box("Test Box", items, width=40)

            calls = [str(call) for call in mock_console.print.call_args_list]
            output = " ".join(calls)
            # Should contain box-drawing characters
            assert BOX_CHARS["top_left"] in output or "┌" in output
            assert "Test Box" in output
            assert "Status" in output
            assert "Active" in output

    def test_long_value_truncation(self):
        """Long values should be truncated to fit box width."""
        items = [
            ("Key", "A" * 100),  # Very long value
        ]

        with patch("guardkit.cli.graphiti_query_commands.console") as mock_console:
            format_status_box("Box", items, width=40)

            calls = [str(call) for call in mock_console.print.call_args_list]
            output = " ".join(calls)
            # Should not contain the full 100-char string
            assert "A" * 100 not in output

    def test_multiple_items(self):
        """Multiple items should all be displayed."""
        items = [
            ("Item1", "Value1"),
            ("Item2", "Value2"),
            ("Item3", "Value3"),
        ]

        with patch("guardkit.cli.graphiti_query_commands.console") as mock_console:
            format_status_box("Multi-Item Box", items)

            calls = [str(call) for call in mock_console.print.call_args_list]
            output = " ".join(calls)
            assert "Value1" in output
            assert "Value2" in output
            assert "Value3" in output

    def test_empty_items(self):
        """Empty items list should still show box borders."""
        with patch("guardkit.cli.graphiti_query_commands.console") as mock_console:
            format_status_box("Empty Box", [])

            calls = [str(call) for call in mock_console.print.call_args_list]
            output = " ".join(calls)
            # Should still have borders and title
            assert "Empty Box" in output
            # Should have at least top and bottom borders
            assert len(mock_console.print.call_args_list) >= 2


class TestBoxDrawingCharacters:
    """Tests for box drawing character constants."""

    def test_box_chars_defined(self):
        """All box drawing characters should be defined."""
        required_chars = [
            "top_left",
            "top_right",
            "bottom_left",
            "bottom_right",
            "horizontal",
            "vertical",
            "t_down",
            "t_up",
            "t_right",
            "t_left",
            "cross",
        ]

        for char in required_chars:
            assert char in BOX_CHARS
            assert isinstance(BOX_CHARS[char], str)
            assert len(BOX_CHARS[char]) == 1  # Should be single character

    def test_box_chars_unicode(self):
        """Box characters should be proper Unicode box-drawing chars."""
        # Check a few key characters
        assert BOX_CHARS["top_left"] == "┌"
        assert BOX_CHARS["horizontal"] == "─"
        assert BOX_CHARS["vertical"] == "│"
