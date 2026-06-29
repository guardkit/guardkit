"""Tests for ADR service dual-write integration.

TASK-MEM08-004: Validates that ADRService works with memory client
(supports both GraphitiClient and DualWriteClient).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from guardkit.knowledge.adr import ADREntity, ADRStatus, ADRTrigger
from guardkit.knowledge.adr_service import ADRService


@pytest.fixture
def mock_dual_client():
    """Mock dual-write client."""
    client = AsyncMock()
    client.enabled = True
    client.add_episode = AsyncMock(return_value=None)
    client.search = AsyncMock(return_value=[])
    return client


@pytest.fixture
def adr_service(mock_dual_client):
    """ADRService with dual-write client."""
    return ADRService(client=mock_dual_client)


@pytest.mark.asyncio
async def test_create_adr_with_dual_client(adr_service, mock_dual_client):
    """ADRService.create_adr works with dual-write client."""
    adr = ADREntity(
        id="ADR-0001",
        title="Use PostgreSQL",
        status=ADRStatus.ACCEPTED,
        trigger=ADRTrigger.TASK_REVIEW,
        decision="Use PostgreSQL for data storage",
        rationale="ACID compliance needed",
    )

    adr_id = await adr_service.create_adr(adr)

    # Verify add_episode called with ADR group
    mock_dual_client.add_episode.assert_called_once()
    call_kwargs = mock_dual_client.add_episode.call_args.kwargs
    assert call_kwargs["group_id"] == "adrs"
    assert "adr_ADR-0001" in call_kwargs["name"]

    assert adr_id == "ADR-0001"


@pytest.mark.asyncio
async def test_create_adr_graceful_when_disabled(mock_dual_client):
    """ADRService degrades gracefully when client is disabled."""
    mock_dual_client.enabled = False
    service = ADRService(client=mock_dual_client)

    adr = ADREntity(
        id="ADR-0001",
        title="Use PostgreSQL",
        decision="Use PostgreSQL",
    )

    adr_id = await service.create_adr(adr)

    # Returns None when disabled (graceful degradation)
    assert adr_id is None
    mock_dual_client.add_episode.assert_not_called()
