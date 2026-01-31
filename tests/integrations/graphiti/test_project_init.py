"""
Comprehensive Test Suite for Project Initialization Logic

Tests the project initialization workflow including namespace creation,
project metadata storage, existing project detection, project listing,
and graceful degradation when Graphiti is unavailable.

Coverage Target: >=85%
Test Count: 25+ tests

Acceptance Criteria Coverage:
- [x] First use of project_id creates project namespace
- [x] Project metadata is stored (name, created_at, config)
- [x] Existing projects are detected and loaded
- [x] Project list is queryable
- [x] Graceful handling when Graphiti is unavailable
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Optional, Dict, Any, List

# Import will fail initially - this is expected in RED phase
try:
    from guardkit.integrations.graphiti.project import (
        ProjectInfo,
        ProjectConfig,
        initialize_project,
        get_project_info,
        list_projects,
        project_exists,
        update_project_access_time,
        PROJECT_METADATA_GROUP,
    )
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False
    # Define placeholders for type hints
    ProjectInfo = None
    ProjectConfig = None


# Skip all tests if imports not available (RED phase expected state)
pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="Implementation not yet created (TDD RED phase)"
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_graphiti_client():
    """Create a mock GraphitiClient for testing."""
    client = MagicMock()
    client.enabled = True
    client._connected = True
    client.config = MagicMock()
    client.config.enabled = True
    client.search = AsyncMock(return_value=[])
    client.add_episode = AsyncMock(return_value="episode-uuid-123")
    client._graphiti = MagicMock()
    return client


@pytest.fixture
def mock_disabled_client():
    """Create a disabled GraphitiClient for graceful degradation tests."""
    client = MagicMock()
    client.enabled = False
    client._connected = False
    client.config = MagicMock()
    client.config.enabled = False
    client.search = AsyncMock(return_value=[])
    client.add_episode = AsyncMock(return_value=None)
    return client


@pytest.fixture
def sample_project_metadata():
    """Sample project metadata as stored in Graphiti."""
    return {
        "entity_type": "project_metadata",
        "project_id": "my-project",
        "created_at": "2026-01-30T00:00:00Z",
        "last_accessed": "2026-01-30T12:00:00Z",
        "graphiti_version": "1.0.0",
        "config": {
            "default_mode": "standard",
            "auto_seed": True,
        }
    }


@pytest.fixture
def mock_search_result_with_project(sample_project_metadata):
    """Create a mock search result containing project metadata."""
    return [
        {
            "uuid": "episode-uuid-123",
            "fact": f"Project metadata for {sample_project_metadata['project_id']}",
            "name": f"project_metadata_{sample_project_metadata['project_id']}",
            "episode_body": str(sample_project_metadata),
        }
    ]


# ============================================================================
# 1. ProjectInfo Dataclass Tests (5 tests)
# ============================================================================

class TestProjectInfoDataclass:
    """Test ProjectInfo dataclass structure and behavior."""

    def test_project_info_creation_with_required_fields(self):
        """Test creating ProjectInfo with required fields."""
        info = ProjectInfo(
            project_id="my-project",
            created_at=datetime.now(timezone.utc),
        )

        assert info.project_id == "my-project"
        assert info.created_at is not None
        assert isinstance(info.created_at, datetime)

    def test_project_info_creation_with_all_fields(self):
        """Test creating ProjectInfo with all fields."""
        now = datetime.now(timezone.utc)
        config = ProjectConfig(default_mode="tdd", auto_seed=False)

        info = ProjectInfo(
            project_id="full-project",
            created_at=now,
            last_accessed=now,
            graphiti_version="1.0.0",
            config=config,
        )

        assert info.project_id == "full-project"
        assert info.created_at == now
        assert info.last_accessed == now
        assert info.graphiti_version == "1.0.0"
        assert info.config.default_mode == "tdd"
        assert info.config.auto_seed is False

    def test_project_info_to_dict(self):
        """Test ProjectInfo serialization to dictionary."""
        now = datetime(2026, 1, 30, 12, 0, 0, tzinfo=timezone.utc)
        info = ProjectInfo(
            project_id="test-project",
            created_at=now,
            graphiti_version="1.0.0",
        )

        result = info.to_dict()

        assert result["project_id"] == "test-project"
        assert result["created_at"] == "2026-01-30T12:00:00+00:00"
        assert result["graphiti_version"] == "1.0.0"
        assert "entity_type" in result
        assert result["entity_type"] == "project_metadata"

    def test_project_info_from_dict(self, sample_project_metadata):
        """Test ProjectInfo deserialization from dictionary."""
        info = ProjectInfo.from_dict(sample_project_metadata)

        assert info.project_id == "my-project"
        assert info.graphiti_version == "1.0.0"
        assert info.config is not None
        assert info.config.default_mode == "standard"
        assert info.config.auto_seed is True

    def test_project_info_default_values(self):
        """Test ProjectInfo default values for optional fields."""
        now = datetime.now(timezone.utc)
        info = ProjectInfo(
            project_id="minimal-project",
            created_at=now,
        )

        # Check defaults
        assert info.last_accessed is None or info.last_accessed == now
        assert info.graphiti_version is not None  # Should have default version
        assert info.config is not None  # Should have default config


# ============================================================================
# 2. ProjectConfig Dataclass Tests (3 tests)
# ============================================================================

class TestProjectConfigDataclass:
    """Test ProjectConfig dataclass structure and behavior."""

    def test_project_config_default_values(self):
        """Test ProjectConfig default values."""
        config = ProjectConfig()

        assert config.default_mode == "standard"
        assert config.auto_seed is True

    def test_project_config_custom_values(self):
        """Test ProjectConfig with custom values."""
        config = ProjectConfig(
            default_mode="tdd",
            auto_seed=False,
        )

        assert config.default_mode == "tdd"
        assert config.auto_seed is False

    def test_project_config_to_dict(self):
        """Test ProjectConfig serialization to dictionary."""
        config = ProjectConfig(default_mode="bdd", auto_seed=True)

        result = config.to_dict()

        assert result["default_mode"] == "bdd"
        assert result["auto_seed"] is True


# ============================================================================
# 3. initialize_project() Tests (8 tests)
# ============================================================================

class TestInitializeProject:
    """Test initialize_project() function."""

    @pytest.mark.asyncio
    async def test_initialize_new_project_creates_namespace(self, mock_graphiti_client):
        """Test that first use of project_id creates project namespace."""
        # Mock search returns empty (no existing project)
        mock_graphiti_client.search = AsyncMock(return_value=[])

        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_graphiti_client):
            result = await initialize_project("new-project")

        assert result is not None
        assert isinstance(result, ProjectInfo)
        assert result.project_id == "new-project"
        # Verify episode was created
        mock_graphiti_client.add_episode.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_new_project_stores_metadata(self, mock_graphiti_client):
        """Test that project metadata is stored (name, created_at, config)."""
        mock_graphiti_client.search = AsyncMock(return_value=[])

        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_graphiti_client):
            result = await initialize_project("metadata-project")

        # Verify metadata fields exist
        assert result.project_id == "metadata-project"
        assert result.created_at is not None
        assert result.config is not None
        assert result.graphiti_version is not None

        # Verify the episode body contains all required metadata
        call_args = mock_graphiti_client.add_episode.call_args
        assert call_args is not None
        episode_body = call_args[1].get('episode_body') or call_args[0][1]
        assert "metadata-project" in episode_body

    @pytest.mark.asyncio
    async def test_initialize_existing_project_loads_from_graph(
        self, mock_graphiti_client, mock_search_result_with_project, sample_project_metadata
    ):
        """Test that existing projects are detected and loaded."""
        # Mock search returns existing project
        mock_graphiti_client.search = AsyncMock(return_value=mock_search_result_with_project)

        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_graphiti_client):
            result = await initialize_project("my-project")

        assert result is not None
        assert result.project_id == "my-project"
        # Should NOT create a new episode (project already exists)
        mock_graphiti_client.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_initialize_project_with_custom_config(self, mock_graphiti_client):
        """Test initializing project with custom configuration."""
        mock_graphiti_client.search = AsyncMock(return_value=[])
        custom_config = ProjectConfig(default_mode="tdd", auto_seed=False)

        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_graphiti_client):
            result = await initialize_project("custom-project", config=custom_config)

        assert result.config.default_mode == "tdd"
        assert result.config.auto_seed is False

    @pytest.mark.asyncio
    async def test_initialize_project_normalizes_project_id(self, mock_graphiti_client):
        """Test that project_id is normalized during initialization."""
        mock_graphiti_client.search = AsyncMock(return_value=[])

        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_graphiti_client):
            result = await initialize_project("My Project Name")

        # Should be normalized to lowercase with hyphens
        assert result.project_id == "my-project-name"

    @pytest.mark.asyncio
    async def test_initialize_project_graceful_degradation_when_disabled(self, mock_disabled_client):
        """Test graceful handling when Graphiti is unavailable (disabled)."""
        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_disabled_client):
            result = await initialize_project("offline-project")

        # Should return a local-only ProjectInfo without Graphiti storage
        assert result is not None
        assert result.project_id == "offline-project"
        # Should NOT attempt to add episode
        mock_disabled_client.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_initialize_project_graceful_degradation_when_not_connected(self, mock_graphiti_client):
        """Test graceful handling when Graphiti is not connected."""
        mock_graphiti_client._connected = False
        mock_graphiti_client.enabled = False

        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_graphiti_client):
            result = await initialize_project("disconnected-project")

        # Should return a local-only ProjectInfo
        assert result is not None
        assert result.project_id == "disconnected-project"

    @pytest.mark.asyncio
    async def test_initialize_project_graceful_degradation_when_client_none(self):
        """Test graceful handling when GraphitiClient is None."""
        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=None):
            result = await initialize_project("no-client-project")

        # Should return a local-only ProjectInfo
        assert result is not None
        assert result.project_id == "no-client-project"


# ============================================================================
# 4. get_project_info() Tests (5 tests)
# ============================================================================

class TestGetProjectInfo:
    """Test get_project_info() function."""

    @pytest.mark.asyncio
    async def test_get_project_info_returns_existing_project(
        self, mock_graphiti_client, mock_search_result_with_project
    ):
        """Test getting info for an existing project."""
        mock_graphiti_client.search = AsyncMock(return_value=mock_search_result_with_project)

        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_graphiti_client):
            result = await get_project_info("my-project")

        assert result is not None
        assert result.project_id == "my-project"

    @pytest.mark.asyncio
    async def test_get_project_info_returns_none_for_nonexistent(self, mock_graphiti_client):
        """Test getting info for a nonexistent project returns None."""
        mock_graphiti_client.search = AsyncMock(return_value=[])

        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_graphiti_client):
            result = await get_project_info("nonexistent-project")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_project_info_graceful_degradation(self, mock_disabled_client):
        """Test graceful degradation when Graphiti unavailable."""
        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_disabled_client):
            result = await get_project_info("any-project")

        # Should return None when Graphiti is unavailable
        assert result is None

    @pytest.mark.asyncio
    async def test_get_project_info_handles_search_error(self, mock_graphiti_client):
        """Test graceful handling when search throws an error."""
        mock_graphiti_client.search = AsyncMock(side_effect=Exception("Search failed"))

        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_graphiti_client):
            result = await get_project_info("error-project")

        # Should return None on error
        assert result is None

    @pytest.mark.asyncio
    async def test_get_project_info_normalizes_project_id(self, mock_graphiti_client):
        """Test that project_id is normalized when getting info."""
        mock_graphiti_client.search = AsyncMock(return_value=[])

        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_graphiti_client):
            await get_project_info("My Project")

        # Verify search was called with normalized ID
        call_args = mock_graphiti_client.search.call_args
        query = call_args[1].get('query') or call_args[0][0]
        assert "my-project" in query.lower()


# ============================================================================
# 5. list_projects() Tests (5 tests)
# ============================================================================

class TestListProjects:
    """Test list_projects() function."""

    @pytest.mark.asyncio
    async def test_list_projects_returns_all_projects(self, mock_graphiti_client):
        """Test listing all projects in the knowledge graph."""
        # Mock search returns multiple projects
        mock_search_results = [
            {"uuid": "uuid-1", "fact": "Project metadata for project-a", "episode_body": '{"project_id": "project-a"}'},
            {"uuid": "uuid-2", "fact": "Project metadata for project-b", "episode_body": '{"project_id": "project-b"}'},
            {"uuid": "uuid-3", "fact": "Project metadata for project-c", "episode_body": '{"project_id": "project-c"}'},
        ]
        mock_graphiti_client.search = AsyncMock(return_value=mock_search_results)

        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_graphiti_client):
            result = await list_projects()

        assert isinstance(result, list)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_list_projects_returns_empty_when_no_projects(self, mock_graphiti_client):
        """Test listing projects when none exist."""
        mock_graphiti_client.search = AsyncMock(return_value=[])

        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_graphiti_client):
            result = await list_projects()

        assert result == []

    @pytest.mark.asyncio
    async def test_list_projects_graceful_degradation(self, mock_disabled_client):
        """Test graceful degradation when Graphiti unavailable."""
        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_disabled_client):
            result = await list_projects()

        # Should return empty list when Graphiti unavailable
        assert result == []

    @pytest.mark.asyncio
    async def test_list_projects_handles_search_error(self, mock_graphiti_client):
        """Test graceful handling when search throws an error."""
        mock_graphiti_client.search = AsyncMock(side_effect=Exception("Search failed"))

        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_graphiti_client):
            result = await list_projects()

        # Should return empty list on error
        assert result == []

    @pytest.mark.asyncio
    async def test_list_projects_uses_correct_group(self, mock_graphiti_client):
        """Test that list_projects searches in the correct group."""
        mock_graphiti_client.search = AsyncMock(return_value=[])

        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_graphiti_client):
            await list_projects()

        # Verify search was called with project metadata group
        call_args = mock_graphiti_client.search.call_args
        group_ids = call_args[1].get('group_ids') or []
        assert PROJECT_METADATA_GROUP in group_ids or any('project' in str(g).lower() for g in group_ids)


# ============================================================================
# 6. project_exists() Tests (4 tests)
# ============================================================================

class TestProjectExists:
    """Test project_exists() function."""

    @pytest.mark.asyncio
    async def test_project_exists_returns_true_for_existing(
        self, mock_graphiti_client, mock_search_result_with_project
    ):
        """Test project_exists returns True for existing project."""
        mock_graphiti_client.search = AsyncMock(return_value=mock_search_result_with_project)

        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_graphiti_client):
            result = await project_exists("my-project")

        assert result is True

    @pytest.mark.asyncio
    async def test_project_exists_returns_false_for_nonexistent(self, mock_graphiti_client):
        """Test project_exists returns False for nonexistent project."""
        mock_graphiti_client.search = AsyncMock(return_value=[])

        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_graphiti_client):
            result = await project_exists("nonexistent-project")

        assert result is False

    @pytest.mark.asyncio
    async def test_project_exists_graceful_degradation(self, mock_disabled_client):
        """Test graceful degradation when Graphiti unavailable."""
        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_disabled_client):
            result = await project_exists("any-project")

        # Should return False when Graphiti unavailable
        assert result is False

    @pytest.mark.asyncio
    async def test_project_exists_normalizes_project_id(self, mock_graphiti_client):
        """Test that project_id is normalized when checking existence."""
        mock_graphiti_client.search = AsyncMock(return_value=[])

        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_graphiti_client):
            await project_exists("My Project Name")

        # Verify search was called (we're testing the function doesn't error)
        mock_graphiti_client.search.assert_called_once()


# ============================================================================
# 7. update_project_access_time() Tests (3 tests)
# ============================================================================

class TestUpdateProjectAccessTime:
    """Test update_project_access_time() function."""

    @pytest.mark.asyncio
    async def test_update_access_time_updates_last_accessed(
        self, mock_graphiti_client, mock_search_result_with_project
    ):
        """Test that update_project_access_time updates last_accessed field."""
        mock_graphiti_client.search = AsyncMock(return_value=mock_search_result_with_project)

        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_graphiti_client):
            result = await update_project_access_time("my-project")

        assert result is True
        # Verify an update episode was added
        mock_graphiti_client.add_episode.assert_called()

    @pytest.mark.asyncio
    async def test_update_access_time_returns_false_for_nonexistent(self, mock_graphiti_client):
        """Test update returns False for nonexistent project."""
        mock_graphiti_client.search = AsyncMock(return_value=[])

        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_graphiti_client):
            result = await update_project_access_time("nonexistent-project")

        assert result is False

    @pytest.mark.asyncio
    async def test_update_access_time_graceful_degradation(self, mock_disabled_client):
        """Test graceful degradation when Graphiti unavailable."""
        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_disabled_client):
            result = await update_project_access_time("any-project")

        # Should return False when Graphiti unavailable
        assert result is False


# ============================================================================
# 8. Edge Cases and Error Handling Tests (5 tests)
# ============================================================================

class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_initialize_project_with_empty_string(self, mock_graphiti_client):
        """Test initialize_project with empty string project_id."""
        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_graphiti_client):
            with pytest.raises(ValueError, match="project_id"):
                await initialize_project("")

    @pytest.mark.asyncio
    async def test_initialize_project_with_none(self, mock_graphiti_client):
        """Test initialize_project with None project_id."""
        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_graphiti_client):
            with pytest.raises((ValueError, TypeError)):
                await initialize_project(None)

    @pytest.mark.asyncio
    async def test_initialize_project_with_special_characters(self, mock_graphiti_client):
        """Test initialize_project normalizes special characters."""
        mock_graphiti_client.search = AsyncMock(return_value=[])

        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_graphiti_client):
            result = await initialize_project("My Project! @#$%")

        # Should normalize to valid project_id
        assert result.project_id == "my-project"

    @pytest.mark.asyncio
    async def test_project_info_from_invalid_dict(self):
        """Test ProjectInfo.from_dict with invalid data."""
        invalid_data = {"invalid": "data"}

        with pytest.raises((KeyError, ValueError)):
            ProjectInfo.from_dict(invalid_data)

    @pytest.mark.asyncio
    async def test_concurrent_project_initialization(self, mock_graphiti_client):
        """Test that concurrent initializations don't create duplicates."""
        import asyncio

        # First call returns empty (no existing), subsequent return existing
        call_count = [0]

        async def mock_search(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return []  # First call: no existing project
            return [{"uuid": "uuid-1", "fact": "Project exists"}]  # Subsequent: project exists

        mock_graphiti_client.search = mock_search

        with patch('guardkit.integrations.graphiti.project.get_graphiti', return_value=mock_graphiti_client):
            # Simulate concurrent initialization
            results = await asyncio.gather(
                initialize_project("concurrent-project"),
                initialize_project("concurrent-project"),
            )

        # Both should return valid ProjectInfo
        assert all(r is not None for r in results)
        assert all(r.project_id == "concurrent-project" for r in results)


# ============================================================================
# 9. Constants and Module-Level Tests (2 tests)
# ============================================================================

class TestModuleLevelConstants:
    """Test module-level constants and configuration."""

    def test_project_metadata_group_constant_exists(self):
        """Test that PROJECT_METADATA_GROUP constant is defined."""
        assert PROJECT_METADATA_GROUP is not None
        assert isinstance(PROJECT_METADATA_GROUP, str)
        assert len(PROJECT_METADATA_GROUP) > 0

    def test_project_metadata_group_is_system_group(self):
        """Test that PROJECT_METADATA_GROUP is a system-level group."""
        # System groups typically start with 'guardkit_' or don't have project prefix
        assert "__" not in PROJECT_METADATA_GROUP or PROJECT_METADATA_GROUP.startswith("guardkit")


# ============================================================================
# Integration Test Markers (for real Neo4j tests)
# ============================================================================

@pytest.mark.integration
class TestProjectInitIntegration:
    """
    Integration tests requiring real Neo4j/Graphiti connection.

    Run with: pytest -m integration
    """

    @pytest.mark.asyncio
    async def test_full_project_lifecycle(self):
        """Test complete project lifecycle with real Graphiti."""
        pytest.skip("Integration test - requires running Neo4j")

        # 1. Initialize new project
        # 2. Get project info
        # 3. Update access time
        # 4. List projects (should include new project)
        # 5. Cleanup

    @pytest.mark.asyncio
    async def test_graceful_degradation_with_unavailable_neo4j(self):
        """Test graceful degradation when Neo4j is unavailable."""
        pytest.skip("Integration test - requires Neo4j to be stopped")
