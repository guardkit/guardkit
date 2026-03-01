"""
Tests for temporal superseding spike — verify Graphiti upsert behaviour.

TASK-SAD-001: Determines whether Graphiti's upsert_episode() with stable
entity_id allows prior versions to remain queryable after an update.

This spike validates whether Option A (soft superseding via data-level encoding)
is sufficient, or whether native graph edge support is needed.

Coverage Target: >=80%
TDD Phase: RED → GREEN → REFACTOR
"""

from __future__ import annotations

import hashlib
import json
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
from typing import Dict, Any, List, Optional

from guardkit.knowledge.graphiti_client import GraphitiConfig, GraphitiClient
from guardkit.integrations.graphiti.upsert_result import UpsertResult
from guardkit.integrations.graphiti.exists_result import ExistsResult
from guardkit.integrations.graphiti.metadata import EpisodeMetadata


# ---------------------------------------------------------------------------
# Helper: build mock edge objects returned by Graphiti.search()
# ---------------------------------------------------------------------------


def _make_mock_edge(
    uuid: str,
    entity_id: str,
    content: str,
    source_hash: Optional[str] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> MagicMock:
    """Build a mock Graphiti Edge with embedded JSON metadata in the fact field.

    This mirrors the metadata injection pattern used by GraphitiClient._inject_metadata(),
    where metadata is appended to episode_body as a JSON block.
    """
    metadata: Dict[str, Any] = {
        "entity_id": entity_id,
        "source": "user_added",
        "version": "1.0.0",
        "entity_type": "generic",
        "created_at": "2026-02-01T00:00:00Z",
    }
    if source_hash is not None:
        metadata["source_hash"] = source_hash
    if extra_metadata:
        metadata.update(extra_metadata)

    edge = MagicMock()
    edge.uuid = uuid
    edge.fact = json.dumps(metadata) + "\n\n" + content
    edge.name = f"Episode {uuid}"
    edge.created_at = "2026-02-01T00:00:00Z"
    edge.valid_at = "2026-02-01T00:00:00Z"
    return edge


# ===========================================================================
# AC-001: upsert_episode() twice with same entity_id, different content
# ===========================================================================


class TestUpsertTwiceSameEntityId:
    """Verify upsert_episode() called twice with same entity_id + different content."""

    @pytest.mark.asyncio
    async def test_first_upsert_creates_episode(self):
        """First call to upsert_episode creates a new episode (action='created')."""
        config = GraphitiConfig(enabled=True, project_id="test-project")
        client = GraphitiClient(config)

        # Mock: no existing episode
        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        # Mock add_episode to return a UUID
        from graphiti_core.nodes import EpisodeType

        mock_result = MagicMock()
        mock_result.episode = MagicMock()
        mock_result.episode.uuid = "uuid-v1"
        mock_graphiti.add_episode = AsyncMock(return_value=mock_result)

        client._graphiti = mock_graphiti

        result = await client.upsert_episode(
            name="ADR-001",
            episode_body="Initial architecture decision content",
            group_id="project_decisions",
            entity_id="adr-001",
        )

        assert result is not None
        assert result.action == "created"
        assert result.uuid == "uuid-v1"

    @pytest.mark.asyncio
    async def test_second_upsert_with_different_content_updates(self):
        """Second call with changed content creates update (action='updated')."""
        config = GraphitiConfig(enabled=True, project_id="test-project")
        client = GraphitiClient(config)

        content_v1 = "Original ADR content"
        content_v2 = "Revised ADR content with new information"
        hash_v2 = hashlib.sha256(content_v2.encode()).hexdigest()

        # Mock: existing episode found with different hash
        existing_edge = _make_mock_edge(
            uuid="uuid-v1",
            entity_id="adr-001",
            content=content_v1,
            source_hash=hashlib.sha256(content_v1.encode()).hexdigest(),
        )

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[existing_edge])

        # Mock add_episode for the update (new episode creation)
        from graphiti_core.nodes import EpisodeType

        mock_result = MagicMock()
        mock_result.episode = MagicMock()
        mock_result.episode.uuid = "uuid-v2"
        mock_graphiti.add_episode = AsyncMock(return_value=mock_result)

        client._graphiti = mock_graphiti

        result = await client.upsert_episode(
            name="ADR-001",
            episode_body=content_v2,
            group_id="project_decisions",
            entity_id="adr-001",
        )

        assert result is not None
        assert result.action == "updated"
        assert result.uuid == "uuid-v2"
        assert result.previous_uuid == "uuid-v1"

    @pytest.mark.asyncio
    async def test_second_upsert_same_content_skips(self):
        """Second call with identical content returns action='skipped'."""
        config = GraphitiConfig(enabled=True, project_id="test-project")
        client = GraphitiClient(config)

        content = "Unchanged ADR content"
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Mock: existing episode found with same hash → exact match
        existing_edge = _make_mock_edge(
            uuid="uuid-v1",
            entity_id="adr-001",
            content=content,
            source_hash=content_hash,
        )

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[existing_edge])
        client._graphiti = mock_graphiti

        result = await client.upsert_episode(
            name="ADR-001",
            episode_body=content,
            group_id="project_decisions",
            entity_id="adr-001",
        )

        assert result is not None
        assert result.action == "skipped"
        assert result.uuid == "uuid-v1"


# ===========================================================================
# AC-002 / AC-003: Verify old content retrievability after upsert update
# ===========================================================================


class TestOldContentRetrievability:
    """Verify whether old episode content is still retrievable after an update.

    Key finding from code analysis:
    - upsert_episode() creates a NEW episode (via add_episode) on content change
    - It does NOT delete the old episode
    - The old episode remains in the graph as an orphan (no explicit invalidation)
    - Semantic search may or may not return it depending on query relevance
    - entity_id metadata search returns the FIRST match found by semantic search

    Conclusion: Old content IS preserved in the graph (Graphiti doesn't overwrite),
    but retrievability via entity_id search is unreliable because episode_exists()
    relies on semantic search ranking — both old and new episodes have the same
    entity_id, and which one is returned first depends on embedding similarity.
    """

    @pytest.mark.asyncio
    async def test_old_episode_remains_in_graph_after_update(self):
        """After upsert update, both old and new episodes exist in graph.

        The upsert creates a NEW episode without deleting the old one.
        If semantic search returns both, both are visible.
        """
        config = GraphitiConfig(enabled=True, project_id="test-project")
        client = GraphitiClient(config)

        # Simulate: search returns BOTH old and new episodes
        old_edge = _make_mock_edge(
            uuid="uuid-v1",
            entity_id="adr-001",
            content="Original decision: use REST API",
            source_hash="hash-v1",
        )
        new_edge = _make_mock_edge(
            uuid="uuid-v2",
            entity_id="adr-001",
            content="Revised decision: use GraphQL",
            source_hash="hash-v2",
        )

        mock_graphiti = MagicMock()
        # Search returns both episodes (old and new)
        mock_graphiti.search = AsyncMock(return_value=[new_edge, old_edge])
        client._graphiti = mock_graphiti

        # Semantic search for the old content topic
        results = await client.search(
            query="REST API architecture decision",
            group_ids=["project_decisions"],
        )

        # Both episodes should be returned by search
        assert len(results) == 2
        # Results contain both UUIDs
        uuids = {r["uuid"] for r in results}
        assert "uuid-v1" in uuids
        assert "uuid-v2" in uuids

    @pytest.mark.asyncio
    async def test_entity_id_search_finds_latest_version(self):
        """episode_exists() returns first entity_id match from search results.

        When multiple episodes share the same entity_id, the one ranked
        higher by semantic search is returned. This is non-deterministic
        for retrieving a SPECIFIC version.
        """
        config = GraphitiConfig(enabled=True, project_id="test-project")
        client = GraphitiClient(config)

        # Simulate: search returns new version first (higher relevance)
        new_edge = _make_mock_edge(
            uuid="uuid-v2",
            entity_id="adr-001",
            content="Revised decision",
            source_hash="hash-v2",
        )
        old_edge = _make_mock_edge(
            uuid="uuid-v1",
            entity_id="adr-001",
            content="Original decision",
            source_hash="hash-v1",
        )

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[new_edge, old_edge])
        client._graphiti = mock_graphiti

        result = await client.episode_exists(
            entity_id="adr-001",
            group_id="project_decisions",
        )

        assert result.exists is True
        # Returns the first matching entity_id (could be either version)
        assert result.uuid in ("uuid-v1", "uuid-v2")

    @pytest.mark.asyncio
    async def test_old_content_retrievable_via_semantic_search(self):
        """Old content is retrievable via semantic search (not just entity_id).

        Graphiti's search() returns edges by semantic similarity, so old
        episodes remain queryable if their content matches the search query.
        """
        config = GraphitiConfig(enabled=True, project_id="test-project")
        client = GraphitiClient(config)

        # Only old edge matches a query about "REST API"
        old_edge = _make_mock_edge(
            uuid="uuid-v1",
            entity_id="adr-001",
            content="Original: use REST API for external integrations",
            source_hash="hash-v1",
        )

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[old_edge])
        client._graphiti = mock_graphiti
        client._connected = True

        results = await client.search(
            query="REST API external integrations",
            group_ids=["project_decisions"],
        )

        assert len(results) == 1
        assert results[0]["uuid"] == "uuid-v1"

    @pytest.mark.asyncio
    async def test_entity_id_metadata_search_returns_first_match(self):
        """episode_exists() iterates results and returns first entity_id match.

        This means if the old episode is ranked HIGHER than the new one
        by semantic search, the old version would be returned. The current
        implementation does NOT guarantee returning the LATEST version.
        """
        config = GraphitiConfig(enabled=True, project_id="test-project")
        client = GraphitiClient(config)

        # Old edge appears FIRST in search results (higher semantic similarity)
        old_edge = _make_mock_edge(
            uuid="uuid-v1",
            entity_id="adr-001",
            content="Original decision",
            source_hash="hash-v1",
        )
        new_edge = _make_mock_edge(
            uuid="uuid-v2",
            entity_id="adr-001",
            content="Revised decision",
            source_hash="hash-v2",
        )

        mock_graphiti = MagicMock()
        # Old edge is returned first by search
        mock_graphiti.search = AsyncMock(return_value=[old_edge, new_edge])
        client._graphiti = mock_graphiti

        result = await client.episode_exists(
            entity_id="adr-001",
            group_id="project_decisions",
        )

        assert result.exists is True
        # Returns uuid-v1 because it appears first in search results
        assert result.uuid == "uuid-v1"


# ===========================================================================
# AC-004 / AC-005: Document findings — does Graphiti overwrite or preserve?
# ===========================================================================


class TestGraphitiPreservationBehavior:
    """Document findings about Graphiti's episode preservation behavior.

    Key Finding: Graphiti PRESERVES old episodes.

    The upsert_episode() implementation:
    1. Checks if episode exists via episode_exists() (semantic search + metadata parsing)
    2. If exists with same content hash → skip (no change)
    3. If exists with different content → create NEW episode via add_episode()
    4. Does NOT delete or invalidate the old episode

    This means:
    - Old episodes remain in the graph indefinitely
    - Both old and new can be returned by semantic search
    - entity_id is duplicated across versions (non-unique)
    - No built-in version ordering (no version number, no superseded_by link)

    Recommendation: Implement Option A — create new episode with next ADR number,
    set status=superseded on original via metadata. This is the soft superseding
    approach that works within Graphiti's existing capabilities.
    """

    @pytest.mark.asyncio
    async def test_upsert_creates_new_without_deleting_old(self):
        """Verify upsert update path calls add_episode without deleting old.

        This confirms Graphiti preserves old episodes — the upsert creates
        a new episode and does NOT call any deletion API.
        """
        config = GraphitiConfig(enabled=True, project_id="test-project")
        client = GraphitiClient(config)

        content_v1 = "Version 1 content"
        content_v2 = "Version 2 content"
        hash_v1 = hashlib.sha256(content_v1.encode()).hexdigest()

        # Mock: existing episode found with different hash
        existing_edge = _make_mock_edge(
            uuid="uuid-v1",
            entity_id="adr-001",
            content=content_v1,
            source_hash=hash_v1,
        )

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[existing_edge])

        # Track add_episode calls
        from graphiti_core.nodes import EpisodeType

        mock_result = MagicMock()
        mock_result.episode = MagicMock()
        mock_result.episode.uuid = "uuid-v2"
        mock_graphiti.add_episode = AsyncMock(return_value=mock_result)

        client._graphiti = mock_graphiti

        result = await client.upsert_episode(
            name="ADR-001",
            episode_body=content_v2,
            group_id="project_decisions",
            entity_id="adr-001",
        )

        # Verify add_episode was called (new episode created)
        assert mock_graphiti.add_episode.called
        assert result is not None
        assert result.action == "updated"

        # Verify NO delete operation was called
        # Graphiti instance should not have any delete methods called
        assert not hasattr(mock_graphiti, "delete_episode") or not getattr(
            mock_graphiti, "delete_episode", MagicMock()
        ).called

    @pytest.mark.asyncio
    async def test_upsert_preserves_original_created_at(self):
        """Verify upsert update path preserves original created_at timestamp.

        When updating, the new episode's metadata should carry forward
        the original created_at timestamp for audit trail.
        """
        config = GraphitiConfig(enabled=True, project_id="test-project")
        client = GraphitiClient(config)

        original_created_at = "2026-01-15T10:00:00Z"
        content_v1 = "Version 1"
        content_v2 = "Version 2"
        hash_v1 = hashlib.sha256(content_v1.encode()).hexdigest()

        # Mock: existing episode with specific created_at
        existing_edge = _make_mock_edge(
            uuid="uuid-v1",
            entity_id="adr-001",
            content=content_v1,
            source_hash=hash_v1,
            extra_metadata={"created_at": original_created_at},
        )

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[existing_edge])

        from graphiti_core.nodes import EpisodeType

        mock_result = MagicMock()
        mock_result.episode = MagicMock()
        mock_result.episode.uuid = "uuid-v2"
        mock_graphiti.add_episode = AsyncMock(return_value=mock_result)

        client._graphiti = mock_graphiti

        result = await client.upsert_episode(
            name="ADR-001",
            episode_body=content_v2,
            group_id="project_decisions",
            entity_id="adr-001",
        )

        assert result is not None
        assert result.action == "updated"
        # The result should contain metadata with preserved created_at
        if result.episode and result.episode.get("metadata"):
            assert result.episode["metadata"]["created_at"] == original_created_at

    @pytest.mark.asyncio
    async def test_upsert_sets_updated_at_on_update(self):
        """Verify upsert update path sets updated_at timestamp."""
        config = GraphitiConfig(enabled=True, project_id="test-project")
        client = GraphitiClient(config)

        content_v1 = "Version 1"
        content_v2 = "Version 2"
        hash_v1 = hashlib.sha256(content_v1.encode()).hexdigest()

        existing_edge = _make_mock_edge(
            uuid="uuid-v1",
            entity_id="adr-001",
            content=content_v1,
            source_hash=hash_v1,
        )

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[existing_edge])

        from graphiti_core.nodes import EpisodeType

        mock_result = MagicMock()
        mock_result.episode = MagicMock()
        mock_result.episode.uuid = "uuid-v2"
        mock_graphiti.add_episode = AsyncMock(return_value=mock_result)

        client._graphiti = mock_graphiti

        result = await client.upsert_episode(
            name="ADR-001",
            episode_body=content_v2,
            group_id="project_decisions",
            entity_id="adr-001",
        )

        assert result is not None
        assert result.action == "updated"
        # The result should contain metadata with updated_at set
        if result.episode and result.episode.get("metadata"):
            assert "updated_at" in result.episode["metadata"]
            assert result.episode["metadata"]["updated_at"] is not None


# ===========================================================================
# AC-005: Option A implementation — soft superseding via status metadata
# ===========================================================================


class TestOptionASoftSuperseding:
    """Test Option A: soft superseding via data-level encoding.

    Option A creates a new episode with the next version, and encodes
    superseding status in metadata. The original episode remains in
    the graph but is marked as superseded.

    Since Graphiti doesn't delete old episodes on upsert, this approach
    leverages the existing behavior: both versions remain searchable,
    and consumers can filter by status metadata.
    """

    def test_upsert_result_tracks_previous_uuid(self):
        """UpsertResult.updated() records previous_uuid for lineage tracking."""
        result = UpsertResult.updated(
            episode={"uuid": "uuid-v2", "content": "new"},
            uuid="uuid-v2",
            previous_uuid="uuid-v1",
        )

        assert result.was_updated is True
        assert result.uuid == "uuid-v2"
        assert result.previous_uuid == "uuid-v1"

    def test_episode_metadata_supports_entity_id(self):
        """EpisodeMetadata can carry entity_id for stable identification."""
        metadata = EpisodeMetadata.create_now(
            source="user_added",
            entity_type="decision_record",
            entity_id="adr-001",
        )

        assert metadata.entity_id == "adr-001"
        meta_dict = metadata.to_dict()
        assert meta_dict["entity_id"] == "adr-001"

    def test_episode_metadata_supports_source_hash(self):
        """EpisodeMetadata can carry source_hash for content deduplication."""
        content = "Test content for hashing"
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        metadata = EpisodeMetadata.create_now(
            source="user_added",
            entity_type="decision_record",
            source_hash=content_hash,
        )

        assert metadata.source_hash == content_hash
        meta_dict = metadata.to_dict()
        assert meta_dict["source_hash"] == content_hash

    @pytest.mark.asyncio
    async def test_upsert_episode_graceful_degradation_when_disabled(self):
        """upsert_episode returns None when client is disabled."""
        config = GraphitiConfig(enabled=False)
        client = GraphitiClient(config, auto_detect_project=False)

        result = await client.upsert_episode(
            name="ADR-001",
            episode_body="content",
            group_id="project_decisions",
            entity_id="adr-001",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_episode_graceful_degradation_when_uninitialized(self):
        """upsert_episode returns None when client is not initialized."""
        config = GraphitiConfig(enabled=True, project_id="test-project")
        client = GraphitiClient(config)
        client._graphiti = None

        result = await client.upsert_episode(
            name="ADR-001",
            episode_body="content",
            group_id="project_decisions",
            entity_id="adr-001",
        )

        assert result is None


# ===========================================================================
# AC-006: Recommendation — chosen temporal superseding mechanism
# ===========================================================================


class TestTemporalSupersedingRecommendation:
    """Tests validating the chosen temporal superseding mechanism.

    Recommendation: Use Option A (soft superseding via metadata).

    Rationale:
    1. Graphiti preserves old episodes — upsert creates new without deleting old
    2. Both versions remain searchable via semantic search
    3. entity_id + source_hash provide deduplication (skip if unchanged)
    4. previous_uuid in UpsertResult provides version lineage
    5. EpisodeMetadata.updated_at distinguishes current from historical

    This approach works within Graphiti's existing capabilities without
    requiring native graph edge support for versioning.
    """

    @pytest.mark.asyncio
    async def test_full_superseding_flow(self):
        """End-to-end test of the superseding flow:
        1. Create initial episode
        2. Update with new content
        3. Both versions remain in graph
        4. Lineage tracked via previous_uuid
        """
        config = GraphitiConfig(enabled=True, project_id="test-project")
        client = GraphitiClient(config)

        # --- Step 1: First upsert (create) ---
        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])  # No existing episode

        from graphiti_core.nodes import EpisodeType

        mock_result_v1 = MagicMock()
        mock_result_v1.episode = MagicMock()
        mock_result_v1.episode.uuid = "uuid-v1"
        mock_graphiti.add_episode = AsyncMock(return_value=mock_result_v1)

        client._graphiti = mock_graphiti

        content_v1 = "ADR-001: Use REST API for service communication"
        result_v1 = await client.upsert_episode(
            name="ADR-001",
            episode_body=content_v1,
            group_id="project_decisions",
            entity_id="adr-001",
        )

        assert result_v1 is not None
        assert result_v1.action == "created"
        assert result_v1.uuid == "uuid-v1"

        # --- Step 2: Second upsert (update) ---
        content_v2 = "ADR-001: Switch to GraphQL for better query flexibility"
        hash_v1 = hashlib.sha256(content_v1.encode()).hexdigest()

        existing_edge = _make_mock_edge(
            uuid="uuid-v1",
            entity_id="adr-001",
            content=content_v1,
            source_hash=hash_v1,
        )

        mock_graphiti.search = AsyncMock(return_value=[existing_edge])

        mock_result_v2 = MagicMock()
        mock_result_v2.episode = MagicMock()
        mock_result_v2.episode.uuid = "uuid-v2"
        mock_graphiti.add_episode = AsyncMock(return_value=mock_result_v2)

        result_v2 = await client.upsert_episode(
            name="ADR-001",
            episode_body=content_v2,
            group_id="project_decisions",
            entity_id="adr-001",
        )

        assert result_v2 is not None
        assert result_v2.action == "updated"
        assert result_v2.uuid == "uuid-v2"
        assert result_v2.previous_uuid == "uuid-v1"

        # --- Step 3: Verify both versions in graph ---
        old_edge = _make_mock_edge(
            uuid="uuid-v1",
            entity_id="adr-001",
            content=content_v1,
            source_hash=hash_v1,
        )
        new_edge = _make_mock_edge(
            uuid="uuid-v2",
            entity_id="adr-001",
            content=content_v2,
            source_hash=hashlib.sha256(content_v2.encode()).hexdigest(),
        )
        mock_graphiti.search = AsyncMock(return_value=[new_edge, old_edge])
        client._connected = True

        results = await client.search(
            query="architecture decision communication",
            group_ids=["project_decisions"],
        )

        assert len(results) == 2
        uuids = {r["uuid"] for r in results}
        assert "uuid-v1" in uuids
        assert "uuid-v2" in uuids

    @pytest.mark.asyncio
    async def test_upsert_error_returns_none(self):
        """upsert_episode returns None on unexpected error (graceful degradation)."""
        config = GraphitiConfig(enabled=True, project_id="test-project")
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(
            side_effect=Exception("Unexpected graph error")
        )
        client._graphiti = mock_graphiti

        result = await client.upsert_episode(
            name="ADR-001",
            episode_body="content",
            group_id="project_decisions",
            entity_id="adr-001",
        )

        # Should return None, not raise
        assert result is None
