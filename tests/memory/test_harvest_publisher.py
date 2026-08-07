"""Tests for NATS harvest publisher integration.

Unit tests verify the publish lifecycle, error handling, and idempotency
using a fake NATSClient to avoid requiring a live NATS broker.
"""

from __future__ import annotations

import asyncio
import logging
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

# The `memory` extra (nats-core, a [tool.uv.sources] editable sibling) is not
# installed in CI. Skip the whole module cleanly when it is absent rather than
# erroring at collection.
pytest.importorskip("nats_core.events")

from nats_core.events import MemoryEpisodeV1
from pydantic import SecretStr

from guardkit.memory import harvest_publisher
from guardkit.memory.harvest_publisher import (
    build_nats_client,
    publish_episodes,
    read_nats_password,
)


class TestReadNatsPassword:
    """Test password reading from environment."""

    def test_reads_password_from_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Read GUARDKIT_NATS_PASSWORD from environment."""
        monkeypatch.setenv("GUARDKIT_NATS_PASSWORD", "test-password-123")
        password = read_nats_password()
        assert password == "test-password-123"

    def test_raises_actionable_error_when_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Raise ValueError with actionable message when password is missing."""
        monkeypatch.delenv("GUARDKIT_NATS_PASSWORD", raising=False)
        with pytest.raises(ValueError, match=r"GUARDKIT_NATS_PASSWORD.*environment"):
            read_nats_password()

    def test_raises_actionable_error_when_blank(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Raise ValueError when password is blank/whitespace."""
        monkeypatch.setenv("GUARDKIT_NATS_PASSWORD", "   ")
        with pytest.raises(ValueError, match=r"GUARDKIT_NATS_PASSWORD.*blank"):
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
        """Verify connect → publish x N → disconnect ordering."""
        summary = await publish_episodes(sample_episodes, fake_client)

        # Verify lifecycle ordering
        fake_client.connect.assert_awaited_once()
        assert fake_client.publish_episode.await_count == 2
        fake_client.disconnect.assert_awaited_once()

        # Verify disconnect was called (not close) - check method_calls
        method_names = [mc[0] for mc in fake_client.method_calls]
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
                msg = (
                    f"memory episode body is {len(ep.body.encode())} bytes, "
                    f"exceeding the 921600 byte (900KB) limit; "
                    f"chunk the content upstream"
                )
                raise ValueError(msg)

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


class TestHangingUpIsBounded:
    """A stalled broker must not hold the caller open while we say goodbye.

    ``NATSClient.disconnect`` calls ``nc.drain()``, and nats-py's drain waits on
    the server with its own thirty-second default. A caller that already has a
    deadline of its own — the autobuild terminal's build-outcome capture has one
    — inherited that thirty seconds ON TOP of its deadline, because the close
    runs in the publisher's ``finally`` after the deadline has already fired.

    Nothing here reaches a broker: the connection is a fake that never answers.
    """

    def _stalled_client(self) -> MagicMock:
        """A client that connects and publishes fine, then never hangs up."""
        client = MagicMock()
        client.connect = AsyncMock()
        client.publish_episode = AsyncMock()

        async def _never_finishes() -> None:
            await asyncio.sleep(30)

        client.disconnect = AsyncMock(side_effect=_never_finishes)
        return client

    async def test_a_stalled_close_does_not_hold_the_caller(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        monkeypatch.setattr(
            harvest_publisher, "PUBLISH_TEARDOWN_TIMEOUT_SECONDS", 0.05
        )
        client = self._stalled_client()

        with caplog.at_level(logging.WARNING, logger=harvest_publisher.__name__):
            started = time.monotonic()
            summary = await publish_episodes([], client)
            elapsed = time.monotonic() - started

        # Bounded by the teardown budget, not by nats-py's 30-second drain.
        assert elapsed < 1.0, elapsed
        # And the run still reports its own result rather than raising.
        assert summary.published == 0
        assert any(
            "did not finish closing" in r.getMessage() for r in caplog.records
        ), [r.getMessage() for r in caplog.records]

    async def test_a_close_that_fails_is_logged_not_raised(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The teardown must never be what escapes a ``finally``."""
        client = MagicMock()
        client.connect = AsyncMock()
        client.publish_episode = AsyncMock()
        client.disconnect = AsyncMock(side_effect=OSError("socket already gone"))

        with caplog.at_level(logging.WARNING, logger=harvest_publisher.__name__):
            summary = await publish_episodes([], client)

        assert summary.published == 0
        assert any(
            "socket already gone" in r.getMessage() for r in caplog.records
        )

    async def test_a_failing_close_never_masks_the_real_error(self) -> None:
        """The publish error is what the caller must see, not the goodbye."""
        client = MagicMock()
        client.connect = AsyncMock()
        client.publish_episode = AsyncMock(side_effect=RuntimeError("publish blew up"))
        client.disconnect = AsyncMock(side_effect=OSError("socket already gone"))

        episodes = [
            MemoryEpisodeV1(
                episode_id="ep-mask",
                project_id="guardkit",
                episode_type="test",
                content_format="text",
                body="Content",
            )
        ]

        with pytest.raises(RuntimeError, match="publish blew up"):
            await publish_episodes(episodes, client)


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
