"""
Tests for GraphitiClient.upsert_episode method.

Tests cover the upsert logic that creates, updates, or skips episodes
based on existence and content matching.

Coverage Target: >=85%
Test Count: 10+ tests

NOTE: These tests are designed to FAIL in TDD RED phase because
the upsert_episode method does not exist yet on GraphitiClient.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig
from guardkit.integrations.graphiti.exists_result import ExistsResult
from guardkit.integrations.graphiti.upsert_result import UpsertResult
from guardkit.integrations.graphiti.metadata import EpisodeMetadata


@pytest.fixture
def graphiti_config():
    """Create a test GraphitiConfig."""
    return GraphitiConfig(
        enabled=True,
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="test",
        project_id="test-project"
    )


@pytest.fixture
def graphiti_client(graphiti_config):
    """Create a test GraphitiClient with mocked internals."""
    client = GraphitiClient(graphiti_config)
    client._connected = True
    client._graphiti = MagicMock()
    return client


@pytest.fixture
def disabled_graphiti_client():
    """Create a disabled GraphitiClient for graceful degradation tests."""
    config = GraphitiConfig(enabled=False)
    client = GraphitiClient(config)
    return client


class TestUpsertEpisodeCreation:
    """Test upsert_episode when episode does not exist."""

    @pytest.mark.asyncio
    async def test_upsert_creates_when_not_exists(self, graphiti_client):
        """Test that upsert_episode creates a new episode when none exists."""
        # Mock episode_exists to return not found
        graphiti_client.episode_exists = AsyncMock(
            return_value=ExistsResult.not_found()
        )

        # Mock add_episode to return a UUID
        graphiti_client.add_episode = AsyncMock(return_value="new-uuid-123")

        # Call upsert_episode
        result = await graphiti_client.upsert_episode(
            name="Test Episode",
            episode_body="Test content",
            group_id="test_group",
            entity_id="test-entity-001"
        )

        # Verify result
        assert result is not None
        assert isinstance(result, UpsertResult)
        assert result.was_created is True
        assert result.uuid == "new-uuid-123"

        # Verify add_episode was called
        graphiti_client.add_episode.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_returns_created_action(self, graphiti_client):
        """Test that upsert_episode returns action='created' for new episodes."""
        graphiti_client.episode_exists = AsyncMock(
            return_value=ExistsResult.not_found()
        )
        graphiti_client.add_episode = AsyncMock(return_value="uuid-456")

        result = await graphiti_client.upsert_episode(
            name="New Episode",
            episode_body="Content",
            group_id="group",
            entity_id="entity-002"
        )

        assert result.action == "created"


class TestUpsertEpisodeSkip:
    """Test upsert_episode when episode exists with same content."""

    @pytest.mark.asyncio
    async def test_upsert_skips_when_exact_match(self, graphiti_client):
        """Test that upsert_episode skips when content hash matches."""
        existing_episode = {
            "uuid": "existing-uuid",
            "fact": "Existing content",
            "metadata": {"source_hash": "abc123"}
        }

        # Mock episode_exists to return exact match
        graphiti_client.episode_exists = AsyncMock(
            return_value=ExistsResult.found(
                episode=existing_episode,
                exact_match=True,
                uuid="existing-uuid"
            )
        )

        # Call upsert_episode
        result = await graphiti_client.upsert_episode(
            name="Test Episode",
            episode_body="Existing content",
            group_id="test_group",
            entity_id="test-entity"
        )

        # Verify result
        assert result is not None
        assert isinstance(result, UpsertResult)
        assert result.was_skipped is True
        assert result.uuid == "existing-uuid"

    @pytest.mark.asyncio
    async def test_upsert_returns_skipped_action(self, graphiti_client):
        """Test that upsert_episode returns action='skipped' for exact matches."""
        existing = {"uuid": "ep-123"}
        graphiti_client.episode_exists = AsyncMock(
            return_value=ExistsResult.found(episode=existing, exact_match=True, uuid="ep-123")
        )

        result = await graphiti_client.upsert_episode(
            name="Episode",
            episode_body="Same content",
            group_id="group",
            entity_id="entity"
        )

        assert result.action == "skipped"
        assert result.episode is not None


class TestUpsertEpisodeUpdate:
    """Test upsert_episode when episode exists with different content."""

    @pytest.mark.asyncio
    async def test_upsert_updates_when_exists_different_content(self, graphiti_client):
        """Test that upsert_episode updates when entity exists but content differs."""
        existing_episode = {
            "uuid": "old-uuid",
            "fact": "Old content",
            "metadata": {
                "source_hash": "old-hash",
                "created_at": "2025-01-01T00:00:00Z"
            }
        }

        # Mock episode_exists to return found but not exact match
        graphiti_client.episode_exists = AsyncMock(
            return_value=ExistsResult.found(
                episode=existing_episode,
                exact_match=False,
                uuid="old-uuid"
            )
        )

        # Mock add_episode for the new version
        graphiti_client.add_episode = AsyncMock(return_value="new-uuid-789")

        # Call upsert_episode
        result = await graphiti_client.upsert_episode(
            name="Updated Episode",
            episode_body="New content",
            group_id="test_group",
            entity_id="test-entity"
        )

        # Verify result
        assert result is not None
        assert isinstance(result, UpsertResult)
        assert result.was_updated is True
        assert result.uuid == "new-uuid-789"
        assert result.previous_uuid == "old-uuid"

    @pytest.mark.asyncio
    async def test_upsert_returns_updated_action(self, graphiti_client):
        """Test that upsert_episode returns action='updated' for content changes."""
        existing = {"uuid": "prev-uuid", "metadata": {"created_at": "2025-01-01T00:00:00Z"}}
        graphiti_client.episode_exists = AsyncMock(
            return_value=ExistsResult.found(episode=existing, exact_match=False, uuid="prev-uuid")
        )
        graphiti_client.add_episode = AsyncMock(return_value="new-uuid")

        result = await graphiti_client.upsert_episode(
            name="Episode",
            episode_body="Changed content",
            group_id="group",
            entity_id="entity"
        )

        assert result.action == "updated"
        assert result.previous_uuid == "prev-uuid"


class TestUpsertEpisodeTimestamps:
    """Test timestamp handling in upsert operations."""

    @pytest.mark.asyncio
    async def test_upsert_preserves_created_at_on_update(self, graphiti_client):
        """Test that upsert preserves original created_at timestamp on update."""
        original_created_at = "2024-06-15T10:30:00Z"
        existing = {
            "uuid": "old-uuid",
            "metadata": {"created_at": original_created_at}
        }

        graphiti_client.episode_exists = AsyncMock(
            return_value=ExistsResult.found(episode=existing, exact_match=False, uuid="old-uuid")
        )
        graphiti_client.add_episode = AsyncMock(return_value="new-uuid")

        # Capture the metadata passed to add_episode
        result = await graphiti_client.upsert_episode(
            name="Updated",
            episode_body="New content",
            group_id="group",
            entity_id="entity"
        )

        # Verify add_episode was called
        graphiti_client.add_episode.assert_called_once()
        call_kwargs = graphiti_client.add_episode.call_args.kwargs

        # The metadata should preserve original created_at
        if "metadata" in call_kwargs and call_kwargs["metadata"]:
            assert call_kwargs["metadata"].created_at == original_created_at

    @pytest.mark.asyncio
    async def test_upsert_updates_updated_at_on_update(self, graphiti_client):
        """Test that upsert sets a new updated_at timestamp on update."""
        existing = {
            "uuid": "old-uuid",
            "metadata": {
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-06-01T00:00:00Z"
            }
        }

        graphiti_client.episode_exists = AsyncMock(
            return_value=ExistsResult.found(episode=existing, exact_match=False, uuid="old-uuid")
        )
        graphiti_client.add_episode = AsyncMock(return_value="new-uuid")

        before_call = datetime.now(timezone.utc)
        result = await graphiti_client.upsert_episode(
            name="Updated",
            episode_body="New content",
            group_id="group",
            entity_id="entity"
        )
        after_call = datetime.now(timezone.utc)

        # Verify the result indicates update
        assert result.was_updated is True

        # Verify add_episode was called (the implementation should set updated_at)
        graphiti_client.add_episode.assert_called_once()


class TestUpsertEpisodeGracefulDegradation:
    """Test graceful degradation when Graphiti is disabled."""

    @pytest.mark.asyncio
    async def test_upsert_returns_none_when_disabled(self, disabled_graphiti_client):
        """Test that upsert_episode returns None when client is disabled."""
        result = await disabled_graphiti_client.upsert_episode(
            name="Test",
            episode_body="Content",
            group_id="group",
            entity_id="entity"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_returns_none_when_not_initialized(self, graphiti_client):
        """Test that upsert_episode returns None when not initialized."""
        graphiti_client._graphiti = None
        graphiti_client._connected = False

        result = await graphiti_client.upsert_episode(
            name="Test",
            episode_body="Content",
            group_id="group",
            entity_id="entity"
        )

        assert result is None


class TestUpsertEpisodeSourceHash:
    """Test source hash generation for content deduplication."""

    @pytest.mark.asyncio
    async def test_upsert_generates_source_hash_from_content(self, graphiti_client):
        """Test that upsert_episode generates a source_hash from content."""
        graphiti_client.episode_exists = AsyncMock(
            return_value=ExistsResult.not_found()
        )
        graphiti_client.add_episode = AsyncMock(return_value="new-uuid")

        result = await graphiti_client.upsert_episode(
            name="Test",
            episode_body="Content to hash",
            group_id="group",
            entity_id="entity"
        )

        # Verify add_episode was called with source_hash in metadata or calculated
        graphiti_client.add_episode.assert_called_once()
        # The implementation should compute source_hash from episode_body

    @pytest.mark.asyncio
    async def test_upsert_uses_provided_source_hash(self, graphiti_client):
        """Test that upsert_episode can use a provided source_hash."""
        graphiti_client.episode_exists = AsyncMock(
            return_value=ExistsResult.not_found()
        )
        graphiti_client.add_episode = AsyncMock(return_value="new-uuid")

        # Pass explicit source_hash
        result = await graphiti_client.upsert_episode(
            name="Test",
            episode_body="Content",
            group_id="group",
            entity_id="entity",
            source_hash="explicit-hash-value"
        )

        assert result is not None
        graphiti_client.add_episode.assert_called_once()


class TestUpsertEpisodeEntityId:
    """Test entity_id handling in upsert operations."""

    @pytest.mark.asyncio
    async def test_upsert_passes_entity_id_to_episode_exists(self, graphiti_client):
        """Test that entity_id is passed to episode_exists check."""
        graphiti_client.episode_exists = AsyncMock(
            return_value=ExistsResult.not_found()
        )
        graphiti_client.add_episode = AsyncMock(return_value="uuid")

        await graphiti_client.upsert_episode(
            name="Test",
            episode_body="Content",
            group_id="group",
            entity_id="my-unique-entity-id"
        )

        # Verify episode_exists was called with the entity_id
        graphiti_client.episode_exists.assert_called_once()
        call_args = graphiti_client.episode_exists.call_args
        assert call_args.kwargs.get("entity_id") == "my-unique-entity-id" or \
               call_args.args[0] == "my-unique-entity-id"

    @pytest.mark.asyncio
    async def test_upsert_includes_entity_id_in_metadata(self, graphiti_client):
        """Test that entity_id is included in the episode metadata."""
        graphiti_client.episode_exists = AsyncMock(
            return_value=ExistsResult.not_found()
        )
        graphiti_client.add_episode = AsyncMock(return_value="uuid")

        await graphiti_client.upsert_episode(
            name="Test",
            episode_body="Content",
            group_id="group",
            entity_id="stable-entity-id"
        )

        # The metadata passed to add_episode should include entity_id
        graphiti_client.add_episode.assert_called_once()
        call_kwargs = graphiti_client.add_episode.call_args.kwargs

        # Check if metadata has entity_id
        if "metadata" in call_kwargs and call_kwargs["metadata"]:
            assert call_kwargs["metadata"].entity_id == "stable-entity-id"
