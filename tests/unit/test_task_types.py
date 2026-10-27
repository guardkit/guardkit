"""
Comprehensive Test Suite for Task Type and Quality Gate Profile Models

Tests task type enumeration, quality gate profile configuration, default profile
registry, and profile lookup functionality.

Coverage Target: >=90%
Test Count: 42+ tests
"""

import logging

import pytest
from guardkit.models.task_types import (
    TaskType,
    QualityGateProfile,
    DEFAULT_PROFILES,
    TASK_TYPE_ALIASES,
    get_profile,
    normalise_task_type,
)


# ============================================================================
# 1. TaskType Enum Tests (6 tests)
# ============================================================================

class TestTaskTypeEnum:
    """Test TaskType enumeration."""

    def test_task_type_enum_has_eleven_values(self):
        """Test that TaskType enum has exactly 11 values.

        JOIN-1 (DF-016 §6(a)) added GLUE + WIRING to the prior 9.
        """
        assert len(TaskType) == 11

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

    def test_task_type_declarative_value(self):
        """Test DECLARATIVE task type value."""
        assert TaskType.DECLARATIVE.value == "declarative"

    def test_task_type_operator_handoff_value(self):
        """Test OPERATOR_HANDOFF task type value."""
        assert TaskType.OPERATOR_HANDOFF.value == "operator_handoff"

    def test_task_type_glue_value(self):
        """Test GLUE task type value (JOIN-1 / DF-016 §6(a))."""
        assert TaskType.GLUE.value == "glue"

    def test_task_type_wiring_value(self):
        """Test WIRING task type value (JOIN-1 / DF-016 §6(a))."""
        assert TaskType.WIRING.value == "wiring"

    def test_task_type_enum_lookup_by_value(self):
        """Test looking up enum members by value."""
        assert TaskType("scaffolding") == TaskType.SCAFFOLDING
        assert TaskType("feature") == TaskType.FEATURE
        assert TaskType("infrastructure") == TaskType.INFRASTRUCTURE
        assert TaskType("documentation") == TaskType.DOCUMENTATION
        assert TaskType("testing") == TaskType.TESTING
        assert TaskType("refactor") == TaskType.REFACTOR
        assert TaskType("declarative") == TaskType.DECLARATIVE
        assert TaskType("glue") == TaskType.GLUE
        assert TaskType("wiring") == TaskType.WIRING
        assert TaskType("operator_handoff") == TaskType.OPERATOR_HANDOFF


# ============================================================================
# 2. QualityGateProfile Creation Tests (8 tests)
# ============================================================================

class TestQualityGateProfileCreation:
    """Test creating QualityGateProfile instances."""

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

# ============================================================================
# 3. QualityGateProfile Validation Tests (10 tests)
# ============================================================================

# ============================================================================
# 4. QualityGateProfile.for_type() Tests (4 tests)
# ============================================================================

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

# ============================================================================
# 6. get_profile() Function Tests (8 tests)
# ============================================================================

class TestGetProfile:
    """Test get_profile() function."""

    def test_get_profile_with_documentation(self):
        """Test get_profile with DOCUMENTATION type."""
        profile = get_profile(TaskType.DOCUMENTATION)
        assert profile.tests_required is False

# ============================================================================
# 7. Backward Compatibility Tests (2 tests)
# ============================================================================

class TestBackwardCompatibility:
    """Test backward compatibility with task_type field."""

    def test_old_tasks_without_task_type_use_feature_gates(self):
        """Test that old tasks without task_type field get FEATURE gates."""
        # This simulates backward compatibility for existing tasks
        # that don't have the task_type field set
        profile = get_profile(None)  # Simulating missing task_type
        assert profile == DEFAULT_PROFILES[TaskType.FEATURE]


# ============================================================================
# 8. Profile Equality and Immutability Tests (2 tests)
# ============================================================================

# ============================================================================
# 9. Integration Tests (3 tests)
# ============================================================================

# ============================================================================
# 10. Seam Test Recommendation Tests (TASK-SFT-009)
# ============================================================================

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

    def test_default_profiles_contains_integration(self):
        """Test DEFAULT_PROFILES includes INTEGRATION entry."""
        assert TaskType.INTEGRATION in DEFAULT_PROFILES

# ============================================================================
# 12. normalise_task_type() Tests (TASK-FIX-7534)
# ============================================================================

class TestNormaliseTaskType:
    """Test normalise_task_type() function."""

    @pytest.mark.parametrize("canonical", [t.value for t in TaskType])
    def test_canonical_values_pass_through(self, canonical):
        """Test that canonical enum values are returned unchanged."""
        assert normalise_task_type(canonical) == canonical

    @pytest.mark.parametrize(
        "alias,expected",
        [
            ("implementation", "feature"),
            ("bug-fix", "feature"),
            ("bug_fix", "feature"),
            ("enhancement", "feature"),
            ("benchmark", "testing"),
            ("research", "documentation"),
            ("config", "declarative"),
            ("dto", "declarative"),
        ],
    )
    def test_known_aliases_resolve(self, alias, expected):
        """Test that known aliases are resolved to canonical values."""
        assert normalise_task_type(alias) == expected

    def test_all_aliases_covered(self):
        """Verify test covers every entry in TASK_TYPE_ALIASES."""
        for alias, task_type in TASK_TYPE_ALIASES.items():
            assert normalise_task_type(alias) == task_type.value

    def test_unknown_value_defaults_to_feature(self):
        """Test that unknown task_type defaults to 'feature'."""
        assert normalise_task_type("banana") == "feature"

    def test_unknown_value_logs_warning(self, caplog):
        """Test that unknown task_type logs a warning."""
        with caplog.at_level(logging.WARNING, logger="guardkit.models.task_types"):
            normalise_task_type("banana")
        assert "Unknown task_type 'banana'" in caplog.text

    def test_alias_logs_info(self, caplog):
        """Test that alias resolution logs an info message."""
        with caplog.at_level(logging.INFO, logger="guardkit.models.task_types"):
            normalise_task_type("enhancement")
        assert "Normalised task_type 'enhancement' -> 'feature'" in caplog.text

    def test_canonical_value_does_not_log(self, caplog):
        """Test that canonical values do not produce log messages."""
        with caplog.at_level(logging.DEBUG, logger="guardkit.models.task_types"):
            normalise_task_type("feature")
        assert caplog.text == ""

    def test_normalise_task_type_declarative(self):
        """Test that 'declarative' canonical value passes through."""
        assert normalise_task_type("declarative") == "declarative"


# ============================================================================
# 13. DECLARATIVE Task Type Tests (TASK-IMP-D4A0)
# ============================================================================

class TestDeclarativeTaskType:
    """Test DECLARATIVE task type enum, profile, and lookup."""

    def test_declarative_enum_value(self):
        """TaskType.DECLARATIVE exists with value 'declarative'."""
        assert TaskType.DECLARATIVE.value == "declarative"

    def test_declarative_enum_lookup_by_value(self):
        """Test looking up DECLARATIVE by value string."""
        assert TaskType("declarative") == TaskType.DECLARATIVE

    def test_declarative_profile_differs_from_scaffolding(self):
        """DECLARATIVE requires tests while SCAFFOLDING does not."""
        declarative = get_profile(TaskType.DECLARATIVE)
        scaffolding = get_profile(TaskType.SCAFFOLDING)
        assert declarative.tests_required is True
        assert scaffolding.tests_required is False

# ============================================================================
# 14. OPERATOR_HANDOFF Task Type Tests (TASK-FPTC-002)
# ============================================================================

class TestOperatorHandoffTaskType:
    """Test OPERATOR_HANDOFF task type enum and skip-everything profile."""

    def test_operator_handoff_enum_value(self):
        """AC-FPTC-002-01: TaskType.OPERATOR_HANDOFF exists with value 'operator_handoff'."""
        assert TaskType.OPERATOR_HANDOFF.value == "operator_handoff"

    def test_operator_handoff_constructs_without_error(self):
        """AC-FPTC-002-03: TaskType('operator_handoff') constructs without error."""
        assert TaskType("operator_handoff") == TaskType.OPERATOR_HANDOFF

    def test_operator_handoff_not_in_aliases(self):
        """Implementation note: OPERATOR_HANDOFF must not have fuzzy alias matches."""
        # The value is intentionally explicit; aliases like "handoff" or
        # "operator-handoff" should not silently resolve to it.
        for alias_value in TASK_TYPE_ALIASES.values():
            assert alias_value != TaskType.OPERATOR_HANDOFF

    def test_normalise_operator_handoff_passes_through(self):
        """Canonical 'operator_handoff' string passes through normalise_task_type unchanged."""
        assert normalise_task_type("operator_handoff") == "operator_handoff"

    def test_default_profiles_contains_operator_handoff(self):
        """DEFAULT_PROFILES registry includes OPERATOR_HANDOFF entry."""
        assert TaskType.OPERATOR_HANDOFF in DEFAULT_PROFILES


# ============================================================================
# 15. GLUE / WIRING Task Type Tests (JOIN-1 / DF-016 §6(a))
# ============================================================================

class TestGlueWiringTaskType:
    """Test the DF-016 §6(a) glue/wiring task class: enum, strict profile, lookup.

    DF-016 §6(a) resolution: guardkit marks glue-authoring tasks with an
    explicit `glue`/`wiring` class so the clause-5 Coach posture keys
    mechanically. Consumer: FEAT-DF12 DFEM-013's oracle-green `glue` cutover.
    """

    # The strictest posture — clause 5 "highest-risk task class".
    _STRICT_FIELDS = dict(
        arch_review_required=True,
        arch_review_threshold=60,
        coverage_required=True,
        coverage_threshold=80.0,
        tests_required=True,
        plan_audit_required=True,
        zero_test_blocking=True,
        seam_tests_recommended=True,
    )

    def test_glue_enum_value(self):
        """TaskType.GLUE exists with value 'glue'."""
        assert TaskType.GLUE.value == "glue"

    def test_wiring_enum_value(self):
        """TaskType.WIRING exists with value 'wiring'."""
        assert TaskType.WIRING.value == "wiring"

    def test_glue_enum_lookup_by_value(self):
        """TaskType('glue') constructs without error."""
        assert TaskType("glue") == TaskType.GLUE

    def test_wiring_enum_lookup_by_value(self):
        """TaskType('wiring') constructs without error."""
        assert TaskType("wiring") == TaskType.WIRING

    @pytest.mark.parametrize("task_type", [TaskType.GLUE, TaskType.WIRING])
    def test_default_profiles_contains_glue_wiring(self, task_type):
        """DEFAULT_PROFILES registry includes GLUE and WIRING entries."""
        assert task_type in DEFAULT_PROFILES

    def test_glue_wiring_share_one_posture(self):
        """DF-016 names 'glue/wiring' ONE class — the two profiles are equal."""
        assert DEFAULT_PROFILES[TaskType.GLUE] == DEFAULT_PROFILES[TaskType.WIRING]

    @pytest.mark.parametrize("value", ["glue", "wiring"])
    def test_normalise_glue_wiring_passes_through(self, value):
        """Canonical 'glue'/'wiring' strings pass through normalise unchanged."""
        assert normalise_task_type(value) == value

    @pytest.mark.parametrize("value", ["glue", "wiring"])
    def test_glue_wiring_not_aliases(self, value):
        """GLUE/WIRING are canonical enum values, not legacy aliases."""
        assert value not in TASK_TYPE_ALIASES


class TestTestsRequiredByType:
    """The one profile setting left: whether the project's tests run for a type."""

    @pytest.mark.parametrize(
        "task_type,expected",
        [
            (TaskType.FEATURE, True),
            (TaskType.REFACTOR, True),
            (TaskType.TESTING, True),
            (TaskType.INFRASTRUCTURE, True),
            (TaskType.INTEGRATION, True),
            (TaskType.DECLARATIVE, True),
            (TaskType.GLUE, True),
            (TaskType.WIRING, True),
            (TaskType.SCAFFOLDING, False),
            (TaskType.DOCUMENTATION, False),
            (TaskType.OPERATOR_HANDOFF, False),
        ],
    )
    def test_tests_required(self, task_type, expected):
        assert get_profile(task_type).tests_required is expected
        assert QualityGateProfile.for_type(task_type).tests_required is expected

    def test_no_type_means_feature(self):
        assert get_profile(None) == get_profile(TaskType.FEATURE)
