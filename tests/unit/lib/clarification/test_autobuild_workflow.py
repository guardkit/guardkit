"""Unit tests for AutoBuild workflow question templates.

Tests for TASK-GR4-007: Add AutoBuild workflow customization questions.
Based on TASK-REV-7549 findings about role reversal and threshold drift.
"""

import sys
from pathlib import Path
import pytest

# Add the installer/core/commands directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "installer" / "core" / "commands"))

from lib.clarification.core import Question


class TestAutoBuildQuestionTemplates:
    """Tests for AutoBuild workflow question templates."""

    def test_role_customization_questions_exist(self):
        """Should have role customization questions for Player/Coach boundaries."""
        from lib.clarification.templates.autobuild_workflow import ROLE_CUSTOMIZATION_QUESTIONS

        assert len(ROLE_CUSTOMIZATION_QUESTIONS) >= 3
        assert all(isinstance(q, Question) for q in ROLE_CUSTOMIZATION_QUESTIONS)

        # Check category is consistent
        for q in ROLE_CUSTOMIZATION_QUESTIONS:
            assert q.category == "role_customization"

    def test_player_ask_before_question(self):
        """Should have question about what Player should ask before implementing."""
        from lib.clarification.templates.autobuild_workflow import ROLE_CUSTOMIZATION_QUESTIONS

        player_ask_q = next(
            (q for q in ROLE_CUSTOMIZATION_QUESTIONS if "player_ask_before" in q.id),
            None
        )
        assert player_ask_q is not None
        assert "ask" in player_ask_q.text.lower() or "confirm" in player_ask_q.text.lower()
        assert len(player_ask_q.options) >= 3

    def test_coach_escalate_question(self):
        """Should have question about what Coach should escalate to humans."""
        from lib.clarification.templates.autobuild_workflow import ROLE_CUSTOMIZATION_QUESTIONS

        escalate_q = next(
            (q for q in ROLE_CUSTOMIZATION_QUESTIONS if "coach_escalate" in q.id),
            None
        )
        assert escalate_q is not None
        assert "escalate" in escalate_q.text.lower() or "human" in escalate_q.text.lower()
        assert len(escalate_q.options) >= 3

    def test_autonomous_restriction_question(self):
        """Should have question about areas where AI should never make autonomous changes."""
        from lib.clarification.templates.autobuild_workflow import ROLE_CUSTOMIZATION_QUESTIONS

        restrict_q = next(
            (q for q in ROLE_CUSTOMIZATION_QUESTIONS if "autonomous" in q.id or "restrict" in q.id),
            None
        )
        assert restrict_q is not None
        assert "never" in restrict_q.text.lower() or "restrict" in restrict_q.text.lower() or "autonomous" in restrict_q.text.lower()

    def test_quality_gate_questions_exist(self):
        """Should have quality gate threshold questions."""
        from lib.clarification.templates.autobuild_workflow import QUALITY_GATE_QUESTIONS

        assert len(QUALITY_GATE_QUESTIONS) >= 2
        assert all(isinstance(q, Question) for q in QUALITY_GATE_QUESTIONS)

        for q in QUALITY_GATE_QUESTIONS:
            assert q.category == "quality_gates"

    def test_coverage_threshold_question(self):
        """Should have question about acceptable test coverage threshold."""
        from lib.clarification.templates.autobuild_workflow import QUALITY_GATE_QUESTIONS

        coverage_q = next(
            (q for q in QUALITY_GATE_QUESTIONS if "coverage" in q.id),
            None
        )
        assert coverage_q is not None
        assert "coverage" in coverage_q.text.lower() or "test" in coverage_q.text.lower()
        # Should have percentage options
        assert any("80" in opt or "70" in opt or "90" in opt for opt in coverage_q.options)

    def test_arch_review_threshold_question(self):
        """Should have question about architectural review score threshold."""
        from lib.clarification.templates.autobuild_workflow import QUALITY_GATE_QUESTIONS

        arch_q = next(
            (q for q in QUALITY_GATE_QUESTIONS if "arch" in q.id),
            None
        )
        assert arch_q is not None
        assert "arch" in arch_q.text.lower() or "review" in arch_q.text.lower()

    def test_workflow_preference_questions_exist(self):
        """Should have workflow preference questions."""
        from lib.clarification.templates.autobuild_workflow import WORKFLOW_PREFERENCE_QUESTIONS

        assert len(WORKFLOW_PREFERENCE_QUESTIONS) >= 2
        assert all(isinstance(q, Question) for q in WORKFLOW_PREFERENCE_QUESTIONS)

        for q in WORKFLOW_PREFERENCE_QUESTIONS:
            assert q.category == "workflow_prefs"

    def test_implementation_mode_question(self):
        """Should have question about preferred implementation mode."""
        from lib.clarification.templates.autobuild_workflow import WORKFLOW_PREFERENCE_QUESTIONS

        mode_q = next(
            (q for q in WORKFLOW_PREFERENCE_QUESTIONS if "mode" in q.id),
            None
        )
        assert mode_q is not None
        # Should offer TDD, standard, or auto-detect
        assert any("tdd" in opt.lower() or "standard" in opt.lower() for opt in mode_q.options)

    def test_max_auto_turns_question(self):
        """Should have question about maximum automatic turns."""
        from lib.clarification.templates.autobuild_workflow import WORKFLOW_PREFERENCE_QUESTIONS

        turns_q = next(
            (q for q in WORKFLOW_PREFERENCE_QUESTIONS if "turn" in q.id or "iteration" in q.id),
            None
        )
        assert turns_q is not None
        # Should offer numeric options
        assert any(opt.replace("[", "").replace("]", "").strip().split()[0].isdigit() or
                   any(c.isdigit() for c in opt)
                   for opt in turns_q.options)

    def test_all_questions_have_valid_defaults(self):
        """All questions should have defaults in their options."""
        from lib.clarification.templates.autobuild_workflow import (
            ROLE_CUSTOMIZATION_QUESTIONS,
            QUALITY_GATE_QUESTIONS,
            WORKFLOW_PREFERENCE_QUESTIONS,
        )

        all_questions = (
            ROLE_CUSTOMIZATION_QUESTIONS +
            QUALITY_GATE_QUESTIONS +
            WORKFLOW_PREFERENCE_QUESTIONS
        )

        for q in all_questions:
            assert q.default in q.options, f"Question {q.id} default not in options"

    def test_all_questions_have_rationale(self):
        """All questions should have non-empty rationale."""
        from lib.clarification.templates.autobuild_workflow import (
            ROLE_CUSTOMIZATION_QUESTIONS,
            QUALITY_GATE_QUESTIONS,
            WORKFLOW_PREFERENCE_QUESTIONS,
        )

        all_questions = (
            ROLE_CUSTOMIZATION_QUESTIONS +
            QUALITY_GATE_QUESTIONS +
            WORKFLOW_PREFERENCE_QUESTIONS
        )

        for q in all_questions:
            assert q.rationale, f"Question {q.id} missing rationale"
            assert len(q.rationale) > 10, f"Question {q.id} rationale too short"


class TestAutoBuildGenerator:
    """Tests for AutoBuild question generator."""

    def test_generator_exists(self):
        """Should have autobuild_generator module."""
        from lib.clarification.generators.autobuild_generator import generate_autobuild_questions
        assert callable(generate_autobuild_questions)

    def test_detects_autobuild_context(self):
        """Should detect when task is AutoBuild-related."""
        from lib.clarification.generators.autobuild_generator import detect_autobuild_context

        # Should detect autobuild keywords
        result = detect_autobuild_context("Add feature using feature-build workflow")
        assert result is not None
        assert result.detected

        # Should detect player/coach keywords
        result = detect_autobuild_context("Configure Player-Coach validation rules")
        assert result is not None
        assert result.detected

    def test_no_detection_for_non_autobuild(self):
        """Should not detect AutoBuild for regular tasks."""
        from lib.clarification.generators.autobuild_generator import detect_autobuild_context

        result = detect_autobuild_context("Fix typo in README")
        assert result is None

    def test_generates_questions_for_autobuild_task(self):
        """Should generate questions for AutoBuild tasks."""
        from lib.clarification.generators.autobuild_generator import generate_autobuild_questions
        from lib.clarification.core import ClarificationMode

        questions = generate_autobuild_questions(
            task_description="Configure feature-build workflow for new feature",
            mode=ClarificationMode.FULL
        )

        assert len(questions) > 0
        # Should include role and quality gate categories
        categories = {q.category for q in questions}
        assert "role_customization" in categories or "quality_gates" in categories

    def test_returns_empty_for_skip_mode(self):
        """Should return empty for SKIP mode."""
        from lib.clarification.generators.autobuild_generator import generate_autobuild_questions
        from lib.clarification.core import ClarificationMode

        questions = generate_autobuild_questions(
            task_description="Configure feature-build",
            mode=ClarificationMode.SKIP
        )

        assert len(questions) == 0

    def test_limits_questions_in_quick_mode(self):
        """Should limit to 3 questions in QUICK mode."""
        from lib.clarification.generators.autobuild_generator import generate_autobuild_questions
        from lib.clarification.core import ClarificationMode

        questions = generate_autobuild_questions(
            task_description="Configure feature-build workflow with Player-Coach",
            mode=ClarificationMode.QUICK
        )

        assert len(questions) <= 3

    def test_focus_flag_role_customization(self):
        """Should filter to role questions with --focus role-customization."""
        from lib.clarification.generators.autobuild_generator import generate_autobuild_questions
        from lib.clarification.core import ClarificationMode

        questions = generate_autobuild_questions(
            task_description="Configure feature-build",
            mode=ClarificationMode.FULL,
            focus="role-customization"
        )

        # All returned questions should be role_customization category
        for q in questions:
            assert q.category == "role_customization"

    def test_focus_flag_quality_gates(self):
        """Should filter to quality gate questions with --focus quality-gates."""
        from lib.clarification.generators.autobuild_generator import generate_autobuild_questions
        from lib.clarification.core import ClarificationMode

        questions = generate_autobuild_questions(
            task_description="Configure feature-build",
            mode=ClarificationMode.FULL,
            focus="quality-gates"
        )

        # All returned questions should be quality_gates category
        for q in questions:
            assert q.category == "quality_gates"


class TestGroupIdMapping:
    """Tests for group_id mapping in AutoBuild questions."""

    def test_role_questions_have_group_id(self):
        """Role questions should map to role_constraints group."""
        from lib.clarification.templates.autobuild_workflow import (
            ROLE_CUSTOMIZATION_QUESTIONS,
            get_group_id_for_category,
        )

        group_id = get_group_id_for_category("role_customization")
        assert group_id == "role_constraints"

    def test_quality_gate_questions_have_group_id(self):
        """Quality gate questions should map to quality_gate_configs group."""
        from lib.clarification.templates.autobuild_workflow import get_group_id_for_category

        group_id = get_group_id_for_category("quality_gates")
        assert group_id == "quality_gate_configs"

    def test_workflow_questions_have_group_id(self):
        """Workflow preference questions should map to workflow_prefs group."""
        from lib.clarification.templates.autobuild_workflow import get_group_id_for_category

        group_id = get_group_id_for_category("workflow_prefs")
        assert group_id in ("workflow_prefs", "implementation_modes")


class TestTemplateExports:
    """Tests for module exports."""

    def test_templates_init_exports_autobuild(self):
        """Templates __init__.py should export AutoBuild questions."""
        from lib.clarification.templates import (
            ROLE_CUSTOMIZATION_QUESTIONS,
            QUALITY_GATE_QUESTIONS,
            WORKFLOW_PREFERENCE_QUESTIONS,
        )

        assert len(ROLE_CUSTOMIZATION_QUESTIONS) > 0
        assert len(QUALITY_GATE_QUESTIONS) > 0
        assert len(WORKFLOW_PREFERENCE_QUESTIONS) > 0

    def test_generators_init_exports_autobuild(self):
        """Generators __init__.py should export generate_autobuild_questions."""
        from lib.clarification.generators import generate_autobuild_questions

        assert callable(generate_autobuild_questions)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
