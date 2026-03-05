"""Tests for architectural decisions seeding in project_seeding module.

Tests the seed_architectural_decisions function and its integration
into the seed_project_knowledge orchestrator.

Coverage Target: >=85%
"""

import json

import pytest
from unittest.mock import AsyncMock, MagicMock

from guardkit.knowledge.project_seeding import (
    seed_architectural_decisions,
    seed_project_knowledge,
    estimate_episode_count,
    SeedResult,
)
from guardkit.integrations.graphiti.episodes.architectural_decision import (
    ARCHITECTURAL_DECISION_DEFAULTS,
)


class TestSeedArchitecturalDecisions:
    """Test seed_architectural_decisions function."""

    @pytest.mark.asyncio
    async def test_returns_skip_when_client_is_none(self):
        """Should return success with skip message when client is None."""
        result = await seed_architectural_decisions(client=None)

        assert result.success is True
        assert result.component == "architectural_decisions"
        assert "Skipped" in result.message
        assert result.episodes_created == 0

    @pytest.mark.asyncio
    async def test_returns_skip_when_client_disabled(self):
        """Should return success with skip message when client is disabled."""
        client = MagicMock()
        client.enabled = False

        result = await seed_architectural_decisions(client=client)

        assert result.success is True
        assert "Skipped" in result.message
        assert result.episodes_created == 0

    @pytest.mark.asyncio
    async def test_seeds_all_default_decisions(self):
        """Should seed all decisions from ARCHITECTURAL_DECISION_DEFAULTS."""
        client = AsyncMock()
        client.enabled = True
        client.upsert_episode = AsyncMock(return_value=MagicMock(was_skipped=False))

        result = await seed_architectural_decisions(client=client)

        assert result.success is True
        assert result.episodes_created == len(ARCHITECTURAL_DECISION_DEFAULTS)
        assert client.upsert_episode.call_count == len(ARCHITECTURAL_DECISION_DEFAULTS)

    @pytest.mark.asyncio
    async def test_uses_architecture_decisions_group_id(self):
        """Should use 'architecture_decisions' group_id."""
        client = AsyncMock()
        client.enabled = True
        client.upsert_episode = AsyncMock(return_value=MagicMock(was_skipped=False))

        await seed_architectural_decisions(client=client)

        for call_obj in client.upsert_episode.call_args_list:
            assert call_obj.kwargs["group_id"] == "architecture_decisions"

    @pytest.mark.asyncio
    async def test_uses_system_scope(self):
        """Should use system scope (not project-specific)."""
        client = AsyncMock()
        client.enabled = True
        client.upsert_episode = AsyncMock(return_value=MagicMock(was_skipped=False))

        await seed_architectural_decisions(client=client)

        for call_obj in client.upsert_episode.call_args_list:
            assert call_obj.kwargs["scope"] == "system"

    @pytest.mark.asyncio
    async def test_episode_body_is_valid_json(self):
        """Should produce valid JSON episode bodies."""
        client = AsyncMock()
        client.enabled = True
        client.upsert_episode = AsyncMock(return_value=MagicMock(was_skipped=False))

        await seed_architectural_decisions(client=client)

        for call_obj in client.upsert_episode.call_args_list:
            body = call_obj.kwargs["episode_body"]
            data = json.loads(body)
            assert "title" in data
            assert "summary" in data
            assert "implications" in data
            assert "content" in data

    @pytest.mark.asyncio
    async def test_episode_body_contains_fidelity_content(self):
        """Should contain the Graphiti fidelity limitation content."""
        client = AsyncMock()
        client.enabled = True
        client.upsert_episode = AsyncMock(return_value=MagicMock(was_skipped=False))

        await seed_architectural_decisions(client=client)

        # Find the fidelity episode
        for call_obj in client.upsert_episode.call_args_list:
            body = json.loads(call_obj.kwargs["episode_body"])
            if "Fidelity" in body.get("title", ""):
                assert "semantic" in body["summary"].lower() or "facts" in body["summary"].lower()
                assert len(body["implications"]) >= 3
                return

        pytest.fail("Graphiti fidelity limitation episode not found")

    @pytest.mark.asyncio
    async def test_handles_upsert_exception_gracefully(self):
        """Should handle upsert exceptions without failing."""
        client = AsyncMock()
        client.enabled = True
        client.upsert_episode = AsyncMock(side_effect=Exception("API error"))

        result = await seed_architectural_decisions(client=client)

        assert result.success is True
        assert result.episodes_created == 0

    @pytest.mark.asyncio
    async def test_skips_unchanged_episodes(self):
        """Should count skipped episodes correctly."""
        client = AsyncMock()
        client.enabled = True
        client.upsert_episode = AsyncMock(return_value=MagicMock(was_skipped=True))

        result = await seed_architectural_decisions(client=client)

        assert result.success is True
        assert result.episodes_created == 0

    @pytest.mark.asyncio
    async def test_handles_none_upsert_result(self):
        """Should handle None return from upsert_episode."""
        client = AsyncMock()
        client.enabled = True
        client.upsert_episode = AsyncMock(return_value=None)

        result = await seed_architectural_decisions(client=client)

        assert result.success is True
        assert result.episodes_created == 0


class TestSeedProjectKnowledgeExcludesDecisions:
    """Test that seed_project_knowledge does NOT include architectural decisions (TASK-ISF-006).

    Architectural decisions are system-scoped and now handled by `guardkit graphiti seed-system`.
    """

    @pytest.mark.asyncio
    async def test_orchestrator_does_not_seed_architectural_decisions(self):
        """seed_project_knowledge should NOT include architectural decisions."""
        client = AsyncMock()
        client.enabled = True
        client.upsert_episode = AsyncMock(return_value=MagicMock(was_skipped=False))
        client.add_episode = AsyncMock(return_value="ep_id")

        result = await seed_project_knowledge(
            project_name="test-project",
            client=client,
            skip_overview=True,
        )

        assert result.success is True
        assert result.architectural_decisions_seeded is False

        # Should NOT have architectural_decisions component in results
        component_names = [r.component for r in result.results]
        assert "architectural_decisions" not in component_names

    @pytest.mark.asyncio
    async def test_orchestrator_graceful_when_client_none(self):
        """Should degrade gracefully with None client."""
        result = await seed_project_knowledge(
            project_name="test-project",
            client=None,
            skip_overview=True,
        )

        assert result.success is True
        assert result.architectural_decisions_seeded is False


class TestEstimateEpisodeCountExcludesDecisions:
    """Test that estimate_episode_count excludes system content (TASK-ISF-006)."""

    def test_estimate_excludes_architectural_decisions(self):
        """Estimate should NOT include system content (decisions, constraints, modes)."""
        count = estimate_episode_count(skip_overview=True)

        # With skip_overview and no system content, count should be 0
        assert count == 0
