"""Integration tests for clarification Python module.

Tests verify that the clarification module is importable and core functionality
works correctly without AI/model calls.

These are smoke tests - they verify module structure and data operations,
not the actual AI-driven clarification behavior.
"""

import sys
import pytest
from pathlib import Path
from datetime import datetime

# Add lib directory to path for imports
lib_path = Path(__file__).parent.parent.parent.parent.parent / "installer" / "core" / "commands" / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))


class TestCoreModuleImportable:
    """Test that clarification core module is importable."""

    def test_core_module_importable(self):
        """Verify clarification.core module can be imported."""
        from clarification import core
        assert core is not None

    def test_core_classes_importable(self):
        """Verify core classes can be imported."""
        from clarification.core import (
            ClarificationMode,
            Question,
            Decision,
            ClarificationContext,
        )

        assert ClarificationMode is not None
        assert Question is not None
        assert Decision is not None
        assert ClarificationContext is not None

    def test_core_functions_importable(self):
        """Verify core functions can be imported."""
        from clarification.core import (
            should_clarify,
            process_responses,
            format_for_prompt,
            parse_frontmatter,
            serialize_frontmatter,
        )

        assert callable(should_clarify)
        assert callable(process_responses)
        assert callable(format_for_prompt)
        assert callable(parse_frontmatter)
        assert callable(serialize_frontmatter)


class TestQuestionDataclass:
    """Test Question dataclass validation."""

    def test_question_creation_valid(self):
        """Verify Question can be created with valid data."""
        from clarification.core import Question

        question = Question(
            id="scope_01",
            category="scope",
            text="What scope should this feature have?",
            options=["minimal", "standard", "complete"],
            default="standard",
            rationale="Standard scope is suitable for most features",
        )

        assert question.id == "scope_01"
        assert question.category == "scope"
        assert question.text == "What scope should this feature have?"
        assert question.options == ["minimal", "standard", "complete"]
        assert question.default == "standard"
        assert question.rationale == "Standard scope is suitable for most features"

    def test_question_requires_id(self):
        """Verify Question requires non-empty id."""
        from clarification.core import Question

        with pytest.raises(ValueError, match="Question ID cannot be empty"):
            Question(
                id="",
                category="scope",
                text="Test question",
                options=["yes", "no"],
                default="yes",
                rationale="Test",
            )

    def test_question_requires_text(self):
        """Verify Question requires non-empty text."""
        from clarification.core import Question

        with pytest.raises(ValueError, match="Question text cannot be empty"):
            Question(
                id="q1",
                category="scope",
                text="",
                options=["yes", "no"],
                default="yes",
                rationale="Test",
            )

    def test_question_requires_options(self):
        """Verify Question requires at least one option."""
        from clarification.core import Question

        with pytest.raises(ValueError, match="Question must have at least one option"):
            Question(
                id="q1",
                category="scope",
                text="Test question",
                options=[],
                default="yes",
                rationale="Test",
            )

    def test_question_default_must_be_in_options(self):
        """Verify Question default must be in options list."""
        from clarification.core import Question

        with pytest.raises(ValueError, match="Default .* must be in options"):
            Question(
                id="q1",
                category="scope",
                text="Test question",
                options=["yes", "no"],
                default="maybe",
                rationale="Test",
            )


class TestDecisionDataclass:
    """Test Decision dataclass validation."""

    def test_decision_creation_valid(self):
        """Verify Decision can be created with valid data."""
        from clarification.core import Decision

        decision = Decision(
            question_id="scope_01",
            category="scope",
            question_text="What scope?",
            answer="complete",
            answer_display="Complete (full feature)",
            default_used=False,
            rationale="User explicitly chose: complete",
        )

        assert decision.question_id == "scope_01"
        assert decision.category == "scope"
        assert decision.answer == "complete"
        assert decision.answer_display == "Complete (full feature)"
        assert decision.default_used is False
        assert decision.confidence == 1.0  # Default value

    def test_decision_confidence_range(self):
        """Verify Decision confidence must be between 0 and 1."""
        from clarification.core import Decision

        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            Decision(
                question_id="scope_01",
                category="scope",
                question_text="What scope?",
                answer="complete",
                answer_display="Complete",
                default_used=False,
                rationale="Test",
                confidence=1.5,
            )

    def test_decision_is_default_property(self):
        """Verify Decision has is_default backward compatibility property."""
        from clarification.core import Decision

        decision = Decision(
            question_id="scope_01",
            category="scope",
            question_text="What scope?",
            answer="standard",
            answer_display="Standard",
            default_used=True,
            rationale="Default used",
        )

        assert decision.is_default is True
        assert decision.default_used is True

    def test_decision_question_property(self):
        """Verify Decision has question backward compatibility property."""
        from clarification.core import Decision

        decision = Decision(
            question_id="scope_01",
            category="scope",
            question_text="What scope should we use?",
            answer="standard",
            answer_display="Standard",
            default_used=True,
            rationale="Test",
        )

        assert decision.question == "What scope should we use?"


class TestClarificationContext:
    """Test ClarificationContext dataclass operations."""

    def test_context_creation_empty(self):
        """Verify empty ClarificationContext can be created."""
        from clarification.core import ClarificationContext

        ctx = ClarificationContext()

        assert ctx.context_type == "implementation_planning"
        assert ctx.explicit_decisions == []
        assert ctx.assumed_defaults == []
        assert ctx.not_applicable == []
        assert ctx.total_questions == 0
        assert ctx.answered_count == 0
        assert ctx.skipped_count == 0
        assert isinstance(ctx.timestamp, datetime)

    def test_context_add_decision_explicit(self):
        """Verify add_decision adds explicit decision correctly."""
        from clarification.core import ClarificationContext, Decision

        ctx = ClarificationContext()
        decision = Decision(
            question_id="scope_01",
            category="scope",
            question_text="What scope?",
            answer="complete",
            answer_display="Complete",
            default_used=False,
            rationale="User choice",
        )

        ctx.add_decision(decision)

        assert len(ctx.explicit_decisions) == 1
        assert len(ctx.assumed_defaults) == 0
        assert ctx.answered_count == 1

    def test_context_add_decision_default(self):
        """Verify add_decision adds default decision correctly."""
        from clarification.core import ClarificationContext, Decision

        ctx = ClarificationContext()
        decision = Decision(
            question_id="scope_01",
            category="scope",
            question_text="What scope?",
            answer="standard",
            answer_display="Standard",
            default_used=True,
            rationale="Default used",
        )

        ctx.add_decision(decision)

        assert len(ctx.explicit_decisions) == 0
        assert len(ctx.assumed_defaults) == 1
        assert ctx.answered_count == 1

    def test_context_decisions_property(self):
        """Verify decisions property returns all decisions."""
        from clarification.core import ClarificationContext, Decision

        ctx = ClarificationContext()

        # Add explicit decision
        ctx.add_decision(Decision(
            question_id="scope_01",
            category="scope",
            question_text="Scope?",
            answer="complete",
            answer_display="Complete",
            default_used=False,
            rationale="User choice",
        ))

        # Add default decision
        ctx.add_decision(Decision(
            question_id="tech_01",
            category="technology",
            question_text="Tech?",
            answer="standard",
            answer_display="Standard",
            default_used=True,
            rationale="Default",
        ))

        assert len(ctx.decisions) == 2
        assert len(ctx.explicit_decisions) == 1
        assert len(ctx.assumed_defaults) == 1

    def test_context_add_skipped(self):
        """Verify add_skipped tracks skipped questions."""
        from clarification.core import ClarificationContext

        ctx = ClarificationContext(total_questions=3)
        ctx.add_skipped("scope_01")

        assert "scope_01" in ctx.not_applicable
        assert ctx.skipped_count == 1

    def test_context_is_complete(self):
        """Verify is_complete property works correctly."""
        from clarification.core import ClarificationContext, Decision

        ctx = ClarificationContext(total_questions=2)

        # Not complete yet
        assert ctx.is_complete is False

        # Add one answer
        ctx.add_decision(Decision(
            question_id="q1",
            category="scope",
            question_text="Q1?",
            answer="yes",
            answer_display="Yes",
            default_used=False,
            rationale="Test",
        ))
        assert ctx.is_complete is False

        # Add second answer
        ctx.add_decision(Decision(
            question_id="q2",
            category="scope",
            question_text="Q2?",
            answer="no",
            answer_display="No",
            default_used=True,
            rationale="Test",
        ))
        assert ctx.is_complete is True

    def test_context_has_explicit_decisions(self):
        """Verify has_explicit_decisions property works."""
        from clarification.core import ClarificationContext, Decision

        ctx = ClarificationContext()
        assert ctx.has_explicit_decisions is False

        ctx.add_decision(Decision(
            question_id="q1",
            category="scope",
            question_text="Q1?",
            answer="yes",
            answer_display="Yes",
            default_used=False,
            rationale="User choice",
        ))
        assert ctx.has_explicit_decisions is True


class TestShouldClarify:
    """Test should_clarify function mode determination."""

    def test_skip_mode_for_no_questions_flag(self):
        """Verify --no-questions flag results in SKIP mode."""
        from clarification.core import should_clarify, ClarificationMode

        mode = should_clarify("planning", complexity=8, flags={"no_questions": True})
        assert mode == ClarificationMode.SKIP

    def test_skip_mode_for_micro_flag(self):
        """Verify --micro flag results in SKIP mode."""
        from clarification.core import should_clarify, ClarificationMode

        mode = should_clarify("planning", complexity=8, flags={"micro": True})
        assert mode == ClarificationMode.SKIP

    def test_defaults_mode_for_defaults_flag(self):
        """Verify --defaults flag results in USE_DEFAULTS mode."""
        from clarification.core import should_clarify, ClarificationMode

        mode = should_clarify("planning", complexity=8, flags={"defaults": True})
        assert mode == ClarificationMode.USE_DEFAULTS

    def test_full_mode_for_with_questions_flag(self):
        """Verify --with-questions flag forces FULL mode."""
        from clarification.core import should_clarify, ClarificationMode

        mode = should_clarify("planning", complexity=2, flags={"with_questions": True})
        assert mode == ClarificationMode.FULL

    def test_skip_mode_for_low_complexity(self):
        """Verify low complexity results in SKIP mode."""
        from clarification.core import should_clarify, ClarificationMode

        mode = should_clarify("planning", complexity=2, flags={})
        assert mode == ClarificationMode.SKIP

    def test_quick_mode_for_medium_complexity(self):
        """Verify medium complexity results in QUICK mode."""
        from clarification.core import should_clarify, ClarificationMode

        mode = should_clarify("planning", complexity=3, flags={})
        assert mode == ClarificationMode.QUICK

    def test_full_mode_for_high_complexity(self):
        """Verify high complexity results in FULL mode."""
        from clarification.core import should_clarify, ClarificationMode

        mode = should_clarify("planning", complexity=5, flags={})
        assert mode == ClarificationMode.FULL


class TestProcessResponses:
    """Test process_responses function."""

    def test_process_responses_creates_context(self):
        """Verify process_responses creates ClarificationContext."""
        from clarification.core import (
            process_responses,
            ClarificationContext,
            ClarificationMode,
            Question,
        )

        questions = [
            Question(
                id="scope_01",
                category="scope",
                text="What scope?",
                options=["minimal", "standard", "complete"],
                default="standard",
                rationale="Default scope",
            ),
        ]

        user_input = {"scope_01": "complete"}

        context = process_responses(questions, user_input, ClarificationMode.FULL)

        assert isinstance(context, ClarificationContext)
        assert context.answered_count == 1

    def test_process_responses_tracks_explicit_answers(self):
        """Verify explicit answers are tracked correctly."""
        from clarification.core import (
            process_responses,
            ClarificationMode,
            Question,
        )

        questions = [
            Question(
                id="scope_01",
                category="scope",
                text="What scope?",
                options=["minimal", "standard", "complete"],
                default="standard",
                rationale="Default scope",
            ),
        ]

        # User chose non-default
        user_input = {"scope_01": "complete"}

        context = process_responses(questions, user_input, ClarificationMode.FULL)

        assert len(context.explicit_decisions) == 1
        assert context.explicit_decisions[0].answer == "complete"
        assert context.explicit_decisions[0].default_used is False

    def test_process_responses_tracks_default_answers(self):
        """Verify default answers are tracked correctly."""
        from clarification.core import (
            process_responses,
            ClarificationMode,
            Question,
        )

        questions = [
            Question(
                id="scope_01",
                category="scope",
                text="What scope?",
                options=["minimal", "standard", "complete"],
                default="standard",
                rationale="Default scope",
            ),
        ]

        # User chose default
        user_input = {"scope_01": "standard"}

        context = process_responses(questions, user_input, ClarificationMode.FULL)

        assert len(context.assumed_defaults) == 1
        assert context.assumed_defaults[0].answer == "standard"
        assert context.assumed_defaults[0].default_used is True

    def test_process_responses_tracks_skipped(self):
        """Verify skipped questions are tracked."""
        from clarification.core import (
            process_responses,
            ClarificationMode,
            Question,
        )

        questions = [
            Question(
                id="scope_01",
                category="scope",
                text="What scope?",
                options=["minimal", "standard", "complete"],
                default="standard",
                rationale="Default scope",
            ),
        ]

        # No answer provided
        user_input = {}

        context = process_responses(questions, user_input, ClarificationMode.FULL)

        assert context.skipped_count == 1
        assert "scope_01" in context.not_applicable


class TestFormatForPrompt:
    """Test format_for_prompt function."""

    def test_format_for_prompt_with_decisions(self):
        """Verify format_for_prompt produces readable output."""
        from clarification.core import (
            format_for_prompt,
            ClarificationContext,
            Decision,
        )

        ctx = ClarificationContext(total_questions=2, answered_count=2)
        ctx.explicit_decisions = [
            Decision(
                question_id="scope_01",
                category="scope",
                question_text="What scope?",
                answer="complete",
                answer_display="Complete",
                default_used=False,
                rationale="User explicitly chose: complete",
            ),
        ]
        ctx.assumed_defaults = [
            Decision(
                question_id="tech_01",
                category="technology",
                question_text="Use async?",
                answer="no",
                answer_display="No",
                default_used=True,
                rationale="Simple case",
            ),
        ]

        output = format_for_prompt(ctx)

        assert "# Clarification Context" in output
        assert "EXPLICIT DECISIONS" in output
        assert "ASSUMED DEFAULTS" in output
        assert "scope" in output.lower()
        assert "complete" in output.lower()

    def test_format_for_prompt_empty_context(self):
        """Verify format_for_prompt handles empty context."""
        from clarification.core import (
            format_for_prompt,
            ClarificationContext,
        )

        ctx = ClarificationContext()

        output = format_for_prompt(ctx)

        assert "complexity too low or skipped" in output.lower()


class TestFrontmatterParsing:
    """Test frontmatter parsing functions."""

    def test_parse_frontmatter_valid(self):
        """Verify parse_frontmatter handles valid input."""
        from clarification.core import parse_frontmatter

        content = """---
id: TASK-123
title: Test task
complexity: 5
---

# Task Body

Description here.
"""

        frontmatter, body = parse_frontmatter(content)

        assert frontmatter["id"] == "TASK-123"
        assert frontmatter["title"] == "Test task"
        assert frontmatter["complexity"] == 5
        assert "# Task Body" in body
        assert "Description here" in body

    def test_parse_frontmatter_no_frontmatter(self):
        """Verify parse_frontmatter handles content without frontmatter."""
        from clarification.core import parse_frontmatter

        content = "# Just a header\n\nSome content."

        frontmatter, body = parse_frontmatter(content)

        assert frontmatter == {}
        assert body == content

    def test_serialize_frontmatter(self):
        """Verify serialize_frontmatter produces valid YAML."""
        from clarification.core import serialize_frontmatter

        frontmatter = {
            "id": "TASK-123",
            "title": "Test task",
            "complexity": 5,
        }

        output = serialize_frontmatter(frontmatter)

        assert output.startswith("---\n")
        assert output.endswith("---\n")
        assert "id: TASK-123" in output
        assert "title: Test task" in output


class TestGeneratorsImportable:
    """Test that question generators are importable."""

    def test_planning_generator_importable(self):
        """Verify planning generator can be imported."""
        from clarification.generators.planning_generator import generate_planning_questions
        assert callable(generate_planning_questions)

    def test_review_generator_importable(self):
        """Verify review generator can be imported."""
        from clarification.generators.review_generator import generate_review_questions
        assert callable(generate_review_questions)

    def test_implement_generator_importable(self):
        """Verify implement generator can be imported."""
        from clarification.generators.implement_generator import generate_implement_questions
        assert callable(generate_implement_questions)


class TestDisplayModuleImportable:
    """Test that display module is importable."""

    def test_display_module_importable(self):
        """Verify display module can be imported."""
        from clarification.display import (
            collect_full_responses,
            collect_quick_responses,
            create_skip_context,
        )

        assert callable(collect_full_responses)
        assert callable(collect_quick_responses)
        assert callable(create_skip_context)
