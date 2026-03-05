"""
Tests for guardkit.knowledge.seed_helpers._add_episodes

Covers:
- Return type (created, skipped) tuple
- Circuit breaker skip counting (None returns)
- Exception handling counting
- Disabled client early return
- Orchestrator integration with new return type

Coverage Target: >=85%
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from guardkit.knowledge.seed_helpers import _add_episodes


class TestAddEpisodesReturnType:
    """Test _add_episodes returns (created, skipped) tuple."""

    @pytest.mark.asyncio
    async def test_returns_tuple_on_success(self):
        """All episodes created successfully returns (N, 0)."""
        client = AsyncMock()
        client.enabled = True
        client.add_episode = AsyncMock(return_value="episode_id")

        episodes = [
            ("ep1", {"key": "val1"}),
            ("ep2", {"key": "val2"}),
            ("ep3", {"key": "val3"}),
        ]

        result = await _add_episodes(client, episodes, "grp", "test")
        assert result == (3, 0)

    @pytest.mark.asyncio
    async def test_returns_zero_tuple_when_disabled(self):
        """Disabled client returns (0, 0) immediately."""
        client = AsyncMock()
        client.enabled = False

        episodes = [("ep1", {"key": "val"})]

        result = await _add_episodes(client, episodes, "grp", "test")
        assert result == (0, 0)
        client.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_zero_tuple_for_empty_episodes(self):
        """Empty episodes list returns (0, 0)."""
        client = AsyncMock()
        client.enabled = True

        result = await _add_episodes(client, [], "grp", "test")
        assert result == (0, 0)


class TestCircuitBreakerCounting:
    """Test that circuit-breaker-blocked episodes (None returns) are counted as skipped."""

    @pytest.mark.asyncio
    async def test_none_return_counted_as_skipped(self):
        """add_episode returning None counts as skipped."""
        client = AsyncMock()
        client.enabled = True
        client.add_episode = AsyncMock(return_value=None)

        episodes = [
            ("ep1", {"key": "val1"}),
            ("ep2", {"key": "val2"}),
        ]

        result = await _add_episodes(client, episodes, "grp", "test")
        assert result == (0, 2)

    @pytest.mark.asyncio
    async def test_mixed_success_and_none(self):
        """Mix of successful and None returns are counted correctly."""
        client = AsyncMock()
        client.enabled = True
        client.add_episode = AsyncMock(
            side_effect=["id1", None, "id3", None, None]
        )

        episodes = [
            ("ep1", {"k": "v"}),
            ("ep2", {"k": "v"}),
            ("ep3", {"k": "v"}),
            ("ep4", {"k": "v"}),
            ("ep5", {"k": "v"}),
        ]

        result = await _add_episodes(client, episodes, "grp", "test")
        assert result == (2, 3)

    @pytest.mark.asyncio
    async def test_exception_counted_as_skipped(self):
        """Exception during add_episode counts as skipped."""
        client = AsyncMock()
        client.enabled = True
        client.add_episode = AsyncMock(
            side_effect=[Exception("timeout"), "id2"]
        )

        episodes = [
            ("ep1", {"k": "v"}),
            ("ep2", {"k": "v"}),
        ]

        result = await _add_episodes(client, episodes, "grp", "test")
        assert result == (1, 1)

    @pytest.mark.asyncio
    async def test_all_exceptions_counted_as_skipped(self):
        """All exceptions returns (0, N)."""
        client = AsyncMock()
        client.enabled = True
        client.add_episode = AsyncMock(side_effect=Exception("fail"))

        episodes = [
            ("ep1", {"k": "v"}),
            ("ep2", {"k": "v"}),
            ("ep3", {"k": "v"}),
        ]

        result = await _add_episodes(client, episodes, "grp", "test")
        assert result == (0, 3)


class TestAddEpisodesCallsClient:
    """Test _add_episodes passes correct args to client.add_episode."""

    @pytest.mark.asyncio
    async def test_passes_correct_kwargs(self):
        """Verify correct kwargs are passed to add_episode."""
        client = AsyncMock()
        client.enabled = True
        client.add_episode = AsyncMock(return_value="id")

        episodes = [("test_ep", {"content": "data"})]

        await _add_episodes(
            client, episodes, "my_group", "my category",
            entity_type="custom_type"
        )

        client.add_episode.assert_called_once_with(
            name="test_ep",
            episode_body=json.dumps({"content": "data"}),
            group_id="my_group",
            source="guardkit_seeding",
            entity_type="custom_type",
        )
