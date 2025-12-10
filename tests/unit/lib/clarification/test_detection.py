"""
Unit tests for clarification detection algorithms.

Tests cover all detection functions to ensure they correctly identify
areas of ambiguity in task descriptions.
"""

import pytest
import sys
from pathlib import Path

# Add lib directory to path
lib_path = Path(__file__).parent.parent.parent.parent / "installer" / "core" / "commands" / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

from clarification.detection import (
    TaskContext,
    CodebaseContext,
    detect_scope_ambiguity,
    detect_technology_choices,
    detect_integration_points,
    detect_user_ambiguity,
    detect_tradeoff_needs,
    detect_unhandled_edge_cases,
)


class TestDetectScopeAmbiguity:
    """Tests for detect_scope_ambiguity function."""

    def test_detects_auth_without_password_reset(self):
        """Should detect auth implementation missing password reset mention."""
        task = TaskContext(
            task_id="TASK-001",
            title="Implement user authentication",
            description="Create login and signup functionality",
            complexity=5
        )

        result = detect_scope_ambiguity(task)

        assert result is not None
        assert result.feature == "auth" or result.feature == "authentication"
        assert "password reset" in result.unmentioned_extensions
        assert result.confidence > 0.7

    def test_detects_api_without_pagination(self):
        """Should detect API implementation missing pagination."""
        task = TaskContext(
            task_id="TASK-002",
            title="Create API endpoint",
            description="Build REST API for user data",
            complexity=4
        )

        result = detect_scope_ambiguity(task)

        assert result is not None
        assert result.feature == "api"
        assert "pagination" in result.unmentioned_extensions
        assert result.confidence > 0.7

    def test_detects_list_without_filtering(self):
        """Should detect list feature missing filtering/sorting."""
        task = TaskContext(
            task_id="TASK-003",
            title="Display user list",
            description="Show list of all users",
            complexity=3
        )

        result = detect_scope_ambiguity(task)

        assert result is not None
        assert result.feature == "list"
        assert any(ext in result.unmentioned_extensions for ext in ["filtering", "sorting"])

    def test_no_ambiguity_when_extensions_mentioned(self):
        """Should not detect ambiguity when extensions are explicitly mentioned."""
        task = TaskContext(
            task_id="TASK-004",
            title="Implement authentication",
            description="Create login, signup, and password reset functionality. No 2FA needed.",
            acceptance_criteria=["Login", "Signup", "Password reset"],
            complexity=5
        )

        result = detect_scope_ambiguity(task)

        # Should still detect some unmentioned extensions
        if result:
            assert "password reset" not in result.unmentioned_extensions
            # But might detect OAuth, 2FA, etc.

    def test_higher_confidence_with_no_acceptance_criteria(self):
        """Should have higher confidence when acceptance criteria missing."""
        task_no_ac = TaskContext(
            task_id="TASK-005",
            title="Add user features",
            description="Implement user functionality",
            complexity=5
        )

        task_with_ac = TaskContext(
            task_id="TASK-006",
            title="Add user features",
            description="Implement user functionality",
            acceptance_criteria=["Profile page", "Settings"],
            complexity=5
        )

        result_no_ac = detect_scope_ambiguity(task_no_ac)
        result_with_ac = detect_scope_ambiguity(task_with_ac)

        if result_no_ac and result_with_ac:
            assert result_no_ac.confidence >= result_with_ac.confidence

    def test_no_detection_for_unrelated_features(self):
        """Should not detect scope ambiguity for non-feature tasks."""
        task = TaskContext(
            task_id="TASK-007",
            title="Fix bug in login",
            description="Resolve issue where login button is disabled",
            complexity=2
        )

        result = detect_scope_ambiguity(task)

        # Might still detect "auth" pattern, but confidence should be reasonable
        # or no detection at all
        assert result is None or result.confidence < 0.9


class TestDetectTechnologyChoices:
    """Tests for detect_technology_choices function."""

    def test_detects_data_fetching_choices_react(self):
        """Should detect data fetching technology choices for React."""
        task = TaskContext(
            task_id="TASK-010",
            title="Add data fetching to dashboard",
            description="Fetch user data from API for React dashboard",
            tags=["react"],
            complexity=5
        )

        result = detect_technology_choices(task)

        assert result is not None
        assert len(result.choices) > 0
        data_fetching_choice = next(
            (c for c in result.choices if c.domain == "data_fetching"),
            None
        )
        assert data_fetching_choice is not None
        assert "React Query" in data_fetching_choice.alternatives

    def test_detects_state_management_choices(self):
        """Should detect state management technology choices."""
        task = TaskContext(
            task_id="TASK-011",
            title="Implement global state management",
            description="Add state management for React application",
            tags=["react"],
            complexity=6
        )

        result = detect_technology_choices(task)

        assert result is not None
        state_choice = next(
            (c for c in result.choices if c.domain == "state_management"),
            None
        )
        assert state_choice is not None
        assert "Redux" in state_choice.alternatives or "Zustand" in state_choice.alternatives

    def test_recommends_extending_existing_tech(self):
        """Should recommend extending when technology already in use."""
        task = TaskContext(
            task_id="TASK-012",
            title="Add new API endpoint data fetching",
            description="Fetch order data from new endpoint",
            tags=["react"],
            complexity=4
        )

        codebase = CodebaseContext(
            detected_stack="react",
            tech_inventory={"data_fetching": ["React Query"]}
        )

        result = detect_technology_choices(task, codebase)

        if result:
            data_choice = next(
                (c for c in result.choices if c.domain == "data_fetching"),
                None
            )
            if data_choice:
                assert data_choice.existing == "React Query"
                assert data_choice.recommendation == "extend_existing"

    def test_no_choices_for_unrelated_task(self):
        """Should not detect technology choices for simple tasks."""
        task = TaskContext(
            task_id="TASK-013",
            title="Update documentation",
            description="Fix typo in README",
            complexity=1
        )

        result = detect_technology_choices(task)

        assert result is None or len(result.choices) == 0


class TestDetectIntegrationPoints:
    """Tests for detect_integration_points function."""

    def test_detects_stripe_integration(self):
        """Should detect Stripe payment integration."""
        task = TaskContext(
            task_id="TASK-020",
            title="Add Stripe payment processing",
            description="Integrate Stripe for credit card payments",
            complexity=7
        )

        result = detect_integration_points(task)

        assert len(result) > 0
        stripe_integration = next(
            (i for i in result if "stripe" in i.system.lower()),
            None
        )
        assert stripe_integration is not None

    def test_detects_api_integration(self):
        """Should detect generic API integration."""
        task = TaskContext(
            task_id="TASK-021",
            title="Connect to third-party API",
            description="Integrate with external weather API",
            complexity=5
        )

        result = detect_integration_points(task)

        assert len(result) > 0
        api_integration = next(
            (i for i in result if "api" in i.system.lower()),
            None
        )
        assert api_integration is not None

    def test_detects_extend_integration_type(self):
        """Should detect extending existing integration."""
        task = TaskContext(
            task_id="TASK-022",
            title="Extend Twilio integration",
            description="Add SMS functionality to existing Twilio integration",
            complexity=4
        )

        codebase = CodebaseContext(
            external_services=["Twilio"]
        )

        result = detect_integration_points(task, codebase)

        if result:
            twilio_integration = next(
                (i for i in result if "twilio" in i.system.lower()),
                None
            )
            if twilio_integration:
                assert twilio_integration.integration_type == "extend"

    def test_no_integration_for_internal_features(self):
        """Should not detect integration for purely internal features."""
        task = TaskContext(
            task_id="TASK-023",
            title="Add user profile page",
            description="Create internal user profile display",
            complexity=3
        )

        result = detect_integration_points(task)

        assert len(result) == 0


class TestDetectUserAmbiguity:
    """Tests for detect_user_ambiguity function."""

    def test_detects_multiple_user_types(self):
        """Should detect when multiple user types are possible."""
        task = TaskContext(
            task_id="TASK-030",
            title="Add admin dashboard",
            description="Create dashboard for admin and user management",
            complexity=6
        )

        result = detect_user_ambiguity(task)

        assert result is not None
        assert "admin" in result.possible_users or "administrator" in [u.lower() for u in result.possible_users]

    def test_detects_permission_requirements(self):
        """Should detect when permissions are mentioned."""
        task = TaskContext(
            task_id="TASK-031",
            title="Implement role-based access control",
            description="Add permission system for different user roles",
            complexity=7
        )

        result = detect_user_ambiguity(task)

        assert result is not None
        assert result.requires_permissions is True
        assert result.confidence > 0.7

    def test_no_ambiguity_for_single_user_type(self):
        """Should have lower confidence for tasks with clear single user type."""
        task = TaskContext(
            task_id="TASK-032",
            title="Display user profile",
            description="Show user's own profile information",
            complexity=3
        )

        result = detect_user_ambiguity(task)

        # May detect "user" but should have single user type
        if result:
            assert len(result.possible_users) <= 1 or result.confidence < 0.8

    def test_no_ambiguity_for_non_user_features(self):
        """Should not detect user ambiguity for non-user-related tasks."""
        task = TaskContext(
            task_id="TASK-033",
            title="Optimize database queries",
            description="Improve query performance",
            complexity=5
        )

        result = detect_user_ambiguity(task)

        assert result is None


class TestDetectTradeoffNeeds:
    """Tests for detect_tradeoff_needs function."""

    def test_detects_performance_tradeoff(self):
        """Should detect performance optimization trade-offs."""
        task = TaskContext(
            task_id="TASK-040",
            title="Optimize API performance",
            description="Improve API response time with caching",
            complexity=6
        )

        result = detect_tradeoff_needs(task)

        assert len(result) > 0
        perf_tradeoff = next(
            (t for t in result if t.tradeoff_type == "performance"),
            None
        )
        assert perf_tradeoff is not None

    def test_detects_security_tradeoff(self):
        """Should detect security vs UX trade-offs."""
        task = TaskContext(
            task_id="TASK-041",
            title="Implement authentication security",
            description="Add 2FA and password complexity requirements",
            complexity=5
        )

        result = detect_tradeoff_needs(task)

        assert len(result) > 0
        security_tradeoff = next(
            (t for t in result if t.tradeoff_type == "security"),
            None
        )
        assert security_tradeoff is not None

    def test_detects_complexity_based_tradeoff(self):
        """Should detect trade-offs for high complexity tasks."""
        task = TaskContext(
            task_id="TASK-042",
            title="Refactor authentication system",
            description="Complete rewrite of auth module",
            complexity=8
        )

        result = detect_tradeoff_needs(task)

        assert len(result) > 0
        impl_tradeoff = next(
            (t for t in result if t.tradeoff_type == "implementation_approach"),
            None
        )
        assert impl_tradeoff is not None

    def test_detects_error_handling_tradeoff(self):
        """Should detect error handling strategy trade-offs."""
        task = TaskContext(
            task_id="TASK-043",
            title="Add error handling",
            description="Implement error handling for API failures",
            complexity=4
        )

        result = detect_tradeoff_needs(task)

        error_tradeoff = next(
            (t for t in result if t.tradeoff_type == "error_handling"),
            None
        )
        assert error_tradeoff is not None

    def test_no_tradeoffs_for_simple_tasks(self):
        """Should not detect trade-offs for simple tasks."""
        task = TaskContext(
            task_id="TASK-044",
            title="Fix typo",
            description="Correct spelling mistake",
            complexity=1
        )

        result = detect_tradeoff_needs(task)

        assert len(result) == 0


class TestDetectUnhandledEdgeCases:
    """Tests for detect_unhandled_edge_cases function."""

    def test_detects_crud_without_error_handling(self):
        """Should detect CRUD operations missing error handling."""
        task = TaskContext(
            task_id="TASK-050",
            title="Create user management",
            description="Add create, update, and delete operations for users",
            complexity=5
        )

        result = detect_unhandled_edge_cases(task)

        assert len(result) > 0
        error_case = next(
            (e for e in result if e.category == "error_handling"),
            None
        )
        assert error_case is not None

    def test_detects_network_without_timeout(self):
        """Should detect network operations missing timeout/retry."""
        task = TaskContext(
            task_id="TASK-051",
            title="Fetch data from API",
            description="Make HTTP request to external API",
            complexity=4
        )

        result = detect_unhandled_edge_cases(task)

        timeout_case = next(
            (e for e in result if e.category == "timeout_retry"),
            None
        )
        assert timeout_case is not None

    def test_detects_input_without_validation(self):
        """Should detect user input missing validation."""
        task = TaskContext(
            task_id="TASK-052",
            title="Create input form",
            description="Add form for user data entry",
            complexity=3
        )

        result = detect_unhandled_edge_cases(task)

        validation_case = next(
            (e for e in result if e.category == "validation"),
            None
        )
        assert validation_case is not None

    def test_detects_list_without_empty_state(self):
        """Should detect list display missing empty state."""
        task = TaskContext(
            task_id="TASK-053",
            title="Display user list",
            description="Show table of all users",
            complexity=3
        )

        result = detect_unhandled_edge_cases(task)

        empty_case = next(
            (e for e in result if e.category == "empty_state"),
            None
        )
        assert empty_case is not None

    def test_detects_auth_without_recovery(self):
        """Should detect authentication missing password recovery."""
        task = TaskContext(
            task_id="TASK-054",
            title="Implement password authentication",
            description="Add login with username and password",
            complexity=5
        )

        result = detect_unhandled_edge_cases(task)

        recovery_case = next(
            (e for e in result if e.category == "account_recovery"),
            None
        )
        assert recovery_case is not None

    def test_no_edge_cases_with_complete_spec(self):
        """Should detect fewer edge cases when specification is complete."""
        task = TaskContext(
            task_id="TASK-055",
            title="Create user form with validation",
            description="""
            Add user input form with:
            - Validation for all fields
            - Error handling for failures
            - Empty state message
            - Timeout for API requests
            """,
            complexity=4
        )

        result = detect_unhandled_edge_cases(task)

        # Should detect fewer edge cases since many are addressed
        assert len(result) < 3


class TestTaskContext:
    """Tests for TaskContext dataclass."""

    def test_creates_minimal_task_context(self):
        """Should create task context with minimal fields."""
        task = TaskContext(
            task_id="TASK-001",
            title="Test task",
            description="Test description"
        )

        assert task.task_id == "TASK-001"
        assert task.title == "Test task"
        assert task.description == "Test description"
        assert task.acceptance_criteria == []
        assert task.complexity == 0
        assert task.tags == []

    def test_creates_full_task_context(self):
        """Should create task context with all fields."""
        task = TaskContext(
            task_id="TASK-002",
            title="Full task",
            description="Full description",
            acceptance_criteria=["AC1", "AC2"],
            complexity=7,
            tags=["react", "api"],
            metadata={"priority": "high"}
        )

        assert len(task.acceptance_criteria) == 2
        assert task.complexity == 7
        assert len(task.tags) == 2
        assert task.metadata["priority"] == "high"


class TestCodebaseContext:
    """Tests for CodebaseContext dataclass."""

    def test_creates_minimal_codebase_context(self):
        """Should create codebase context with defaults."""
        codebase = CodebaseContext()

        assert codebase.detected_stack == "unknown"
        assert codebase.existing_patterns == []
        assert codebase.external_services == []

    def test_creates_full_codebase_context(self):
        """Should create codebase context with all fields."""
        codebase = CodebaseContext(
            detected_stack="react",
            existing_patterns=["Repository pattern", "Factory pattern"],
            external_services=["Stripe", "SendGrid"],
            tech_inventory={"data_fetching": ["React Query"]}
        )

        assert codebase.detected_stack == "react"
        assert len(codebase.existing_patterns) == 2
        assert len(codebase.external_services) == 2
        assert "React Query" in codebase.tech_inventory["data_fetching"]
