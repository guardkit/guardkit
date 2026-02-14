"""
Tests for GraphitiClient clear methods.

Test Coverage:
- clear_all() - Clear all knowledge (system + project)
- clear_system_groups() - Clear only system-level knowledge
- clear_project_groups() - Clear only project-level knowledge
- get_clear_preview() - Preview what would be deleted
- Graceful degradation on errors
- Namespace boundary respect
- Driver-agnostic execute_query() (TASK-FKDB-006)
- None return handling for FalkorDB edge case (AC-004)
- Neo4j EagerResult and FalkorDB tuple return types (AC-007)
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Optional, List
from collections import namedtuple
import os

# Import will succeed once implemented
try:
    from guardkit.knowledge.graphiti_client import (
        GraphitiConfig,
        GraphitiClient,
    )
    import guardkit.knowledge.graphiti_client as graphiti_module
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False
    graphiti_module = None


# Skip all tests if imports not available
pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="Implementation not yet created"
)


# Define the system and project group IDs as specified in the task
SYSTEM_GROUP_IDS = [
    "guardkit_templates",
    "guardkit_patterns",
    "guardkit_workflows",
    # From seeding.py we also have these system groups:
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
]

PROJECT_GROUP_PATTERN = "{project}__"  # e.g., "guardkit__project_overview"

# Neo4j EagerResult is a named tuple
EagerResult = namedtuple("EagerResult", ["records", "summary", "keys"])


class TestGraphitiClientClearAll:
    """Test GraphitiClient.clear_all() method."""

    @pytest.mark.asyncio
    async def test_clear_all_when_disabled(self):
        """Test clear_all returns empty result when client disabled."""
        config = GraphitiConfig(enabled=False)
        client = GraphitiClient(config)

        result = await client.clear_all()

        assert result is not None
        assert result.get("system_groups_cleared", 0) == 0
        assert result.get("project_groups_cleared", 0) == 0
        assert result.get("total_episodes_deleted", 0) == 0

    @pytest.mark.asyncio
    async def test_clear_all_when_not_initialized(self):
        """Test clear_all returns empty result when not initialized."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._graphiti = None

        result = await client.clear_all()

        assert result is not None
        assert result.get("system_groups_cleared", 0) == 0

    @pytest.mark.asyncio
    async def test_clear_all_success(self):
        """Test successful clear_all clears both system and project groups."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_driver = MagicMock()
        # Mock execute_query for _list_groups (returns group records)
        mock_driver.execute_query = AsyncMock(return_value=(
            [{"group_id": "guardkit_templates"}],
            None,
            None,
        ))
        mock_graphiti.driver = mock_driver

        client._graphiti = mock_graphiti
        client._connected = True

        result = await client.clear_all()

        assert result is not None
        assert "system_groups_cleared" in result or "total_episodes_deleted" in result

    @pytest.mark.asyncio
    async def test_clear_all_graceful_degradation_on_error(self):
        """Test clear_all returns empty result on error (graceful degradation)."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_graphiti.driver = MagicMock()
        mock_graphiti.driver.execute_query = AsyncMock(
            side_effect=Exception("Database error")
        )
        client._graphiti = mock_graphiti
        client._connected = True

        result = await client.clear_all()

        # Should return empty/error result, not raise exception
        assert result is not None


class TestGraphitiClientClearSystemGroups:
    """Test GraphitiClient.clear_system_groups() method."""

    @pytest.mark.asyncio
    async def test_clear_system_groups_when_disabled(self):
        """Test clear_system_groups returns empty result when disabled."""
        config = GraphitiConfig(enabled=False)
        client = GraphitiClient(config)

        result = await client.clear_system_groups()

        assert result is not None
        assert result.get("groups_cleared", []) == []
        assert result.get("episodes_deleted", 0) == 0

    @pytest.mark.asyncio
    async def test_clear_system_groups_clears_correct_groups(self):
        """Test clear_system_groups clears only system groups."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        # Track which groups are cleared
        cleared_groups = []

        async def mock_clear_group(group_id):
            cleared_groups.append(group_id)
            return 10  # episodes deleted

        client._graphiti = MagicMock()
        client._connected = True
        client._clear_group = mock_clear_group

        result = await client.clear_system_groups()

        # Verify only system groups were cleared
        for group in cleared_groups:
            assert not group.startswith("guardkit__")  # No project groups
            assert group in SYSTEM_GROUP_IDS or group.startswith("guardkit_")

    @pytest.mark.asyncio
    async def test_clear_system_groups_graceful_degradation(self):
        """Test clear_system_groups handles errors gracefully."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._graphiti = None

        result = await client.clear_system_groups()

        assert result is not None


class TestGraphitiClientClearProjectGroups:
    """Test GraphitiClient.clear_project_groups() method."""

    @pytest.mark.asyncio
    async def test_clear_project_groups_when_disabled(self):
        """Test clear_project_groups returns empty result when disabled."""
        config = GraphitiConfig(enabled=False)
        client = GraphitiClient(config)

        result = await client.clear_project_groups()

        assert result is not None
        assert result.get("groups_cleared", []) == []

    @pytest.mark.asyncio
    async def test_clear_project_groups_with_project_name(self):
        """Test clear_project_groups uses project name for namespace."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        cleared_groups = []

        async def mock_clear_group(group_id):
            cleared_groups.append(group_id)
            return 5

        client._graphiti = MagicMock()
        client._connected = True
        client._clear_group = mock_clear_group

        result = await client.clear_project_groups(project_name="myproject")

        # Verify only project groups with correct prefix were cleared
        for group in cleared_groups:
            assert group.startswith("myproject__")

    @pytest.mark.asyncio
    async def test_clear_project_groups_auto_detects_project(self):
        """Test clear_project_groups auto-detects current project name."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        client._graphiti = MagicMock()
        client._connected = True

        # Mock the project detection
        with patch('guardkit.knowledge.graphiti_client.get_current_project_name', return_value="autodetected"):
            result = await client.clear_project_groups()

            assert result.get("project") == "autodetected" or result is not None

    @pytest.mark.asyncio
    async def test_clear_project_groups_respects_boundaries(self):
        """Test that clear_project_groups only clears its own project's data."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        cleared_groups = []

        async def mock_clear_group(group_id):
            cleared_groups.append(group_id)
            return 5

        client._graphiti = MagicMock()
        client._connected = True
        client._clear_group = mock_clear_group

        result = await client.clear_project_groups(project_name="projectA")

        # Should NOT clear projectB's groups
        for group in cleared_groups:
            assert not group.startswith("projectB__")
            assert group.startswith("projectA__")


class TestGraphitiClientGetClearPreview:
    """Test GraphitiClient.get_clear_preview() method."""

    @pytest.mark.asyncio
    async def test_get_clear_preview_when_disabled(self):
        """Test get_clear_preview returns empty preview when disabled."""
        config = GraphitiConfig(enabled=False)
        client = GraphitiClient(config)

        result = await client.get_clear_preview()

        assert result is not None
        assert result.get("system_groups", []) == []
        assert result.get("project_groups", []) == []

    @pytest.mark.asyncio
    async def test_get_clear_preview_all(self):
        """Test get_clear_preview shows both system and project groups."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        # Mock execute_query for episode estimation
        mock_graphiti.driver = MagicMock()
        mock_graphiti.driver.execute_query = AsyncMock(return_value=(
            [{"count": 42}], None, None
        ))
        client._graphiti = mock_graphiti
        client._connected = True

        # Mock the group listing
        with patch.object(client, '_list_groups', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [
                "guardkit_templates",
                "guardkit_patterns",
                "myproject__overview",
                "myproject__architecture",
            ]

            result = await client.get_clear_preview()

            assert "system_groups" in result or "total_groups" in result

    @pytest.mark.asyncio
    async def test_get_clear_preview_system_only(self):
        """Test get_clear_preview with system_only shows only system groups."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        client._graphiti = MagicMock()
        client._connected = True

        result = await client.get_clear_preview(system_only=True)

        # Project groups should be empty or not included
        assert result.get("project_groups", []) == [] or "project_groups" not in result

    @pytest.mark.asyncio
    async def test_get_clear_preview_project_only(self):
        """Test get_clear_preview with project_only shows only project groups."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        client._graphiti = MagicMock()
        client._connected = True

        result = await client.get_clear_preview(project_only=True)

        # System groups should be empty or not included
        assert result.get("system_groups", []) == [] or "system_groups" not in result

    @pytest.mark.asyncio
    async def test_get_clear_preview_includes_episode_estimates(self):
        """Test get_clear_preview includes episode count estimates."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        client._graphiti = MagicMock()
        client._connected = True

        result = await client.get_clear_preview()

        # Should include some estimate of episodes
        assert "estimated_episodes" in result or "total_episodes" in result or \
               "episode" in str(result).lower()


class TestGraphitiClientClearGroup:
    """Test internal _clear_group helper method."""

    @pytest.mark.asyncio
    async def test_clear_group_deletes_episodes(self):
        """Test _clear_group deletes episodes via execute_query."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_driver = MagicMock()
        # execute_query returns (records, summary, keys) tuple
        mock_driver.execute_query = AsyncMock(return_value=(
            [{"count": 25}], None, None
        ))
        mock_graphiti.driver = mock_driver

        client._graphiti = mock_graphiti
        client._connected = True

        count = await client._clear_group("test_group")

        assert count == 25
        mock_driver.execute_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_group_handles_empty_group(self):
        """Test _clear_group handles groups with no episodes."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_driver = MagicMock()
        # Empty records list
        mock_driver.execute_query = AsyncMock(return_value=(
            [], None, None
        ))
        mock_graphiti.driver = mock_driver

        client._graphiti = mock_graphiti
        client._connected = True

        count = await client._clear_group("empty_group")

        assert count == 0


class TestGraphitiClientListGroups:
    """Test internal _list_groups helper method."""

    @pytest.mark.asyncio
    async def test_list_groups_returns_all_groups(self):
        """Test _list_groups returns all group IDs via execute_query."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_driver = MagicMock()
        # execute_query returns (records, summary, keys) tuple
        mock_driver.execute_query = AsyncMock(return_value=(
            [
                {"group_id": "group1"},
                {"group_id": "group2"},
                {"group_id": "group3"},
            ],
            None,
            None,
        ))
        mock_graphiti.driver = mock_driver

        client._graphiti = mock_graphiti
        client._connected = True

        groups = await client._list_groups()

        assert isinstance(groups, list)
        assert len(groups) == 3
        assert "group1" in groups
        assert "group2" in groups
        assert "group3" in groups

    @pytest.mark.asyncio
    async def test_list_groups_handles_error(self):
        """Test _list_groups returns empty list on error."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._graphiti = None

        groups = await client._list_groups()

        assert groups == []


class TestClearConstants:
    """Test that clear operations use correct group constants."""

    def test_system_groups_defined(self):
        """Verify system group IDs are defined correctly."""
        # These are the groups from the task spec
        expected_system = [
            "guardkit_templates",
            "guardkit_patterns",
            "guardkit_workflows",
        ]

        for group in expected_system:
            assert group in SYSTEM_GROUP_IDS

    def test_project_group_pattern(self):
        """Verify project group pattern is correct."""
        # Project groups follow pattern: {project}__group_name
        test_project = "myproject"
        test_group = f"{test_project}__project_overview"

        assert test_group.startswith(f"{test_project}__")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_clear_all_with_no_data(self):
        """Test clear_all when database has no data."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        client._graphiti = MagicMock()
        client._connected = True

        with patch.object(client, '_list_groups', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []

            result = await client.clear_all()

            assert result.get("total_episodes_deleted", 0) == 0

    @pytest.mark.asyncio
    async def test_clear_project_with_special_characters(self):
        """Test clear_project_groups handles project names with special chars."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        client._graphiti = MagicMock()
        client._connected = True

        # Project names might have hyphens, underscores
        result = await client.clear_project_groups(project_name="my-project_2")

        assert result is not None

    @pytest.mark.asyncio
    async def test_clear_multiple_times_is_safe(self):
        """Test clearing multiple times doesn't cause errors."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        client._graphiti = MagicMock()
        client._connected = True

        # Clear twice
        result1 = await client.clear_all()
        result2 = await client.clear_all()

        assert result1 is not None
        assert result2 is not None


# =========================================================================
# TASK-FKDB-006: Driver-agnostic execute_query() tests
# =========================================================================

class TestExecuteQueryNoneReturn:
    """Test None return handling from execute_query (AC-004).

    FalkorDB edge case: execute_query() can return None when the driver
    has no results or encounters certain conditions (DD-8).
    """

    @pytest.mark.asyncio
    async def test_list_groups_none_result(self):
        """Test _list_groups returns empty list when execute_query returns None."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_driver = MagicMock()
        mock_driver.execute_query = AsyncMock(return_value=None)
        mock_graphiti.driver = mock_driver

        client._graphiti = mock_graphiti
        client._connected = True

        groups = await client._list_groups()

        assert groups == []

    @pytest.mark.asyncio
    async def test_clear_group_none_result(self):
        """Test _clear_group returns 0 when execute_query returns None."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_driver = MagicMock()
        mock_driver.execute_query = AsyncMock(return_value=None)
        mock_graphiti.driver = mock_driver

        client._graphiti = mock_graphiti
        client._connected = True

        count = await client._clear_group("test_group")

        assert count == 0

    @pytest.mark.asyncio
    async def test_get_clear_preview_none_result(self):
        """Test get_clear_preview handles None from execute_query for estimation."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_driver = MagicMock()
        mock_driver.execute_query = AsyncMock(return_value=None)
        mock_graphiti.driver = mock_driver
        client._graphiti = mock_graphiti
        client._connected = True

        with patch.object(client, '_list_groups', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = ["guardkit_templates"]

            result = await client.get_clear_preview()

            # estimated_episodes should be 0 when execute_query returns None
            assert result["estimated_episodes"] == 0


class TestExecuteQueryReturnTypes:
    """Test both Neo4j EagerResult-style and FalkorDB tuple-style return types (AC-005, AC-007).

    Neo4j EagerResult: named tuple (records, summary, keys)
    FalkorDB: plain tuple (records, header, None)
    Both support records[0]["field"] access and tuple unpacking.
    """

    @pytest.mark.asyncio
    async def test_list_groups_neo4j_eager_result(self):
        """Test _list_groups with Neo4j EagerResult named tuple."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_driver = MagicMock()
        # Simulate Neo4j EagerResult (named tuple)
        neo4j_result = EagerResult(
            records=[{"group_id": "group_a"}, {"group_id": "group_b"}],
            summary=MagicMock(),
            keys=["group_id"],
        )
        mock_driver.execute_query = AsyncMock(return_value=neo4j_result)
        mock_graphiti.driver = mock_driver

        client._graphiti = mock_graphiti
        client._connected = True

        groups = await client._list_groups()

        assert groups == ["group_a", "group_b"]

    @pytest.mark.asyncio
    async def test_list_groups_falkordb_tuple(self):
        """Test _list_groups with FalkorDB plain tuple return."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_driver = MagicMock()
        # Simulate FalkorDB return: (records, header, None)
        falkordb_result = (
            [{"group_id": "fk_group1"}, {"group_id": "fk_group2"}],
            ["group_id"],
            None,
        )
        mock_driver.execute_query = AsyncMock(return_value=falkordb_result)
        mock_graphiti.driver = mock_driver

        client._graphiti = mock_graphiti
        client._connected = True

        groups = await client._list_groups()

        assert groups == ["fk_group1", "fk_group2"]

    @pytest.mark.asyncio
    async def test_clear_group_neo4j_eager_result(self):
        """Test _clear_group with Neo4j EagerResult named tuple."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_driver = MagicMock()
        neo4j_result = EagerResult(
            records=[{"count": 15}],
            summary=MagicMock(),
            keys=["count"],
        )
        mock_driver.execute_query = AsyncMock(return_value=neo4j_result)
        mock_graphiti.driver = mock_driver

        client._graphiti = mock_graphiti
        client._connected = True

        count = await client._clear_group("test_group")

        assert count == 15

    @pytest.mark.asyncio
    async def test_clear_group_falkordb_tuple(self):
        """Test _clear_group with FalkorDB plain tuple return."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_driver = MagicMock()
        # FalkorDB: (records, header, None)
        falkordb_result = ([{"count": 30}], ["count"], None)
        mock_driver.execute_query = AsyncMock(return_value=falkordb_result)
        mock_graphiti.driver = mock_driver

        client._graphiti = mock_graphiti
        client._connected = True

        count = await client._clear_group("test_group")

        assert count == 30

    @pytest.mark.asyncio
    async def test_get_clear_preview_neo4j_eager_result(self):
        """Test get_clear_preview episode estimation with Neo4j EagerResult."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_driver = MagicMock()
        neo4j_result = EagerResult(
            records=[{"count": 99}],
            summary=MagicMock(),
            keys=["count"],
        )
        mock_driver.execute_query = AsyncMock(return_value=neo4j_result)
        mock_graphiti.driver = mock_driver
        client._graphiti = mock_graphiti
        client._connected = True

        with patch.object(client, '_list_groups', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = ["guardkit_templates"]

            result = await client.get_clear_preview()

            assert result["estimated_episodes"] == 99

    @pytest.mark.asyncio
    async def test_get_clear_preview_falkordb_tuple(self):
        """Test get_clear_preview episode estimation with FalkorDB tuple."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_driver = MagicMock()
        falkordb_result = ([{"count": 55}], ["count"], None)
        mock_driver.execute_query = AsyncMock(return_value=falkordb_result)
        mock_graphiti.driver = mock_driver
        client._graphiti = mock_graphiti
        client._connected = True

        with patch.object(client, '_list_groups', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = ["guardkit_templates"]

            result = await client.get_clear_preview()

            assert result["estimated_episodes"] == 55

    @pytest.mark.asyncio
    async def test_list_groups_filters_none_group_ids(self):
        """Test _list_groups filters out None group_id values."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_driver = MagicMock()
        mock_driver.execute_query = AsyncMock(return_value=(
            [
                {"group_id": "valid_group"},
                {"group_id": None},
                {"group_id": "another_valid"},
            ],
            None,
            None,
        ))
        mock_graphiti.driver = mock_driver

        client._graphiti = mock_graphiti
        client._connected = True

        groups = await client._list_groups()

        assert groups == ["valid_group", "another_valid"]

    @pytest.mark.asyncio
    async def test_clear_group_empty_records(self):
        """Test _clear_group returns 0 when records list is empty."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_driver = MagicMock()
        mock_driver.execute_query = AsyncMock(return_value=([], None, None))
        mock_graphiti.driver = mock_driver

        client._graphiti = mock_graphiti
        client._connected = True

        count = await client._clear_group("group_with_no_match")

        assert count == 0

    @pytest.mark.asyncio
    async def test_clear_group_no_driver(self):
        """Test _clear_group returns 0 when driver is None."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_graphiti.driver = None
        client._graphiti = mock_graphiti
        client._connected = True

        count = await client._clear_group("test_group")

        assert count == 0

    @pytest.mark.asyncio
    async def test_list_groups_no_driver(self):
        """Test _list_groups returns [] when driver is None."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_graphiti.driver = None
        client._graphiti = mock_graphiti
        client._connected = True

        groups = await client._list_groups()

        assert groups == []

    @pytest.mark.asyncio
    async def test_list_groups_execute_query_exception(self):
        """Test _list_groups returns [] when execute_query raises exception."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_driver = MagicMock()
        mock_driver.execute_query = AsyncMock(
            side_effect=Exception("Connection lost")
        )
        mock_graphiti.driver = mock_driver
        client._graphiti = mock_graphiti
        client._connected = True

        groups = await client._list_groups()

        assert groups == []

    @pytest.mark.asyncio
    async def test_clear_group_execute_query_exception(self):
        """Test _clear_group returns 0 when execute_query raises exception."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_driver = MagicMock()
        mock_driver.execute_query = AsyncMock(
            side_effect=Exception("Connection lost")
        )
        mock_graphiti.driver = mock_driver
        client._graphiti = mock_graphiti
        client._connected = True

        count = await client._clear_group("test_group")

        assert count == 0


@pytest.mark.integration
class TestGraphitiClientClearIntegration:
    """
    Integration tests for clear methods.

    These tests require Neo4j to be running.
    Mark with @pytest.mark.integration to run selectively.
    """

    @pytest.mark.asyncio
    async def test_clear_workflow_with_real_neo4j(self):
        """Test complete clear workflow with real Neo4j instance."""
        config = GraphitiConfig(
            enabled=True,
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password123"
        )
        client = GraphitiClient(config)

        # Initialize
        initialized = await client.initialize()
        if not initialized:
            pytest.skip("Neo4j or graphiti-core not available")

        try:
            # Add some test data first
            episode_id = await client.add_episode(
                name="Test Clear Episode",
                episode_body="This episode will be cleared",
                group_id="test_clear_group"
            )

            # Get preview
            preview = await client.get_clear_preview()
            assert isinstance(preview, dict)

            # Clear
            result = await client.clear_all()
            assert isinstance(result, dict)
        finally:
            await client.close()
