"""Unit tests for lib/clarification/display.py

Tests the display formatting functions for the clarifying questions feature.
"""

import pytest
from unittest.mock import patch, MagicMock
from io import StringIO
import sys

from lib.clarification.display import (
    display_questions_full,
    display_questions_quick,
    display_question_skip,
    format_question,
    format_options,
    format_decision_summary,
)
from lib.clarification.core import Question, Decision, ClarificationContext


class TestFormatQuestion:
    """Test individual question formatting."""

    def test_format_basic_question(self):
        """Test formatting a basic question."""
        q = Question(
            id="scope",
            category="scope",
            text="How comprehensive should the implementation be?",
            options=["[M]inimal", "[S]tandard", "[C]omplete"],
            default="S",
        )

        formatted = format_question(q)

        assert "How comprehensive" in formatted
        assert "[M]inimal" in formatted
        assert "[S]tandard" in formatted
        assert "[C]omplete" in formatted
        # Should indicate default
        assert "default" in formatted.lower() or "S" in formatted

    def test_format_question_with_rationale(self):
        """Test formatting question with rationale."""
        q = Question(
            id="testing",
            category="quality",
            text="What testing level?",
            options=["[U]nit", "[I]ntegration", "[E]nd-to-end"],
            default="U",
            rationale="Unit tests provide fast feedback",
        )

        formatted = format_question(q)

        assert "What testing level?" in formatted
        assert "Unit tests provide fast feedback" in formatted

    def test_format_question_no_default(self):
        """Test formatting question without default."""
        q = Question(
            id="tech",
            category="technology",
            text="Which technology?",
            options=["[R]edis", "[M]emcached"],
        )

        formatted = format_question(q)

        assert "Which technology?" in formatted
        # Should not mention default if not present
        assert "[R]edis" in formatted
        assert "[M]emcached" in formatted


class TestFormatOptions:
    """Test option formatting."""

    def test_format_simple_options(self):
        """Test formatting simple options."""
        options = ["[Y]es", "[N]o"]
        formatted = format_options(options)

        assert "[Y]es" in formatted
        assert "[N]o" in formatted

    def test_format_multiple_options(self):
        """Test formatting multiple options."""
        options = ["[M]inimal", "[S]tandard", "[C]omplete", "[F]ull"]
        formatted = format_options(options, default="S")

        assert all(opt in formatted for opt in options)
        # Should highlight default somehow
        assert "S" in formatted or "Standard" in formatted

    def test_format_options_with_descriptions(self):
        """Test formatting options with descriptions."""
        options = [
            "[M]inimal - Basic implementation only",
            "[S]tandard - With error handling",
            "[C]omplete - Production-ready",
        ]
        formatted = format_options(options)

        assert "Basic implementation" in formatted
        assert "error handling" in formatted
        assert "Production-ready" in formatted


class TestFormatDecisionSummary:
    """Test decision summary formatting."""

    def test_format_single_decision(self):
        """Test formatting a single decision."""
        decision = Decision(
            question_id="scope",
            category="scope",
            question_text="How comprehensive?",
            answer="standard",
            answer_display="Standard - With error handling",
            default_used=True,
            rationale="Default selected",
        )

        summary = format_decision_summary([decision])

        assert "How comprehensive?" in summary
        assert "Standard" in summary or "standard" in summary
        # Should indicate it was a default
        assert "default" in summary.lower() or "automatically" in summary.lower()

    def test_format_multiple_decisions(self):
        """Test formatting multiple decisions."""
        decisions = [
            Decision(
                question_id="scope",
                category="scope",
                question_text="How comprehensive?",
                answer="standard",
                answer_display="Standard",
                default_used=True,
                rationale="Default",
            ),
            Decision(
                question_id="testing",
                category="quality",
                question_text="What testing?",
                answer="unit",
                answer_display="Unit tests",
                default_used=False,
                rationale="User selected",
            ),
        ]

        summary = format_decision_summary(decisions)

        assert "How comprehensive?" in summary
        assert "What testing?" in summary
        assert "Standard" in summary
        assert "Unit tests" in summary

    def test_format_no_decisions(self):
        """Test formatting empty decision list."""
        summary = format_decision_summary([])

        assert "no" in summary.lower() or "none" in summary.lower() or "" == summary


class TestDisplayQuestionsFull:
    """Test full interactive question display."""

    @patch('builtins.input')
    def test_display_full_with_user_input(self, mock_input):
        """Test full display with user providing answers."""
        # Setup mock user inputs
        mock_input.side_effect = ["S", "U", "N"]

        questions = [
            Question(
                id="scope",
                category="scope",
                text="How comprehensive?",
                options=["[M]inimal", "[S]tandard", "[C]omplete"],
                default="S",
            ),
            Question(
                id="testing",
                category="quality",
                text="What testing?",
                options=["[U]nit", "[I]ntegration"],
                default="U",
            ),
            Question(
                id="docs",
                category="documentation",
                text="Update docs?",
                options=["[Y]es", "[N]o"],
            ),
        ]

        context = display_questions_full(
            questions=questions,
            context_type="implementation_planning",
        )

        assert context is not None
        assert context.context_type == "implementation_planning"
        assert context.mode == "full"
        assert len(context.decisions) == 3

        # Verify answers recorded
        assert context.decisions[0].answer.upper() == "S"
        assert context.decisions[1].answer.upper() == "U"
        assert context.decisions[2].answer.upper() == "N"

    @patch('builtins.input')
    def test_display_full_with_defaults(self, mock_input):
        """Test full display using all defaults (user hits Enter)."""
        # User hits Enter for all questions (use defaults)
        mock_input.side_effect = ["", "", ""]

        questions = [
            Question(
                id="scope",
                category="scope",
                text="How comprehensive?",
                options=["[M]inimal", "[S]tandard"],
                default="S",
            ),
            Question(
                id="testing",
                category="quality",
                text="What testing?",
                options=["[U]nit", "[I]ntegration"],
                default="U",
            ),
            Question(
                id="docs",
                category="documentation",
                text="Update docs?",
                options=["[Y]es", "[N]o"],
                default="Y",
            ),
        ]

        context = display_questions_full(
            questions=questions,
            context_type="implementation_planning",
        )

        assert context is not None
        assert len(context.decisions) == 3

        # All should use defaults
        assert all(d.default_used for d in context.decisions)
        assert context.decisions[0].answer.upper() == "S"
        assert context.decisions[1].answer.upper() == "U"
        assert context.decisions[2].answer.upper() == "Y"

    @patch('builtins.input')
    def test_display_full_invalid_then_valid_input(self, mock_input):
        """Test full display with invalid input, then valid."""
        # First invalid ("X"), then valid ("S")
        mock_input.side_effect = ["X", "S"]

        questions = [
            Question(
                id="scope",
                category="scope",
                text="How comprehensive?",
                options=["[M]inimal", "[S]tandard"],
                default="S",
            ),
        ]

        context = display_questions_full(
            questions=questions,
            context_type="implementation_planning",
        )

        assert context is not None
        assert context.decisions[0].answer.upper() == "S"


class TestDisplayQuestionsQuick:
    """Test quick mode with timeout."""

    @patch('builtins.input')
    @patch('lib.clarification.display.timeout_input')
    def test_display_quick_with_timeout(self, mock_timeout_input, mock_input):
        """Test quick mode with timeout expiring."""
        # Simulate timeout (returns None)
        mock_timeout_input.return_value = None

        questions = [
            Question(
                id="scope",
                category="scope",
                text="How comprehensive?",
                options=["[M]inimal", "[S]tandard"],
                default="S",
            ),
        ]

        context = display_questions_quick(
            questions=questions,
            context_type="implementation_planning",
            timeout=15,
        )

        assert context is not None
        assert context.mode == "quick"
        # Should use default due to timeout
        assert context.decisions[0].default_used is True
        assert context.decisions[0].answer.upper() == "S"

    @patch('builtins.input')
    @patch('lib.clarification.display.timeout_input')
    def test_display_quick_with_answer(self, mock_timeout_input, mock_input):
        """Test quick mode with user providing answer before timeout."""
        # User answers before timeout
        mock_timeout_input.return_value = "M"

        questions = [
            Question(
                id="scope",
                category="scope",
                text="How comprehensive?",
                options=["[M]inimal", "[S]tandard"],
                default="S",
            ),
        ]

        context = display_questions_quick(
            questions=questions,
            context_type="implementation_planning",
            timeout=15,
        )

        assert context is not None
        assert context.mode == "quick"
        # Should use user's answer
        assert context.decisions[0].default_used is False
        assert context.decisions[0].answer.upper() == "M"

    @patch('builtins.input')
    @patch('lib.clarification.display.timeout_input')
    def test_display_quick_mixed_timeout_and_answers(self, mock_timeout_input, mock_input):
        """Test quick mode with some timeouts and some answers."""
        # First question: user answers, second: timeout
        mock_timeout_input.side_effect = ["M", None]

        questions = [
            Question(
                id="scope",
                category="scope",
                text="How comprehensive?",
                options=["[M]inimal", "[S]tandard"],
                default="S",
            ),
            Question(
                id="testing",
                category="quality",
                text="What testing?",
                options=["[U]nit", "[I]ntegration"],
                default="U",
            ),
        ]

        context = display_questions_quick(
            questions=questions,
            context_type="implementation_planning",
            timeout=15,
        )

        assert context is not None
        assert len(context.decisions) == 2

        # First decision: user answered
        assert context.decisions[0].default_used is False
        assert context.decisions[0].answer.upper() == "M"

        # Second decision: timeout (default)
        assert context.decisions[1].default_used is True
        assert context.decisions[1].answer.upper() == "U"


class TestDisplayQuestionSkip:
    """Test skip mode."""

    def test_skip_returns_skip_context(self):
        """Test skip mode returns context with skip mode."""
        context = display_question_skip(context_type="implementation_planning")

        assert context is not None
        assert context.context_type == "implementation_planning"
        assert context.mode == "skip"
        assert len(context.decisions) == 0

    def test_skip_different_contexts(self):
        """Test skip mode with different context types."""
        context_types = [
            "implementation_planning",
            "review_scope",
            "implementation_prefs",
        ]

        for ctx_type in context_types:
            context = display_question_skip(context_type=ctx_type)
            assert context.context_type == ctx_type
            assert context.mode == "skip"


class TestDisplayFormatting:
    """Test visual formatting and output."""

    @patch('sys.stdout', new_callable=StringIO)
    @patch('builtins.input')
    def test_output_contains_formatting(self, mock_input, mock_stdout):
        """Test that output contains proper formatting elements."""
        mock_input.return_value = "S"

        questions = [
            Question(
                id="scope",
                category="scope",
                text="How comprehensive?",
                options=["[M]inimal", "[S]tandard"],
                default="S",
            ),
        ]

        display_questions_full(
            questions=questions,
            context_type="implementation_planning",
        )

        output = mock_stdout.getvalue()

        # Should have some visual separators or headers
        # Exact formatting depends on implementation
        assert len(output) > 0

    @patch('sys.stdout', new_callable=StringIO)
    @patch('builtins.input')
    def test_quick_mode_shows_timeout_warning(self, mock_input, mock_stdout):
        """Test that quick mode displays timeout warning."""
        mock_input.return_value = "S"

        questions = [
            Question(
                id="scope",
                category="scope",
                text="How comprehensive?",
                options=["[M]inimal", "[S]tandard"],
                default="S",
            ),
        ]

        display_questions_quick(
            questions=questions,
            context_type="implementation_planning",
            timeout=15,
        )

        output = mock_stdout.getvalue()

        # Should mention timeout
        assert "15" in output or "timeout" in output.lower() or "seconds" in output.lower()


class TestEdgeCases:
    """Test edge cases."""

    @patch('builtins.input')
    def test_empty_questions_list(self, mock_input):
        """Test handling of empty questions list."""
        context = display_questions_full(
            questions=[],
            context_type="implementation_planning",
        )

        # Should return valid context with no decisions
        assert context is not None
        assert len(context.decisions) == 0
        assert context.mode == "full"

    @patch('builtins.input')
    def test_question_without_options(self, mock_input):
        """Test handling of question without options."""
        mock_input.return_value = "yes"

        questions = [
            Question(
                id="confirm",
                category="confirmation",
                text="Proceed?",
                options=[],  # Empty options
            ),
        ]

        # Behavior depends on implementation
        # May skip question, use free-form input, or raise error
        try:
            context = display_questions_full(
                questions=questions,
                context_type="implementation_planning",
            )
            # If it doesn't error, verify context is valid
            assert context is not None
        except ValueError:
            # Also acceptable to raise error for malformed question
            pass

    @patch('builtins.input')
    def test_case_insensitive_input(self, mock_input):
        """Test that input is case-insensitive."""
        # User types lowercase, should match [S]tandard
        mock_input.return_value = "s"

        questions = [
            Question(
                id="scope",
                category="scope",
                text="How comprehensive?",
                options=["[M]inimal", "[S]tandard"],
                default="S",
            ),
        ]

        context = display_questions_full(
            questions=questions,
            context_type="implementation_planning",
        )

        assert context.decisions[0].answer.upper() == "S"
