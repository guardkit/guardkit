"""
Comprehensive Test Suite for ADR Service

Tests ADRService for creating, searching, superseding, and deprecating ADRs.
Tests include Graphiti integration, graceful degradation, and ID generation.

Coverage Target: >=85%
Test Count: 30+ tests

This is a TDD GREEN phase test file - adding tests to improve coverage to >80%.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import json

# EXPECTED TO PASS - modules now exist (TDD GREEN phase)
from guardkit.knowledge.adr import ADRStatus, ADRTrigger, ADREntity
from guardkit.knowledge.adr_service import ADRService
from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_graphiti_client():
    """Create a mock GraphitiClient for testing."""
    client = MagicMock(spec=GraphitiClient)
    client.config = GraphitiConfig(enabled=True)
    client.enabled = True
    client.add_episode = AsyncMock(return_value="episode-123")
    client.search = AsyncMock(return_value=[])
    return client


@pytest.fixture
def adr_service(mock_graphiti_client):
    """Create ADRService instance with mock client."""
    return ADRService(mock_graphiti_client)


@pytest.fixture
def sample_adr():
    """Create a sample ADREntity for testing."""
    return ADREntity(
        id="ADR-0001",
        title="Use PostgreSQL for primary database",
        status=ADRStatus.ACCEPTED,
        trigger=ADRTrigger.TASK_REVIEW,
        context="Need reliable ACID guarantees",
        decision="Use PostgreSQL 15",
        rationale="Strong ACID compliance, mature ecosystem"
    )


# ============================================================================
# 1. ADRService Initialization Tests (2 tests)
# ============================================================================


def test_adr_service_initialization(mock_graphiti_client):
    """Test ADRService initializes with GraphitiClient."""
    service = ADRService(mock_graphiti_client)

    assert service.client == mock_graphiti_client


def test_adr_service_requires_client():
    """Test ADRService requires a GraphitiClient instance."""
    with pytest.raises(TypeError):
        ADRService()  # Should fail - client is required


# ============================================================================
# 2. Create ADR Tests (8 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_create_adr_with_id(adr_service, sample_adr, mock_graphiti_client):
    """Test create_adr stores ADR with provided ID."""
    adr_id = await adr_service.create_adr(sample_adr)

    assert adr_id == "ADR-0001"
    mock_graphiti_client.add_episode.assert_called_once()


@pytest.mark.asyncio
async def test_create_adr_generates_id_if_missing(adr_service, mock_graphiti_client):
    """Test create_adr generates ID if not provided."""
    adr = ADREntity(id="", title="Test Decision")

    adr_id = await adr_service.create_adr(adr)

    # Should generate ID in ADR-XXXX format
    assert adr_id.startswith("ADR-")
    assert len(adr_id) == 8  # ADR-0001 or ADR-a3f8 format
    mock_graphiti_client.add_episode.assert_called_once()


@pytest.mark.asyncio
async def test_create_adr_calls_graphiti_add_episode(adr_service, sample_adr, mock_graphiti_client):
    """Test create_adr calls GraphitiClient.add_episode."""
    await adr_service.create_adr(sample_adr)

    mock_graphiti_client.add_episode.assert_called_once()
    call_args = mock_graphiti_client.add_episode.call_args

    # Verify episode name format
    assert call_args.kwargs["name"] == "adr_ADR-0001"

    # Verify group_id is "adrs"
    assert call_args.kwargs["group_id"] == "adrs"

    # Verify episode_body contains serialized ADR
    episode_body = call_args.kwargs["episode_body"]
    assert isinstance(episode_body, str)
    assert "ADR-0001" in episode_body
    assert "Use PostgreSQL for primary database" in episode_body


@pytest.mark.asyncio
async def test_create_adr_with_clarifying_question_trigger(adr_service, mock_graphiti_client):
    """Test create_adr with CLARIFYING_QUESTION trigger."""
    adr = ADREntity(
        id="ADR-0002",
        title="Use monorepo structure",
        trigger=ADRTrigger.CLARIFYING_QUESTION,
        source_command="feature-plan"
    )

    adr_id = await adr_service.create_adr(adr)

    assert adr_id == "ADR-0002"
    mock_graphiti_client.add_episode.assert_called_once()


@pytest.mark.asyncio
async def test_create_adr_with_implementation_choice_trigger(adr_service, mock_graphiti_client):
    """Test create_adr with IMPLEMENTATION_CHOICE trigger."""
    adr = ADREntity(
        id="ADR-0003",
        title="Use JWT for authentication",
        trigger=ADRTrigger.IMPLEMENTATION_CHOICE,
        source_task_id="TASK-AUTH-001"
    )

    adr_id = await adr_service.create_adr(adr)

    assert adr_id == "ADR-0003"
    mock_graphiti_client.add_episode.assert_called_once()


@pytest.mark.asyncio
async def test_create_adr_graceful_degradation(adr_service, sample_adr, mock_graphiti_client):
    """Test create_adr handles Graphiti failure gracefully."""
    mock_graphiti_client.add_episode.side_effect = Exception("Connection failed")

    # Should not raise exception, but return None or handle gracefully
    adr_id = await adr_service.create_adr(sample_adr)

    # Expect graceful degradation (return None or empty string)
    assert adr_id is None or adr_id == ""


@pytest.mark.asyncio
async def test_create_adr_when_graphiti_disabled(sample_adr):
    """Test create_adr when Graphiti is disabled."""
    disabled_client = MagicMock(spec=GraphitiClient)
    disabled_client.enabled = False
    disabled_client.config = GraphitiConfig(enabled=False)

    service = ADRService(disabled_client)
    adr_id = await service.create_adr(sample_adr)

    # Should handle gracefully when disabled
    assert adr_id is None or adr_id == ""


@pytest.mark.asyncio
async def test_create_adr_id_format(adr_service, mock_graphiti_client):
    """Test generated ADR IDs follow ADR-XXXX format."""
    adr = ADREntity(id="", title="Test Decision")

    adr_id = await adr_service.create_adr(adr)

    # Should match ADR-XXXX pattern (sequential or hash)
    assert adr_id.startswith("ADR-")
    # Accept both ADR-0001 (sequential) and ADR-a3f8 (hash) formats
    suffix = adr_id[4:]
    assert len(suffix) == 4
    assert suffix.isalnum()


# ============================================================================
# 3. Search ADRs Tests (6 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_search_adrs_calls_graphiti_search(adr_service, mock_graphiti_client):
    """Test search_adrs calls GraphitiClient.search with correct parameters."""
    await adr_service.search_adrs("authentication patterns")

    mock_graphiti_client.search.assert_called_once()
    call_args = mock_graphiti_client.search.call_args

    assert call_args.kwargs["query"] == "authentication patterns"
    assert call_args.kwargs["group_ids"] == ["adrs"]


@pytest.mark.asyncio
async def test_search_adrs_returns_parsed_adrs(adr_service, mock_graphiti_client):
    """Test search_adrs parses Graphiti results into ADREntity objects."""
    mock_graphiti_client.search.return_value = [
        {
            "id": "ADR-0001",
            "title": "Use PostgreSQL",
            "status": "accepted",
            "trigger": "task_review"
        },
        {
            "id": "ADR-0002",
            "title": "Use Redis for caching",
            "status": "accepted",
            "trigger": "manual"
        }
    ]

    results = await adr_service.search_adrs("database decisions")

    assert len(results) == 2
    assert all(isinstance(adr, ADREntity) for adr in results)
    assert results[0].id == "ADR-0001"
    assert results[1].id == "ADR-0002"


@pytest.mark.asyncio
async def test_search_adrs_filter_by_status(adr_service, mock_graphiti_client):
    """Test search_adrs filters results by status."""
    mock_graphiti_client.search.return_value = [
        {
            "id": "ADR-0001",
            "title": "Use PostgreSQL",
            "status": "accepted",
            "trigger": "manual"
        },
        {
            "id": "ADR-0002",
            "title": "Use MySQL",
            "status": "deprecated",
            "trigger": "manual"
        }
    ]

    results = await adr_service.search_adrs("database", status=ADRStatus.ACCEPTED)

    # Should only return ACCEPTED ADRs
    assert len(results) == 1
    assert results[0].status == ADRStatus.ACCEPTED


@pytest.mark.asyncio
async def test_search_adrs_num_results(adr_service, mock_graphiti_client):
    """Test search_adrs respects num_results parameter."""
    await adr_service.search_adrs("patterns", num_results=5)

    call_args = mock_graphiti_client.search.call_args
    assert call_args.kwargs["num_results"] == 5


@pytest.mark.asyncio
async def test_search_adrs_empty_results(adr_service, mock_graphiti_client):
    """Test search_adrs handles empty results gracefully."""
    mock_graphiti_client.search.return_value = []

    results = await adr_service.search_adrs("nonexistent topic")

    assert results == []


@pytest.mark.asyncio
async def test_search_adrs_graceful_degradation(adr_service, mock_graphiti_client):
    """Test search_adrs handles Graphiti failure gracefully."""
    mock_graphiti_client.search.side_effect = Exception("Connection failed")

    results = await adr_service.search_adrs("patterns")

    # Should return empty list on failure
    assert results == []


# ============================================================================
# 4. Get ADR Tests (3 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_get_adr_retrieves_by_id(adr_service, mock_graphiti_client):
    """Test get_adr retrieves ADR by ID."""
    mock_graphiti_client.search.return_value = [
        {
            "id": "ADR-0001",
            "title": "Use PostgreSQL",
            "status": "accepted",
            "trigger": "manual"
        }
    ]

    adr = await adr_service.get_adr("ADR-0001")

    assert adr is not None
    assert adr.id == "ADR-0001"
    mock_graphiti_client.search.assert_called_once()


@pytest.mark.asyncio
async def test_get_adr_not_found(adr_service, mock_graphiti_client):
    """Test get_adr returns None when ADR not found."""
    mock_graphiti_client.search.return_value = []

    adr = await adr_service.get_adr("ADR-9999")

    assert adr is None


@pytest.mark.asyncio
async def test_get_adr_graceful_degradation(adr_service, mock_graphiti_client):
    """Test get_adr handles Graphiti failure gracefully."""
    mock_graphiti_client.search.side_effect = Exception("Connection failed")

    adr = await adr_service.get_adr("ADR-0001")

    assert adr is None


# ============================================================================
# 5. Supersede ADR Tests (5 tests - added 1 for coverage)
# ============================================================================


@pytest.mark.asyncio
async def test_supersede_adr_updates_old_status(adr_service, mock_graphiti_client):
    """Test supersede_adr sets old ADR status to SUPERSEDED."""
    # Mock get_adr to return existing ADR
    old_adr = ADREntity(
        id="ADR-0001",
        title="Use MySQL",
        status=ADRStatus.ACCEPTED
    )

    with patch.object(adr_service, 'get_adr', return_value=old_adr):
        new_adr = ADREntity(
            id="ADR-0002",
            title="Use PostgreSQL",
            status=ADRStatus.ACCEPTED
        )

        new_id = await adr_service.supersede_adr("ADR-0001", new_adr)

        # Old ADR should be updated to SUPERSEDED
        assert old_adr.status == ADRStatus.SUPERSEDED
        assert old_adr.superseded_by == "ADR-0002"


@pytest.mark.asyncio
async def test_supersede_adr_creates_new_with_reference(adr_service, mock_graphiti_client):
    """Test supersede_adr creates new ADR with supersedes reference."""
    old_adr = ADREntity(id="ADR-0001", title="Use MySQL", status=ADRStatus.ACCEPTED)

    with patch.object(adr_service, 'get_adr', return_value=old_adr):
        new_adr = ADREntity(id="ADR-0002", title="Use PostgreSQL")

        new_id = await adr_service.supersede_adr("ADR-0001", new_adr)

        # New ADR should reference old one
        assert new_adr.supersedes == "ADR-0001"
        assert new_id == "ADR-0002"


@pytest.mark.asyncio
async def test_supersede_adr_calls_create(adr_service, mock_graphiti_client):
    """Test supersede_adr calls create_adr for new ADR."""
    old_adr = ADREntity(id="ADR-0001", title="Use MySQL", status=ADRStatus.ACCEPTED)

    with patch.object(adr_service, 'get_adr', return_value=old_adr):
        with patch.object(adr_service, 'create_adr', return_value="ADR-0002") as mock_create:
            new_adr = ADREntity(id="ADR-0002", title="Use PostgreSQL")

            await adr_service.supersede_adr("ADR-0001", new_adr)

            mock_create.assert_called_once_with(new_adr)


@pytest.mark.asyncio
async def test_supersede_adr_old_adr_not_found(adr_service, mock_graphiti_client):
    """Test supersede_adr when old ADR is not found."""
    with patch.object(adr_service, 'get_adr', return_value=None):
        new_adr = ADREntity(id="ADR-0002", title="Use PostgreSQL")

        result = await adr_service.supersede_adr("ADR-9999", new_adr)

        # Should return None when old ADR not found
        assert result is None


@pytest.mark.asyncio
async def test_supersede_adr_graceful_degradation(adr_service, mock_graphiti_client):
    """Test supersede_adr handles failure gracefully."""
    with patch.object(adr_service, 'get_adr', side_effect=Exception("Connection failed")):
        new_adr = ADREntity(id="ADR-0002", title="Use PostgreSQL")

        result = await adr_service.supersede_adr("ADR-0001", new_adr)

        # Should handle gracefully
        assert result is None or result == ""


# ============================================================================
# 6. Deprecate ADR Tests (3 tests - added 1 for coverage)
# ============================================================================


@pytest.mark.asyncio
async def test_deprecate_adr_sets_status(adr_service, mock_graphiti_client):
    """Test deprecate_adr sets status to DEPRECATED."""
    adr = ADREntity(id="ADR-0001", title="Use MySQL", status=ADRStatus.ACCEPTED)

    with patch.object(adr_service, 'get_adr', return_value=adr):
        await adr_service.deprecate_adr("ADR-0001")

        assert adr.status == ADRStatus.DEPRECATED
        assert adr.deprecated_at is not None
        assert isinstance(adr.deprecated_at, datetime)


@pytest.mark.asyncio
async def test_deprecate_adr_not_found(adr_service, mock_graphiti_client):
    """Test deprecate_adr when ADR is not found."""
    with patch.object(adr_service, 'get_adr', return_value=None):
        result = await adr_service.deprecate_adr("ADR-9999")

        # Should return None when ADR not found
        assert result is None


@pytest.mark.asyncio
async def test_deprecate_adr_graceful_degradation(adr_service, mock_graphiti_client):
    """Test deprecate_adr handles failure gracefully."""
    with patch.object(adr_service, 'get_adr', side_effect=Exception("Connection failed")):
        result = await adr_service.deprecate_adr("ADR-0001")

        # Should handle gracefully
        assert result is None or result is False


# ============================================================================
# 7. record_decision() Convenience Function Tests (7 tests - added 1)
# ============================================================================


@pytest.mark.asyncio
async def test_record_decision_basic(adr_service, mock_graphiti_client):
    """Test record_decision creates ADR from Q&A pair."""
    adr_id = await adr_service.record_decision(
        question="Which database should we use?",
        answer="PostgreSQL because of ACID compliance",
        trigger=ADRTrigger.CLARIFYING_QUESTION
    )

    # Should create ADR
    assert adr_id is not None
    assert adr_id.startswith("ADR-")
    mock_graphiti_client.add_episode.assert_called_once()


@pytest.mark.asyncio
async def test_record_decision_with_task_context(adr_service, mock_graphiti_client):
    """Test record_decision includes task and feature context."""
    adr_id = await adr_service.record_decision(
        question="Should we use microservices?",
        answer="Monolith for now because we're a small team",
        trigger=ADRTrigger.TASK_REVIEW,
        source_task_id="TASK-GI-004",
        source_feature_id="FEAT-GI",
        source_command="task-review"
    )

    assert adr_id is not None
    # Verify the call includes context
    call_args = mock_graphiti_client.add_episode.call_args
    episode_body = call_args.kwargs["episode_body"]
    assert "TASK-GI-004" in episode_body
    assert "FEAT-GI" in episode_body


@pytest.mark.asyncio
async def test_record_decision_low_significance_skipped(adr_service, mock_graphiti_client):
    """Test record_decision skips low-significance decisions."""
    adr_id = await adr_service.record_decision(
        question="What should we name this variable?",
        answer="userCount",
        trigger=ADRTrigger.CLARIFYING_QUESTION
    )

    # Low significance - should return None and not call add_episode
    assert adr_id is None
    mock_graphiti_client.add_episode.assert_not_called()


@pytest.mark.asyncio
async def test_record_decision_implementation_trigger(adr_service, mock_graphiti_client):
    """Test record_decision with IMPLEMENTATION_CHOICE trigger."""
    adr_id = await adr_service.record_decision(
        question="Which authentication strategy?",
        answer="JWT with refresh tokens for stateless scalability",
        trigger=ADRTrigger.IMPLEMENTATION_CHOICE,
        source_task_id="TASK-AUTH-001"
    )

    assert adr_id is not None
    assert adr_id.startswith("ADR-")


@pytest.mark.asyncio
async def test_record_decision_when_graphiti_disabled(sample_adr):
    """Test record_decision when Graphiti is disabled."""
    disabled_client = MagicMock(spec=GraphitiClient)
    disabled_client.enabled = False
    disabled_client.config = GraphitiConfig(enabled=False)

    service = ADRService(disabled_client)
    adr_id = await service.record_decision(
        question="Which framework?",
        answer="FastAPI because of async support",
        trigger=ADRTrigger.MANUAL
    )

    # Should return None when disabled
    assert adr_id is None


@pytest.mark.asyncio
async def test_record_decision_graceful_degradation(adr_service, mock_graphiti_client):
    """Test record_decision handles Graphiti failure gracefully."""
    mock_graphiti_client.add_episode.side_effect = Exception("Connection failed")

    adr_id = await adr_service.record_decision(
        question="Which framework?",
        answer="FastAPI because of async support and performance",
        trigger=ADRTrigger.MANUAL
    )

    # Should return None on failure, not raise
    assert adr_id is None


@pytest.mark.asyncio
async def test_record_decision_custom_threshold(mock_graphiti_client):
    """Test record_decision respects custom significance threshold."""
    # Create service with high threshold
    service = ADRService(mock_graphiti_client, significance_threshold=0.9)

    adr_id = await service.record_decision(
        question="Which logging level?",
        answer="INFO for production",
        trigger=ADRTrigger.IMPLEMENTATION_CHOICE
    )

    # Medium significance should be skipped with high threshold
    assert adr_id is None
    mock_graphiti_client.add_episode.assert_not_called()


# ============================================================================
# 8. ID Generation Tests (2 tests for coverage)
# ============================================================================


@pytest.mark.asyncio
async def test_get_next_adr_id_exception_fallback(adr_service, monkeypatch, tmp_path):
    """Test _get_next_adr_id falls back to timestamp when counter file fails."""
    # Patch counter file to raise exception on write
    bad_counter_file = tmp_path / "bad" / "counter.json"
    monkeypatch.setattr(adr_service, '_counter_file', bad_counter_file)

    # Make parent directory read-only to trigger exception
    bad_counter_file.parent.mkdir(parents=True, exist_ok=True)
    import os
    os.chmod(bad_counter_file.parent, 0o444)

    try:
        adr = ADREntity(id="", title="Test")
        adr_id = await adr_service.create_adr(adr)

        # Should generate fallback ID in ADR-XXXX format
        assert adr_id.startswith("ADR-")
        assert len(adr_id) == 8
    finally:
        # Restore permissions for cleanup
        os.chmod(bad_counter_file.parent, 0o755)


# ============================================================================
# 9. Parse ADR Tests (4 tests for coverage)
# ============================================================================


@pytest.mark.asyncio
async def test_parse_adr_invalid_status_string(adr_service, mock_graphiti_client):
    """Test _parse_adr handles invalid status string values."""
    mock_graphiti_client.search.return_value = [
        {
            "id": "ADR-0001",
            "title": "Test",
            "status": "invalid_status",  # Invalid enum value
            "trigger": "manual"
        }
    ]

    results = await adr_service.search_adrs("test")

    # Should default to ACCEPTED for invalid status
    assert len(results) == 1
    assert results[0].status == ADRStatus.ACCEPTED


@pytest.mark.asyncio
async def test_parse_adr_non_string_status(adr_service, mock_graphiti_client):
    """Test _parse_adr handles non-string status values."""
    mock_graphiti_client.search.return_value = [
        {
            "id": "ADR-0001",
            "title": "Test",
            "status": 123,  # Non-string value
            "trigger": "manual"
        }
    ]

    results = await adr_service.search_adrs("test")

    # Should default to ACCEPTED for non-string status
    assert len(results) == 1
    assert results[0].status == ADRStatus.ACCEPTED


@pytest.mark.asyncio
async def test_parse_adr_invalid_trigger_string(adr_service, mock_graphiti_client):
    """Test _parse_adr handles invalid trigger string values."""
    mock_graphiti_client.search.return_value = [
        {
            "id": "ADR-0001",
            "title": "Test",
            "status": "accepted",
            "trigger": "invalid_trigger"  # Invalid enum value
        }
    ]

    results = await adr_service.search_adrs("test")

    # Should default to MANUAL for invalid trigger
    assert len(results) == 1
    assert results[0].trigger == ADRTrigger.MANUAL


@pytest.mark.asyncio
async def test_parse_adr_datetime_parsing(adr_service, mock_graphiti_client):
    """Test _parse_adr handles datetime string parsing."""
    mock_graphiti_client.search.return_value = [
        {
            "id": "ADR-0001",
            "title": "Test",
            "status": "accepted",
            "trigger": "manual",
            "created_at": "2024-01-15T10:30:00"  # ISO format string
        }
    ]

    results = await adr_service.search_adrs("test")

    # Should parse datetime string correctly
    assert len(results) == 1
    assert isinstance(results[0].created_at, datetime)
    assert results[0].created_at.year == 2024
    assert results[0].created_at.month == 1
    assert results[0].created_at.day == 15
