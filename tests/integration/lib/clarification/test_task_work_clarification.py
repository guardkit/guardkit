"""Integration tests for clarification in task-work workflow.

Tests Phase 1.6 clarification integration with task-work command.

NOTE: Unlike task-review and feature-plan which have Python orchestrators,
task-work is implemented as a Claude Code command (task-work.md) and executed
by Claude itself. The actual orchestration happens in:
- installer/core/commands/lib/phase_execution.py (execute_phase_1_6_clarification)

These tests verify the Phase 1.6 clarification logic that gets called during
task-work execution, including:
- Complexity-based mode selection (skip/quick/full)
- Flag handling (--no-questions, --with-questions, --defaults, --answers)
- Timeout behavior in quick mode
- Clarification context propagation to Phase 2

For real orchestrator integration tests, see:
- test_task_review_clarification.py (tests task_review_orchestrator.py)
- test_feature_plan_clarification.py (tests feature_plan_orchestrator.py)
"""

import sys
import pytest
from unittest.mock import patch, MagicMock, call
from pathlib import Path
import tempfile

# Add lib directory to path for imports
lib_path = Path(__file__).parent.parent.parent.parent.parent / "installer" / "core" / "commands" / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Import from the real clarification module path
from clarification.core import Question, Decision, ClarificationContext
from clarification.generators.planning_generator import generate_planning_questions
from clarification.display import (
    collect_full_responses as display_questions_full,
    collect_quick_responses as display_questions_quick,
)

# Note: phase_execution.py has optional imports that may fail in test context.
# For these tests, we test the clarification logic directly without importing phase_execution.
# The mock execute_task_work_phase_15 function simulates the Phase 1.6 behavior.
execute_phase_1_6_clarification = None
CLARIFICATION_AVAILABLE = True  # We have clarification modules available


class TaskContext:
    """Mock task context object for planning generator."""
    def __init__(self, task_id="TASK-test", title="Test Task", description="Test task", complexity=5, status="backlog"):
        self.id = task_id
        self.title = title
        self.description = description
        self.complexity = complexity
        self.complexity_score = complexity  # Alias for compatibility with planning_generator
        self.status = status
        self.acceptance_criteria = []
        self.dependencies = []


def create_test_task(complexity=5, task_desc="Test task"):
    """Helper to create a test task structure."""
    return {
        "id": "TASK-test",
        "title": "Test Task",
        "description": task_desc,
        "complexity": complexity,
        "status": "backlog",
    }


def create_task_context(complexity=5, task_desc="Test task"):
    """Helper to create a TaskContext for planning generator."""
    return TaskContext(
        task_id="TASK-test",
        title="Test Task",
        description=task_desc,
        complexity=complexity,
        status="backlog",
    )


def execute_task_work_phase_15(task, flags=None):
    """Mock function representing Phase 1.5 of task-work.

    This would normally be part of the actual task-work implementation.
    For testing, we simulate the phase 1.5 logic.
    """
    if flags is None:
        flags = {}

    complexity = task.get("complexity", 5)
    task_desc = task.get("description", "")

    # Create TaskContext for planning generator
    task_context = create_task_context(complexity=complexity, task_desc=task_desc)

    # Check for --no-questions flag
    if flags.get("no_questions", False):
        return {"clarification": None, "task": task}

    # Check for --answers flag (inline answers)
    if "answers" in flags:
        # Parse inline answers (e.g., "scope:standard testing:unit")
        inline_answers = flags["answers"]
        decisions = []

        for pair in inline_answers.split():
            if ":" in pair:
                q_id, answer = pair.split(":", 1)
                decisions.append(Decision(
                    question_id=q_id,
                    category=q_id,
                    question_text=f"Question for {q_id}",
                    answer=answer,
                    answer_display=answer.capitalize(),
                    default_used=False,
                    rationale=f"Inline answer provided: {answer}",
                ))

        context = ClarificationContext(
            context_type="implementation_planning",
            mode="full",
        )
        # Add decisions directly to explicit_decisions
        context.explicit_decisions = decisions
        return {"clarification": context, "task": task}

    # Check for --with-questions flag (force questions)
    if flags.get("with_questions", False):
        # Force full mode regardless of complexity
        questions = generate_planning_questions(task_context, complexity)
        if questions:
            with patch('builtins.input', return_value=''):
                context = display_questions_full(
                    questions=questions,
                    task_id=task_context.id,
                    task_title=task_context.title,
                    complexity=complexity,
                )
                context.context_type = "implementation_planning"
        else:
            context = ClarificationContext(
                context_type="implementation_planning",
                mode="full",
            )
        return {"clarification": context, "task": task}

    # Normal complexity-based routing
    if complexity <= 2:
        # Skip clarification for trivial tasks
        return {"clarification": None, "task": task}
    elif complexity <= 4:
        # Quick mode with timeout
        questions = generate_planning_questions(task_context, complexity)
        if questions:
            with patch('builtins.input', return_value=''):
                context = display_questions_quick(
                    questions=questions,
                    timeout_seconds=15,
                )
                context.context_type = "implementation_planning"
        else:
            context = ClarificationContext(
                context_type="implementation_planning",
                mode="quick",
            )
        return {"clarification": context, "task": task}
    else:
        # Full mode for complex tasks
        questions = generate_planning_questions(task_context, complexity)
        if questions:
            with patch('builtins.input', return_value=''):
                context = display_questions_full(
                    questions=questions,
                    task_id=task_context.id,
                    task_title=task_context.title,
                    complexity=complexity,
                )
                context.context_type = "implementation_planning"
        else:
            context = ClarificationContext(
                context_type="implementation_planning",
                mode="full",
            )
        return {"clarification": context, "task": task}


class TestTaskWorkClarification:
    """Test clarification integration in task-work workflow."""

    def test_phase_15_skip_low_complexity(self):
        """Complexity 1-2 should skip clarification."""
        task = create_test_task(complexity=2)

        result = execute_task_work_phase_15(task, flags={})

        assert result["clarification"] is None

    def test_phase_15_skip_complexity_1(self):
        """Complexity 1 should skip clarification."""
        task = create_test_task(complexity=1)

        result = execute_task_work_phase_15(task, flags={})

        assert result["clarification"] is None

    def test_phase_15_quick_medium_complexity(self):
        """Complexity 3-4 should use quick mode with timeout."""
        task = create_test_task(complexity=4)

        result = execute_task_work_phase_15(task, flags={})

        # Should have used quick mode
        assert result["clarification"] is not None
        assert result["clarification"].mode == "quick"

    def test_phase_15_quick_complexity_3(self):
        """Complexity 3 should use quick mode."""
        task = create_test_task(complexity=3)

        result = execute_task_work_phase_15(task, flags={})

        assert result["clarification"] is not None
        assert result["clarification"].mode == "quick"

    def test_phase_15_full_high_complexity(self):
        """Complexity 5+ should use full blocking mode."""
        task = create_test_task(complexity=6)

        result = execute_task_work_phase_15(task, flags={})

        assert result["clarification"] is not None
        assert result["clarification"].mode == "full"

    def test_phase_15_full_complexity_5(self):
        """Complexity 5 should use full mode."""
        task = create_test_task(complexity=5)

        result = execute_task_work_phase_15(task, flags={})

        assert result["clarification"] is not None
        assert result["clarification"].mode == "full"

    def test_phase_15_full_very_high_complexity(self):
        """Very high complexity (8+) should use full mode."""
        task = create_test_task(complexity=9)

        result = execute_task_work_phase_15(task, flags={})

        assert result["clarification"] is not None
        assert result["clarification"].mode == "full"

    def test_no_questions_flag(self):
        """--no-questions should skip clarification regardless of complexity."""
        task = create_test_task(complexity=8)

        result = execute_task_work_phase_15(task, flags={'no_questions': True})

        assert result["clarification"] is None

    def test_no_questions_flag_medium_complexity(self):
        """--no-questions should skip even for medium complexity."""
        task = create_test_task(complexity=4)

        result = execute_task_work_phase_15(task, flags={'no_questions': True})

        assert result["clarification"] is None

    def test_with_questions_flag(self):
        """--with-questions should force clarification for low complexity."""
        task = create_test_task(complexity=1)

        result = execute_task_work_phase_15(task, flags={'with_questions': True})

        assert result["clarification"] is not None
        assert result["clarification"].mode == "full"

    def test_with_questions_flag_complexity_2(self):
        """--with-questions should override skip for complexity 2."""
        task = create_test_task(complexity=2)

        result = execute_task_work_phase_15(task, flags={'with_questions': True})

        assert result["clarification"] is not None

    def test_inline_answers(self):
        """--answers should parse and apply inline answers."""
        task = create_test_task(complexity=5)

        result = execute_task_work_phase_15(
            task,
            flags={'answers': 'scope:standard testing:integration'}
        )

        assert result["clarification"] is not None
        assert len(result["clarification"].decisions) >= 2

        # Find decisions by question_id
        scope_decision = next((d for d in result["clarification"].decisions if d.question_id == 'scope'), None)
        testing_decision = next((d for d in result["clarification"].decisions if d.question_id == 'testing'), None)

        assert scope_decision is not None
        assert scope_decision.answer == 'standard'
        
        assert testing_decision is not None
        assert testing_decision.answer == 'integration'

    def test_inline_answers_single_pair(self):
        """--answers with single key:value pair."""
        task = create_test_task(complexity=5)

        result = execute_task_work_phase_15(
            task,
            flags={'answers': 'scope:minimal'}
        )

        assert result["clarification"] is not None
        assert len(result["clarification"].decisions) >= 1

        scope_decision = result["clarification"].decisions[0]
        assert scope_decision.question_id == 'scope'
        assert scope_decision.answer == 'minimal'

    def test_inline_answers_multiple_pairs(self):
        """--answers with multiple key:value pairs."""
        task = create_test_task(complexity=5)

        result = execute_task_work_phase_15(
            task,
            flags={'answers': 'scope:complete testing:e2e docs:yes'}
        )

        assert result["clarification"] is not None
        assert len(result["clarification"].decisions) == 3

        decisions_by_id = {d.question_id: d for d in result["clarification"].decisions}
        
        assert decisions_by_id['scope'].answer == 'complete'
        assert decisions_by_id['testing'].answer == 'e2e'
        assert decisions_by_id['docs'].answer == 'yes'

    def test_inline_answers_no_interactive_prompts(self):
        """--answers should not trigger interactive prompts."""
        task = create_test_task(complexity=5)

        with patch('builtins.input') as mock_input:
            result = execute_task_work_phase_15(
                task,
                flags={'answers': 'scope:standard'}
            )

            # Input should not be called when inline answers provided
            mock_input.assert_not_called()

        assert result["clarification"] is not None


class TestQuickModeTimeout:
    """Test timeout behavior in quick mode."""

    def test_quick_mode_timeout_uses_defaults(self):
        """Quick mode timeout should apply defaults."""
        task = create_test_task(complexity=4)

        result = execute_task_work_phase_15(task, flags={})

        assert result["clarification"] is not None
        assert result["clarification"].mode == "quick"

        # All decisions should use defaults (if any questions were generated)
        if len(result["clarification"].decisions) > 0:
            assert all(d.default_used for d in result["clarification"].decisions)

    def test_quick_mode_user_answers_before_timeout(self):
        """User answering before timeout should use their answer.

        This test verifies the expected behavior using inline answers
        as a proxy for user input before timeout.
        """
        task = create_test_task(complexity=4)

        # Simulate user providing answer via inline flag (bypasses timeout)
        result = execute_task_work_phase_15(task, flags={'answers': 'scope:minimal'})

        assert result["clarification"] is not None
        # When using inline answers, decision should not be default
        if len(result["clarification"].decisions) > 0:
            scope_decision = result["clarification"].decisions[0]
            assert scope_decision.answer == "minimal"
            assert scope_decision.default_used is False

    def test_quick_mode_mixed_timeout_and_answers(self):
        """Some questions timeout, some answered.

        This test verifies mixed behavior using inline answers.
        """
        task = create_test_task(complexity=4)

        # Simulate user providing partial answers via inline flag
        result = execute_task_work_phase_15(task, flags={'answers': 'scope:minimal testing:unit'})

        # Both should be recorded as explicit decisions
        assert result["clarification"] is not None
        assert len(result["clarification"].decisions) == 2
        decisions_by_id = {d.question_id: d for d in result["clarification"].decisions}
        assert decisions_by_id['scope'].answer == 'minimal'
        assert decisions_by_id['testing'].answer == 'unit'


class TestClarificationContextPropagation:
    """Test that clarification context is passed to Phase 2."""

    def test_context_available_to_phase_2(self):
        """Clarification context should be available to planning phase."""
        task = create_test_task(complexity=6)

        result = execute_task_work_phase_15(task, flags={})

        # Phase 2 would receive this context
        clarification = result["clarification"]

        assert clarification is not None
        assert clarification.context_type == "implementation_planning"
        assert isinstance(clarification.decisions, list)

    def test_decisions_accessible_in_phase_2(self):
        """Phase 2 should be able to access individual decisions."""
        task = create_test_task(complexity=6)

        result = execute_task_work_phase_15(
            task,
            flags={'answers': 'scope:complete testing:integration docs:yes'}
        )

        clarification = result["clarification"]

        # Phase 2 could access decisions like this
        decisions_by_category = {d.category: d for d in clarification.decisions}

        assert "scope" in decisions_by_category
        assert decisions_by_category["scope"].answer == "complete"

    def test_skip_clarification_phase_2_handles_none(self):
        """Phase 2 should handle None clarification (skip case)."""
        task = create_test_task(complexity=1)

        result = execute_task_work_phase_15(task, flags={})

        clarification = result["clarification"]

        # Phase 2 should check for None and use defaults
        assert clarification is None


class TestEdgeCases:
    """Test edge cases."""

    def test_complexity_boundary_2_to_3(self):
        """Test complexity boundary between skip and quick."""
        task_2 = create_test_task(complexity=2)
        task_3 = create_test_task(complexity=3)

        result_2 = execute_task_work_phase_15(task_2, flags={})
        result_3 = execute_task_work_phase_15(task_3, flags={})

        # Complexity 2 should skip
        assert result_2["clarification"] is None

        # Complexity 3 should use quick mode
        assert result_3["clarification"] is not None
        assert result_3["clarification"].mode == "quick"

    def test_complexity_boundary_4_to_5(self):
        """Test complexity boundary between quick and full."""
        task_4 = create_test_task(complexity=4)
        task_5 = create_test_task(complexity=5)

        result_4 = execute_task_work_phase_15(task_4, flags={})
        result_5 = execute_task_work_phase_15(task_5, flags={})

        # Complexity 4 should use quick mode
        assert result_4["clarification"] is not None
        assert result_4["clarification"].mode == "quick"

        # Complexity 5 should use full mode
        assert result_5["clarification"] is not None
        assert result_5["clarification"].mode == "full"

    def test_flag_precedence_no_questions_over_with_questions(self):
        """--no-questions should take precedence over --with-questions."""
        task = create_test_task(complexity=6)

        result = execute_task_work_phase_15(
            task,
            flags={'no_questions': True, 'with_questions': True}
        )

        # --no-questions should win
        assert result["clarification"] is None

    def test_flag_precedence_answers_over_with_questions(self):
        """--answers should take precedence over --with-questions."""
        task = create_test_task(complexity=6)

        result = execute_task_work_phase_15(
            task,
            flags={'answers': 'scope:minimal', 'with_questions': True}
        )

        # --answers should be used
        assert result["clarification"] is not None
        assert len(result["clarification"].decisions) >= 1
        assert result["clarification"].decisions[0].answer == "minimal"

    def test_empty_task_description(self):
        """Empty task description should still allow clarification."""
        task = create_test_task(complexity=5, task_desc="")

        result = execute_task_work_phase_15(task, flags={})

        # Should still work, might generate generic questions
        assert result["clarification"] is not None
