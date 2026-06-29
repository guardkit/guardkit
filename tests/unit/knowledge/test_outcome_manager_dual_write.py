"""Tests for outcome_manager dual-write integration.

TASK-MEM08-004: Validates that capture_task_outcome uses get_memory_client()
and works correctly in dual-write mode.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from guardkit.knowledge.entities.outcome import OutcomeType


@pytest.fixture
def mock_dual_client():
    """Mock memory client (dual-write mode)."""
    client = AsyncMock()
    client.enabled = True
    client.add_episode = AsyncMock(return_value="graphiti-uuid")
    return client


@pytest.mark.asyncio
@patch("guardkit.knowledge.outcome_manager.get_memory_client")
async def test_capture_outcome_uses_memory_client(mock_get_client, mock_dual_client):
    """capture_task_outcome uses get_memory_client() instead of get_graphiti()."""
    from guardkit.knowledge.outcome_manager import capture_task_outcome

    mock_get_client.return_value = mock_dual_client

    outcome_id = await capture_task_outcome(
        outcome_type=OutcomeType.TASK_COMPLETED,
        task_id="TASK-001",
        task_title="Test task",
        task_requirements="Requirements",
        success=True,
        summary="Done",
    )

    # Verify get_memory_client was called (not get_graphiti)
    mock_get_client.assert_called_once()

    # Verify add_episode was called with correct args
    mock_dual_client.add_episode.assert_called_once()
    call_kwargs = mock_dual_client.add_episode.call_args.kwargs
    assert call_kwargs["group_id"] == "task_outcomes"
    assert "TASK-001" in call_kwargs["name"]

    # Returns generated outcome ID
    assert outcome_id.startswith("OUT-")


@pytest.mark.asyncio
@patch("guardkit.knowledge.outcome_manager.get_memory_client")
async def test_capture_outcome_graceful_when_client_none(mock_get_client):
    """capture_task_outcome degrades gracefully when memory client is None."""
    from guardkit.knowledge.outcome_manager import capture_task_outcome

    mock_get_client.return_value = None

    outcome_id = await capture_task_outcome(
        outcome_type=OutcomeType.TASK_COMPLETED,
        task_id="TASK-001",
        task_title="Test task",
        task_requirements="Requirements",
        success=True,
        summary="Done",
    )

    # Still returns outcome ID even when client unavailable
    assert outcome_id.startswith("OUT-")


@pytest.mark.asyncio
@patch("guardkit.knowledge.outcome_manager.get_memory_client")
async def test_capture_outcome_graceful_when_client_disabled(mock_get_client):
    """capture_task_outcome degrades gracefully when client is disabled."""
    from guardkit.knowledge.outcome_manager import capture_task_outcome

    mock_client = MagicMock()
    mock_client.enabled = False
    mock_get_client.return_value = mock_client

    outcome_id = await capture_task_outcome(
        outcome_type=OutcomeType.TASK_COMPLETED,
        task_id="TASK-001",
        task_title="Test task",
        task_requirements="Requirements",
        success=True,
        summary="Done",
    )

    # Still returns outcome ID
    assert outcome_id.startswith("OUT-")
