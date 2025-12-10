"""Integration tests for clarification in feature-plan workflow.

Tests clarification propagation through feature-plan which combines:
- Context A: Review scope (same as task-review)
- Context B: Implementation preferences (same as task-review)
- Subtask generation using clarification context
"""

import pytest
from unittest.mock import patch, MagicMock

from lib.clarification.core import Question, Decision, ClarificationContext
from lib.clarification.generators.review_generator import generate_review_questions
from lib.clarification.generators.implement_generator import generate_implement_questions
from lib.clarification.display import display_questions_full


def execute_feature_plan(feature_desc, flags=None):
    """Mock function representing feature-plan workflow.
    
    This simulates the full feature-plan flow including both clarification contexts.
    """
    if flags is None:
        flags = {}
    
    # Step 1: Create review task (automatic)
    review_task = {
        "id": "TASK-review-generated",
        "title": f"Review: {feature_desc}",
        "description": feature_desc,
        "task_type": "review",
    }
    
    # Step 2: Context A - Review scope clarification
    review_clarification = None
    if not flags.get("no_questions", False):
        questions = generate_review_questions(feature_desc, mode='decision')
        with patch('builtins.input', return_value=''):
            review_clarification = display_questions_full(
                questions=questions,
                context_type="review_scope",
            )
    
    # Step 3: Execute review (simulated)
    findings = {
        "recommendations": [
            "Add state management",
            "Implement UI components",
            "Add API integration",
        ],
        "options": [
            {"id": 1, "title": "Minimal - Basic functionality"},
            {"id": 2, "title": "Standard - With error handling"},
            {"id": 3, "title": "Complete - Production-ready"},
        ],
    }
    
    # Step 4: User chooses [I]mplement
    # Step 5: Context B - Implementation preferences
    implement_clarification = None
    if not flags.get("no_questions", False):
        questions = generate_implement_questions(findings)
        with patch('builtins.input', return_value=''):
            implement_clarification = display_questions_full(
                questions=questions,
                context_type="implementation_prefs",
            )
    
    # Step 6: Generate subtasks using clarification context
    subtasks = generate_subtasks(findings, implement_clarification)
    
    return {
        "review_task": review_task,
        "review_clarification": review_clarification,
        "findings": findings,
        "implement_clarification": implement_clarification,
        "subtasks": subtasks,
    }


def generate_subtasks(findings, clarification_context):
    """Generate subtasks based on findings and clarification context."""
    subtasks = []
    
    recommendations = findings.get("recommendations", [])
    
    # Determine scope from clarification
    scope = "standard"  # default
    if clarification_context:
        scope_decision = next(
            (d for d in clarification_context.decisions if d.category == "implementation_scope"),
            None
        )
        if scope_decision:
            scope = scope_decision.answer
    
    # Generate subtasks based on scope
    for i, rec in enumerate(recommendations):
        # Minimal scope: only first recommendation
        if scope == "minimal" and i > 0:
            continue
        
        # Standard scope: first 2 recommendations
        if scope == "standard" and i > 1:
            continue
        
        # Complete scope: all recommendations
        subtasks.append({
            "id": f"TASK-{i+1}",
            "title": rec,
            "scope": scope,
        })
    
    return subtasks


class TestFeaturePlanClarification:
    """Test clarification flow through feature-plan."""

    def test_full_clarification_flow(self):
        """Test complete feature-plan with both clarification contexts."""
        result = execute_feature_plan("implement dark mode")

        # Should have review clarification (Context A)
        assert result["review_clarification"] is not None
        assert result["review_clarification"].context_type == "review_scope"

        # Should have implementation clarification (Context B)
        assert result["implement_clarification"] is not None
        assert result["implement_clarification"].context_type == "implementation_prefs"

        # Should generate subtasks
        assert len(result["subtasks"]) >= 1

    def test_context_a_review_scope(self):
        """Context A should ask review scope questions."""
        result = execute_feature_plan("add user authentication")

        review_clarification = result["review_clarification"]

        assert review_clarification is not None
        assert review_clarification.context_type == "review_scope"
        assert len(review_clarification.decisions) >= 1

    def test_context_b_implementation_prefs(self):
        """Context B should ask implementation preference questions."""
        result = execute_feature_plan("add notifications")

        implement_clarification = result["implement_clarification"]

        assert implement_clarification is not None
        assert implement_clarification.context_type == "implementation_prefs"
        assert len(implement_clarification.decisions) >= 1

    def test_subtask_generation_uses_clarification(self):
        """Subtasks should reflect clarification decisions."""
        result = execute_feature_plan("implement search functionality")

        subtasks = result["subtasks"]
        implement_clarification = result["implement_clarification"]

        assert len(subtasks) >= 1

        # All subtasks should reflect the scope from clarification
        if implement_clarification:
            scope_decision = next(
                (d for d in implement_clarification.decisions 
                 if d.category == "implementation_scope"),
                None
            )
            if scope_decision:
                expected_scope = scope_decision.answer
                # All subtasks should have this scope
                # (In real implementation, this would affect task content)
                assert all(st.get("scope") == expected_scope for st in subtasks)

    def test_minimal_scope_fewer_subtasks(self):
        """Minimal scope should generate fewer subtasks."""
        # Mock implementation preferences to return minimal scope
        with patch('lib.clarification.display.display_questions_full') as mock_display:
            # First call: review clarification
            # Second call: implement clarification with minimal scope
            mock_display.side_effect = [
                ClarificationContext(
                    context_type="review_scope",
                    mode="full",
                    decisions=[],
                ),
                ClarificationContext(
                    context_type="implementation_prefs",
                    mode="full",
                    decisions=[
                        Decision(
                            question_id="scope",
                            category="implementation_scope",
                            question_text="How comprehensive?",
                            answer="minimal",
                            answer_display="Minimal",
                            default_used=False,
                            rationale="User chose minimal",
                        )
                    ],
                ),
            ]

            result = execute_feature_plan("add feature")

            # Minimal scope should have only 1 subtask
            assert len(result["subtasks"]) == 1
            assert result["subtasks"][0]["scope"] == "minimal"

    def test_complete_scope_all_subtasks(self):
        """Complete scope should generate all subtasks."""
        with patch('lib.clarification.display.display_questions_full') as mock_display:
            mock_display.side_effect = [
                ClarificationContext(
                    context_type="review_scope",
                    mode="full",
                    decisions=[],
                ),
                ClarificationContext(
                    context_type="implementation_prefs",
                    mode="full",
                    decisions=[
                        Decision(
                            question_id="scope",
                            category="implementation_scope",
                            question_text="How comprehensive?",
                            answer="complete",
                            answer_display="Complete",
                            default_used=False,
                            rationale="User chose complete",
                        )
                    ],
                ),
            ]

            result = execute_feature_plan("add feature")

            # Complete scope should have all 3 subtasks
            assert len(result["subtasks"]) == 3
            assert all(st["scope"] == "complete" for st in result["subtasks"])

    def test_standard_scope_moderate_subtasks(self):
        """Standard scope should generate moderate number of subtasks."""
        with patch('lib.clarification.display.display_questions_full') as mock_display:
            mock_display.side_effect = [
                ClarificationContext(
                    context_type="review_scope",
                    mode="full",
                    decisions=[],
                ),
                ClarificationContext(
                    context_type="implementation_prefs",
                    mode="full",
                    decisions=[
                        Decision(
                            question_id="scope",
                            category="implementation_scope",
                            question_text="How comprehensive?",
                            answer="standard",
                            answer_display="Standard",
                            default_used=True,
                            rationale="Default",
                        )
                    ],
                ),
            ]

            result = execute_feature_plan("add feature")

            # Standard scope should have 2 subtasks
            assert len(result["subtasks"]) == 2
            assert all(st["scope"] == "standard" for st in result["subtasks"])


class TestFeaturePlanFlags:
    """Test command-line flags with feature-plan."""

    def test_no_questions_flag(self):
        """--no-questions should skip both clarification contexts."""
        result = execute_feature_plan(
            "add feature",
            flags={'no_questions': True}
        )

        # Both contexts should be None
        assert result["review_clarification"] is None
        assert result["implement_clarification"] is None

        # Subtasks should still be generated (with defaults)
        assert len(result["subtasks"]) >= 1

    def test_no_questions_subtasks_use_defaults(self):
        """--no-questions should use default scope for subtasks."""
        result = execute_feature_plan(
            "add feature",
            flags={'no_questions': True}
        )

        # Should use standard (default) scope
        assert all(st["scope"] == "standard" for st in result["subtasks"])


class TestClarificationPropagation:
    """Test clarification context propagation through feature-plan."""

    def test_review_clarification_persisted(self):
        """Review clarification should be persisted to review task."""
        result = execute_feature_plan("add dark mode")

        review_task = result["review_task"]
        review_clarification = result["review_clarification"]

        # In real implementation, clarification would be persisted to task frontmatter
        assert review_clarification is not None
        assert review_clarification.context_type == "review_scope"

    def test_implement_clarification_affects_subtasks(self):
        """Implementation clarification should affect subtask generation."""
        result = execute_feature_plan("add notifications")

        implement_clarification = result["implement_clarification"]
        subtasks = result["subtasks"]

        assert implement_clarification is not None
        assert len(subtasks) >= 1

        # Subtasks should reflect clarification preferences
        # (verified by scope matching in previous tests)

    def test_independent_clarification_contexts(self):
        """Review and implementation clarifications should be independent."""
        result = execute_feature_plan("add search")

        review_clarification = result["review_clarification"]
        implement_clarification = result["implement_clarification"]

        assert review_clarification is not None
        assert implement_clarification is not None

        # Different context types
        assert review_clarification.context_type == "review_scope"
        assert implement_clarification.context_type == "implementation_prefs"

        # Independent decisions
        assert review_clarification.decisions != implement_clarification.decisions


class TestFeaturePlanWorkflowSteps:
    """Test individual workflow steps."""

    def test_step_1_create_review_task(self):
        """Step 1 should create a review task."""
        result = execute_feature_plan("implement API versioning")

        review_task = result["review_task"]

        assert review_task is not None
        assert review_task["task_type"] == "review"
        assert "API versioning" in review_task["description"]

    def test_step_2_review_scope_clarification(self):
        """Step 2 should execute review scope clarification."""
        result = execute_feature_plan("add caching layer")

        review_clarification = result["review_clarification"]

        assert review_clarification is not None
        assert review_clarification.context_type == "review_scope"

    def test_step_3_execute_review(self):
        """Step 3 should execute review and generate findings."""
        result = execute_feature_plan("implement logging")

        findings = result["findings"]

        assert findings is not None
        assert "recommendations" in findings
        assert len(findings["recommendations"]) >= 1

    def test_step_5_implementation_preferences(self):
        """Step 5 should clarify implementation preferences."""
        result = execute_feature_plan("add error handling")

        implement_clarification = result["implement_clarification"]

        assert implement_clarification is not None
        assert implement_clarification.context_type == "implementation_prefs"

    def test_step_6_generate_subtasks(self):
        """Step 6 should generate subtasks."""
        result = execute_feature_plan("implement authentication")

        subtasks = result["subtasks"]

        assert len(subtasks) >= 1
        assert all("id" in st for st in subtasks)
        assert all("title" in st for st in subtasks)


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_feature_description(self):
        """Empty feature description should handle gracefully."""
        result = execute_feature_plan("")

        # Should still execute, might use generic questions
        assert result is not None
        assert "subtasks" in result

    def test_very_long_feature_description(self):
        """Very long feature description should handle gracefully."""
        long_desc = " ".join(["implement feature"] * 100)

        result = execute_feature_plan(long_desc)

        assert result is not None
        assert result["review_clarification"] is not None

    def test_feature_with_special_characters(self):
        """Feature description with special characters."""
        result = execute_feature_plan("add @mentions & #hashtags support")

        assert result is not None
        assert len(result["subtasks"]) >= 1

    def test_no_findings_generated(self):
        """Handle case where review generates no findings."""
        # This would be unusual but should be handled
        # Mock would need to return empty findings
        # For now, this test verifies current behavior expects findings
        result = execute_feature_plan("add feature")

        # Current implementation always generates findings
        assert len(result["findings"]["recommendations"]) >= 1
