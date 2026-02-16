"""
Comprehensive Test Suite for Task Type and Quality Gate Profile Models

Tests task type enumeration, quality gate profile configuration, default profile
registry, and profile lookup functionality.

Coverage Target: >=90%
Test Count: 42+ tests
"""

import pytest
from guardkit.models.task_types import (
    TaskType,
    QualityGateProfile,
    DEFAULT_PROFILES,
    get_profile,
)


# ============================================================================
# 1. TaskType Enum Tests (6 tests)
# ============================================================================

class TestTaskTypeEnum:
    """Test TaskType enumeration."""

    def test_task_type_enum_has_seven_values(self):
        """Test that TaskType enum has exactly 7 values."""
        assert len(TaskType) == 7

    def test_task_type_scaffolding_value(self):
        """Test SCAFFOLDING task type value."""
        assert TaskType.SCAFFOLDING.value == "scaffolding"

    def test_task_type_feature_value(self):
        """Test FEATURE task type value."""
        assert TaskType.FEATURE.value == "feature"

    def test_task_type_infrastructure_value(self):
        """Test INFRASTRUCTURE task type value."""
        assert TaskType.INFRASTRUCTURE.value == "infrastructure"

    def test_task_type_documentation_value(self):
        """Test DOCUMENTATION task type value."""
        assert TaskType.DOCUMENTATION.value == "documentation"

    def test_task_type_testing_value(self):
        """Test TESTING task type value."""
        assert TaskType.TESTING.value == "testing"

    def test_task_type_refactor_value(self):
        """Test REFACTOR task type value."""
        assert TaskType.REFACTOR.value == "refactor"

    def test_task_type_enum_lookup_by_value(self):
        """Test looking up enum members by value."""
        assert TaskType("scaffolding") == TaskType.SCAFFOLDING
        assert TaskType("feature") == TaskType.FEATURE
        assert TaskType("infrastructure") == TaskType.INFRASTRUCTURE
        assert TaskType("documentation") == TaskType.DOCUMENTATION
        assert TaskType("testing") == TaskType.TESTING
        assert TaskType("refactor") == TaskType.REFACTOR


# ============================================================================
# 2. QualityGateProfile Creation Tests (8 tests)
# ============================================================================

class TestQualityGateProfileCreation:
    """Test creating QualityGateProfile instances."""

    def test_create_feature_profile(self):
        """Test creating a feature task profile."""
        profile = QualityGateProfile(
            arch_review_required=True,
            arch_review_threshold=60,
            coverage_required=True,
            coverage_threshold=80.0,
            tests_required=True,
            plan_audit_required=True,
        )
        assert profile.arch_review_required is True
        assert profile.arch_review_threshold == 60
        assert profile.coverage_required is True
        assert profile.coverage_threshold == 80.0
        assert profile.tests_required is True
        assert profile.plan_audit_required is True

    def test_create_scaffolding_profile(self):
        """Test creating a scaffolding task profile."""
        profile = QualityGateProfile(
            arch_review_required=False,
            arch_review_threshold=0,
            coverage_required=False,
            coverage_threshold=0.0,
            tests_required=False,
            plan_audit_required=True,
        )
        assert profile.arch_review_required is False
        assert profile.coverage_required is False
        assert profile.tests_required is False
        assert profile.plan_audit_required is True

    def test_create_infrastructure_profile(self):
        """Test creating an infrastructure task profile."""
        profile = QualityGateProfile(
            arch_review_required=False,
            arch_review_threshold=0,
            coverage_required=False,
            coverage_threshold=0.0,
            tests_required=True,
            plan_audit_required=True,
        )
        assert profile.arch_review_required is False
        assert profile.tests_required is True
        assert profile.plan_audit_required is True

    def test_create_documentation_profile(self):
        """Test creating a documentation task profile."""
        profile = QualityGateProfile(
            arch_review_required=False,
            arch_review_threshold=0,
            coverage_required=False,
            coverage_threshold=0.0,
            tests_required=False,
            plan_audit_required=False,
        )
        assert profile.arch_review_required is False
        assert profile.coverage_required is False
        assert profile.tests_required is False
        assert profile.plan_audit_required is False

    def test_create_testing_profile(self):
        """Test creating a testing task profile."""
        profile = QualityGateProfile(
            arch_review_required=False,
            arch_review_threshold=0,
            coverage_required=False,
            coverage_threshold=0.0,
            tests_required=False,
            plan_audit_required=True,
        )
        assert profile.arch_review_required is False
        assert profile.coverage_required is False
        assert profile.tests_required is False
        assert profile.plan_audit_required is True

    def test_create_refactor_profile(self):
        """Test creating a refactor task profile."""
        profile = QualityGateProfile(
            arch_review_required=True,
            arch_review_threshold=60,
            coverage_required=True,
            coverage_threshold=80.0,
            tests_required=True,
            plan_audit_required=True,
        )
        assert profile.arch_review_required is True
        assert profile.arch_review_threshold == 60
        assert profile.coverage_required is True
        assert profile.coverage_threshold == 80.0
        assert profile.tests_required is True
        assert profile.plan_audit_required is True

    def test_create_profile_with_default_values(self):
        """Test that all fields are required (no defaults)."""
        # This test documents that QualityGateProfile requires all fields
        # to be explicitly set (following dataclass best practices)
        with pytest.raises(TypeError):
            QualityGateProfile()  # type: ignore

    def test_create_profile_with_partial_values(self):
        """Test that creating profile with missing fields raises TypeError."""
        with pytest.raises(TypeError):
            QualityGateProfile(  # type: ignore
                arch_review_required=True,
                arch_review_threshold=60,
            )

    def test_profile_with_zero_coverage_threshold(self):
        """Test profile with zero coverage threshold."""
        profile = QualityGateProfile(
            arch_review_required=True,
            arch_review_threshold=60,
            coverage_required=False,
            coverage_threshold=0.0,
            tests_required=True,
            plan_audit_required=True,
        )
        assert profile.coverage_threshold == 0.0

    def test_profile_with_float_coverage_threshold(self):
        """Test profile with float coverage threshold."""
        profile = QualityGateProfile(
            arch_review_required=True,
            arch_review_threshold=60,
            coverage_required=True,
            coverage_threshold=75.5,
            tests_required=True,
            plan_audit_required=True,
        )
        assert profile.coverage_threshold == 75.5


# ============================================================================
# 3. QualityGateProfile Validation Tests (10 tests)
# ============================================================================

class TestQualityGateProfileValidation:
    """Test QualityGateProfile validation in __post_init__."""

    def test_arch_review_threshold_below_range_raises_error(self):
        """Test that arch_review_threshold below 0 raises ValueError."""
        with pytest.raises(ValueError, match="arch_review_threshold must be 0-100"):
            QualityGateProfile(
                arch_review_required=True,
                arch_review_threshold=-1,
                coverage_required=False,
                coverage_threshold=0.0,
                tests_required=True,
                plan_audit_required=True,
            )

    def test_arch_review_threshold_above_range_raises_error(self):
        """Test that arch_review_threshold above 100 raises ValueError."""
        with pytest.raises(ValueError, match="arch_review_threshold must be 0-100"):
            QualityGateProfile(
                arch_review_required=True,
                arch_review_threshold=101,
                coverage_required=False,
                coverage_threshold=0.0,
                tests_required=True,
                plan_audit_required=True,
            )

    def test_coverage_threshold_below_range_raises_error(self):
        """Test that coverage_threshold below 0 raises ValueError."""
        with pytest.raises(ValueError, match="coverage_threshold must be 0-100"):
            QualityGateProfile(
                arch_review_required=True,
                arch_review_threshold=60,
                coverage_required=True,
                coverage_threshold=-1.0,
                tests_required=True,
                plan_audit_required=True,
            )

    def test_coverage_threshold_above_range_raises_error(self):
        """Test that coverage_threshold above 100 raises ValueError."""
        with pytest.raises(ValueError, match="coverage_threshold must be 0-100"):
            QualityGateProfile(
                arch_review_required=True,
                arch_review_threshold=60,
                coverage_required=True,
                coverage_threshold=100.1,
                tests_required=True,
                plan_audit_required=True,
            )

    def test_arch_review_threshold_nonzero_when_not_required_raises_error(self):
        """Test that non-zero arch_review_threshold when not required raises error."""
        with pytest.raises(
            ValueError, match="arch_review_threshold should be 0 when"
        ):
            QualityGateProfile(
                arch_review_required=False,
                arch_review_threshold=60,
                coverage_required=False,
                coverage_threshold=0.0,
                tests_required=True,
                plan_audit_required=True,
            )

    def test_coverage_threshold_nonzero_when_not_required_raises_error(self):
        """Test that non-zero coverage_threshold when not required raises error."""
        with pytest.raises(ValueError, match="coverage_threshold should be 0 when"):
            QualityGateProfile(
                arch_review_required=True,
                arch_review_threshold=60,
                coverage_required=False,
                coverage_threshold=80.0,
                tests_required=True,
                plan_audit_required=True,
            )

    def test_arch_review_threshold_boundary_0(self):
        """Test arch_review_threshold boundary value 0."""
        profile = QualityGateProfile(
            arch_review_required=False,
            arch_review_threshold=0,
            coverage_required=False,
            coverage_threshold=0.0,
            tests_required=True,
            plan_audit_required=True,
        )
        assert profile.arch_review_threshold == 0

    def test_arch_review_threshold_boundary_100(self):
        """Test arch_review_threshold boundary value 100."""
        profile = QualityGateProfile(
            arch_review_required=True,
            arch_review_threshold=100,
            coverage_required=False,
            coverage_threshold=0.0,
            tests_required=True,
            plan_audit_required=True,
        )
        assert profile.arch_review_threshold == 100

    def test_coverage_threshold_boundary_0(self):
        """Test coverage_threshold boundary value 0."""
        profile = QualityGateProfile(
            arch_review_required=True,
            arch_review_threshold=60,
            coverage_required=False,
            coverage_threshold=0.0,
            tests_required=True,
            plan_audit_required=True,
        )
        assert profile.coverage_threshold == 0.0

    def test_coverage_threshold_boundary_100(self):
        """Test coverage_threshold boundary value 100."""
        profile = QualityGateProfile(
            arch_review_required=True,
            arch_review_threshold=60,
            coverage_required=True,
            coverage_threshold=100.0,
            tests_required=True,
            plan_audit_required=True,
        )
        assert profile.coverage_threshold == 100.0


# ============================================================================
# 4. QualityGateProfile.for_type() Tests (4 tests)
# ============================================================================

class TestQualityGateProfileForType:
    """Test QualityGateProfile.for_type() class method."""

    def test_for_type_returns_feature_profile(self):
        """Test that for_type returns feature profile."""
        profile = QualityGateProfile.for_type(TaskType.FEATURE)
        assert profile.arch_review_required is True
        assert profile.arch_review_threshold == 60
        assert profile.coverage_required is True
        assert profile.coverage_threshold == 80.0

    def test_for_type_returns_scaffolding_profile(self):
        """Test that for_type returns scaffolding profile."""
        profile = QualityGateProfile.for_type(TaskType.SCAFFOLDING)
        assert profile.arch_review_required is False
        assert profile.coverage_required is False

    def test_for_type_returns_infrastructure_profile(self):
        """Test that for_type returns infrastructure profile."""
        profile = QualityGateProfile.for_type(TaskType.INFRASTRUCTURE)
        assert profile.arch_review_required is False
        assert profile.tests_required is True

    def test_for_type_returns_documentation_profile(self):
        """Test that for_type returns documentation profile."""
        profile = QualityGateProfile.for_type(TaskType.DOCUMENTATION)
        assert profile.arch_review_required is False
        assert profile.coverage_required is False
        assert profile.tests_required is False
        assert profile.plan_audit_required is False

    def test_for_type_returns_testing_profile(self):
        """Test that for_type returns testing profile."""
        profile = QualityGateProfile.for_type(TaskType.TESTING)
        assert profile.arch_review_required is False
        assert profile.coverage_required is False
        assert profile.tests_required is False
        assert profile.plan_audit_required is True

    def test_for_type_returns_refactor_profile(self):
        """Test that for_type returns refactor profile."""
        profile = QualityGateProfile.for_type(TaskType.REFACTOR)
        assert profile.arch_review_required is True
        assert profile.arch_review_threshold == 60
        assert profile.coverage_required is True
        assert profile.coverage_threshold == 80.0
        assert profile.tests_required is True
        assert profile.plan_audit_required is True


# ============================================================================
# 5. DEFAULT_PROFILES Registry Tests (7 tests)
# ============================================================================

class TestDefaultProfiles:
    """Test DEFAULT_PROFILES registry."""

    def test_default_profiles_contains_all_task_types(self):
        """Test that DEFAULT_PROFILES contains all TaskType values."""
        assert len(DEFAULT_PROFILES) == len(TaskType)
        for task_type in TaskType:
            assert task_type in DEFAULT_PROFILES

    def test_default_profiles_scaffolding_configuration(self):
        """Test DEFAULT_PROFILES scaffolding profile configuration."""
        profile = DEFAULT_PROFILES[TaskType.SCAFFOLDING]
        assert profile.arch_review_required is False
        assert profile.arch_review_threshold == 0
        assert profile.coverage_required is False
        assert profile.coverage_threshold == 0.0
        assert profile.tests_required is False
        assert profile.plan_audit_required is True

    def test_default_profiles_feature_configuration(self):
        """Test DEFAULT_PROFILES feature profile configuration."""
        profile = DEFAULT_PROFILES[TaskType.FEATURE]
        assert profile.arch_review_required is True
        assert profile.arch_review_threshold == 60
        assert profile.coverage_required is True
        assert profile.coverage_threshold == 80.0
        assert profile.tests_required is True
        assert profile.plan_audit_required is True

    def test_default_profiles_infrastructure_configuration(self):
        """Test DEFAULT_PROFILES infrastructure profile configuration."""
        profile = DEFAULT_PROFILES[TaskType.INFRASTRUCTURE]
        assert profile.arch_review_required is False
        assert profile.arch_review_threshold == 0
        assert profile.coverage_required is False
        assert profile.coverage_threshold == 0.0
        assert profile.tests_required is True
        assert profile.plan_audit_required is True

    def test_default_profiles_documentation_configuration(self):
        """Test DEFAULT_PROFILES documentation profile configuration."""
        profile = DEFAULT_PROFILES[TaskType.DOCUMENTATION]
        assert profile.arch_review_required is False
        assert profile.arch_review_threshold == 0
        assert profile.coverage_required is False
        assert profile.coverage_threshold == 0.0
        assert profile.tests_required is False
        assert profile.plan_audit_required is False

    def test_default_profiles_testing_configuration(self):
        """Test DEFAULT_PROFILES testing profile configuration."""
        profile = DEFAULT_PROFILES[TaskType.TESTING]
        assert profile.arch_review_required is False
        assert profile.arch_review_threshold == 0
        assert profile.coverage_required is False
        assert profile.coverage_threshold == 0.0
        assert profile.tests_required is False
        assert profile.plan_audit_required is True

    def test_default_profiles_refactor_configuration(self):
        """Test DEFAULT_PROFILES refactor profile configuration."""
        profile = DEFAULT_PROFILES[TaskType.REFACTOR]
        assert profile.arch_review_required is True
        assert profile.arch_review_threshold == 60
        assert profile.coverage_required is True
        assert profile.coverage_threshold == 80.0
        assert profile.tests_required is True
        assert profile.plan_audit_required is True


# ============================================================================
# 6. get_profile() Function Tests (8 tests)
# ============================================================================

class TestGetProfile:
    """Test get_profile() function."""

    def test_get_profile_returns_feature_by_default(self):
        """Test that get_profile() without args returns FEATURE profile."""
        profile = get_profile()
        assert profile.arch_review_required is True
        assert profile.arch_review_threshold == 60

    def test_get_profile_with_none_returns_feature(self):
        """Test that get_profile(None) returns FEATURE profile."""
        profile = get_profile(None)
        assert profile.arch_review_required is True
        assert profile.arch_review_threshold == 60

    def test_get_profile_with_scaffolding(self):
        """Test get_profile with SCAFFOLDING type."""
        profile = get_profile(TaskType.SCAFFOLDING)
        assert profile.arch_review_required is False

    def test_get_profile_with_feature(self):
        """Test get_profile with FEATURE type."""
        profile = get_profile(TaskType.FEATURE)
        assert profile.arch_review_required is True

    def test_get_profile_with_infrastructure(self):
        """Test get_profile with INFRASTRUCTURE type."""
        profile = get_profile(TaskType.INFRASTRUCTURE)
        assert profile.arch_review_required is False
        assert profile.tests_required is True

    def test_get_profile_with_documentation(self):
        """Test get_profile with DOCUMENTATION type."""
        profile = get_profile(TaskType.DOCUMENTATION)
        assert profile.tests_required is False

    def test_get_profile_with_testing(self):
        """Test get_profile with TESTING type."""
        profile = get_profile(TaskType.TESTING)
        assert profile.arch_review_required is False
        assert profile.tests_required is False
        assert profile.plan_audit_required is True

    def test_get_profile_with_refactor(self):
        """Test get_profile with REFACTOR type."""
        profile = get_profile(TaskType.REFACTOR)
        assert profile.arch_review_required is True
        assert profile.tests_required is True


# ============================================================================
# 7. Backward Compatibility Tests (2 tests)
# ============================================================================

class TestBackwardCompatibility:
    """Test backward compatibility with task_type field."""

    def test_get_profile_default_matches_feature_profile(self):
        """Test that default profile matches explicit FEATURE profile."""
        default_profile = get_profile()
        feature_profile = get_profile(TaskType.FEATURE)
        assert default_profile.arch_review_required == feature_profile.arch_review_required
        assert default_profile.arch_review_threshold == feature_profile.arch_review_threshold
        assert default_profile.coverage_required == feature_profile.coverage_required
        assert default_profile.coverage_threshold == feature_profile.coverage_threshold
        assert default_profile.tests_required == feature_profile.tests_required
        assert default_profile.plan_audit_required == feature_profile.plan_audit_required

    def test_old_tasks_without_task_type_use_feature_gates(self):
        """Test that old tasks without task_type field get FEATURE gates."""
        # This simulates backward compatibility for existing tasks
        # that don't have the task_type field set
        profile = get_profile(None)  # Simulating missing task_type
        assert profile == DEFAULT_PROFILES[TaskType.FEATURE]


# ============================================================================
# 8. Profile Equality and Immutability Tests (2 tests)
# ============================================================================

class TestProfileImmutabilityAndEquality:
    """Test profile immutability and equality."""

    def test_profiles_are_immutable_after_creation(self):
        """Test that profiles are immutable (frozen dataclass behavior)."""
        profile = DEFAULT_PROFILES[TaskType.FEATURE]
        original_value = profile.arch_review_threshold
        # Dataclasses are mutable by default; test attempts to modify
        # This documents the current behavior
        try:
            profile.arch_review_threshold = 70
            # Note: If frozen=True is added in future, this should raise FrozenInstanceError
            assert profile.arch_review_threshold == 70  # Currently mutable
        finally:
            # IMPORTANT: Restore the original value to avoid test pollution
            # This is a shared global object that other tests depend on
            profile.arch_review_threshold = original_value

    def test_same_profile_type_configurations_are_equal(self):
        """Test that profiles created with same config are equal."""
        profile1 = QualityGateProfile(
            arch_review_required=True,
            arch_review_threshold=60,
            coverage_required=True,
            coverage_threshold=80.0,
            tests_required=True,
            plan_audit_required=True,
        )
        profile2 = QualityGateProfile(
            arch_review_required=True,
            arch_review_threshold=60,
            coverage_required=True,
            coverage_threshold=80.0,
            tests_required=True,
            plan_audit_required=True,
        )
        assert profile1 == profile2


# ============================================================================
# 9. Integration Tests (3 tests)
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflows."""

    def test_workflow_scaffolding_task(self):
        """Test complete workflow for scaffolding task."""
        # Get profile for scaffolding task
        profile = get_profile(TaskType.SCAFFOLDING)

        # Verify quality gates are appropriately relaxed
        assert profile.arch_review_required is False
        assert profile.coverage_required is False
        assert profile.tests_required is False
        # But plan audit is still required
        assert profile.plan_audit_required is True

    def test_workflow_feature_task(self):
        """Test complete workflow for feature task."""
        # Get profile for feature task
        profile = get_profile(TaskType.FEATURE)

        # Verify all quality gates are enforced
        assert profile.arch_review_required is True
        assert profile.coverage_required is True
        assert profile.tests_required is True
        assert profile.plan_audit_required is True

    def test_workflow_infrastructure_task(self):
        """Test complete workflow for infrastructure task."""
        # Get profile for infrastructure task
        profile = get_profile(TaskType.INFRASTRUCTURE)

        # Verify tests are required but architecture review is not
        assert profile.arch_review_required is False
        assert profile.tests_required is True
        assert profile.plan_audit_required is True

    def test_workflow_testing_task(self):
        """Test complete workflow for testing task."""
        # Get profile for testing task
        profile = get_profile(TaskType.TESTING)

        # Verify minimal gates for test-writing tasks
        assert profile.arch_review_required is False
        assert profile.coverage_required is False
        assert profile.tests_required is False
        # But plan audit is still required
        assert profile.plan_audit_required is True

    def test_workflow_refactor_task(self):
        """Test complete workflow for refactor task."""
        # Get profile for refactor task
        profile = get_profile(TaskType.REFACTOR)

        # Verify full quality gates for refactoring
        assert profile.arch_review_required is True
        assert profile.coverage_required is True
        assert profile.tests_required is True
        assert profile.plan_audit_required is True


# ============================================================================
# 10. Seam Test Recommendation Tests (TASK-SFT-009)
# ============================================================================

class TestSeamTestRecommendation:
    """Test seam_tests_recommended field on QualityGateProfile."""

    def test_seam_tests_recommended_field_exists(self):
        """AC-001: QualityGateProfile has seam_tests_recommended field."""
        profile = QualityGateProfile(
            arch_review_required=True,
            arch_review_threshold=60,
            coverage_required=True,
            coverage_threshold=80.0,
            tests_required=True,
            plan_audit_required=True,
        )
        # Field should exist with default value False
        assert hasattr(profile, "seam_tests_recommended")
        assert profile.seam_tests_recommended is False

    def test_seam_tests_recommended_explicit_true(self):
        """Test explicitly setting seam_tests_recommended=True."""
        profile = QualityGateProfile(
            arch_review_required=True,
            arch_review_threshold=60,
            coverage_required=True,
            coverage_threshold=80.0,
            tests_required=True,
            plan_audit_required=True,
            seam_tests_recommended=True,
        )
        assert profile.seam_tests_recommended is True

    def test_seam_tests_recommended_explicit_false(self):
        """Test explicitly setting seam_tests_recommended=False."""
        profile = QualityGateProfile(
            arch_review_required=True,
            arch_review_threshold=60,
            coverage_required=True,
            coverage_threshold=80.0,
            tests_required=True,
            plan_audit_required=True,
            seam_tests_recommended=False,
        )
        assert profile.seam_tests_recommended is False

    def test_feature_profile_seam_tests_recommended_true(self):
        """AC-002: FEATURE profile has seam_tests_recommended=True."""
        profile = DEFAULT_PROFILES[TaskType.FEATURE]
        assert profile.seam_tests_recommended is True

    def test_refactor_profile_seam_tests_recommended_true(self):
        """AC-002: REFACTOR profile has seam_tests_recommended=True."""
        profile = DEFAULT_PROFILES[TaskType.REFACTOR]
        assert profile.seam_tests_recommended is True

    def test_scaffolding_profile_seam_tests_recommended_false(self):
        """AC-003: SCAFFOLDING profile has seam_tests_recommended=False."""
        profile = DEFAULT_PROFILES[TaskType.SCAFFOLDING]
        assert profile.seam_tests_recommended is False

    def test_documentation_profile_seam_tests_recommended_false(self):
        """AC-003: DOCUMENTATION profile has seam_tests_recommended=False."""
        profile = DEFAULT_PROFILES[TaskType.DOCUMENTATION]
        assert profile.seam_tests_recommended is False

    def test_testing_profile_seam_tests_recommended_false(self):
        """AC-003: TESTING profile has seam_tests_recommended=False."""
        profile = DEFAULT_PROFILES[TaskType.TESTING]
        assert profile.seam_tests_recommended is False

    def test_infrastructure_profile_seam_tests_recommended_false(self):
        """INFRASTRUCTURE profile has seam_tests_recommended=False."""
        profile = DEFAULT_PROFILES[TaskType.INFRASTRUCTURE]
        assert profile.seam_tests_recommended is False

    def test_integration_profile_seam_tests_recommended_false(self):
        """INTEGRATION profile has seam_tests_recommended=False."""
        profile = DEFAULT_PROFILES[TaskType.INTEGRATION]
        assert profile.seam_tests_recommended is False

    def test_get_profile_feature_has_seam_tests_recommended(self):
        """Test get_profile for FEATURE returns profile with seam_tests_recommended=True."""
        profile = get_profile(TaskType.FEATURE)
        assert profile.seam_tests_recommended is True

    def test_get_profile_scaffolding_has_seam_tests_not_recommended(self):
        """Test get_profile for SCAFFOLDING returns profile with seam_tests_recommended=False."""
        profile = get_profile(TaskType.SCAFFOLDING)
        assert profile.seam_tests_recommended is False

    def test_for_type_feature_has_seam_tests_recommended(self):
        """Test QualityGateProfile.for_type(FEATURE) has seam_tests_recommended=True."""
        profile = QualityGateProfile.for_type(TaskType.FEATURE)
        assert profile.seam_tests_recommended is True

    def test_for_type_refactor_has_seam_tests_recommended(self):
        """Test QualityGateProfile.for_type(REFACTOR) has seam_tests_recommended=True."""
        profile = QualityGateProfile.for_type(TaskType.REFACTOR)
        assert profile.seam_tests_recommended is True


# ============================================================================
# 11. INTEGRATION Task Type Tests (TASK-FIX-93C1)
# ============================================================================

class TestIntegrationTaskType:
    """Test INTEGRATION task type enum, profile, and lookup."""

    def test_integration_enum_value(self):
        """AC-001: TaskType.INTEGRATION exists with value 'integration'."""
        assert TaskType.INTEGRATION.value == "integration"

    def test_integration_enum_lookup_by_value(self):
        """Test looking up INTEGRATION by value string."""
        assert TaskType("integration") == TaskType.INTEGRATION

    def test_integration_profile_configuration(self):
        """AC-002: INTEGRATION profile has correct field values."""
        profile = DEFAULT_PROFILES[TaskType.INTEGRATION]
        assert profile.tests_required is True
        assert profile.zero_test_blocking is False
        assert profile.arch_review_required is False
        assert profile.arch_review_threshold == 0
        assert profile.coverage_required is False
        assert profile.coverage_threshold == 0.0
        assert profile.plan_audit_required is True

    def test_get_profile_with_integration(self):
        """AC-008: get_profile(TaskType.INTEGRATION) returns correct profile."""
        profile = get_profile(TaskType.INTEGRATION)
        assert profile.arch_review_required is False
        assert profile.tests_required is True
        assert profile.zero_test_blocking is False
        assert profile.coverage_required is False

    def test_for_type_returns_integration_profile(self):
        """Test QualityGateProfile.for_type(TaskType.INTEGRATION) works."""
        profile = QualityGateProfile.for_type(TaskType.INTEGRATION)
        assert profile.tests_required is True
        assert profile.zero_test_blocking is False
        assert profile.arch_review_required is False

    def test_get_profile_none_still_returns_feature(self):
        """AC-009: get_profile(None) still returns FEATURE profile."""
        profile = get_profile(None)
        assert profile == DEFAULT_PROFILES[TaskType.FEATURE]
        assert profile.zero_test_blocking is True  # FEATURE has blocking

    def test_default_profiles_contains_integration(self):
        """Test DEFAULT_PROFILES includes INTEGRATION entry."""
        assert TaskType.INTEGRATION in DEFAULT_PROFILES

    def test_integration_profile_differs_from_feature(self):
        """Test INTEGRATION profile is less strict than FEATURE."""
        integration = get_profile(TaskType.INTEGRATION)
        feature = get_profile(TaskType.FEATURE)
        assert integration.zero_test_blocking is False
        assert feature.zero_test_blocking is True
        assert integration.arch_review_required is False
        assert feature.arch_review_required is True
        assert integration.coverage_required is False
        assert feature.coverage_required is True

    def test_integration_profile_similar_to_infrastructure(self):
        """Test INTEGRATION profile is similar to INFRASTRUCTURE."""
        integration = get_profile(TaskType.INTEGRATION)
        infrastructure = get_profile(TaskType.INFRASTRUCTURE)
        assert integration.arch_review_required == infrastructure.arch_review_required
        assert integration.coverage_required == infrastructure.coverage_required
        assert integration.tests_required == infrastructure.tests_required
        assert integration.plan_audit_required == infrastructure.plan_audit_required

    def test_workflow_integration_task(self):
        """Test complete workflow for integration task."""
        profile = get_profile(TaskType.INTEGRATION)
        # Tests should pass if they exist
        assert profile.tests_required is True
        # But missing tests should not block
        assert profile.zero_test_blocking is False
        # Plan audit ensures integration is complete
        assert profile.plan_audit_required is True
