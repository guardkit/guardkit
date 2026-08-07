"""The writer tells the truth about whether an outcome reached the store.

``capture_task_outcome`` returns its generated ``OUT-`` id whether the episode
landed or not — the id is minted before any publish is attempted, and the
memory client underneath is fail-open (it catches everything and returns
``None``). That is the right behaviour for a call that must never break a
build, and the wrong thing to read if you want to say "captured" out loud.

``capture_task_outcome_verified`` is the honest variant: it hands back the
store's own episode key, or ``None`` and a plain reason.

The store call is faked in every test — no broker, no store, no network.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.knowledge.entities.outcome import OutcomeType
from guardkit.knowledge.outcome_manager import (
    OutcomeCapture,
    capture_task_outcome,
    capture_task_outcome_verified,
)

MANAGER = "guardkit.knowledge.outcome_manager"


def _client(add_episode_result=None, *, enabled: bool = True, raises=None) -> MagicMock:
    client = MagicMock()
    client.enabled = enabled
    if raises is not None:
        client.add_episode = AsyncMock(side_effect=raises)
    else:
        client.add_episode = AsyncMock(return_value=add_episode_result)
    return client


async def _capture(**overrides) -> OutcomeCapture:
    kwargs = dict(
        outcome_type=OutcomeType.TASK_COMPLETED,
        task_id="TASK-VER-001",
        task_title="Verified capture",
        task_requirements="Tell the truth about the write",
        success=True,
        summary="It worked",
    )
    kwargs.update(overrides)
    return await capture_task_outcome_verified(**kwargs)


class TestVerifiedCaptureReportsWhatHappened:
    """``stored`` is true only when the store handed back a key."""

    @pytest.mark.asyncio
    async def test_a_landed_write_carries_the_store_key(self):
        client = _client("build_outcome:guardkit:TASK_VER_001")

        with patch(f"{MANAGER}.get_memory_client", return_value=client):
            capture = await _capture()

        assert capture.stored is True
        assert capture.episode_key == "build_outcome:guardkit:TASK_VER_001"
        assert capture.outcome_id.startswith("OUT-")
        assert capture.detail is None
        client.add_episode.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_a_publish_that_stored_nothing_is_reported_as_not_stored(self):
        # This is the real failure shape: the broker unreachable or the writer
        # credential absent comes back as a quiet None, never an exception.
        client = _client(None)

        with patch(f"{MANAGER}.get_memory_client", return_value=client):
            capture = await _capture()

        assert capture.stored is False
        assert capture.episode_key is None
        assert capture.outcome_id.startswith("OUT-")
        assert "published nothing" in capture.detail

    @pytest.mark.asyncio
    async def test_a_not_stored_write_says_so_out_loud(self, caplog):
        client = _client(None)

        with caplog.at_level(logging.WARNING, logger=MANAGER), \
             patch(f"{MANAGER}.get_memory_client", return_value=client):
            capture = await _capture()

        messages = [r.getMessage() for r in caplog.records if r.name == MANAGER]
        assert any("was NOT stored" in m for m in messages), messages
        assert any(capture.outcome_id in m for m in messages), messages

    @pytest.mark.asyncio
    async def test_a_raising_writer_is_reported_not_raised(self):
        client = _client(raises=ConnectionRefusedError("nothing is listening"))

        with patch(f"{MANAGER}.get_memory_client", return_value=client):
            capture = await _capture()

        assert capture.stored is False
        assert "ConnectionRefusedError" in capture.detail

    @pytest.mark.asyncio
    async def test_memory_off_is_reported_without_a_write(self):
        client = _client("never", enabled=False)

        with patch(f"{MANAGER}.get_memory_client", return_value=client):
            capture = await _capture()

        assert capture.stored is False
        assert capture.detail == "memory is off"
        client.add_episode.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_a_missing_client_is_reported_without_a_write(self):
        with patch(f"{MANAGER}.get_memory_client", return_value=None):
            capture = await _capture()

        assert capture.stored is False
        assert "unavailable" in capture.detail


class TestTheOriginalCallIsUnchanged:
    """``capture_task_outcome`` keeps its old contract for its old callers."""

    @pytest.mark.asyncio
    async def test_it_still_returns_the_outcome_id_when_the_write_lands(self):
        client = _client("build_outcome:guardkit:TASK_VER_002")

        with patch(f"{MANAGER}.get_memory_client", return_value=client):
            outcome_id = await capture_task_outcome(
                outcome_type=OutcomeType.TASK_COMPLETED,
                task_id="TASK-VER-002",
                task_title="Old contract",
                task_requirements="unchanged",
                success=True,
                summary="ok",
            )

        assert outcome_id.startswith("OUT-")

    @pytest.mark.asyncio
    async def test_it_still_returns_an_id_when_nothing_was_stored(self):
        # Deliberate: the old contract is "you always get a name for this
        # outcome". That is exactly why a caller who needs to know whether the
        # write LANDED has to use the verified variant instead.
        client = _client(None)

        with patch(f"{MANAGER}.get_memory_client", return_value=client):
            outcome_id = await capture_task_outcome(
                outcome_type=OutcomeType.TASK_FAILED,
                task_id="TASK-VER-003",
                task_title="Old contract, failed write",
                task_requirements="unchanged",
                success=False,
                summary="ok",
            )

        assert outcome_id.startswith("OUT-")
