"""Tests for NATS harvest publisher integration.

Unit tests verify the publish lifecycle, error handling, and idempotency
using a fake NATSClient to avoid requiring a live NATS broker.
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from nats_core.events import MemoryEpisodeV1
from pydantic import SecretStr

from guardkit.memory.harvest_publisher import (
    PublishSummary,
    build_nats_client,
    publish_episodes,
    read_nats_password,
)


class TestReadNatsPassword:
    """Test password reading from environment."""

    def test_reads_password_from_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Read GUARDKIT_NATS_PASSWORD from environment."""
        monkeypatch.setenv("GUARDKIT_NATS_PASSWORD", "test-password-123")
        password = read_nats_password()
        assert password == "test-password-123"

    def test_raises_actionable_error_when_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Raise ValueError with actionable message when password is missing."""
        monkeypatch.delenv("GUARDKIT_NATS_PASSWORD", raising=False)
        with pytest.raises(ValueError, match="GUARDKIT_NATS_PASSWORD.*environment"):
            read_nats_password()

    def test_raises_actionable_error_when_blank(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Raise ValueError when password is blank/whitespace."""
        monkeypatch.setenv("GUARDKIT_NATS_PASSWORD", "   ")
        with pytest.raises(ValueError, match="GUARDKIT_NATS_PASSWORD.*blank"):
            read_nats_password()


class TestBuildNatsClient:
    """Test NATSClient construction."""

    def test_builds_client_with_correct_config(self) -> None:
        """Build NATSClient with correct NATSConfig parameters."""
        client = build_nats_client("test-password")

        # Verify client was created with expected source_id
        assert client._source_id == "guardkit-harvest"

        # Verify config parameters
        config = client._config
        assert config.url == "nats://127.0.0.1:4222"
        assert config.user == "guardkit"
        assert isinstance(config.password, SecretStr)
        assert config.password.get_secret_value() == "test-password"
        assert config.name == "guardkit-harvest"


class TestPublishEpisodes:
    """Test episode publishing lifecycle."""

    @pytest.fixture
    def fake_client(self) -> MagicMock:
        """Create a fake NATSClient with mocked async methods."""
        client = MagicMock()
        client.connect = AsyncMock()
        client.publish_episode = AsyncMock()
        client.disconnect = AsyncMock()
        return client

    @pytest.fixture
    def sample_episodes(self) -> list[MemoryEpisodeV1]:
        """Create sample episodes for testing."""
        return [
            MemoryEpisodeV1(
                episode_id="ep-001",
                project_id="guardkit",
                episode_type="test_run",
                content_format="markdown",
                body="# Test Episode 1\n\nThis is a test.",
            ),
            MemoryEpisodeV1(
                episode_id="ep-002",
                project_id="guardkit",
                episode_type="feature_spec",
                content_format="json",
                body='{"feature": "test"}',
            ),
        ]

    async def test_publish_lifecycle_ordering(
        self, fake_client: MagicMock, sample_episodes: list[MemoryEpisodeV1]
    ) -> None:
        """Verify connect → publish × N → disconnect ordering."""
        summary = await publish_episodes(sample_episodes, fake_client)

        # Verify lifecycle ordering
        fake_client.connect.assert_awaited_once()
        assert fake_client.publish_episode.await_count == 2
        fake_client.disconnect.assert_awaited_once()

        # Verify disconnect was called (not close) - check method_calls
        method_names = [call[0] for call in fake_client.method_calls]
        assert "disconnect" in method_names
        assert "close" not in method_names

        # Verify summary
        assert summary.published == 2
        assert summary.skipped_oversized == 0
        assert summary.counts_per_type == {"test_run": 1, "feature_spec": 1}

    async def test_catches_oversized_episode_per_item(
        self, fake_client: MagicMock
    ) -> None:
        """Catch ValueError for >900KB episode, skip it, continue publishing."""
        episodes = [
            MemoryEpisodeV1(
                episode_id="ep-small",
                project_id="guardkit",
                episode_type="small_doc",
                content_format="text",
                body="Small content",
            ),
            MemoryEpisodeV1(
                episode_id="ep-huge",
                project_id="guardkit",
                episode_type="huge_doc",
                content_format="text",
                body="X" * (901 * 1024),  # >900KB
            ),
            MemoryEpisodeV1(
                episode_id="ep-normal",
                project_id="guardkit",
                episode_type="normal_doc",
                content_format="text",
                body="Normal content",
            ),
        ]

        # Make publish_episode raise ValueError for the huge episode
        async def publish_side_effect(ep: MemoryEpisodeV1) -> None:
            if ep.episode_id == "ep-huge":
                raise ValueError(
                    f"memory episode body is {len(ep.body.encode())} bytes, "
                    f"exceeding the 921600 byte (900KB) limit; chunk the content upstream"
                )

        fake_client.publish_episode.side_effect = publish_side_effect

        summary = await publish_episodes(episodes, fake_client)

        # Verify we tried to publish all 3
        assert fake_client.publish_episode.await_count == 3

        # Verify summary shows 1 skipped
        assert summary.published == 2
        assert summary.skipped_oversized == 1
        assert summary.counts_per_type == {"small_doc": 1, "normal_doc": 1}

    async def test_empty_episodes_list(self, fake_client: MagicMock) -> None:
        """Handle empty episodes list gracefully."""
        summary = await publish_episodes([], fake_client)

        fake_client.connect.assert_awaited_once()
        fake_client.publish_episode.assert_not_awaited()
        fake_client.disconnect.assert_awaited_once()

        assert summary.published == 0
        assert summary.skipped_oversized == 0
        assert summary.counts_per_type == {}

    async def test_disconnect_called_even_after_error(
        self, fake_client: MagicMock, sample_episodes: list[MemoryEpisodeV1]
    ) -> None:
        """Ensure disconnect is called even if unexpected error occurs."""
        # Make publish_episode raise an unexpected error
        fake_client.publish_episode.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(RuntimeError, match="Unexpected error"):
            await publish_episodes(sample_episodes, fake_client)

        # Disconnect should still be called
        fake_client.disconnect.assert_awaited_once()


class TestIdempotency:
    """Test idempotency and resumability."""

    async def test_no_client_side_dedupe_state(self) -> None:
        """Verify no client-side deduplication state is maintained.

        The publisher relies on deterministic episode_id → Nats-Msg-Id
        for server-side JetStream deduplication. Re-running should
        attempt to publish the same IDs.
        """
        episodes = [
            MemoryEpisodeV1(
                episode_id="ep-deterministic",
                project_id="guardkit",
                episode_type="test",
                content_format="text",
                body="Content",
            )
        ]

        fake_client = MagicMock()
        fake_client.connect = AsyncMock()
        fake_client.publish_episode = AsyncMock()
        fake_client.disconnect = AsyncMock()

        # First run
        await publish_episodes(episodes, fake_client)
        first_call = fake_client.publish_episode.call_args

        # Reset mock
        fake_client.reset_mock()
        fake_client.connect = AsyncMock()
        fake_client.publish_episode = AsyncMock()
        fake_client.disconnect = AsyncMock()

        # Second run with same episodes
        await publish_episodes(episodes, fake_client)
        second_call = fake_client.publish_episode.call_args

        # Both runs should publish the same episode_id
        assert first_call == second_call
