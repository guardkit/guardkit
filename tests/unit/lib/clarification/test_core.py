"""Unit tests for clarification core module."""

import sys
from pathlib import Path
import pytest

# Add the installer/global/commands directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "installer" / "global" / "commands"))

from lib.clarification.core import (
    ClarificationMode,
    Question,
    Decision,
    ClarificationContext,
    should_clarify,
    process_responses,
    format_for_prompt,
    persist_to_frontmatter,
)


class TestClarificationMode:
    """Tests for ClarificationMode enum."""

    def test_enum_values(self):
        """Test that all expected modes exist."""
        assert ClarificationMode.SKIP.value == "skip"
        assert ClarificationMode.QUICK.value == "quick"
        assert ClarificationMode.FULL.value == "full"
        assert ClarificationMode.USE_DEFAULTS.value == "defaults"


class TestQuestion:
    """Tests for Question dataclass."""

    def test_valid_question(self):
        """Test creating a valid question."""
        q = Question(
            id="q1",
            category="scope",
            text="Include tests?",
            options=["yes", "no"],
            default="yes",
            rationale="Tests are recommended"
        )
        assert q.id == "q1"
        assert q.category == "scope"
        assert q.default == "yes"

    def test_question_validation_empty_id(self):
        """Test that empty ID raises error."""
        with pytest.raises(ValueError, match="Question ID cannot be empty"):
            Question(
                id="",
                category="scope",
                text="Question?",
                options=["yes", "no"],
                default="yes",
                rationale="Test"
            )

    def test_question_validation_empty_text(self):
        """Test that empty text raises error."""
        with pytest.raises(ValueError, match="Question text cannot be empty"):
            Question(
                id="q1",
                category="scope",
                text="",
                options=["yes", "no"],
                default="yes",
                rationale="Test"
            )

    def test_question_validation_empty_options(self):
        """Test that empty options raises error."""
        with pytest.raises(ValueError, match="must have at least one option"):
            Question(
                id="q1",
                category="scope",
                text="Question?",
                options=[],
                default="yes",
                rationale="Test"
            )

    def test_question_validation_invalid_default(self):
        """Test that invalid default raises error."""
        with pytest.raises(ValueError, match="must be in options"):
            Question(
                id="q1",
                category="scope",
                text="Question?",
                options=["yes", "no"],
                default="maybe",
                rationale="Test"
            )


class TestDecision:
    """Tests for Decision dataclass."""

    def test_valid_decision(self):
        """Test creating a valid decision."""
        d = Decision(
            category="scope",
            question="Include tests?",
            answer="yes",
            is_default=False,
            confidence=1.0,
            rationale="User chose explicitly"
        )
        assert d.answer == "yes"
        assert d.confidence == 1.0
        assert not d.is_default

    def test_decision_validation_invalid_confidence(self):
        """Test that invalid confidence raises error."""
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            Decision(
                category="scope",
                question="Include tests?",
                answer="yes",
                is_default=False,
                confidence=1.5,
                rationale="Test"
            )


class TestClarificationContext:
    """Tests for ClarificationContext dataclass."""

    def test_empty_context(self):
        """Test creating an empty context."""
        ctx = ClarificationContext()
        assert ctx.total_questions == 0
        assert ctx.answered_count == 0
        assert ctx.skipped_count == 0
        assert not ctx.is_complete
        assert not ctx.has_explicit_decisions

    def test_add_explicit_decision(self):
        """Test adding an explicit decision."""
        ctx = ClarificationContext(total_questions=2)
        decision = Decision(
            category="scope",
            question="Include tests?",
            answer="yes",
            is_default=False,
            confidence=1.0,
            rationale="User chose"
        )
        ctx.add_decision(decision)

        assert ctx.answered_count == 1
        assert len(ctx.explicit_decisions) == 1
        assert len(ctx.assumed_defaults) == 0
        assert ctx.has_explicit_decisions

    def test_add_default_decision(self):
        """Test adding a default decision."""
        ctx = ClarificationContext(total_questions=2)
        decision = Decision(
            category="scope",
            question="Include tests?",
            answer="yes",
            is_default=True,
            confidence=0.7,
            rationale="Default choice"
        )
        ctx.add_decision(decision)

        assert ctx.answered_count == 1
        assert len(ctx.explicit_decisions) == 0
        assert len(ctx.assumed_defaults) == 1
        assert not ctx.has_explicit_decisions

    def test_add_skipped(self):
        """Test adding a skipped question."""
        ctx = ClarificationContext(total_questions=2)
        ctx.add_skipped("q1")

        assert ctx.skipped_count == 1
        assert "q1" in ctx.not_applicable

    def test_is_complete(self):
        """Test completion check."""
        ctx = ClarificationContext(total_questions=2)
        assert not ctx.is_complete

        decision = Decision(
            category="scope",
            question="Include tests?",
            answer="yes",
            is_default=False,
            confidence=1.0,
            rationale="User chose"
        )
        ctx.add_decision(decision)
        assert not ctx.is_complete

        ctx.add_skipped("q2")
        assert ctx.is_complete


class TestShouldClarify:
    """Tests for should_clarify function."""

    def test_no_questions_flag(self):
        """Test that no_questions flag skips clarification."""
        mode = should_clarify("review", complexity=8, flags={"no_questions": True})
        assert mode == ClarificationMode.SKIP

    def test_micro_flag(self):
        """Test that micro flag skips clarification."""
        mode = should_clarify("planning", complexity=6, flags={"micro": True})
        assert mode == ClarificationMode.SKIP

    def test_defaults_flag(self):
        """Test that defaults flag uses defaults."""
        mode = should_clarify("implement_prefs", complexity=5, flags={"defaults": True})
        assert mode == ClarificationMode.USE_DEFAULTS

    def test_review_context_low_complexity(self):
        """Test review context with low complexity."""
        mode = should_clarify("review", complexity=1, flags={})
        assert mode == ClarificationMode.SKIP

    def test_review_context_medium_complexity(self):
        """Test review context with medium complexity."""
        mode = should_clarify("review", complexity=4, flags={})
        assert mode == ClarificationMode.QUICK

    def test_review_context_high_complexity(self):
        """Test review context with high complexity."""
        mode = should_clarify("review", complexity=8, flags={})
        assert mode == ClarificationMode.FULL

    def test_implement_prefs_context_low_complexity(self):
        """Test implement_prefs context with low complexity."""
        mode = should_clarify("implement_prefs", complexity=2, flags={})
        assert mode == ClarificationMode.SKIP

    def test_implement_prefs_context_medium_complexity(self):
        """Test implement_prefs context with medium complexity."""
        mode = should_clarify("implement_prefs", complexity=5, flags={})
        assert mode == ClarificationMode.QUICK

    def test_implement_prefs_context_high_complexity(self):
        """Test implement_prefs context with high complexity."""
        mode = should_clarify("implement_prefs", complexity=8, flags={})
        assert mode == ClarificationMode.FULL

    def test_planning_context_low_complexity(self):
        """Test planning context with low complexity."""
        mode = should_clarify("planning", complexity=1, flags={})
        assert mode == ClarificationMode.SKIP

    def test_planning_context_medium_complexity(self):
        """Test planning context with medium complexity."""
        mode = should_clarify("planning", complexity=4, flags={})
        assert mode == ClarificationMode.QUICK

    def test_planning_context_high_complexity(self):
        """Test planning context with high complexity."""
        mode = should_clarify("planning", complexity=6, flags={})
        assert mode == ClarificationMode.FULL


class TestProcessResponses:
    """Tests for process_responses function."""

    def test_all_questions_answered_with_defaults(self):
        """Test processing responses where all use defaults."""
        questions = [
            Question("q1", "scope", "Include tests?", ["yes", "no"], "yes", "Default"),
            Question("q2", "tech", "Use async?", ["yes", "no"], "no", "Simple case")
        ]
        user_input = {"q1": "yes", "q2": "no"}

        ctx = process_responses(questions, user_input, ClarificationMode.FULL)

        assert ctx.total_questions == 2
        assert ctx.answered_count == 2
        assert ctx.skipped_count == 0
        assert len(ctx.assumed_defaults) == 2
        assert len(ctx.explicit_decisions) == 0

    def test_all_questions_answered_explicitly(self):
        """Test processing responses with explicit choices."""
        questions = [
            Question("q1", "scope", "Include tests?", ["yes", "no"], "yes", "Default"),
            Question("q2", "tech", "Use async?", ["yes", "no"], "no", "Simple case")
        ]
        user_input = {"q1": "no", "q2": "yes"}

        ctx = process_responses(questions, user_input, ClarificationMode.FULL)

        assert ctx.total_questions == 2
        assert ctx.answered_count == 2
        assert len(ctx.explicit_decisions) == 2
        assert len(ctx.assumed_defaults) == 0
        assert ctx.explicit_decisions[0].answer == "no"
        assert ctx.explicit_decisions[1].answer == "yes"

    def test_mixed_responses(self):
        """Test processing mixed explicit and default responses."""
        questions = [
            Question("q1", "scope", "Include tests?", ["yes", "no"], "yes", "Default"),
            Question("q2", "tech", "Use async?", ["yes", "no"], "no", "Simple case")
        ]
        user_input = {"q1": "yes", "q2": "yes"}

        ctx = process_responses(questions, user_input, ClarificationMode.FULL)

        assert ctx.answered_count == 2
        assert len(ctx.assumed_defaults) == 1
        assert len(ctx.explicit_decisions) == 1
        assert ctx.assumed_defaults[0].answer == "yes"
        assert ctx.explicit_decisions[0].answer == "yes"

    def test_skipped_questions(self):
        """Test processing with skipped questions."""
        questions = [
            Question("q1", "scope", "Include tests?", ["yes", "no"], "yes", "Default"),
            Question("q2", "tech", "Use async?", ["yes", "no"], "no", "Simple case")
        ]
        user_input = {"q1": "yes"}

        ctx = process_responses(questions, user_input, ClarificationMode.QUICK)

        assert ctx.total_questions == 2
        assert ctx.answered_count == 1
        assert ctx.skipped_count == 1
        assert "q2" in ctx.not_applicable

    def test_skip_mode(self):
        """Test processing with SKIP mode."""
        questions = [
            Question("q1", "scope", "Include tests?", ["yes", "no"], "yes", "Default")
        ]
        user_input = {}

        ctx = process_responses(questions, user_input, ClarificationMode.SKIP)

        assert ctx.user_override == "skip"
        assert ctx.answered_count == 0
        assert ctx.skipped_count == 1

    def test_use_defaults_mode(self):
        """Test processing with USE_DEFAULTS mode."""
        questions = [
            Question("q1", "scope", "Include tests?", ["yes", "no"], "yes", "Default")
        ]
        user_input = {"q1": "yes"}

        ctx = process_responses(questions, user_input, ClarificationMode.USE_DEFAULTS)

        assert ctx.user_override == "defaults"


class TestFormatForPrompt:
    """Tests for format_for_prompt function."""

    def test_empty_context(self):
        """Test formatting an empty context."""
        ctx = ClarificationContext()
        output = format_for_prompt(ctx)

        assert "No clarification questions were asked" in output

    def test_explicit_decisions_only(self):
        """Test formatting with only explicit decisions."""
        ctx = ClarificationContext(
            explicit_decisions=[
                Decision("scope", "Include tests?", "yes", False, 1.0, "User chose")
            ],
            total_questions=1,
            answered_count=1
        )
        output = format_for_prompt(ctx)

        assert "# Clarification Context" in output
        assert "EXPLICIT DECISIONS" in output
        assert "Include tests?" in output
        assert "yes" in output
        assert "100%" in output

    def test_assumed_defaults_only(self):
        """Test formatting with only assumed defaults."""
        ctx = ClarificationContext(
            assumed_defaults=[
                Decision("tech", "Use async?", "no", True, 0.7, "Simple case")
            ],
            total_questions=1,
            answered_count=1
        )
        output = format_for_prompt(ctx)

        assert "ASSUMED DEFAULTS" in output
        assert "Use async?" in output
        assert "no" in output
        assert "70%" in output

    def test_mixed_decisions(self):
        """Test formatting with both explicit and assumed decisions."""
        ctx = ClarificationContext(
            explicit_decisions=[
                Decision("scope", "Include tests?", "yes", False, 1.0, "User chose")
            ],
            assumed_defaults=[
                Decision("tech", "Use async?", "no", True, 0.7, "Simple case")
            ],
            total_questions=2,
            answered_count=2
        )
        output = format_for_prompt(ctx)

        assert "EXPLICIT DECISIONS" in output
        assert "ASSUMED DEFAULTS" in output
        assert "Total Questions: 2" in output
        assert "Answered: 2" in output

    def test_with_skipped_questions(self):
        """Test formatting with skipped questions."""
        ctx = ClarificationContext(
            explicit_decisions=[
                Decision("scope", "Include tests?", "yes", False, 1.0, "User chose")
            ],
            not_applicable=["q2", "q3"],
            total_questions=3,
            answered_count=1,
            skipped_count=2
        )
        output = format_for_prompt(ctx)

        assert "NOT APPLICABLE" in output
        assert "Skipped 2 question(s)" in output

    def test_with_user_override(self):
        """Test formatting with user override."""
        ctx = ClarificationContext(
            user_override="skip",
            total_questions=5,
            skipped_count=5
        )
        ctx.not_applicable = ["q1", "q2", "q3", "q4", "q5"]
        output = format_for_prompt(ctx)

        assert "User Override: skip" in output


class TestPersistToFrontmatter:
    """Tests for persist_to_frontmatter function."""

    def test_persist_to_frontmatter_stub(self):
        """Test that persist_to_frontmatter is a stub (does nothing)."""
        ctx = ClarificationContext()
        # Should not raise any errors
        persist_to_frontmatter(ctx, "TASK-001")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
