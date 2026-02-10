"""Unit tests for bdd_scenarios group registration in GraphitiClient.

TDD RED phase: Tests written before implementation.
These tests verify that bdd_scenarios is properly registered as a project group.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestBddScenariosGroupRegistration:
    """Tests for bdd_scenarios group registration in GraphitiClient."""

    def test_bdd_scenarios_in_project_groups(self):
        """Test that bdd_scenarios is registered in PROJECT_GROUP_NAMES."""
        from guardkit.knowledge.graphiti_client import GraphitiClient

        assert "bdd_scenarios" in GraphitiClient.PROJECT_GROUP_NAMES

    def test_bdd_scenarios_auto_detects_project_scope(self):
        """Test that is_project_group returns True for bdd_scenarios."""
        from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig

        config = GraphitiConfig(enabled=False)  # Disabled for unit test
        client = GraphitiClient(config, auto_detect_project=False)

        assert client.is_project_group("bdd_scenarios") is True

    def test_get_group_id_bdd_scenarios(self):
        """Test that get_group_id returns project-prefixed ID for bdd_scenarios."""
        from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig

        config = GraphitiConfig(enabled=False, project_id="my-project")
        client = GraphitiClient(config, auto_detect_project=False)

        group_id = client.get_group_id("bdd_scenarios")

        assert group_id == "my-project__bdd_scenarios"

    def test_get_group_id_bdd_scenarios_without_explicit_scope(self):
        """Test that bdd_scenarios auto-detects as project scope without explicit scope param."""
        from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig

        config = GraphitiConfig(enabled=False, project_id="test-project")
        client = GraphitiClient(config, auto_detect_project=False)

        # Don't pass scope parameter - should auto-detect as project
        group_id = client.get_group_id("bdd_scenarios")

        assert group_id == "test-project__bdd_scenarios"
        assert "__" in group_id  # Verify it has project prefix

    def test_bdd_scenarios_not_in_system_groups(self):
        """Test that bdd_scenarios is NOT in SYSTEM_GROUP_IDS."""
        from guardkit.knowledge.graphiti_client import GraphitiClient

        assert "bdd_scenarios" not in GraphitiClient.SYSTEM_GROUP_IDS


class TestBddScenariosWithSearch:
    """Tests for bdd_scenarios group in search operations."""

    def test_search_with_bdd_scenarios_group_applies_prefix(self):
        """Test that searching with bdd_scenarios group applies project prefix."""
        from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig

        config = GraphitiConfig(enabled=False, project_id="my-project")
        client = GraphitiClient(config, auto_detect_project=False)

        # Test _apply_group_prefix directly
        prefixed = client._apply_group_prefix("bdd_scenarios")

        assert prefixed == "my-project__bdd_scenarios"

    def test_apply_group_prefix_respects_already_prefixed(self):
        """Test that already-prefixed group IDs are not double-prefixed."""
        from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig

        config = GraphitiConfig(enabled=False, project_id="my-project")
        client = GraphitiClient(config, auto_detect_project=False)

        # Already prefixed
        prefixed = client._apply_group_prefix("other-project__bdd_scenarios")

        # Should not double-prefix
        assert prefixed == "other-project__bdd_scenarios"
        assert not prefixed.startswith("my-project__other-project")


class TestBddScenariosProjectGroupList:
    """Tests to verify bdd_scenarios is in the correct position in PROJECT_GROUP_NAMES."""

    def test_project_group_names_contains_expected_groups(self):
        """Test that PROJECT_GROUP_NAMES contains all expected project groups."""
        from guardkit.knowledge.graphiti_client import GraphitiClient

        expected_groups = [
            "project_overview",
            "project_architecture",
            "feature_specs",
            "project_decisions",
            "project_constraints",
            "domain_knowledge",
            "bdd_scenarios",  # NEW: Added by FEAT-SC-001
        ]

        for group in expected_groups:
            assert group in GraphitiClient.PROJECT_GROUP_NAMES, f"{group} not found in PROJECT_GROUP_NAMES"

    def test_project_group_names_length(self):
        """Test that PROJECT_GROUP_NAMES has the expected number of groups."""
        from guardkit.knowledge.graphiti_client import GraphitiClient

        # Should have at least 7 groups after adding bdd_scenarios
        assert len(GraphitiClient.PROJECT_GROUP_NAMES) >= 7
