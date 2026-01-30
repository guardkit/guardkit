"""
Tests for seeding metadata validation and injection.

Test Coverage:
- Metadata schema validation
- Metadata injection into episode bodies
- Version tracking in metadata
- Timestamp validation in metadata
- Entity ID uniqueness in metadata
- Metadata schema completeness

AC-001: Unit tests for metadata schema validation
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from guardkit.knowledge.seeding import (
    _add_episodes,
    mark_seeded,
    get_state_dir,
    SEEDING_VERSION,
)


class TestMetadataSchemaValidation:
    """Test metadata schema validation."""

    @pytest.mark.asyncio
    async def test_metadata_injected_into_episode_body(self):
        """Test that _add_episodes injects _metadata block into episode body."""
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock()

        episode_body = {
            "entity_type": "test",
            "name": "Test Episode",
            "description": "Test description"
        }

        episodes = [("test_episode", episode_body)]

        await _add_episodes(mock_client, episodes, "test_group", "test_category")

        # Verify add_episode was called
        assert mock_client.add_episode.called
        call_args = mock_client.add_episode.call_args

        # Parse the episode_body argument (it's JSON string)
        episode_body_arg = json.loads(call_args.kwargs["episode_body"])

        # Verify metadata block exists
        assert "_metadata" in episode_body_arg
        metadata = episode_body_arg["_metadata"]

        # Verify metadata fields
        assert "source" in metadata
        assert "version" in metadata
        assert "created_at" in metadata
        assert "updated_at" in metadata
        assert "source_hash" in metadata
        assert "entity_id" in metadata

    @pytest.mark.asyncio
    async def test_metadata_contains_correct_values(self):
        """Test that metadata contains correct values."""
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock()

        episode_body = {"entity_type": "test"}
        episodes = [("test_episode_001", episode_body)]

        await _add_episodes(mock_client, episodes, "test_group", "test")

        call_args = mock_client.add_episode.call_args
        episode_body_arg = json.loads(call_args.kwargs["episode_body"])
        metadata = episode_body_arg["_metadata"]

        # Verify specific values
        assert metadata["source"] == "guardkit_seeding"
        assert metadata["version"] == SEEDING_VERSION
        assert metadata["entity_id"] == "test_episode_001"
        assert metadata["source_hash"] is None  # Generated content

    @pytest.mark.asyncio
    async def test_metadata_timestamps_are_iso_format(self):
        """Test that metadata timestamps are in ISO format."""
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock()

        episode_body = {"entity_type": "test"}
        episodes = [("test_episode", episode_body)]

        await _add_episodes(mock_client, episodes, "test_group", "test")

        call_args = mock_client.add_episode.call_args
        episode_body_arg = json.loads(call_args.kwargs["episode_body"])
        metadata = episode_body_arg["_metadata"]

        # Verify timestamps can be parsed as ISO format
        created_at = datetime.fromisoformat(metadata["created_at"])
        updated_at = datetime.fromisoformat(metadata["updated_at"])

        # Verify they are UTC
        assert created_at.tzinfo is not None
        assert updated_at.tzinfo is not None

    @pytest.mark.asyncio
    async def test_metadata_preserves_original_body_content(self):
        """Test that metadata injection preserves original episode body content."""
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock()

        episode_body = {
            "entity_type": "test",
            "name": "Test Episode",
            "description": "Test description",
            "custom_field": "custom_value"
        }

        episodes = [("test_episode", episode_body)]

        await _add_episodes(mock_client, episodes, "test_group", "test")

        call_args = mock_client.add_episode.call_args
        episode_body_arg = json.loads(call_args.kwargs["episode_body"])

        # Verify original fields are preserved
        assert episode_body_arg["entity_type"] == "test"
        assert episode_body_arg["name"] == "Test Episode"
        assert episode_body_arg["description"] == "Test description"
        assert episode_body_arg["custom_field"] == "custom_value"

        # And metadata is added
        assert "_metadata" in episode_body_arg


class TestMetadataVersionTracking:
    """Test version tracking in metadata."""

    @pytest.mark.asyncio
    async def test_metadata_includes_seeding_version(self):
        """Test that metadata includes the seeding version."""
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock()

        episodes = [("test_episode", {"entity_type": "test"})]
        await _add_episodes(mock_client, episodes, "test_group", "test")

        call_args = mock_client.add_episode.call_args
        episode_body_arg = json.loads(call_args.kwargs["episode_body"])

        assert episode_body_arg["_metadata"]["version"] == SEEDING_VERSION

    def test_marker_file_contains_version(self, tmp_path, monkeypatch):
        """Test that seeding marker file contains version."""
        # Use tmp_path for testing
        monkeypatch.setattr(
            "guardkit.knowledge.seeding.get_state_dir",
            lambda: tmp_path
        )

        from guardkit.knowledge.seeding import mark_seeded

        mark_seeded()

        marker_file = tmp_path / ".graphiti_seeded.json"
        assert marker_file.exists()

        marker_data = json.loads(marker_file.read_text())
        assert marker_data["version"] == SEEDING_VERSION
        assert marker_data["seeded"] is True


class TestMetadataEntityIDUniqueness:
    """Test entity ID uniqueness in metadata."""

    @pytest.mark.asyncio
    async def test_each_episode_has_unique_entity_id(self):
        """Test that each episode gets a unique entity_id based on name."""
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock()

        episodes = [
            ("episode_001", {"entity_type": "test"}),
            ("episode_002", {"entity_type": "test"}),
            ("episode_003", {"entity_type": "test"}),
        ]

        await _add_episodes(mock_client, episodes, "test_group", "test")

        # Get all calls to add_episode
        calls = mock_client.add_episode.call_args_list

        # Extract entity_ids from all calls
        entity_ids = []
        for call in calls:
            episode_body_arg = json.loads(call.kwargs["episode_body"])
            entity_ids.append(episode_body_arg["_metadata"]["entity_id"])

        # Verify uniqueness
        assert len(entity_ids) == 3
        assert len(set(entity_ids)) == 3
        assert "episode_001" in entity_ids
        assert "episode_002" in entity_ids
        assert "episode_003" in entity_ids


class TestMetadataErrorHandling:
    """Test error handling in metadata injection."""

    @pytest.mark.asyncio
    async def test_metadata_injection_continues_on_episode_failure(self):
        """Test that metadata injection continues even if one episode fails."""
        mock_client = MagicMock()
        mock_client.enabled = True

        # Make second episode fail
        mock_client.add_episode = AsyncMock(
            side_effect=[None, Exception("Episode failed"), None]
        )

        episodes = [
            ("episode_001", {"entity_type": "test"}),
            ("episode_002", {"entity_type": "test"}),
            ("episode_003", {"entity_type": "test"}),
        ]

        # Should not raise exception
        await _add_episodes(mock_client, episodes, "test_group", "test")

        # Should have tried all 3 episodes
        assert mock_client.add_episode.call_count == 3

    @pytest.mark.asyncio
    async def test_skips_seeding_when_client_disabled(self):
        """Test that seeding is skipped when client is disabled."""
        mock_client = MagicMock()
        mock_client.enabled = False
        mock_client.add_episode = AsyncMock()

        episodes = [("episode_001", {"entity_type": "test"})]

        await _add_episodes(mock_client, episodes, "test_group", "test")

        # Should not have called add_episode
        mock_client.add_episode.assert_not_called()


class TestMetadataSchemaCompleteness:
    """Test that metadata schema is complete and consistent."""

    @pytest.mark.asyncio
    async def test_all_required_metadata_fields_present(self):
        """Test that all required metadata fields are present."""
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock()

        episodes = [("test_episode", {"entity_type": "test"})]
        await _add_episodes(mock_client, episodes, "test_group", "test")

        call_args = mock_client.add_episode.call_args
        episode_body_arg = json.loads(call_args.kwargs["episode_body"])
        metadata = episode_body_arg["_metadata"]

        # Define required fields
        required_fields = [
            "source",
            "version",
            "created_at",
            "updated_at",
            "source_hash",
            "entity_id"
        ]

        # Verify all required fields are present
        for field in required_fields:
            assert field in metadata, f"Required field '{field}' missing from metadata"

    @pytest.mark.asyncio
    async def test_metadata_field_types_are_correct(self):
        """Test that metadata field types are correct."""
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock()

        episodes = [("test_episode", {"entity_type": "test"})]
        await _add_episodes(mock_client, episodes, "test_group", "test")

        call_args = mock_client.add_episode.call_args
        episode_body_arg = json.loads(call_args.kwargs["episode_body"])
        metadata = episode_body_arg["_metadata"]

        # Verify types
        assert isinstance(metadata["source"], str)
        assert isinstance(metadata["version"], str)
        assert isinstance(metadata["created_at"], str)
        assert isinstance(metadata["updated_at"], str)
        assert metadata["source_hash"] is None or isinstance(metadata["source_hash"], str)
        assert isinstance(metadata["entity_id"], str)
