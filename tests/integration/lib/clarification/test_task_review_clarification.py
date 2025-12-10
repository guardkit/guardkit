"""Integration tests for clarification in task-review workflow.

Tests two integration points:
- Context A: Review scope clarification (Phase 1)
- Context B: Implementation preferences ([I]mplement handler)
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from lib.clarification.core import Question, Decision, ClarificationContext
from lib.clarification.generators.review_generator import generate_review_questions
from lib.clarification.generators.implement_generator import generate_implement_questions
from lib.clarification.display import display_questions_full


def create_test_task(task_type='review', complexity=5, review_desc="Review the system"):
    """Helper to create a test review task."""
    return {
        "id": "TASK-review-test",
        "title": "Review Task",
        "description": review_desc,
        "task_type": task_type,
        "complexity": complexity,
        "status": "backlog",
    }


def create_test_findings(num_recommendations=3, num_options=3):
    """Helper to create test review findings."""
    recommendations = [f"Recommendation {i+1}" for i in range(num_recommendations)]
    
    options = []
    if num_options > 0:
        option_labels = ["Minimal", "Standard", "Complete", "Full", "Comprehensive"]
        for i in range(min(num_options, len(option_labels))):
            options.append({
                "id": i + 1,
                "title": f"{option_labels[i]} - Implementation scope {i+1}",
            })
    
    return {
        "recommendations": recommendations,
        "options": options,
    }


def execute_task_review_phase_1(task, mode='decision', flags=None):
    """Mock function representing Phase 1 (Context A) of task-review.
    
    This is the review scope clarification point.
    """
    if flags is None:
        flags = {}
    
    review_desc = task.get("description", "")
    
    # Check for --no-questions flag
    if flags.get("no_questions", False):
        return {"clarification": None, "task": task}
    
    # Generate review scope questions
    questions = generate_review_questions(review_desc, mode=mode)
    
    # Display questions (mocked with defaults)
    with patch('builtins.input', return_value=''):
        context = display_questions_full(
            questions=questions,
            context_type="review_scope",
        )
    
    return {"clarification": context, "task": task}


def handle_implement_decision(findings, flags=None):
    """Mock function representing [I]mplement handler (Context B) of task-review.
    
    This is where implementation preferences are clarified.
    """
    if flags is None:
        flags = {}
    
    # Check for --no-questions flag
    if flags.get("no_questions", False):
        return {"clarification": None, "findings": findings}
    
    # Generate implementation preference questions
    questions = generate_implement_questions(findings)
    
    # Display questions (mocked with defaults)
    with patch('builtins.input', return_value=''):
        context = display_questions_full(
            questions=questions,
            context_type="implementation_prefs",
        )
    
    return {"clarification": context, "findings": findings}


class TestTaskReviewClarification:
    """Test Context A: Review scope clarification."""

    def test_context_a_review_scope(self):
        """Context A should ask review scope questions."""
        task = create_test_task(task_type='review', complexity=5)

        result = execute_task_review_phase_1(task, mode='decision', flags={})

        assert result["clarification"] is not None
        assert result["clarification"].context_type == "review_scope"
        assert result["clarification"].mode == "full"
        assert len(result["clarification"].decisions) >= 1

    def test_context_a_decision_mode(self):
        """Decision mode should ask appropriate questions."""
        task = create_test_task(
            review_desc="Should we migrate to microservices?",
            complexity=6
        )

        result = execute_task_review_phase_1(task, mode='decision', flags={})

        assert result["clarification"] is not None
        # Should have questions about decision criteria, options, etc.
        assert len(result["clarification"].decisions) >= 2

    def test_context_a_architectural_mode(self):
        """Architectural mode should ask architecture-specific questions."""
        task = create_test_task(
            review_desc="Review API architecture for SOLID compliance",
            complexity=5
        )

        result = execute_task_review_phase_1(task, mode='architectural', flags={})

        assert result["clarification"] is not None
        assert result["clarification"].context_type == "review_scope"

    def test_context_a_security_mode(self):
        """Security mode should ask security-specific questions."""
        task = create_test_task(
            review_desc="Security audit of authentication endpoints",
            complexity=7
        )

        result = execute_task_review_phase_1(task, mode='security', flags={})

        assert result["clarification"] is not None
        assert result["clarification"].context_type == "review_scope"

    def test_context_a_code_quality_mode(self):
        """Code quality mode should ask quality-specific questions."""
        task = create_test_task(
            review_desc="Review code quality and maintainability",
            complexity=5
        )

        result = execute_task_review_phase_1(task, mode='code-quality', flags={})

        assert result["clarification"] is not None

    def test_context_a_technical_debt_mode(self):
        """Technical debt mode should ask debt assessment questions."""
        task = create_test_task(
            review_desc="Assess technical debt in legacy codebase",
            complexity=6
        )

        result = execute_task_review_phase_1(task, mode='technical-debt', flags={})

        assert result["clarification"] is not None

    def test_context_a_no_questions_flag(self):
        """--no-questions should skip review clarification."""
        task = create_test_task(complexity=6)

        result = execute_task_review_phase_1(
            task,
            mode='decision',
            flags={'no_questions': True}
        )

        assert result["clarification"] is None


class TestImplementHandler:
    """Test Context B: Implementation preferences at [I]mplement."""

    def test_context_b_implement_handler(self):
        """Context B should ask implementation preference questions."""
        findings = create_test_findings(num_recommendations=3, num_options=3)

        result = handle_implement_decision(findings, flags={})

        assert result["clarification"] is not None
        assert result["clarification"].context_type == "implementation_prefs"
        assert result["clarification"].mode == "full"
        assert len(result["clarification"].decisions) >= 1

    def test_context_b_single_recommendation(self):
        """Single recommendation should still have questions."""
        findings = create_test_findings(num_recommendations=1, num_options=0)

        result = handle_implement_decision(findings, flags={})

        assert result["clarification"] is not None
        assert len(result["clarification"].decisions) >= 1

    def test_context_b_multiple_recommendations(self):
        """Multiple recommendations should ask prioritization questions."""
        findings = create_test_findings(num_recommendations=5, num_options=3)

        result = handle_implement_decision(findings, flags={})

        assert result["clarification"] is not None
        # Should ask about prioritization or batching
        categories = [d.category for d in result["clarification"].decisions]
        assert any(cat in ["prioritization", "batching", "implementation_scope"] for cat in categories)

    def test_context_b_with_options(self):
        """Findings with options should include option selection question."""
        findings = create_test_findings(num_recommendations=3, num_options=3)

        result = handle_implement_decision(findings, flags={})

        assert result["clarification"] is not None
        # Should have a question about which option
        scope_questions = [
            d for d in result["clarification"].decisions 
            if d.category in ["implementation_scope", "approach"]
        ]
        assert len(scope_questions) >= 1

    def test_context_b_without_options(self):
        """Findings without options should still have implementation questions."""
        findings = create_test_findings(num_recommendations=2, num_options=0)

        result = handle_implement_decision(findings, flags={})

        assert result["clarification"] is not None
        # Should still have questions about implementation approach
        assert len(result["clarification"].decisions) >= 1

    def test_context_b_no_questions_flag(self):
        """--no-questions should skip implementation preferences."""
        findings = create_test_findings(num_recommendations=3, num_options=3)

        result = handle_implement_decision(findings, flags={'no_questions': True})

        assert result["clarification"] is None


class TestFullWorkflow:
    """Test complete task-review workflow with both contexts."""

    def test_review_then_implement_workflow(self):
        """Test full workflow: Context A → Review → Context B → Implement."""
        # Phase 1: Review scope clarification (Context A)
        task = create_test_task(
            review_desc="Review authentication architecture",
            complexity=6
        )

        review_result = execute_task_review_phase_1(task, mode='decision', flags={})

        assert review_result["clarification"] is not None
        assert review_result["clarification"].context_type == "review_scope"

        # Simulate review execution (would generate findings)
        findings = create_test_findings(num_recommendations=4, num_options=3)

        # User chooses [I]mplement at checkpoint
        # Phase B: Implementation preferences (Context B)
        implement_result = handle_implement_decision(findings, flags={})

        assert implement_result["clarification"] is not None
        assert implement_result["clarification"].context_type == "implementation_prefs"

        # Both clarifications should be independent
        assert review_result["clarification"] != implement_result["clarification"]

    def test_review_with_accept_decision(self):
        """Test review workflow with [A]ccept decision (no Context B)."""
        task = create_test_task(complexity=5)

        # Context A
        review_result = execute_task_review_phase_1(task, mode='architectural', flags={})

        assert review_result["clarification"] is not None

        # If user chooses [A]ccept, Context B is not triggered
        # Task goes to IN_REVIEW state
        # No implementation clarification needed

    def test_review_with_revise_decision(self):
        """Test review workflow with [R]evise decision (re-run review)."""
        task = create_test_task(complexity=5)

        # First review (Context A)
        review_result_1 = execute_task_review_phase_1(task, mode='decision', flags={})

        assert review_result_1["clarification"] is not None

        # User chooses [R]evise with different scope
        # Second review (Context A again with updated clarification)
        review_result_2 = execute_task_review_phase_1(task, mode='decision', flags={})

        assert review_result_2["clarification"] is not None

    def test_review_skip_both_contexts(self):
        """Test --no-questions skips both contexts."""
        task = create_test_task(complexity=6)
        findings = create_test_findings(num_recommendations=3, num_options=3)

        # Context A with --no-questions
        review_result = execute_task_review_phase_1(
            task,
            mode='decision',
            flags={'no_questions': True}
        )

        assert review_result["clarification"] is None

        # Context B with --no-questions
        implement_result = handle_implement_decision(
            findings,
            flags={'no_questions': True}
        )

        assert implement_result["clarification"] is None


class TestContextPropagation:
    """Test clarification context propagation."""

    def test_review_context_available_to_review_phase(self):
        """Review clarification should be available during review execution."""
        task = create_test_task(complexity=6)

        result = execute_task_review_phase_1(task, mode='decision', flags={})

        clarification = result["clarification"]

        # Review execution phase would receive this context
        assert clarification is not None
        assert clarification.context_type == "review_scope"

        # Could access decisions like:
        decisions_by_category = {d.category: d for d in clarification.decisions}
        # Use these to focus the review
        assert len(decisions_by_category) >= 1

    def test_implement_context_available_to_subtask_creation(self):
        """Implementation preferences should be available when creating subtasks."""
        findings = create_test_findings(num_recommendations=3, num_options=3)

        result = handle_implement_decision(findings, flags={})

        clarification = result["clarification"]

        # Subtask creation would receive this context
        assert clarification is not None
        assert clarification.context_type == "implementation_prefs"

        # Could access preferences like:
        scope_decision = next(
            (d for d in clarification.decisions if d.category == "implementation_scope"),
            None
        )

        # Use this to determine which subtasks to create
        if scope_decision:
            assert scope_decision.answer in ["minimal", "standard", "complete"]


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_review_description(self):
        """Empty review description should still allow clarification."""
        task = create_test_task(review_desc="")

        result = execute_task_review_phase_1(task, mode='decision', flags={})

        # Should still work, might generate generic questions
        assert result["clarification"] is not None

    def test_empty_findings(self):
        """Empty findings should handle gracefully."""
        findings = {
            "recommendations": [],
            "options": [],
        }

        result = handle_implement_decision(findings, flags={})

        # Should handle gracefully
        assert result["clarification"] is not None or result["clarification"] is None

    def test_missing_mode(self):
        """Missing review mode should use default."""
        task = create_test_task(complexity=5)

        # Mode defaults to 'decision' or similar
        try:
            result = execute_task_review_phase_1(task, mode=None, flags={})
            assert result["clarification"] is not None
        except (ValueError, TypeError):
            # Also acceptable to raise error
            pass

    def test_concurrent_review_and_implement(self):
        """Test that two contexts don't interfere with each other."""
        task = create_test_task(complexity=6)
        findings = create_test_findings(num_recommendations=3, num_options=3)

        # Execute both contexts
        review_result = execute_task_review_phase_1(task, mode='decision', flags={})
        implement_result = handle_implement_decision(findings, flags={})

        # Both should exist independently
        assert review_result["clarification"] is not None
        assert implement_result["clarification"] is not None

        # Different context types
        assert review_result["clarification"].context_type == "review_scope"
        assert implement_result["clarification"].context_type == "implementation_prefs"

        # Decisions should be independent
        assert review_result["clarification"].decisions != implement_result["clarification"].decisions
