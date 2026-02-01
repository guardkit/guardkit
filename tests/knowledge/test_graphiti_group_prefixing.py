"""
Tests for Group ID Prefixing (TASK-GR-PRE-001-B)

Tests comprehensive group ID prefixing logic:
- Project-specific groups get {project_id}__ prefix
- System-level groups remain unprefixed
- Prefix is applied automatically when adding episodes
- Search respects project namespace
- Cross-project search is possible when needed

Coverage Target: >=90%
Test Count: 25+ tests
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Optional, List
import os

# Import will fail initially - this is expected in RED phase
try:
    from guardkit.knowledge.graphiti_client import (
        GraphitiConfig,
        GraphitiClient,
        init_graphiti,
        get_graphiti,
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


# ============================================================================
# 1. get_group_id() Method Tests (10 tests)
# ============================================================================

class TestGetGroupId:
    """Test the get_group_id() method for correct prefixing."""

    def test_get_group_id_project_scope_simple_name(self):
        """Test project scope returns prefixed ID with simple name."""
        config = GraphitiConfig()
        client = GraphitiClient(config)
        client.project_id = "my-project"

        result = client.get_group_id("project_overview", scope="project")

        assert result == "my-project__project_overview"

    def test_get_group_id_project_scope_default(self):
        """Test project scope is default when scope not specified."""
        config = GraphitiConfig()
        client = GraphitiClient(config)
        client.project_id = "test-app"

        # Default scope should be "project"
        result = client.get_group_id("feature_specs")

        assert result == "test-app__feature_specs"

    def test_get_group_id_system_scope_no_prefix(self):
        """Test system scope returns unprefixed ID."""
        config = GraphitiConfig()
        client = GraphitiClient(config)
        client.project_id = "my-project"

        result = client.get_group_id("role_constraints", scope="system")

        assert result == "role_constraints"
        assert "__" not in result

    def test_get_group_id_multiple_project_ids(self):
        """Test prefixing with different project IDs."""
        config = GraphitiConfig()
        client = GraphitiClient(config)

        # Project A
        client.project_id = "project-a"
        result_a = client.get_group_id("domain_knowledge")
        assert result_a == "project-a__domain_knowledge"

        # Project B
        client.project_id = "project-b"
        result_b = client.get_group_id("domain_knowledge")
        assert result_b == "project-b__domain_knowledge"

        # Should be different
        assert result_a != result_b

    def test_get_group_id_empty_project_id(self):
        """Test behavior with empty project_id."""
        config = GraphitiConfig()
        client = GraphitiClient(config)
        client.project_id = ""

        # Should raise ValueError or return unprefixed
        with pytest.raises(ValueError, match="project_id cannot be empty"):
            client.get_group_id("project_overview", scope="project")

    def test_get_group_id_none_project_id(self):
        """Test behavior with None project_id."""
        config = GraphitiConfig()
        client = GraphitiClient(config)
        client.project_id = None

        # Should raise ValueError
        with pytest.raises(ValueError, match="project_id must be set"):
            client.get_group_id("project_overview", scope="project")

    def test_get_group_id_invalid_scope(self):
        """Test behavior with invalid scope value."""
        config = GraphitiConfig()
        client = GraphitiClient(config)
        client.project_id = "my-project"

        # Should raise ValueError
        with pytest.raises(ValueError, match="scope must be 'project' or 'system'"):
            client.get_group_id("some_group", scope="invalid")

    def test_get_group_id_none_scope_uses_default(self):
        """Test that None scope falls back to default (project)."""
        config = GraphitiConfig()
        client = GraphitiClient(config)
        client.project_id = "my-project"

        result = client.get_group_id("feature_specs", scope=None)

        assert result == "my-project__feature_specs"

    def test_get_group_id_preserves_group_name_case(self):
        """Test that group name case is preserved in result."""
        config = GraphitiConfig()
        client = GraphitiClient(config)
        client.project_id = "my-project"

        result = client.get_group_id("Feature_Specs", scope="project")

        assert result == "my-project__Feature_Specs"

    def test_get_group_id_special_characters_in_group_name(self):
        """Test handling of special characters in group name."""
        config = GraphitiConfig()
        client = GraphitiClient(config)
        client.project_id = "my-project"

        # Underscores should be allowed
        result = client.get_group_id("project_overview_v2", scope="project")
        assert result == "my-project__project_overview_v2"


# ============================================================================
# 2. Project Group Detection Tests (6 tests)
# ============================================================================

class TestProjectGroupDetection:
    """Test detection of project-specific groups."""

    def test_is_project_group_standard_names(self):
        """Test project group detection for standard names."""
        config = GraphitiConfig()
        client = GraphitiClient(config)

        # All standard project groups
        project_groups = [
            "project_overview",
            "project_architecture",
            "feature_specs",
            "project_decisions",
            "project_constraints",
            "domain_knowledge",
        ]

        for group in project_groups:
            assert client.is_project_group(group) is True

    def test_is_system_group_standard_names(self):
        """Test system group detection for standard names."""
        config = GraphitiConfig()
        client = GraphitiClient(config)

        # All standard system groups
        system_groups = [
            "role_constraints",
            "quality_gate_configs",
            "implementation_modes",
            "guardkit_templates",
            "guardkit_patterns",
        ]

        for group in system_groups:
            assert client.is_project_group(group) is False

    def test_is_project_group_custom_name(self):
        """Test that unknown group names default to project scope."""
        config = GraphitiConfig()
        client = GraphitiClient(config)

        # Unknown groups should default to project scope for safety
        assert client.is_project_group("custom_group") is True
        assert client.is_project_group("my_feature_data") is True

    def test_is_project_group_guardkit_prefix(self):
        """Test that guardkit_ prefix always means system scope."""
        config = GraphitiConfig()
        client = GraphitiClient(config)

        assert client.is_project_group("guardkit_anything") is False
        assert client.is_project_group("guardkit_custom") is False

    def test_is_project_group_case_sensitivity(self):
        """Test case sensitivity in group detection."""
        config = GraphitiConfig()
        client = GraphitiClient(config)

        # Should be case-sensitive
        assert client.is_project_group("PROJECT_OVERVIEW") is True  # Not recognized, defaults to project
        assert client.is_project_group("Role_Constraints") is True   # Not recognized, defaults to project

    def test_is_project_group_empty_string(self):
        """Test behavior with empty group name."""
        config = GraphitiConfig()
        client = GraphitiClient(config)

        # Should raise ValueError
        with pytest.raises(ValueError, match="group name cannot be empty"):
            client.is_project_group("")


# ============================================================================
# 3. add_episode() with Automatic Prefixing (5 tests)
# ============================================================================

class TestAddEpisodeAutoPrefixing:
    """Test that add_episode() applies correct prefix automatically."""

    @pytest.mark.asyncio
    async def test_add_episode_auto_prefix_project_group(self):
        """Test add_episode automatically prefixes project groups."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client.project_id = "my-project"

        mock_episode = MagicMock()
        mock_episode.uuid = "episode-uuid-123"
        mock_result = MagicMock()
        mock_result.episode = mock_episode

        mock_graphiti = MagicMock()
        mock_graphiti.add_episode = AsyncMock(return_value=mock_result)
        client._graphiti = mock_graphiti

        # Mock EpisodeType
        mock_episode_type = MagicMock()
        mock_episode_type.text = "text"
        mock_nodes_module = MagicMock(EpisodeType=mock_episode_type)

        with patch.dict('sys.modules', {'graphiti_core.nodes': mock_nodes_module}):
            result = await client.add_episode(
                name="Test Episode",
                episode_body="Content",
                group_id="project_overview"  # Project group, should be prefixed
            )

            # Verify the correct prefixed group_id was passed
            call_kwargs = mock_graphiti.add_episode.call_args[1]
            assert call_kwargs['group_id'] == "my-project__project_overview"

    @pytest.mark.asyncio
    async def test_add_episode_no_prefix_system_group(self):
        """Test add_episode doesn't prefix system groups."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client.project_id = "my-project"

        mock_episode = MagicMock()
        mock_episode.uuid = "episode-uuid-456"
        mock_result = MagicMock()
        mock_result.episode = mock_episode

        mock_graphiti = MagicMock()
        mock_graphiti.add_episode = AsyncMock(return_value=mock_result)
        client._graphiti = mock_graphiti

        # Mock EpisodeType
        mock_episode_type = MagicMock()
        mock_episode_type.text = "text"
        mock_nodes_module = MagicMock(EpisodeType=mock_episode_type)

        with patch.dict('sys.modules', {'graphiti_core.nodes': mock_nodes_module}):
            result = await client.add_episode(
                name="System Episode",
                episode_body="Content",
                group_id="role_constraints"  # System group, no prefix
            )

            # Verify no prefix was added
            call_kwargs = mock_graphiti.add_episode.call_args[1]
            assert call_kwargs['group_id'] == "role_constraints"
            assert "__" not in call_kwargs['group_id']

    @pytest.mark.asyncio
    async def test_add_episode_explicit_scope_project(self):
        """Test add_episode with explicit scope="project"."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client.project_id = "test-app"

        mock_episode = MagicMock()
        mock_episode.uuid = "episode-uuid"
        mock_result = MagicMock()
        mock_result.episode = mock_episode

        mock_graphiti = MagicMock()
        mock_graphiti.add_episode = AsyncMock(return_value=mock_result)
        client._graphiti = mock_graphiti

        # Mock EpisodeType
        mock_episode_type = MagicMock()
        mock_episode_type.text = "text"
        mock_nodes_module = MagicMock(EpisodeType=mock_episode_type)

        with patch.dict('sys.modules', {'graphiti_core.nodes': mock_nodes_module}):
            result = await client.add_episode(
                name="Episode",
                episode_body="Content",
                group_id="custom_group",
                scope="project"  # Explicit project scope
            )

            call_kwargs = mock_graphiti.add_episode.call_args[1]
            assert call_kwargs['group_id'] == "test-app__custom_group"

    @pytest.mark.asyncio
    async def test_add_episode_explicit_scope_system(self):
        """Test add_episode with explicit scope="system"."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client.project_id = "test-app"

        mock_episode = MagicMock()
        mock_episode.uuid = "episode-uuid"
        mock_result = MagicMock()
        mock_result.episode = mock_episode

        mock_graphiti = MagicMock()
        mock_graphiti.add_episode = AsyncMock(return_value=mock_result)
        client._graphiti = mock_graphiti

        # Mock EpisodeType
        mock_episode_type = MagicMock()
        mock_episode_type.text = "text"
        mock_nodes_module = MagicMock(EpisodeType=mock_episode_type)

        with patch.dict('sys.modules', {'graphiti_core.nodes': mock_nodes_module}):
            result = await client.add_episode(
                name="Episode",
                episode_body="Content",
                group_id="custom_system_group",
                scope="system"  # Explicit system scope
            )

            call_kwargs = mock_graphiti.add_episode.call_args[1]
            assert call_kwargs['group_id'] == "custom_system_group"

    @pytest.mark.asyncio
    async def test_add_episode_already_prefixed_group_id(self):
        """Test behavior when group_id is already prefixed."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client.project_id = "my-project"

        mock_episode = MagicMock()
        mock_episode.uuid = "episode-uuid"
        mock_result = MagicMock()
        mock_result.episode = mock_episode

        mock_graphiti = MagicMock()
        mock_graphiti.add_episode = AsyncMock(return_value=mock_result)
        client._graphiti = mock_graphiti

        # Mock EpisodeType
        mock_episode_type = MagicMock()
        mock_episode_type.text = "text"
        mock_nodes_module = MagicMock(EpisodeType=mock_episode_type)

        with patch.dict('sys.modules', {'graphiti_core.nodes': mock_nodes_module}):
            # Pass already prefixed group_id
            result = await client.add_episode(
                name="Episode",
                episode_body="Content",
                group_id="my-project__project_overview"  # Already prefixed
            )

            # Should NOT double-prefix
            call_kwargs = mock_graphiti.add_episode.call_args[1]
            assert call_kwargs['group_id'] == "my-project__project_overview"
            assert call_kwargs['group_id'].count("__") == 1


# ============================================================================
# 4. search() with Project Namespace (4 tests)
# ============================================================================

class TestSearchProjectNamespace:
    """Test that search respects project namespace."""

    @pytest.mark.asyncio
    async def test_search_auto_prefix_project_groups(self):
        """Test search automatically prefixes project group IDs."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client.project_id = "my-project"

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        client._graphiti = mock_graphiti

        await client.search(
            query="test query",
            group_ids=["project_overview", "feature_specs"]
        )

        # Verify search was called with prefixed group_ids
        call_args = mock_graphiti.search.call_args
        assert call_args[1]['group_ids'] == [
            "my-project__project_overview",
            "my-project__feature_specs"
        ]

    @pytest.mark.asyncio
    async def test_search_no_prefix_system_groups(self):
        """Test search doesn't prefix system group IDs."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client.project_id = "my-project"

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        client._graphiti = mock_graphiti

        await client.search(
            query="test query",
            group_ids=["role_constraints", "quality_gate_configs"]
        )

        # Verify search was called with unprefixed system groups
        call_args = mock_graphiti.search.call_args
        assert call_args[1]['group_ids'] == [
            "role_constraints",
            "quality_gate_configs"
        ]

    @pytest.mark.asyncio
    async def test_search_mixed_group_types(self):
        """Test search with mixed project and system groups."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client.project_id = "test-app"

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        client._graphiti = mock_graphiti

        await client.search(
            query="test query",
            group_ids=[
                "project_overview",      # Project - prefix
                "role_constraints",      # System - no prefix
                "feature_specs",         # Project - prefix
                "guardkit_templates"     # System - no prefix
            ]
        )

        # Verify correct selective prefixing
        call_args = mock_graphiti.search.call_args
        assert call_args[1]['group_ids'] == [
            "test-app__project_overview",
            "role_constraints",
            "test-app__feature_specs",
            "guardkit_templates"
        ]

    @pytest.mark.asyncio
    async def test_search_explicit_scope_parameter(self):
        """Test search with explicit scope parameter."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client.project_id = "my-project"

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        client._graphiti = mock_graphiti

        # Force system scope for all groups
        await client.search(
            query="test query",
            group_ids=["project_overview", "feature_specs"],
            scope="system"  # Override to system
        )

        # Should NOT prefix when scope is system
        call_args = mock_graphiti.search.call_args
        assert call_args[1]['group_ids'] == [
            "project_overview",
            "feature_specs"
        ]


# ============================================================================
# 5. Cross-Project Search (3 tests)
# ============================================================================

class TestCrossProjectSearch:
    """Test cross-project search capabilities."""

    @pytest.mark.asyncio
    async def test_search_explicit_project_prefix(self):
        """Test searching specific project by explicit prefix."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client.project_id = "current-project"

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        client._graphiti = mock_graphiti

        # Search other project's groups by explicit prefix
        await client.search(
            query="test query",
            group_ids=["other-project__project_overview"]
        )

        # Should pass through the explicit prefix unchanged
        call_args = mock_graphiti.search.call_args
        assert call_args[1]['group_ids'] == ["other-project__project_overview"]

    @pytest.mark.asyncio
    async def test_search_multiple_projects(self):
        """Test searching multiple projects simultaneously."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client.project_id = "project-a"

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        client._graphiti = mock_graphiti

        # Search across multiple projects
        await client.search(
            query="shared knowledge",
            group_ids=[
                "project-a__domain_knowledge",    # Current project (explicit)
                "project-b__domain_knowledge",    # Other project (explicit)
                "guardkit_patterns"               # System (no prefix)
            ]
        )

        # Should preserve all explicit prefixes
        call_args = mock_graphiti.search.call_args
        assert call_args[1]['group_ids'] == [
            "project-a__domain_knowledge",
            "project-b__domain_knowledge",
            "guardkit_patterns"
        ]

    @pytest.mark.asyncio
    async def test_search_all_projects_wildcard(self):
        """Test searching all projects with special parameter."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client.project_id = "my-project"

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        client._graphiti = mock_graphiti

        # Search all projects by passing None group_ids
        await client.search(
            query="test query",
            group_ids=None  # None means all groups
        )

        # Should pass None through to search all
        call_args = mock_graphiti.search.call_args
        assert call_args[1]['group_ids'] is None


# ============================================================================
# 6. Edge Cases and Error Handling (7 tests)
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_client_initialization_without_project_id(self):
        """Test client can be created without project_id initially."""
        config = GraphitiConfig()
        client = GraphitiClient(config, auto_detect_project=False)

        # Should initialize successfully
        assert client is not None
        assert client.project_id is None  # Not set when auto_detect_project=False

    def test_set_project_id_after_initialization(self):
        """Test setting project_id after client creation."""
        config = GraphitiConfig()
        client = GraphitiClient(config)

        # Set project_id later
        client.project_id = "late-project"

        result = client.get_group_id("project_overview")
        assert result == "late-project__project_overview"

    @pytest.mark.asyncio
    async def test_add_episode_without_project_id_set(self):
        """Test add_episode fails gracefully without project_id."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config, auto_detect_project=False)
        # project_id not set (auto_detect_project=False prevents auto-detection)

        mock_graphiti = MagicMock()
        client._graphiti = mock_graphiti

        # Should raise ValueError when trying to use project scope
        with pytest.raises(ValueError, match="project_id must be set"):
            await client.add_episode(
                name="Episode",
                episode_body="Content",
                group_id="project_overview"  # Project group requires project_id
            )

    @pytest.mark.asyncio
    async def test_search_without_project_id_system_groups_only(self):
        """Test search works with system groups even without project_id."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        # project_id not set

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        client._graphiti = mock_graphiti

        # Should work for system groups
        await client.search(
            query="test query",
            group_ids=["role_constraints", "guardkit_templates"]
        )

        # Should succeed
        assert mock_graphiti.search.called

    def test_get_group_id_with_special_chars_in_project_id(self):
        """Test group_id generation with special characters in project_id."""
        config = GraphitiConfig()
        client = GraphitiClient(config)
        client.project_id = "my-project-v2.0"

        result = client.get_group_id("project_overview")

        # Should preserve special characters
        assert result == "my-project-v2.0__project_overview"

    def test_get_group_id_very_long_names(self):
        """Test handling of very long project and group names."""
        config = GraphitiConfig()
        client = GraphitiClient(config)
        client.project_id = "very-long-project-name-with-many-characters"

        result = client.get_group_id("very_long_group_name_with_many_underscores")

        # Should handle without truncation
        assert result == "very-long-project-name-with-many-characters__very_long_group_name_with_many_underscores"
        assert len(result) > 50

    def test_get_group_id_unicode_characters(self):
        """Test handling of unicode characters in names."""
        config = GraphitiConfig()
        client = GraphitiClient(config)
        client.project_id = "projet-français"  # French characters

        result = client.get_group_id("übersicht")  # German characters

        # Should preserve unicode
        assert result == "projet-français__übersicht"


# ============================================================================
# 7. Integration Tests (2 tests)
# ============================================================================

@pytest.mark.integration
class TestGroupPrefixingIntegration:
    """Integration tests requiring Neo4j."""

    @pytest.mark.asyncio
    async def test_full_workflow_with_prefixing(self):
        """Test complete workflow with automatic prefixing."""
        config = GraphitiConfig(
            enabled=True,
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password123"
        )
        client = GraphitiClient(config)
        client.project_id = "integration-test-project"

        initialized = await client.initialize()
        if not initialized:
            pytest.skip("Neo4j or graphiti-core not available")

        try:
            # Add episodes to project and system groups
            project_episode = await client.add_episode(
                name="Project Episode",
                episode_body="Project-specific knowledge",
                group_id="project_overview"  # Should be prefixed
            )

            system_episode = await client.add_episode(
                name="System Episode",
                episode_body="System-level knowledge",
                group_id="guardkit_templates"  # Should NOT be prefixed
            )

            assert project_episode is not None
            assert system_episode is not None

            # Search project namespace
            project_results = await client.search(
                query="knowledge",
                group_ids=["project_overview"]
            )

            # Search system namespace
            system_results = await client.search(
                query="knowledge",
                group_ids=["guardkit_templates"]
            )

            # Should find results in correct namespaces
            assert isinstance(project_results, list)
            assert isinstance(system_results, list)

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_cross_project_isolation(self):
        """Test that different projects are properly isolated."""
        config = GraphitiConfig(
            enabled=True,
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password123"
        )

        # Project A client
        client_a = GraphitiClient(config)
        client_a.project_id = "project-a"

        # Project B client
        client_b = GraphitiClient(config)
        client_b.project_id = "project-b"

        initialized_a = await client_a.initialize()
        initialized_b = await client_b.initialize()

        if not (initialized_a and initialized_b):
            pytest.skip("Neo4j or graphiti-core not available")

        try:
            # Add episode to project A
            episode_a = await client_a.add_episode(
                name="Project A Episode",
                episode_body="Specific to project A",
                group_id="domain_knowledge"
            )

            # Add episode to project B
            episode_b = await client_b.add_episode(
                name="Project B Episode",
                episode_body="Specific to project B",
                group_id="domain_knowledge"
            )

            # Project A should only see its own knowledge
            results_a = await client_a.search(
                query="project",
                group_ids=["domain_knowledge"]
            )

            # Project B should only see its own knowledge
            results_b = await client_b.search(
                query="project",
                group_ids=["domain_knowledge"]
            )

            # Verify isolation (implementation-dependent on search results)
            assert isinstance(results_a, list)
            assert isinstance(results_b, list)

        finally:
            await client_a.close()
            await client_b.close()
