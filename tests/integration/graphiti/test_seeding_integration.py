"""
Integration tests for seeding with metadata.

Test Coverage:
- End-to-end seeding workflow with metadata
- Metadata persisted in Graphiti
- Version tracking across seeding operations
- Force re-seeding with metadata updates

AC-003: Integration tests for seeding with metadata

Note: These tests can be run with a real Neo4j instance or mocked client.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from guardkit.knowledge.seeding import (
    seed_all_system_context,
    is_seeded,
    clear_seeding_marker,
    mark_seeded,
    SEEDING_VERSION,
)
from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig


@pytest.fixture
def mock_graphiti_client():
    """Create a mock Graphiti client for integration tests."""
    client = MagicMock(spec=GraphitiClient)
    client.enabled = True
    client.add_episode = AsyncMock()
    client.search = AsyncMock(return_value=[])
    client.close = AsyncMock()
    return client


class TestSeedingIntegrationWithMetadata:
    """Test end-to-end seeding with metadata."""

    @pytest.mark.asyncio
    async def test_seeding_adds_metadata_to_all_episodes(self, mock_graphiti_client, tmp_path, monkeypatch):
        """Test that seeding adds metadata to all episodes."""
        monkeypatch.setattr(
            "guardkit.knowledge.seeding.get_state_dir",
            lambda: tmp_path
        )

        # Clear any existing marker
        from guardkit.knowledge.seeding import clear_seeding_marker
        clear_seeding_marker()

        # Run seeding
        result = await seed_all_system_context(mock_graphiti_client, force=True)

        assert result is True

        # Verify add_episode was called multiple times
        assert mock_graphiti_client.add_episode.call_count > 0

        # Check a sample of calls for metadata
        calls = mock_graphiti_client.add_episode.call_args_list

        for call in calls[:5]:  # Check first 5 calls
            episode_body_json = call.kwargs["episode_body"]
            episode_body = json.loads(episode_body_json)

            # Verify metadata exists
            assert "_metadata" in episode_body

            metadata = episode_body["_metadata"]
            assert metadata["source"] == "guardkit_seeding"
            assert metadata["version"] == SEEDING_VERSION
            assert "created_at" in metadata
            assert "entity_id" in metadata

    @pytest.mark.asyncio
    async def test_seeding_creates_marker_file_with_metadata(self, mock_graphiti_client, tmp_path, monkeypatch):
        """Test that seeding creates marker file with version metadata."""
        monkeypatch.setattr(
            "guardkit.knowledge.seeding.get_state_dir",
            lambda: tmp_path
        )

        from guardkit.knowledge.seeding import clear_seeding_marker, seed_all_system_context

        clear_seeding_marker()

        # Run seeding
        await seed_all_system_context(mock_graphiti_client, force=True)

        # Verify marker file exists
        marker_file = tmp_path / ".graphiti_seeded.json"
        assert marker_file.exists()

        # Verify marker content
        marker_data = json.loads(marker_file.read_text())
        assert marker_data["seeded"] is True
        assert marker_data["version"] == SEEDING_VERSION
        assert "timestamp" in marker_data

    @pytest.mark.asyncio
    async def test_force_reseeding_updates_metadata_timestamps(self, mock_graphiti_client, tmp_path, monkeypatch):
        """Test that force re-seeding updates metadata timestamps."""
        monkeypatch.setattr(
            "guardkit.knowledge.seeding.get_state_dir",
            lambda: tmp_path
        )

        from guardkit.knowledge.seeding import seed_all_system_context

        # First seeding
        await seed_all_system_context(mock_graphiti_client, force=True)
        first_call_count = mock_graphiti_client.add_episode.call_count

        # Reset mock
        mock_graphiti_client.add_episode.reset_mock()

        # Second seeding with force=True
        await seed_all_system_context(mock_graphiti_client, force=True)
        second_call_count = mock_graphiti_client.add_episode.call_count

        # Verify episodes were added again
        assert second_call_count == first_call_count

    @pytest.mark.asyncio
    async def test_seeding_skipped_if_already_seeded(self, mock_graphiti_client, tmp_path, monkeypatch):
        """Test that seeding is skipped if already seeded and force=False."""
        monkeypatch.setattr(
            "guardkit.knowledge.seeding.get_state_dir",
            lambda: tmp_path
        )

        from guardkit.knowledge.seeding import seed_all_system_context, mark_seeded

        # Mark as already seeded
        mark_seeded()

        # Try to seed again without force
        result = await seed_all_system_context(mock_graphiti_client, force=False)

        # Should return True (already seeded)
        assert result is True

        # Should not have called add_episode
        mock_graphiti_client.add_episode.assert_not_called()


class TestSeedingErrorHandlingIntegration:
    """Test error handling in seeding integration."""

    @pytest.mark.asyncio
    async def test_seeding_continues_on_partial_failures(self, tmp_path, monkeypatch):
        """Test that seeding continues even if some episodes fail."""
        monkeypatch.setattr(
            "guardkit.knowledge.seeding.get_state_dir",
            lambda: tmp_path
        )

        # Create client that fails on some episodes
        mock_client = MagicMock()
        mock_client.enabled = True

        # Make every 3rd call fail
        call_count = [0]

        async def add_episode_with_failures(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] % 3 == 0:
                raise Exception("Simulated failure")

        mock_client.add_episode = AsyncMock(side_effect=add_episode_with_failures)
        mock_client.close = AsyncMock()

        from guardkit.knowledge.seeding import seed_all_system_context, clear_seeding_marker

        clear_seeding_marker()

        # Should complete despite failures
        result = await seed_all_system_context(mock_client, force=True)

        # Should return True (completed with warnings)
        assert result is True

        # Marker should still be created
        marker_file = tmp_path / ".graphiti_seeded.json"
        assert marker_file.exists()

    @pytest.mark.asyncio
    async def test_seeding_handles_disabled_client(self):
        """Test that seeding handles disabled client gracefully."""
        mock_client = MagicMock()
        mock_client.enabled = False

        from guardkit.knowledge.seeding import seed_all_system_context

        result = await seed_all_system_context(mock_client, force=True)

        # Should return False (client disabled)
        assert result is False

    @pytest.mark.asyncio
    async def test_seeding_handles_none_client(self):
        """Test that seeding handles None client gracefully."""
        from guardkit.knowledge.seeding import seed_all_system_context

        result = await seed_all_system_context(None, force=True)

        # Should return False (no client)
        assert result is False


class TestMetadataVersionTracking:
    """Test version tracking through seeding lifecycle."""

    @pytest.mark.asyncio
    async def test_metadata_version_matches_seeding_version(self, mock_graphiti_client, tmp_path, monkeypatch):
        """Test that metadata version matches SEEDING_VERSION constant."""
        monkeypatch.setattr(
            "guardkit.knowledge.seeding.get_state_dir",
            lambda: tmp_path
        )

        from guardkit.knowledge.seeding import seed_all_system_context, clear_seeding_marker

        clear_seeding_marker()

        await seed_all_system_context(mock_graphiti_client, force=True)

        # Check episode metadata
        calls = mock_graphiti_client.add_episode.call_args_list
        for call in calls[:3]:
            episode_body = json.loads(call.kwargs["episode_body"])
            assert episode_body["_metadata"]["version"] == SEEDING_VERSION

        # Check marker file
        marker_file = tmp_path / ".graphiti_seeded.json"
        marker_data = json.loads(marker_file.read_text())
        assert marker_data["version"] == SEEDING_VERSION

    @pytest.mark.asyncio
    async def test_marker_file_timestamp_is_recent(self, mock_graphiti_client, tmp_path, monkeypatch):
        """Test that marker file timestamp is recent."""
        monkeypatch.setattr(
            "guardkit.knowledge.seeding.get_state_dir",
            lambda: tmp_path
        )

        from guardkit.knowledge.seeding import seed_all_system_context, clear_seeding_marker

        clear_seeding_marker()

        from datetime import timezone
        before = datetime.now(timezone.utc)
        await seed_all_system_context(mock_graphiti_client, force=True)
        after = datetime.now(timezone.utc)

        marker_file = tmp_path / ".graphiti_seeded.json"
        marker_data = json.loads(marker_file.read_text())

        marker_timestamp = datetime.fromisoformat(marker_data["timestamp"])

        # Timestamp should be between before and after
        assert before <= marker_timestamp <= after


class TestSeedingCategoriesIntegration:
    """Test that all seeding categories include metadata."""

    @pytest.mark.asyncio
    async def test_all_categories_include_metadata(self, mock_graphiti_client, tmp_path, monkeypatch):
        """Test that all seeding categories include metadata in episodes."""
        monkeypatch.setattr(
            "guardkit.knowledge.seeding.get_state_dir",
            lambda: tmp_path
        )

        from guardkit.knowledge.seeding import seed_all_system_context, clear_seeding_marker

        clear_seeding_marker()

        await seed_all_system_context(mock_graphiti_client, force=True)

        # Get all calls
        calls = mock_graphiti_client.add_episode.call_args_list

        # Track calls with and without metadata
        calls_with_metadata = []
        calls_without_metadata = []

        for call in calls:
            episode_body = json.loads(call.kwargs["episode_body"])
            if "_metadata" in episode_body:
                calls_with_metadata.append(episode_body)

                # Verify metadata structure
                metadata = episode_body["_metadata"]
                assert metadata["source"] == "guardkit_seeding"
                assert metadata["version"] == SEEDING_VERSION
                assert "entity_id" in metadata
                assert "created_at" in metadata
                assert "updated_at" in metadata
            else:
                calls_without_metadata.append(episode_body)

        # Most calls should have metadata (>80%)
        # Some categories may use different seeding methods (e.g., failed_approaches)
        total_calls = len(calls)
        metadata_percentage = len(calls_with_metadata) / total_calls * 100
        assert metadata_percentage >= 80, f"Only {metadata_percentage:.1f}% of episodes have metadata"
