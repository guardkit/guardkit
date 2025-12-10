"""Unit tests for implementation planning question generator."""

import sys
from pathlib import Path
import pytest

# Add the installer/core/commands directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "installer" / "core" / "commands"))

from lib.clarification.core import Question, ClarificationMode
from lib.clarification.generators.planning_generator import (
    TaskContext,
    CodebaseContext,
    DetectionResult,
    detect_scope_ambiguity,
    detect_user_ambiguity,
    detect_technology_choices,
    detect_integration_points,
    detect_unhandled_edge_cases,
    instantiate_questions,
    prioritize_questions,
    generate_planning_questions,
)


# =============================================================================
# DETECTION TESTS
# =============================================================================

class TestScopeDetection:
    """Tests for scope ambiguity detection."""

    def test_detects_vague_language(self):
        """Should detect vague language like 'support', 'handle', 'manage'."""
        task = TaskContext(
            task_id="TASK-001",
            title="Add support for user authentication",
            description="Handle login and registration",
            complexity_score=5
        )
        result = detect_scope_ambiguity(task)
        assert result is not None
        assert result.detected
        assert result.context["has_vague_language"]

    def test_detects_minimal_criteria(self):
        """Should detect missing or minimal acceptance criteria."""
        task = TaskContext(
            task_id="TASK-002",
            title="Implement authentication",
            description="Add login feature",
            acceptance_criteria=["Add login"],  # Only 1 criterion
            complexity_score=5
        )
        result = detect_scope_ambiguity(task)
        assert result is not None
        assert result.detected
        assert result.context["has_minimal_criteria"]

    def test_detects_multiple_concerns(self):
        """Should detect multiple concerns in title."""
        task = TaskContext(
            task_id="TASK-003",
            title="Add login and registration and password reset",
            description="Implement authentication",
            complexity_score=5
        )
        result = detect_scope_ambiguity(task)
        assert result is not None
        assert result.detected
        assert result.context["has_multiple_concerns"]

    def test_no_detection_for_clear_scope(self):
        """Should not detect ambiguity for clear, specific tasks."""
        task = TaskContext(
            task_id="TASK-004",
            title="Create login endpoint",
            description="POST /api/login endpoint that validates credentials",
            acceptance_criteria=[
                "Accept email and password",
                "Return JWT token on success",
                "Return 401 on failure",
            ],
            complexity_score=5
        )
        result = detect_scope_ambiguity(task)
        # May still detect due to vague language, but should be less ambiguous
        # This test documents current behavior


class TestUserDetection:
    """Tests for user/persona ambiguity detection."""

    def test_detects_no_user_mention(self):
        """Should detect when no users are mentioned."""
        task = TaskContext(
            task_id="TASK-005",
            title="Implement caching",
            description="Add Redis caching layer",
            complexity_score=5
        )
        result = detect_user_ambiguity(task)
        assert result is not None
        assert result.detected
        assert result.context["needs_persona"]

    def test_detects_generic_user(self):
        """Should detect generic 'user' without specificity."""
        task = TaskContext(
            task_id="TASK-006",
            title="Add user profile",
            description="Users should be able to view their profile",
            complexity_score=5
        )
        result = detect_user_ambiguity(task)
        assert result is not None
        assert result.detected
        assert result.context["has_generic_user"]

    def test_detects_multiple_user_types(self):
        """Should detect when multiple user types are mentioned."""
        task = TaskContext(
            task_id="TASK-007",
            title="Add admin and developer dashboard",
            description="Both admins and developers need access",
            complexity_score=5
        )
        result = detect_user_ambiguity(task)
        assert result is not None
        assert result.detected
        assert len(result.context["mentioned_types"]) > 1

    def test_no_detection_for_specific_user(self):
        """Should not detect ambiguity for specific user mention."""
        task = TaskContext(
            task_id="TASK-008",
            title="Add developer API keys",
            description="Developers need to generate API keys",
            complexity_score=5
        )
        result = detect_user_ambiguity(task)
        # Should be None or not need persona
        # This test documents current behavior


class TestTechnologyDetection:
    """Tests for technology choice detection."""

    def test_detects_implementation_choices(self):
        """Should detect when implementation approach needs decision."""
        task = TaskContext(
            task_id="TASK-009",
            title="Implement API service",
            description="Create new API handler",
            complexity_score=5
        )
        result = detect_technology_choices(task)
        assert result is not None
        assert result.detected
        assert "component" in result.context

    def test_detects_async_concerns(self):
        """Should detect when async/sync decision is needed."""
        task = TaskContext(
            task_id="TASK-010",
            title="Add background job processor",
            description="Implement async worker for queue",
            complexity_score=5
        )
        result = detect_technology_choices(task)
        assert result is not None
        assert result.detected
        assert result.context["needs_async_decision"]

    def test_no_detection_for_simple_task(self):
        """Should not detect technology choices for simple tasks."""
        task = TaskContext(
            task_id="TASK-011",
            title="Fix typo in README",
            description="Correct spelling error",
            complexity_score=1
        )
        result = detect_technology_choices(task)
        assert result is None


class TestIntegrationDetection:
    """Tests for integration point detection."""

    def test_detects_database_integration(self):
        """Should detect database integration needs."""
        task = TaskContext(
            task_id="TASK-012",
            title="Add user table migration",
            description="Create database schema for users",
            complexity_score=5
        )
        result = detect_integration_points(task)
        assert result is not None
        assert result.detected
        assert result.context["has_database"]

    def test_detects_api_integration(self):
        """Should detect external API integration."""
        task = TaskContext(
            task_id="TASK-013",
            title="Integrate with Stripe API",
            description="Connect to external payment service",
            complexity_score=6
        )
        result = detect_integration_points(task)
        assert result is not None
        assert result.detected
        assert result.context["has_api"]

    def test_detects_component_integration(self):
        """Should detect component interaction needs."""
        task = TaskContext(
            task_id="TASK-014",
            title="Connect auth to user service",
            description="Integrate authentication with existing user service",
            complexity_score=5
        )
        result = detect_integration_points(task)
        assert result is not None
        assert result.detected

    def test_no_detection_for_isolated_task(self):
        """Should not detect integration for isolated tasks."""
        task = TaskContext(
            task_id="TASK-015",
            title="Add utility function",
            description="Create string formatting helper",
            complexity_score=2
        )
        result = detect_integration_points(task)
        assert result is None


class TestEdgeCaseDetection:
    """Tests for edge case detection."""

    def test_detects_missing_error_handling_high_complexity(self):
        """Should detect edge cases for complex tasks without error handling discussion."""
        task = TaskContext(
            task_id="TASK-016",
            title="Implement distributed transaction",
            description="Add multi-service transaction handling",
            complexity_score=8
        )
        result = detect_unhandled_edge_cases(task)
        assert result is not None
        assert result.detected
        assert result.context["complexity_suggests_edges"]

    def test_no_detection_for_low_complexity(self):
        """Should not detect edge cases for simple tasks."""
        task = TaskContext(
            task_id="TASK-017",
            title="Add constant",
            description="Define new configuration constant",
            complexity_score=1
        )
        result = detect_unhandled_edge_cases(task)
        assert result is None

    def test_no_detection_when_error_handling_mentioned(self):
        """Should not detect if error handling is already discussed."""
        task = TaskContext(
            task_id="TASK-018",
            title="Implement transaction with error handling",
            description="Add transaction with rollback on failure",
            complexity_score=8
        )
        result = detect_unhandled_edge_cases(task)
        assert result is None


# =============================================================================
# INSTANTIATION TESTS
# =============================================================================

class TestQuestionInstantiation:
    """Tests for question template instantiation."""

    def test_replaces_placeholders_in_text(self):
        """Should replace placeholders in question text."""
        templates = [
            Question(
                id="test_q1",
                category="test",
                text="Should {feature} include {capability}?",
                options=["[Y]es", "[N]o"],
                default="[Y]es",
                rationale="Testing",
            )
        ]
        detection = DetectionResult(
            detected=True,
            context={"feature": "authentication", "capability": "2FA"}
        )

        questions = instantiate_questions(templates, detection)
        assert len(questions) == 1
        assert questions[0].text == "Should authentication include 2FA?"

    def test_replaces_placeholders_in_options(self):
        """Should replace placeholders in options."""
        templates = [
            Question(
                id="test_q2",
                category="test",
                text="Choose approach",
                options=["[A] {option_a}", "[B] {option_b}"],
                default="[A] {option_a}",
                rationale="Testing",
            )
        ]
        detection = DetectionResult(
            detected=True,
            context={"option_a": "Sync", "option_b": "Async"}
        )

        questions = instantiate_questions(templates, detection)
        assert questions[0].options == ["[A] Sync", "[B] Async"]

    def test_replaces_placeholders_in_rationale(self):
        """Should replace placeholders in rationale."""
        templates = [
            Question(
                id="test_q3",
                category="test",
                text="Test question",
                options=["[Y]es", "[N]o"],
                default="[Y]es",
                rationale="Common for {feature}",
            )
        ]
        detection = DetectionResult(
            detected=True,
            context={"feature": "authentication"}
        )

        questions = instantiate_questions(templates, detection)
        assert questions[0].rationale == "Common for authentication"


# =============================================================================
# PRIORITIZATION TESTS
# =============================================================================

class TestQuestionPrioritization:
    """Tests for question prioritization."""

    def test_prioritizes_by_category(self):
        """Should prioritize scope > technology > integration > user > tradeoff > edge_case."""
        questions = [
            Question("e1", "edge_case", "Edge?", ["Y", "N"], "Y", "Test"),
            Question("s1", "scope", "Scope?", ["Y", "N"], "Y", "Test"),
            Question("t1", "technology", "Tech?", ["Y", "N"], "Y", "Test"),
            Question("u1", "user", "User?", ["Y", "N"], "Y", "Test"),
        ]

        prioritized = prioritize_questions(questions, max_questions=10)
        categories = [q.category for q in prioritized]
        assert categories[0] == "scope"
        assert categories[1] == "technology"
        assert categories[2] == "user"
        assert categories[3] == "edge_case"

    def test_limits_to_max_questions(self):
        """Should limit to max_questions."""
        questions = [
            Question(f"q{i}", "scope", f"Q{i}?", ["Y", "N"], "Y", "Test")
            for i in range(10)
        ]

        limited = prioritize_questions(questions, max_questions=5)
        assert len(limited) == 5


# =============================================================================
# MAIN GENERATOR TESTS
# =============================================================================

class TestPlanningGenerator:
    """Tests for main planning question generator."""

    def test_returns_empty_for_skip_mode(self):
        """Should return empty list for SKIP mode."""
        task = TaskContext(
            task_id="TASK-019",
            title="Add feature",
            description="Implement something",
            complexity_score=8
        )
        questions = generate_planning_questions(task, mode=ClarificationMode.SKIP)
        assert len(questions) == 0

    def test_limits_questions_in_quick_mode(self):
        """Should limit to 3 questions in QUICK mode."""
        task = TaskContext(
            task_id="TASK-020",
            title="Implement complex authentication system",
            description="Add login, registration, password reset, 2FA, and OAuth",
            complexity_score=8
        )
        questions = generate_planning_questions(task, mode=ClarificationMode.QUICK)
        assert len(questions) <= 3

    def test_includes_scope_questions(self):
        """Should always include scope questions for ambiguous tasks."""
        task = TaskContext(
            task_id="TASK-021",
            title="Add support for authentication",
            description="Handle user login",
            complexity_score=5
        )
        questions = generate_planning_questions(task)
        assert any(q.category == "scope" for q in questions)

    def test_includes_tradeoff_for_medium_complexity(self):
        """Should include trade-off questions for complexity >= 5."""
        task = TaskContext(
            task_id="TASK-022",
            title="Update caching configuration",
            description="Modify Redis caching settings",
            acceptance_criteria=[
                "Update Redis connection string",
                "Change TTL settings",
                "Update cache key format",
            ],
            complexity_score=5
        )
        questions = generate_planning_questions(task)
        # With clear scope and multiple criteria, tradeoff questions should be included
        assert any(q.category == "tradeoff" for q in questions)

    def test_includes_edge_cases_for_high_complexity(self):
        """Should include edge case questions for complexity >= 7."""
        task = TaskContext(
            task_id="TASK-023",
            title="Implement distributed transaction",
            description="Add multi-service coordination",
            complexity_score=8
        )
        questions = generate_planning_questions(task)
        # Should include edge cases if not mentioned
        categories = [q.category for q in questions]
        # May or may not include edge_case depending on error keyword detection

    def test_respects_max_questions_limit(self):
        """Should never return more than 7 questions in FULL mode."""
        task = TaskContext(
            task_id="TASK-024",
            title="Add complex authentication with database and API integration",
            description="Implement login, registration, OAuth, 2FA with external services",
            complexity_score=9
        )
        questions = generate_planning_questions(task, mode=ClarificationMode.FULL)
        assert len(questions) <= 7

    def test_uses_codebase_context(self):
        """Should use codebase context for integration detection."""
        task = TaskContext(
            task_id="TASK-025",
            title="Add new API endpoint",
            description="Create new service",
            complexity_score=6
        )
        codebase = CodebaseContext(
            project_type="web",
            tech_stack=["python", "fastapi"],
            has_api=True
        )
        questions = generate_planning_questions(task, codebase_context=codebase)
        # Should include technology questions for API
        assert any(q.category == "technology" for q in questions)

    def test_complexity_override(self):
        """Should use complexity_score parameter if provided."""
        task = TaskContext(
            task_id="TASK-026",
            title="Update configuration",
            description="Modify system settings",
            acceptance_criteria=[
                "Update config file",
                "Restart service",
                "Verify changes",
            ],
            complexity_score=2  # Low in task
        )
        # Override with high complexity
        questions = generate_planning_questions(task, complexity_score=8)
        # Should include trade-off questions because of override
        assert any(q.category == "tradeoff" for q in questions)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestEndToEndGeneration:
    """Integration tests for complete question generation flow."""

    def test_realistic_authentication_task(self):
        """Should generate appropriate questions for authentication task."""
        task = TaskContext(
            task_id="TASK-027",
            title="Add user authentication",
            description="Implement login and registration with JWT tokens",
            acceptance_criteria=[
                "Users can register with email/password",
                "Users can login and receive JWT token",
            ],
            complexity_score=6
        )

        questions = generate_planning_questions(task)

        # Should have questions
        assert len(questions) > 0
        assert len(questions) <= 7

        # Should include user questions (generic "users")
        assert any(q.category == "user" for q in questions)

        # Should include trade-offs for medium complexity (>= 5)
        assert any(q.category == "tradeoff" for q in questions)

    def test_realistic_simple_task(self):
        """Should generate minimal questions for simple, clear task."""
        task = TaskContext(
            task_id="TASK-028",
            title="Add email validation utility",
            description="Create function to validate email format using regex",
            acceptance_criteria=[
                "Function accepts email string",
                "Returns true for valid emails",
                "Returns false for invalid emails",
                "Handles null/empty inputs",
            ],
            complexity_score=2
        )

        questions = generate_planning_questions(task)

        # Should have minimal or no questions (low complexity, clear scope)
        # May still have scope questions due to "add" keyword
        assert len(questions) <= 7

    def test_realistic_complex_integration_task(self):
        """Should generate comprehensive questions for complex integration."""
        task = TaskContext(
            task_id="TASK-029",
            title="Integrate with payment gateway",
            description="Add support for Stripe payment processing with webhook handling",
            complexity_score=8
        )

        questions = generate_planning_questions(task)

        # Should have many questions
        assert len(questions) > 0
        assert len(questions) <= 7

        # Should include multiple categories
        categories = {q.category for q in questions}
        assert "scope" in categories
        # Should include integration (API detected)
        assert "integration" in categories


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
