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
    async def test_metadata_passed_via_parameters(self):
        """Test that _add_episodes passes metadata via add_episode parameters."""
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock()

        episode_body = {
            "name": "Test Episode",
            "description": "Test description"
        }

        episodes = [("test_episode", episode_body)]

        await _add_episodes(mock_client, episodes, "test_group", "test_category", entity_type="test_entity")

        # Verify add_episode was called with correct parameters
        assert mock_client.add_episode.called
        call_args = mock_client.add_episode.call_args

        # Verify source parameter
        assert call_args.kwargs["source"] == "guardkit_seeding"

        # Verify entity_type parameter
        assert call_args.kwargs["entity_type"] == "test_entity"

        # Parse the episode_body argument (it's JSON string)
        episode_body_arg = json.loads(call_args.kwargs["episode_body"])

        # Verify body does NOT contain _metadata (injected by client)
        assert "_metadata" not in episode_body_arg

        # Verify body contains original data
        assert episode_body_arg["name"] == "Test Episode"
        assert episode_body_arg["description"] == "Test description"

    @pytest.mark.asyncio
    async def test_metadata_parameters_have_correct_values(self):
        """Test that metadata parameters have correct values."""
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock()

        episode_body = {"data": "test"}
        episodes = [("test_episode_001", episode_body)]

        await _add_episodes(mock_client, episodes, "test_group", "test", entity_type="test_type")

        call_args = mock_client.add_episode.call_args

        # Verify metadata passed via parameters
        assert call_args.kwargs["source"] == "guardkit_seeding"
        assert call_args.kwargs["entity_type"] == "test_type"
        assert call_args.kwargs["name"] == "test_episode_001"

        # Verify body is clean (no metadata fields)
        episode_body_arg = json.loads(call_args.kwargs["episode_body"])
        assert "_metadata" not in episode_body_arg
        assert "entity_type" not in episode_body_arg

    @pytest.mark.asyncio
    async def test_metadata_injection_handled_by_client(self):
        """Test that metadata injection is delegated to GraphitiClient."""
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock()

        episode_body = {"data": "test"}
        episodes = [("test_episode", episode_body)]

        await _add_episodes(mock_client, episodes, "test_group", "test", entity_type="test_type")

        call_args = mock_client.add_episode.call_args

        # Verify client receives source parameter for metadata injection
        assert "source" in call_args.kwargs
        assert call_args.kwargs["source"] == "guardkit_seeding"

        # Verify client receives entity_type for metadata injection
        assert "entity_type" in call_args.kwargs
        assert call_args.kwargs["entity_type"] == "test_type"

        # Verify episode body is clean (client will inject metadata)
        episode_body_arg = json.loads(call_args.kwargs["episode_body"])
        assert "_metadata" not in episode_body_arg

    @pytest.mark.asyncio
    async def test_clean_body_preserves_original_content(self):
        """Test that episode body preserves original content without metadata."""
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock()

        episode_body = {
            "name": "Test Episode",
            "description": "Test description",
            "custom_field": "custom_value"
        }

        episodes = [("test_episode", episode_body)]

        await _add_episodes(mock_client, episodes, "test_group", "test", entity_type="test_type")

        call_args = mock_client.add_episode.call_args
        episode_body_arg = json.loads(call_args.kwargs["episode_body"])

        # Verify original fields are preserved
        assert episode_body_arg["name"] == "Test Episode"
        assert episode_body_arg["description"] == "Test description"
        assert episode_body_arg["custom_field"] == "custom_value"

        # Verify no metadata in body (client will inject)
        assert "_metadata" not in episode_body_arg
        assert "entity_type" not in episode_body_arg


class TestMetadataVersionTracking:
    """Test version tracking in metadata."""

    @pytest.mark.asyncio
    async def test_source_parameter_identifies_seeding(self):
        """Test that source parameter identifies guardkit seeding."""
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock()

        episodes = [("test_episode", {"data": "test"})]
        await _add_episodes(mock_client, episodes, "test_group", "test", entity_type="test_type")

        call_args = mock_client.add_episode.call_args

        # Verify source parameter is passed correctly
        assert call_args.kwargs["source"] == "guardkit_seeding"

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
    async def test_each_episode_has_unique_name(self):
        """Test that each episode gets a unique name parameter."""
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock()

        episodes = [
            ("episode_001", {"data": "test1"}),
            ("episode_002", {"data": "test2"}),
            ("episode_003", {"data": "test3"}),
        ]

        await _add_episodes(mock_client, episodes, "test_group", "test", entity_type="test_type")

        # Get all calls to add_episode
        calls = mock_client.add_episode.call_args_list

        # Extract names from all calls
        names = []
        for call in calls:
            names.append(call.kwargs["name"])

        # Verify uniqueness
        assert len(names) == 3
        assert len(set(names)) == 3
        assert "episode_001" in names
        assert "episode_002" in names
        assert "episode_003" in names


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
    async def test_all_required_parameters_present(self):
        """Test that all required parameters are passed to add_episode."""
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock()

        episodes = [("test_episode", {"data": "test"})]
        await _add_episodes(mock_client, episodes, "test_group", "test", entity_type="test_type")

        call_args = mock_client.add_episode.call_args

        # Define required parameters for metadata injection
        required_params = [
            "name",
            "episode_body",
            "group_id",
            "source",
            "entity_type"
        ]

        # Verify all required parameters are present
        for param in required_params:
            assert param in call_args.kwargs, f"Required parameter '{param}' missing from add_episode call"

    @pytest.mark.asyncio
    async def test_parameter_types_are_correct(self):
        """Test that parameter types passed to add_episode are correct."""
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock()

        episodes = [("test_episode", {"data": "test"})]
        await _add_episodes(mock_client, episodes, "test_group", "test", entity_type="test_type")

        call_args = mock_client.add_episode.call_args

        # Verify parameter types
        assert isinstance(call_args.kwargs["name"], str)
        assert isinstance(call_args.kwargs["episode_body"], str)  # JSON string
        assert isinstance(call_args.kwargs["group_id"], str)
        assert isinstance(call_args.kwargs["source"], str)
        assert isinstance(call_args.kwargs["entity_type"], str)
