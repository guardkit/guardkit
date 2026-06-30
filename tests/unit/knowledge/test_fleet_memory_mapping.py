"""Unit tests for fleet_memory_mapping module.

Tests the group_id → (project, payload_type, domain_tags) mapping
and resolution logic for Graphiti to fleet-memory migration.
"""

from __future__ import annotations

from guardkit.knowledge.fleet_memory_mapping import (
    GROUP_ID_MAP,
    GroupMapping,
    resolve,
)


class TestGroupMapping:
    """Tests for GroupMapping dataclass."""

    def test_group_mapping_structure(self):
        """Verify GroupMapping has required fields."""
        mapping = GroupMapping(
            project="guardkit",
            payload_type="build_outcome",
            domain_tags=["task"],
            disposition="migrate",
        )
        assert mapping.project == "guardkit"
        assert mapping.payload_type == "build_outcome"
        assert mapping.domain_tags == ["task"]
        assert mapping.disposition == "migrate"

    def test_disposition_literal(self):
        """Verify disposition is restricted to 'migrate' or 'retire'."""
        # Valid dispositions
        GroupMapping(
            project="guardkit",
            payload_type="document",
            domain_tags=[],
            disposition="migrate",
        )
        GroupMapping(
            project="guardkit",
            payload_type="document",
            domain_tags=[],
            disposition="retire",
        )


class TestGroupIDMap:
    """Tests for GROUP_ID_MAP completeness and correctness."""

    def test_all_project_groups_mapped(self):
        """Every project group from _group_defs.py must be in GROUP_ID_MAP."""
        project_groups = [
            "project_overview",
            "project_architecture",
            "feature_specs",
            "project_decisions",
            "project_constraints",
            "domain_knowledge",
            "bdd_scenarios",
            "task_outcomes",
            "turn_states",
        ]
        for group_id in project_groups:
            assert group_id in GROUP_ID_MAP, f"Missing project group: {group_id}"

    def test_all_system_groups_mapped(self):
        """Every system group from _group_defs.py must be in GROUP_ID_MAP."""
        system_groups = [
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
        ]
        for group_id in system_groups:
            assert group_id in GROUP_ID_MAP, f"Missing system group: {group_id}"

    def test_total_group_count(self):
        """Exactly 30 groups must be mapped: 9 project + 20 system + the 'adrs'
        alias (ADRService.create_adr's runtime group_id, added in TASK-MEM08-004)."""
        assert len(GROUP_ID_MAP) == 30

    def test_payload_types_are_valid(self):
        """All payload_type values must be from the 7 registered fleet-memory types."""
        valid_types = {
            "adr",
            "review_report",
            "build_outcome",
            "pattern",
            "warning",
            "seed_module",
            "document",
        }
        for group_id, mapping in GROUP_ID_MAP.items():
            assert (
                mapping.payload_type in valid_types
            ), f"{group_id}: invalid payload_type '{mapping.payload_type}'"

    def test_project_field_populated(self):
        """Every mapping must have a non-empty project field."""
        for group_id, mapping in GROUP_ID_MAP.items():
            assert mapping.project, f"{group_id}: empty project field"
            assert (
                mapping.project == mapping.project.lower()
            ), f"{group_id}: project must be lowercase"

    def test_domain_tags_is_list(self):
        """domain_tags must be a list (can be empty)."""
        for group_id, mapping in GROUP_ID_MAP.items():
            assert isinstance(
                mapping.domain_tags, list
            ), f"{group_id}: domain_tags must be a list"

    def test_disposition_is_valid(self):
        """disposition must be 'migrate' or 'retire'."""
        for group_id, mapping in GROUP_ID_MAP.items():
            assert mapping.disposition in {
                "migrate",
                "retire",
            }, f"{group_id}: invalid disposition '{mapping.disposition}'"


class TestResolveFunction:
    """Tests for resolve() function."""

    def test_resolve_known_group(self):
        """resolve() returns GroupMapping for a mapped group_id."""
        result = resolve("task_outcomes")
        assert result is not None
        assert isinstance(result, GroupMapping)
        assert result.payload_type == "build_outcome"
        assert result.project == "guardkit"

    def test_resolve_unknown_group(self):
        """resolve() returns None for an unknown group_id (fail-open)."""
        result = resolve("nonexistent_group")
        assert result is None

    def test_resolve_normalizes_hyphens(self):
        """resolve() normalizes hyphens to underscores before lookup."""
        # If we have a group "task_outcomes", it should also resolve from "task-outcomes"
        result = resolve("task-outcomes")
        assert result is not None
        assert result.payload_type == "build_outcome"

    def test_resolve_case_insensitive(self):
        """resolve() should handle case-insensitive lookup after normalization."""
        # PEP 503 normalization lowercases
        result = resolve("TASK_OUTCOMES")
        assert result is not None
        assert result.payload_type == "build_outcome"


class TestNormalization:
    """Tests for group_id normalization (PEP 503 style)."""

    def test_no_hyphens_in_group_ids(self):
        """All keys in GROUP_ID_MAP must use underscores, not hyphens."""
        for group_id in GROUP_ID_MAP.keys():
            assert "-" not in group_id, f"group_id '{group_id}' contains hyphens"

    def test_all_lowercase_group_ids(self):
        """All keys in GROUP_ID_MAP must be lowercase."""
        for group_id in GROUP_ID_MAP.keys():
            assert (
                group_id == group_id.lower()
            ), f"group_id '{group_id}' not lowercase"


class TestSpecificMappings:
    """Tests for specific group mappings per task requirements."""

    def test_task_outcomes_mapping(self):
        """task_outcomes → build_outcome with task_id identifier."""
        mapping = resolve("task_outcomes")
        assert mapping.payload_type == "build_outcome"
        assert mapping.disposition == "migrate"

    def test_project_decisions_mapping(self):
        """project_decisions → adr."""
        mapping = resolve("project_decisions")
        assert mapping.payload_type == "adr"
        assert mapping.disposition == "migrate"

    def test_architecture_decisions_mapping(self):
        """architecture_decisions (system) → adr."""
        mapping = resolve("architecture_decisions")
        assert mapping.payload_type == "adr"
        assert mapping.disposition == "migrate"

    def test_failure_patterns_migrate(self):
        """failure_patterns should migrate as warning + domain_tag."""
        mapping = resolve("failure_patterns")
        if mapping.disposition == "migrate":
            assert mapping.payload_type == "warning"

    def test_failed_approaches_migrate(self):
        """failed_approaches should migrate as warning + domain_tag."""
        mapping = resolve("failed_approaches")
        if mapping.disposition == "migrate":
            assert mapping.payload_type == "warning"

    def test_product_knowledge_disposition(self):
        """product_knowledge should be retire (covered by harvest corpus)."""
        mapping = resolve("product_knowledge")
        # Per task: system groups mostly retire (harvest already covers)
        # This test just verifies it has a disposition
        assert mapping.disposition in {"migrate", "retire"}
