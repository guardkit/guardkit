"""
Unit tests for Graphiti group constants.

Tests the PROJECT_GROUPS and SYSTEM_GROUPS constants that organize knowledge
within a project namespace, and the derived PROJECT_GROUP_NAMES and
SYSTEM_GROUP_IDS lists used by GraphitiClient.

Test Coverage:
- PROJECT_GROUPS constant structure and content
- SYSTEM_GROUPS constant structure and content
- Derived list consistency (PROJECT_GROUP_NAMES, SYSTEM_GROUP_IDS)
- Group ID uniqueness validation
- Group description quality validation
"""

import pytest
from guardkit.integrations.graphiti.constants import (
    PROJECT_GROUPS,
    SYSTEM_GROUPS,
    PROJECT_GROUP_NAMES,
    SYSTEM_GROUP_IDS,
)


class TestProjectGroups:
    """Tests for PROJECT_GROUPS constant."""

    def test_project_groups_exists_and_is_dict(self):
        """
        PROJECT_GROUPS should exist and be a dictionary.

        This is the most basic requirement - the constant must be defined
        and be the correct type for mapping group IDs to descriptions.
        """
        assert isinstance(PROJECT_GROUPS, dict), "PROJECT_GROUPS must be a dict"

    def test_project_groups_contains_all_required_group_ids(self):
        """
        PROJECT_GROUPS should contain all 7 required group IDs.

        Per the unified specification, these are the standard group IDs
        for organizing project-specific knowledge:
        - project_overview: High-level purpose and goals
        - project_architecture: System architecture and patterns
        - feature_specs: Feature specifications and requirements
        - project_decisions: Architecture Decision Records (ADRs)
        - project_constraints: Constraints and limitations
        - domain_knowledge: Domain terminology and concepts
        - bdd_scenarios: BDD Gherkin scenarios
        """
        required_groups = {
            "project_overview",
            "project_architecture",
            "feature_specs",
            "project_decisions",
            "project_constraints",
            "domain_knowledge",
            "bdd_scenarios",
        }

        actual_groups = set(PROJECT_GROUPS.keys())

        assert required_groups.issubset(actual_groups), (
            f"PROJECT_GROUPS must contain at least these group IDs: {required_groups}. "
            f"Missing: {required_groups - actual_groups}"
        )

    def test_project_groups_all_values_are_non_empty_strings(self):
        """
        All PROJECT_GROUPS values should be non-empty string descriptions.

        Each group ID must have a meaningful description that explains
        what kind of knowledge belongs in that group.
        """
        for group_id, description in PROJECT_GROUPS.items():
            assert isinstance(description, str), (
                f"Group '{group_id}' description must be a string, "
                f"got {type(description)}"
            )
            assert len(description.strip()) > 0, (
                f"Group '{group_id}' description must be non-empty"
            )

    def test_project_groups_descriptions_are_meaningful(self):
        """
        PROJECT_GROUPS descriptions should be meaningful, not just the key name.

        A meaningful description should:
        - Not be just the group ID repeated
        - Not be a simple transformation of the group ID
        - Provide actual context about what belongs in the group
        - Be at least 20 characters (to ensure substance)
        """
        for group_id, description in PROJECT_GROUPS.items():
            stripped_desc = description.strip()
            assert len(stripped_desc) >= 20, (
                f"Group '{group_id}' description too short: '{description}'. "
                f"Expected at least 20 characters for meaningful description."
            )

            assert stripped_desc.lower() != group_id.lower(), (
                f"Group '{group_id}' description is just the group ID"
            )

            simple_transform = group_id.replace("_", " ").title()
            assert stripped_desc != simple_transform, (
                f"Group '{group_id}' description is just a simple transform "
                f"of the group ID: '{simple_transform}'"
            )

    def test_project_groups_expected_descriptions(self):
        """
        PROJECT_GROUPS should have the exact descriptions from the specification.
        """
        expected_descriptions = {
            "project_overview": "High-level project purpose and goals",
            "project_architecture": "System architecture and patterns",
            "feature_specs": "Feature specifications and requirements",
            "project_decisions": "Architecture Decision Records (ADRs)",
            "project_constraints": "Constraints and limitations",
            "domain_knowledge": "Domain terminology and concepts",
            "bdd_scenarios": "BDD Gherkin scenarios for behavior specifications",
        }

        assert PROJECT_GROUPS == expected_descriptions, (
            "PROJECT_GROUPS descriptions do not match specification"
        )


class TestSystemGroups:
    """Tests for SYSTEM_GROUPS constant."""

    def test_system_groups_exists_and_is_dict(self):
        """
        SYSTEM_GROUPS should exist and be a dictionary.
        """
        assert isinstance(SYSTEM_GROUPS, dict), "SYSTEM_GROUPS must be a dict"

    def test_system_groups_contains_all_required_group_ids(self):
        """
        SYSTEM_GROUPS should contain all 20 required group IDs.

        These are the system-level group IDs for GuardKit's internal
        knowledge organization, matching the canonical list in
        GraphitiClient.SYSTEM_GROUP_IDS.
        """
        required_groups = {
            "guardkit_templates",
            "guardkit_patterns",
            "guardkit_workflows",
            "product_knowledge",
            "command_workflows",
            "quality_gate_phases",
            "technology_stack",
            "feature_build_architecture",
            "architecture_decisions",
            "failure_patterns",
            "component_status",
            "integration_points",
            "templates",
            "agents",
            "patterns",
            "rules",
            "failed_approaches",
            "quality_gate_configs",
            "role_constraints",
            "implementation_modes",
        }

        actual_groups = set(SYSTEM_GROUPS.keys())

        assert required_groups.issubset(actual_groups), (
            f"SYSTEM_GROUPS must contain at least these group IDs: {required_groups}. "
            f"Missing: {required_groups - actual_groups}"
        )

    def test_system_groups_all_values_are_non_empty_strings(self):
        """
        All SYSTEM_GROUPS values should be non-empty string descriptions.
        """
        for group_id, description in SYSTEM_GROUPS.items():
            assert isinstance(description, str), (
                f"Group '{group_id}' description must be a string, "
                f"got {type(description)}"
            )
            assert len(description.strip()) > 0, (
                f"Group '{group_id}' description must be non-empty"
            )

    def test_system_groups_descriptions_are_meaningful(self):
        """
        SYSTEM_GROUPS descriptions should be meaningful, not just the key name.
        """
        for group_id, description in SYSTEM_GROUPS.items():
            stripped_desc = description.strip()
            assert len(stripped_desc) >= 20, (
                f"Group '{group_id}' description too short: '{description}'. "
                f"Expected at least 20 characters for meaningful description."
            )

            assert stripped_desc.lower() != group_id.lower(), (
                f"Group '{group_id}' description is just the group ID"
            )

            simple_transform = group_id.replace("_", " ").title()
            assert stripped_desc != simple_transform, (
                f"Group '{group_id}' description is just a simple transform "
                f"of the group ID: '{simple_transform}'"
            )

    def test_system_groups_expected_descriptions(self):
        """
        SYSTEM_GROUPS should have the exact descriptions from the specification.
        """
        expected_descriptions = {
            "guardkit_templates": "GuardKit template definitions and configurations",
            "guardkit_patterns": "GuardKit internal design patterns",
            "guardkit_workflows": "GuardKit workflow definitions and orchestration",
            "product_knowledge": "Product domain knowledge and terminology",
            "command_workflows": "Command execution workflows and pipelines",
            "quality_gate_phases": "Quality gate phase configurations and thresholds",
            "technology_stack": "Technology stack information and dependencies",
            "feature_build_architecture": "Feature build architecture and structure",
            "architecture_decisions": "Architecture decision records and rationale",
            "failure_patterns": "Known failure patterns and mitigations",
            "component_status": "Component health and operational status",
            "integration_points": "Integration touchpoints and external connections",
            "templates": "Template library and project scaffolding definitions",
            "agents": "Agent definitions and operational capabilities",
            "patterns": "Design pattern library and recommendations",
            "rules": "Rule definitions and enforcement policies",
            "failed_approaches": "Failed approaches and lessons learned",
            "quality_gate_configs": "Task-type specific quality thresholds",
            "role_constraints": "Player/Coach role boundaries",
            "implementation_modes": "Direct vs task-work patterns",
        }

        assert SYSTEM_GROUPS == expected_descriptions, (
            "SYSTEM_GROUPS descriptions do not match specification"
        )


class TestGroupIDUniqueness:
    """Tests for group ID uniqueness across PROJECT_GROUPS and SYSTEM_GROUPS."""

    def test_no_overlap_between_project_and_system_groups(self):
        """
        PROJECT_GROUPS and SYSTEM_GROUPS should have no overlapping group IDs.
        """
        project_group_ids = set(PROJECT_GROUPS.keys())
        system_group_ids = set(SYSTEM_GROUPS.keys())

        overlap = project_group_ids & system_group_ids

        assert len(overlap) == 0, (
            f"Found {len(overlap)} group IDs present in both PROJECT_GROUPS "
            f"and SYSTEM_GROUPS: {overlap}. Group IDs must be unique."
        )

    def test_all_group_ids_are_valid_python_identifiers(self):
        """
        All group IDs should be valid Python identifiers.
        """
        all_group_ids = list(PROJECT_GROUPS.keys()) + list(SYSTEM_GROUPS.keys())

        for group_id in all_group_ids:
            assert group_id.isidentifier(), (
                f"Group ID '{group_id}' is not a valid Python identifier"
            )

    def test_all_group_ids_use_snake_case(self):
        """
        All group IDs should use snake_case convention.
        """
        all_group_ids = list(PROJECT_GROUPS.keys()) + list(SYSTEM_GROUPS.keys())

        for group_id in all_group_ids:
            assert group_id.islower(), (
                f"Group ID '{group_id}' should be lowercase (snake_case)"
            )
            assert " " not in group_id, (
                f"Group ID '{group_id}' should not contain spaces"
            )
            assert "-" not in group_id, (
                f"Group ID '{group_id}' should use underscores, not hyphens"
            )


class TestDerivedLists:
    """Tests for PROJECT_GROUP_NAMES and SYSTEM_GROUP_IDS derived lists."""

    def test_project_group_names_matches_project_groups_keys(self):
        """PROJECT_GROUP_NAMES should contain exactly the keys of PROJECT_GROUPS."""
        assert set(PROJECT_GROUP_NAMES) == set(PROJECT_GROUPS.keys())

    def test_system_group_ids_matches_system_groups_keys(self):
        """SYSTEM_GROUP_IDS should contain exactly the keys of SYSTEM_GROUPS."""
        assert set(SYSTEM_GROUP_IDS) == set(SYSTEM_GROUPS.keys())

    def test_project_group_names_is_list(self):
        """PROJECT_GROUP_NAMES should be a list."""
        assert isinstance(PROJECT_GROUP_NAMES, list)

    def test_system_group_ids_is_list(self):
        """SYSTEM_GROUP_IDS should be a list."""
        assert isinstance(SYSTEM_GROUP_IDS, list)

    def test_project_group_names_preserves_order(self):
        """PROJECT_GROUP_NAMES should preserve dict insertion order."""
        assert PROJECT_GROUP_NAMES == list(PROJECT_GROUPS.keys())

    def test_system_group_ids_preserves_order(self):
        """SYSTEM_GROUP_IDS should preserve dict insertion order."""
        assert SYSTEM_GROUP_IDS == list(SYSTEM_GROUPS.keys())


class TestGroupHelperFunctions:
    """Tests for helper functions that work with group constants."""

    def test_get_all_groups_returns_combined_dict(self):
        """
        get_all_groups() should return a combined dictionary of all groups.
        """
        pytest.skip("Helper function get_all_groups() not yet in scope")

    def test_is_valid_project_group_returns_bool(self):
        """
        is_valid_project_group() should return True for valid project groups.
        """
        pytest.skip("Helper function is_valid_project_group() not yet in scope")

    def test_is_valid_system_group_returns_bool(self):
        """
        is_valid_system_group() should return True for valid system groups.
        """
        pytest.skip("Helper function is_valid_system_group() not yet in scope")


class TestGroupConstantsAreImmutable:
    """Tests to ensure group constants cannot be accidentally modified."""

    def test_project_groups_modification_creates_new_dict(self):
        """
        Modifying PROJECT_GROUPS should not affect the original constant.
        """
        original_keys = set(PROJECT_GROUPS.keys())

        test_dict = dict(PROJECT_GROUPS)
        test_dict["new_group"] = "Test description"

        assert set(PROJECT_GROUPS.keys()) == original_keys, (
            "PROJECT_GROUPS was modified when it should be immutable"
        )

    def test_system_groups_modification_creates_new_dict(self):
        """
        Modifying SYSTEM_GROUPS should not affect the original constant.
        """
        original_keys = set(SYSTEM_GROUPS.keys())

        test_dict = dict(SYSTEM_GROUPS)
        test_dict["new_group"] = "Test description"

        assert set(SYSTEM_GROUPS.keys()) == original_keys, (
            "SYSTEM_GROUPS was modified when it should be immutable"
        )


class TestGroupCountExpectations:
    """Tests to validate expected group counts for regression detection."""

    def test_project_groups_count_is_exactly_seven(self):
        """
        PROJECT_GROUPS should contain exactly 7 group IDs.
        """
        assert len(PROJECT_GROUPS) == 7, (
            f"PROJECT_GROUPS should contain exactly 7 groups, "
            f"found {len(PROJECT_GROUPS)}"
        )

    def test_system_groups_count_is_exactly_twenty(self):
        """
        SYSTEM_GROUPS should contain exactly 20 group IDs.
        """
        assert len(SYSTEM_GROUPS) == 20, (
            f"SYSTEM_GROUPS should contain exactly 20 groups, "
            f"found {len(SYSTEM_GROUPS)}"
        )

    def test_total_group_count_is_twenty_seven(self):
        """
        Total number of groups across both constants should be 27.
        (7 project + 20 system = 27 total groups)
        """
        total_count = len(PROJECT_GROUPS) + len(SYSTEM_GROUPS)

        assert total_count == 27, (
            f"Total group count should be 27 (7 project + 20 system), "
            f"found {total_count}"
        )
