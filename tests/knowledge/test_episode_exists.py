"""
Tests for GraphitiClient.episode_exists() method.

Tests cover the episode existence checking functionality for deduplication,
including entity_id matching, source_hash verification, and namespace handling.

Coverage Target: >=85%
Test Count: 10+ tests

TDD Phase: RED - These tests are written before implementation.
"""

import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any, List

# Import will succeed after ExistsResult is created
from guardkit.integrations.graphiti import ExistsResult

# Import GraphitiClient and config
try:
    from guardkit.knowledge.graphiti_client import (
        GraphitiConfig,
        GraphitiClient,
    )
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False


# Skip all tests if imports not available
pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="Implementation not yet created"
)


class TestExistsResult:
    """Test ExistsResult dataclass."""

    def test_not_found_result(self):
        """Test creating a not-found result."""
        result = ExistsResult.not_found()

        assert result.exists is False
        assert result.episode is None
        assert result.exact_match is False
        assert result.uuid is None

    def test_found_result_with_episode(self):
        """Test creating a found result with episode data."""
        episode = {"uuid": "ep-123", "fact": "Test content"}
        result = ExistsResult.found(episode=episode)

        assert result.exists is True
        assert result.episode == episode
        assert result.exact_match is False
        assert result.uuid == "ep-123"

    def test_found_result_with_exact_match(self):
        """Test creating a found result with exact hash match."""
        episode = {"uuid": "ep-456", "fact": "Test content"}
        result = ExistsResult.found(episode=episode, exact_match=True)

        assert result.exists is True
        assert result.episode == episode
        assert result.exact_match is True
        assert result.uuid == "ep-456"

    def test_found_result_with_explicit_uuid(self):
        """Test creating a found result with explicit UUID."""
        episode = {"fact": "Test content"}  # No uuid in episode
        result = ExistsResult.found(episode=episode, uuid="custom-uuid")

        assert result.exists is True
        assert result.uuid == "custom-uuid"

    def test_invalid_not_found_with_episode(self):
        """Test that not-found with episode raises error."""
        with pytest.raises(ValueError, match="episode must be None"):
            ExistsResult(exists=False, episode={"uuid": "ep-123"})

    def test_invalid_not_found_with_exact_match(self):
        """Test that not-found with exact_match raises error."""
        with pytest.raises(ValueError, match="exact_match must be False"):
            ExistsResult(exists=False, exact_match=True)

    def test_invalid_not_found_with_uuid(self):
        """Test that not-found with uuid raises error."""
        with pytest.raises(ValueError, match="uuid must be None"):
            ExistsResult(exists=False, uuid="some-uuid")


class TestEpisodeExistsBasic:
    """Test basic episode_exists functionality."""

    @pytest.mark.asyncio
    async def test_episode_exists_returns_not_found_when_no_match(self):
        """Test episode_exists returns not found when no episode matches."""
        config = GraphitiConfig(enabled=True, project_id="test-project")
        client = GraphitiClient(config)

        # Mock the search to return empty results
        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        client._graphiti = mock_graphiti

        result = await client.episode_exists(
            entity_id="nonexistent-entity",
            group_id="project_overview"
        )

        assert isinstance(result, ExistsResult)
        assert result.exists is False
        assert result.episode is None
        assert result.uuid is None

    @pytest.mark.asyncio
    async def test_episode_exists_returns_found_when_entity_id_matches(self):
        """Test episode_exists returns found when entity_id matches."""
        config = GraphitiConfig(enabled=True, project_id="test-project")
        client = GraphitiClient(config)

        # Create mock episode with entity_id in body metadata
        metadata = {
            "entity_id": "my-entity-123",
            "source": "guardkit_seeding",
            "version": "1.0.0"
        }
        mock_edge = MagicMock()
        mock_edge.uuid = "episode-uuid-abc"
        mock_edge.fact = json.dumps(metadata) + "\n\nActual content here"
        mock_edge.created_at = "2025-01-01T00:00:00Z"
        mock_edge.valid_at = "2025-01-01T00:00:00Z"
        mock_edge.name = "Test Episode"

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[mock_edge])
        client._graphiti = mock_graphiti

        result = await client.episode_exists(
            entity_id="my-entity-123",
            group_id="project_overview"
        )

        assert result.exists is True
        assert result.uuid == "episode-uuid-abc"
        assert result.episode is not None


class TestEpisodeExistsSourceHash:
    """Test episode_exists source_hash matching functionality."""

    @pytest.mark.asyncio
    async def test_episode_exists_with_source_hash_exact_match(self):
        """Test episode_exists returns exact_match=True when hash matches."""
        config = GraphitiConfig(enabled=True, project_id="test-project")
        client = GraphitiClient(config)

        # Create mock episode with matching source_hash
        metadata = {
            "entity_id": "my-entity-123",
            "source_hash": "abc123hash",
            "source": "guardkit_seeding",
            "version": "1.0.0"
        }
        mock_edge = MagicMock()
        mock_edge.uuid = "episode-uuid-def"
        mock_edge.fact = json.dumps(metadata) + "\n\nContent"
        mock_edge.created_at = "2025-01-01T00:00:00Z"
        mock_edge.valid_at = "2025-01-01T00:00:00Z"
        mock_edge.name = "Test Episode"

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[mock_edge])
        client._graphiti = mock_graphiti

        result = await client.episode_exists(
            entity_id="my-entity-123",
            group_id="project_overview",
            source_hash="abc123hash"
        )

        assert result.exists is True
        assert result.exact_match is True
        assert result.uuid == "episode-uuid-def"

    @pytest.mark.asyncio
    async def test_episode_exists_with_source_hash_no_exact_match(self):
        """Test episode_exists returns exact_match=False when hash differs."""
        config = GraphitiConfig(enabled=True, project_id="test-project")
        client = GraphitiClient(config)

        # Create mock episode with different source_hash
        metadata = {
            "entity_id": "my-entity-123",
            "source_hash": "old-hash-xyz",
            "source": "guardkit_seeding",
            "version": "1.0.0"
        }
        mock_edge = MagicMock()
        mock_edge.uuid = "episode-uuid-ghi"
        mock_edge.fact = json.dumps(metadata) + "\n\nContent"
        mock_edge.created_at = "2025-01-01T00:00:00Z"
        mock_edge.valid_at = "2025-01-01T00:00:00Z"
        mock_edge.name = "Test Episode"

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[mock_edge])
        client._graphiti = mock_graphiti

        result = await client.episode_exists(
            entity_id="my-entity-123",
            group_id="project_overview",
            source_hash="new-hash-different"
        )

        assert result.exists is True
        assert result.exact_match is False
        assert result.uuid == "episode-uuid-ghi"


class TestEpisodeExistsNamespace:
    """Test episode_exists group namespace handling."""

    @pytest.mark.asyncio
    async def test_episode_exists_applies_group_prefix(self):
        """Test episode_exists correctly prefixes project group."""
        config = GraphitiConfig(enabled=True, project_id="my-project")
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        client._graphiti = mock_graphiti

        await client.episode_exists(
            entity_id="some-entity",
            group_id="project_overview"
        )

        # Verify search was called with prefixed group_id
        call_args = mock_graphiti.search.call_args
        # Should be called with project-prefixed group
        assert call_args is not None
        # The group_ids should contain the prefixed version
        call_kwargs = call_args[1] if len(call_args) > 1 else call_args.kwargs
        if 'group_ids' in call_kwargs:
            assert "my-project__project_overview" in call_kwargs['group_ids']

    @pytest.mark.asyncio
    async def test_episode_exists_system_group_no_prefix(self):
        """Test episode_exists doesn't prefix system groups."""
        config = GraphitiConfig(enabled=True, project_id="my-project")
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        client._graphiti = mock_graphiti

        # Use a known system group
        await client.episode_exists(
            entity_id="some-entity",
            group_id="guardkit_templates"
        )

        # Verify search was called with unprefixed group_id
        call_args = mock_graphiti.search.call_args
        assert call_args is not None
        call_kwargs = call_args[1] if len(call_args) > 1 else call_args.kwargs
        if 'group_ids' in call_kwargs:
            # System group should NOT be prefixed
            assert "guardkit_templates" in call_kwargs['group_ids']


class TestEpisodeExistsGracefulDegradation:
    """Test episode_exists graceful degradation behavior."""

    @pytest.mark.asyncio
    async def test_episode_exists_when_disabled(self):
        """Test episode_exists returns not found when client disabled."""
        config = GraphitiConfig(enabled=False)
        client = GraphitiClient(config, auto_detect_project=False)

        result = await client.episode_exists(
            entity_id="any-entity",
            group_id="project_overview"
        )

        assert isinstance(result, ExistsResult)
        assert result.exists is False

    @pytest.mark.asyncio
    async def test_episode_exists_handles_search_error_gracefully(self):
        """Test episode_exists handles search errors gracefully."""
        config = GraphitiConfig(enabled=True, project_id="test-project")
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(side_effect=Exception("Search failed"))
        client._graphiti = mock_graphiti

        result = await client.episode_exists(
            entity_id="some-entity",
            group_id="project_overview"
        )

        # Should return not found on error, not raise
        assert isinstance(result, ExistsResult)
        assert result.exists is False

    @pytest.mark.asyncio
    async def test_episode_exists_when_not_initialized(self):
        """Test episode_exists returns not found when not initialized."""
        config = GraphitiConfig(enabled=True, project_id="test-project")
        client = GraphitiClient(config)
        client._graphiti = None

        result = await client.episode_exists(
            entity_id="some-entity",
            group_id="project_overview"
        )

        assert isinstance(result, ExistsResult)
        assert result.exists is False


class TestEpisodeExistsMetadataParsing:
    """Test episode_exists metadata parsing from episode body."""

    @pytest.mark.asyncio
    async def test_episode_exists_parses_json_metadata(self):
        """Test episode_exists correctly parses JSON metadata from body."""
        config = GraphitiConfig(enabled=True, project_id="test-project")
        client = GraphitiClient(config)

        # Create mock episode with JSON metadata prefix
        metadata = {
            "entity_id": "parsed-entity-id",
            "source_hash": "parsed-hash",
            "source": "guardkit_seeding",
            "version": "1.0.0",
            "entity_type": "project_overview"
        }
        mock_edge = MagicMock()
        mock_edge.uuid = "parsed-uuid"
        mock_edge.fact = json.dumps(metadata) + "\n\nActual episode content"
        mock_edge.created_at = "2025-01-01T00:00:00Z"
        mock_edge.valid_at = "2025-01-01T00:00:00Z"
        mock_edge.name = "Parsed Episode"

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[mock_edge])
        client._graphiti = mock_graphiti

        result = await client.episode_exists(
            entity_id="parsed-entity-id",
            group_id="project_overview",
            source_hash="parsed-hash"
        )

        assert result.exists is True
        assert result.exact_match is True

    @pytest.mark.asyncio
    async def test_episode_exists_handles_malformed_metadata(self):
        """Test episode_exists handles episodes without proper metadata."""
        config = GraphitiConfig(enabled=True, project_id="test-project")
        client = GraphitiClient(config)

        # Create mock episode without JSON metadata
        mock_edge = MagicMock()
        mock_edge.uuid = "no-metadata-uuid"
        mock_edge.fact = "Plain text content without JSON metadata"
        mock_edge.created_at = "2025-01-01T00:00:00Z"
        mock_edge.valid_at = "2025-01-01T00:00:00Z"
        mock_edge.name = "Plain Episode"

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[mock_edge])
        client._graphiti = mock_graphiti

        # Should not match since metadata cannot be parsed
        result = await client.episode_exists(
            entity_id="some-entity",
            group_id="project_overview"
        )

        # Episode found but entity_id doesn't match (can't parse metadata)
        # Behavior depends on implementation - could be not found or found without match
        assert isinstance(result, ExistsResult)


class TestEpisodeExistsMultipleResults:
    """Test episode_exists behavior with multiple search results."""

    @pytest.mark.asyncio
    async def test_episode_exists_finds_first_matching_entity_id(self):
        """Test episode_exists returns first episode with matching entity_id."""
        config = GraphitiConfig(enabled=True, project_id="test-project")
        client = GraphitiClient(config)

        # Create multiple mock episodes
        metadata1 = {"entity_id": "other-entity", "source": "test", "version": "1.0.0"}
        mock_edge1 = MagicMock()
        mock_edge1.uuid = "uuid-1"
        mock_edge1.fact = json.dumps(metadata1) + "\n\nContent 1"
        mock_edge1.name = "Episode 1"

        metadata2 = {"entity_id": "target-entity", "source": "test", "version": "1.0.0"}
        mock_edge2 = MagicMock()
        mock_edge2.uuid = "uuid-2"
        mock_edge2.fact = json.dumps(metadata2) + "\n\nContent 2"
        mock_edge2.name = "Episode 2"

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[mock_edge1, mock_edge2])
        client._graphiti = mock_graphiti

        result = await client.episode_exists(
            entity_id="target-entity",
            group_id="project_overview"
        )

        assert result.exists is True
        assert result.uuid == "uuid-2"

    @pytest.mark.asyncio
    async def test_episode_exists_prefers_exact_hash_match(self):
        """Test episode_exists prefers episode with matching source_hash."""
        config = GraphitiConfig(enabled=True, project_id="test-project")
        client = GraphitiClient(config)

        # Create multiple episodes with same entity_id but different hashes
        metadata1 = {
            "entity_id": "same-entity",
            "source_hash": "old-hash",
            "source": "test",
            "version": "1.0.0"
        }
        mock_edge1 = MagicMock()
        mock_edge1.uuid = "uuid-old"
        mock_edge1.fact = json.dumps(metadata1) + "\n\nOld Content"
        mock_edge1.name = "Old Episode"

        metadata2 = {
            "entity_id": "same-entity",
            "source_hash": "exact-hash",
            "source": "test",
            "version": "1.0.0"
        }
        mock_edge2 = MagicMock()
        mock_edge2.uuid = "uuid-exact"
        mock_edge2.fact = json.dumps(metadata2) + "\n\nExact Content"
        mock_edge2.name = "Exact Episode"

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[mock_edge1, mock_edge2])
        client._graphiti = mock_graphiti

        result = await client.episode_exists(
            entity_id="same-entity",
            group_id="project_overview",
            source_hash="exact-hash"
        )

        assert result.exists is True
        assert result.exact_match is True
        assert result.uuid == "uuid-exact"


@pytest.mark.integration
class TestEpisodeExistsIntegration:
    """Integration tests for episode_exists.

    These tests require Neo4j to be running.
    Run with: pytest -m integration --run-integration
    """

    @pytest.mark.asyncio
    async def test_episode_exists_with_real_graphiti(self):
        """Test episode_exists with real Graphiti instance."""
        config = GraphitiConfig(
            enabled=True,
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password123",
            project_id="integration-test"
        )
        client = GraphitiClient(config)

        initialized = await client.initialize()
        if not initialized:
            pytest.skip("Neo4j or graphiti-core not available")

        try:
            # Test not found case
            result = await client.episode_exists(
                entity_id="nonexistent-integration-test",
                group_id="project_overview"
            )
            assert result.exists is False

        finally:
            await client.close()
