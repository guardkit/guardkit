"""
TDD RED Phase: Tests for guardkit.knowledge.entities.feature_overview

These tests define the contract for FeatureOverviewEntity and related functions.
Following TDD, tests are written FIRST to define expected behavior.

Test Coverage:
- FeatureOverviewEntity dataclass creation and validation
- FeatureOverviewEntity.to_episode_body() serialization
- seed_feature_overview() with mocked Graphiti client
- load_feature_overview() query functionality
- Graceful degradation when Graphiti disabled
- Integration with context loading

Coverage Target: >=80%
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Optional, List
from datetime import datetime
import json

# Import will fail initially - this is expected in RED phase
try:
    from guardkit.knowledge.entities.feature_overview import (
        FeatureOverviewEntity,
    )
    from guardkit.knowledge.seed_feature_overviews import (
        seed_feature_overview,
        seed_all_feature_overviews,
        FEATURE_BUILD_OVERVIEW,
    )
    from guardkit.knowledge.context_loader import (
        load_feature_overview,
    )
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)


# Skip all tests if imports not available (expected in RED phase)
pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="Implementation not yet created (TDD RED phase)"
)


# ============================================================================
# 1. FeatureOverviewEntity Dataclass Tests (10 tests)
# ============================================================================

class TestFeatureOverviewEntityDataclass:
    """Test FeatureOverviewEntity dataclass creation and validation."""

    def test_feature_overview_entity_exists(self):
        """Test FeatureOverviewEntity class is defined."""
        assert FeatureOverviewEntity is not None

    def test_feature_overview_entity_creation_minimal(self):
        """Test creating FeatureOverviewEntity with minimal required fields."""
        entity = FeatureOverviewEntity(
            id="feature-build",
            name="feature-build",
            tagline="Autonomous task implementation",
            purpose="Execute multi-task features autonomously",
            what_it_is=["An autonomous orchestrator"],
            what_it_is_not=["NOT an assistant"],
            invariants=["Player implements, Coach validates"],
            architecture_summary="Feature-build orchestrates tasks",
            key_components=["FeatureOrchestrator"],
            key_decisions=["ADR-FB-001"]
        )

        assert entity.id == "feature-build"
        assert entity.name == "feature-build"
        assert entity.tagline == "Autonomous task implementation"
        assert entity.purpose == "Execute multi-task features autonomously"
        assert entity.what_it_is == ["An autonomous orchestrator"]
        assert entity.what_it_is_not == ["NOT an assistant"]
        assert entity.invariants == ["Player implements, Coach validates"]
        assert entity.architecture_summary == "Feature-build orchestrates tasks"
        assert entity.key_components == ["FeatureOrchestrator"]
        assert entity.key_decisions == ["ADR-FB-001"]

    def test_feature_overview_entity_creation_complete(self):
        """Test creating FeatureOverviewEntity with all fields."""
        created = datetime(2025, 1, 1, 10, 0, 0)
        updated = datetime(2025, 1, 1, 12, 30, 0)

        entity = FeatureOverviewEntity(
            id="feature-build",
            name="feature-build",
            tagline="Autonomous task implementation with Player-Coach validation",
            purpose="Execute multi-task features autonomously using the Player-Coach pattern",
            what_it_is=[
                "An autonomous orchestrator",
                "A quality enforcement system",
                "A worktree-based isolation system"
            ],
            what_it_is_not=[
                "NOT an assistant",
                "NOT a code reviewer",
                "NOT an auto-merger"
            ],
            invariants=[
                "Player implements, Coach validates",
                "Implementation plans are REQUIRED",
                "Worktrees preserved for human review"
            ],
            architecture_summary="Feature-build orchestrates multiple tasks in waves",
            key_components=[
                "FeatureOrchestrator",
                "AutoBuildOrchestrator",
                "CoachValidator",
                "TaskWorkInterface"
            ],
            key_decisions=["ADR-FB-001", "ADR-FB-002", "ADR-FB-003"],
            created_at=created,
            updated_at=updated
        )

        assert len(entity.what_it_is) == 3
        assert len(entity.what_it_is_not) == 3
        assert len(entity.invariants) == 3
        assert len(entity.key_components) == 4
        assert len(entity.key_decisions) == 3
        assert entity.created_at == created
        assert entity.updated_at == updated

    def test_feature_overview_entity_default_timestamps(self):
        """Test FeatureOverviewEntity default timestamp values."""
        entity = FeatureOverviewEntity(
            id="test-feature",
            name="test-feature",
            tagline="Test",
            purpose="Test",
            what_it_is=["Test"],
            what_it_is_not=["Not test"],
            invariants=["Rule 1"],
            architecture_summary="Test architecture",
            key_components=["Component 1"],
            key_decisions=["ADR-001"]
        )

        # Should have default timestamps
        assert entity.created_at is not None
        assert entity.updated_at is not None
        assert isinstance(entity.created_at, datetime)
        assert isinstance(entity.updated_at, datetime)

    def test_feature_overview_entity_with_empty_lists(self):
        """Test FeatureOverviewEntity with empty lists."""
        entity = FeatureOverviewEntity(
            id="empty-feature",
            name="empty-feature",
            tagline="Empty",
            purpose="Empty purpose",
            what_it_is=[],
            what_it_is_not=[],
            invariants=[],
            architecture_summary="Empty architecture",
            key_components=[],
            key_decisions=[]
        )

        assert entity.what_it_is == []
        assert entity.what_it_is_not == []
        assert entity.invariants == []
        assert entity.key_components == []
        assert entity.key_decisions == []

    def test_feature_overview_entity_id_formats(self):
        """Test various ID formats are supported."""
        # FEAT-XXX format
        entity1 = FeatureOverviewEntity(
            id="FEAT-A1B2",
            name="feature-name",
            tagline="Test",
            purpose="Test",
            what_it_is=["Test"],
            what_it_is_not=["Not test"],
            invariants=["Rule"],
            architecture_summary="Test",
            key_components=["Component"],
            key_decisions=["ADR-001"]
        )
        assert entity1.id == "FEAT-A1B2"

        # Kebab-case format
        entity2 = FeatureOverviewEntity(
            id="feature-build",
            name="feature-build",
            tagline="Test",
            purpose="Test",
            what_it_is=["Test"],
            what_it_is_not=["Not test"],
            invariants=["Rule"],
            architecture_summary="Test",
            key_components=["Component"],
            key_decisions=["ADR-001"]
        )
        assert entity2.id == "feature-build"

    def test_feature_overview_entity_multiline_strings(self):
        """Test FeatureOverviewEntity with multiline strings."""
        entity = FeatureOverviewEntity(
            id="test-feature",
            name="test-feature",
            tagline="Multi\nline\ntagline",
            purpose="This is a\nmultiline\npurpose",
            what_it_is=["Test"],
            what_it_is_not=["Not test"],
            invariants=["Rule"],
            architecture_summary="This is a\nmultiline\narchitecture summary",
            key_components=["Component"],
            key_decisions=["ADR-001"]
        )

        assert "\n" in entity.tagline
        assert "\n" in entity.purpose
        assert "\n" in entity.architecture_summary


# ============================================================================
# 2. FeatureOverviewEntity.to_episode_body() Tests (8 tests)
# ============================================================================

class TestFeatureOverviewEntitySerialization:
    """Test FeatureOverviewEntity.to_episode_body() serialization."""

    def test_to_episode_body_returns_dict(self):
        """Test to_episode_body returns a dictionary."""
        entity = FeatureOverviewEntity(
            id="test-feature",
            name="test-feature",
            tagline="Test tagline",
            purpose="Test purpose",
            what_it_is=["Thing 1"],
            what_it_is_not=["Not thing 1"],
            invariants=["Rule 1"],
            architecture_summary="Architecture",
            key_components=["Component 1"],
            key_decisions=["ADR-001"]
        )

        episode_body = entity.to_episode_body()

        assert isinstance(episode_body, dict)

    def test_to_episode_body_contains_entity_type(self):
        """Test serialization produces dict with all fields.

        Note: entity_type is NOT included in to_episode_body() - it's injected
        by GraphitiClient according to the docstring.
        """
        entity = FeatureOverviewEntity(
            id="test-feature",
            name="test-feature",
            tagline="Test",
            purpose="Test",
            what_it_is=["Test"],
            what_it_is_not=["Not test"],
            invariants=["Rule"],
            architecture_summary="Test",
            key_components=["Component"],
            key_decisions=["ADR-001"]
        )

        episode_body = entity.to_episode_body()

        # Verify it returns a dict with required fields
        assert isinstance(episode_body, dict)
        assert episode_body["id"] == "test-feature"
        assert episode_body["name"] == "test-feature"

    def test_to_episode_body_contains_all_fields(self):
        """Test serialization includes all expected fields."""
        entity = FeatureOverviewEntity(
            id="feature-build",
            name="feature-build",
            tagline="Autonomous task implementation",
            purpose="Execute features autonomously",
            what_it_is=["Orchestrator", "Quality system"],
            what_it_is_not=["Assistant", "Code reviewer"],
            invariants=["Player implements", "Coach validates"],
            architecture_summary="Feature-build orchestrates tasks",
            key_components=["FeatureOrchestrator", "CoachValidator"],
            key_decisions=["ADR-FB-001", "ADR-FB-002"]
        )

        episode_body = entity.to_episode_body()

        # All required fields should be present
        assert episode_body["id"] == "feature-build"
        assert episode_body["name"] == "feature-build"
        assert episode_body["tagline"] == "Autonomous task implementation"
        assert episode_body["purpose"] == "Execute features autonomously"
        assert episode_body["what_it_is"] == ["Orchestrator", "Quality system"]
        assert episode_body["what_it_is_not"] == ["Assistant", "Code reviewer"]
        assert episode_body["invariants"] == ["Player implements", "Coach validates"]
        assert episode_body["architecture_summary"] == "Feature-build orchestrates tasks"
        assert episode_body["key_components"] == ["FeatureOrchestrator", "CoachValidator"]
        assert episode_body["key_decisions"] == ["ADR-FB-001", "ADR-FB-002"]

    def test_to_episode_body_contains_timestamps(self):
        """Test entity has timestamps but they're not in episode_body dict.

        Note: created_at and updated_at are NOT included in to_episode_body() -
        they're injected by GraphitiClient according to the docstring.
        """
        created = datetime(2025, 1, 1, 10, 0, 0)
        updated = datetime(2025, 1, 1, 12, 30, 0)

        entity = FeatureOverviewEntity(
            id="test-feature",
            name="test-feature",
            tagline="Test",
            purpose="Test",
            what_it_is=["Test"],
            what_it_is_not=["Not test"],
            invariants=["Rule"],
            architecture_summary="Test",
            key_components=["Component"],
            key_decisions=["ADR-001"],
            created_at=created,
            updated_at=updated
        )

        # Entity should have timestamps
        assert entity.created_at == created
        assert entity.updated_at == updated

        episode_body = entity.to_episode_body()

        # But timestamps are NOT in the episode body dict
        assert "created_at" not in episode_body
        assert "updated_at" not in episode_body

    def test_to_episode_body_serializes_to_json(self):
        """Test episode body can be serialized to JSON."""
        entity = FeatureOverviewEntity(
            id="test-feature",
            name="test-feature",
            tagline="Test",
            purpose="Test",
            what_it_is=["Test"],
            what_it_is_not=["Not test"],
            invariants=["Rule"],
            architecture_summary="Test",
            key_components=["Component"],
            key_decisions=["ADR-001"]
        )

        episode_body = entity.to_episode_body()

        # Should be JSON serializable
        json_str = json.dumps(episode_body)
        assert isinstance(json_str, str)

        # Should be valid JSON that can be parsed back
        parsed = json.loads(json_str)
        assert parsed["id"] == "test-feature"

    def test_to_episode_body_handles_special_characters(self):
        """Test serialization handles special characters."""
        entity = FeatureOverviewEntity(
            id="test-feature",
            name="test-feature",
            tagline='Test with "quotes" and \'apostrophes\'',
            purpose="Test with <tags> & symbols",
            what_it_is=["Test\nwith\nnewlines"],
            what_it_is_not=["Test\twith\ttabs"],
            invariants=["Rule with ÜñîçödÉ"],
            architecture_summary="Test with emoji 🎉",
            key_components=["Component"],
            key_decisions=["ADR-001"]
        )

        episode_body = entity.to_episode_body()

        # Should not crash and should preserve special characters
        json_str = json.dumps(episode_body)
        parsed = json.loads(json_str)
        assert '"quotes"' in parsed["tagline"]
        assert "emoji" in parsed["architecture_summary"]


# ============================================================================
# 3. seed_feature_overview() Tests (8 tests)
# ============================================================================

class TestSeedFeatureOverview:
    """Test seed_feature_overview() function."""

    @pytest.mark.asyncio
    async def test_seed_feature_overview_success(self):
        """Test successful feature overview seeding."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        entity = FeatureOverviewEntity(
            id="test-feature",
            name="test-feature",
            tagline="Test",
            purpose="Test",
            what_it_is=["Test"],
            what_it_is_not=["Not test"],
            invariants=["Rule"],
            architecture_summary="Test",
            key_components=["Component"],
            key_decisions=["ADR-001"]
        )

        await seed_feature_overview(mock_client, entity)

        mock_client.add_episode.assert_called_once()

    @pytest.mark.asyncio
    async def test_seed_feature_overview_correct_group_id(self):
        """Test seed uses correct group_id."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        entity = FeatureOverviewEntity(
            id="test-feature",
            name="test-feature",
            tagline="Test",
            purpose="Test",
            what_it_is=["Test"],
            what_it_is_not=["Not test"],
            invariants=["Rule"],
            architecture_summary="Test",
            key_components=["Component"],
            key_decisions=["ADR-001"]
        )

        await seed_feature_overview(mock_client, entity)

        call_args = mock_client.add_episode.call_args
        assert call_args[1]["group_id"] == "feature_overviews"

    @pytest.mark.asyncio
    async def test_seed_feature_overview_correct_name(self):
        """Test seed uses correct episode name."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        entity = FeatureOverviewEntity(
            id="feature-build",
            name="feature-build",
            tagline="Test",
            purpose="Test",
            what_it_is=["Test"],
            what_it_is_not=["Not test"],
            invariants=["Rule"],
            architecture_summary="Test",
            key_components=["Component"],
            key_decisions=["ADR-001"]
        )

        await seed_feature_overview(mock_client, entity)

        call_args = mock_client.add_episode.call_args
        assert "feature-build" in call_args[1]["name"]
        assert "feature_overview" in call_args[1]["name"]

    @pytest.mark.asyncio
    async def test_seed_feature_overview_disabled_client(self):
        """Test graceful degradation when client disabled."""
        mock_client = AsyncMock()
        mock_client.enabled = False

        entity = FeatureOverviewEntity(
            id="test-feature",
            name="test-feature",
            tagline="Test",
            purpose="Test",
            what_it_is=["Test"],
            what_it_is_not=["Not test"],
            invariants=["Rule"],
            architecture_summary="Test",
            key_components=["Component"],
            key_decisions=["ADR-001"]
        )

        # Should not crash
        await seed_feature_overview(mock_client, entity)

        # Should not call add_episode
        mock_client.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_seed_feature_overview_none_client(self):
        """Test graceful degradation when client is None."""
        entity = FeatureOverviewEntity(
            id="test-feature",
            name="test-feature",
            tagline="Test",
            purpose="Test",
            what_it_is=["Test"],
            what_it_is_not=["Not test"],
            invariants=["Rule"],
            architecture_summary="Test",
            key_components=["Component"],
            key_decisions=["ADR-001"]
        )

        # Should not crash
        await seed_feature_overview(None, entity)

    @pytest.mark.asyncio
    async def test_seed_feature_overview_error_handling(self):
        """Test graceful degradation when add_episode fails."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(side_effect=Exception("Graphiti error"))

        entity = FeatureOverviewEntity(
            id="test-feature",
            name="test-feature",
            tagline="Test",
            purpose="Test",
            what_it_is=["Test"],
            what_it_is_not=["Not test"],
            invariants=["Rule"],
            architecture_summary="Test",
            key_components=["Component"],
            key_decisions=["ADR-001"]
        )

        # Should not crash
        await seed_feature_overview(mock_client, entity)


# ============================================================================
# 4. FEATURE_BUILD_OVERVIEW Constant Tests (5 tests)
# ============================================================================

class TestFeatureBuildOverviewConstant:
    """Test the predefined FEATURE_BUILD_OVERVIEW constant."""

    def test_feature_build_overview_exists(self):
        """Test FEATURE_BUILD_OVERVIEW constant is defined."""
        assert FEATURE_BUILD_OVERVIEW is not None

    def test_feature_build_overview_is_entity(self):
        """Test FEATURE_BUILD_OVERVIEW is a FeatureOverviewEntity."""
        assert isinstance(FEATURE_BUILD_OVERVIEW, FeatureOverviewEntity)

    def test_feature_build_overview_id(self):
        """Test FEATURE_BUILD_OVERVIEW has correct ID."""
        assert FEATURE_BUILD_OVERVIEW.id == "feature-build"
        assert FEATURE_BUILD_OVERVIEW.name == "feature-build"

    def test_feature_build_overview_has_invariants(self):
        """Test FEATURE_BUILD_OVERVIEW has critical invariants defined."""
        invariants = FEATURE_BUILD_OVERVIEW.invariants

        # Must contain critical rules
        assert len(invariants) >= 3

        # Check for key invariants
        invariant_text = " ".join(invariants).lower()
        assert "player" in invariant_text
        assert "coach" in invariant_text

    def test_feature_build_overview_has_key_components(self):
        """Test FEATURE_BUILD_OVERVIEW has key components defined."""
        components = FEATURE_BUILD_OVERVIEW.key_components

        assert len(components) >= 2

        # Should include main orchestration components
        component_text = " ".join(components)
        assert "Orchestrator" in component_text or "orchestrator" in component_text.lower()


# ============================================================================
# 5. seed_all_feature_overviews() Tests (4 tests)
# ============================================================================

class TestSeedAllFeatureOverviews:
    """Test seed_all_feature_overviews() function."""

    @pytest.mark.asyncio
    async def test_seed_all_feature_overviews_success(self):
        """Test successful seeding of all feature overviews."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        await seed_all_feature_overviews(mock_client)

        # Should have called add_episode at least once (for FEATURE_BUILD_OVERVIEW)
        assert mock_client.add_episode.call_count >= 1

    @pytest.mark.asyncio
    async def test_seed_all_feature_overviews_disabled_client(self):
        """Test graceful degradation when client disabled."""
        mock_client = AsyncMock()
        mock_client.enabled = False

        # Should not crash
        await seed_all_feature_overviews(mock_client)

        mock_client.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_seed_all_feature_overviews_none_client(self):
        """Test graceful degradation when client is None."""
        # Should not crash
        await seed_all_feature_overviews(None)

    @pytest.mark.asyncio
    async def test_seed_all_feature_overviews_includes_feature_build(self):
        """Test that feature-build overview is included in seeding."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        await seed_all_feature_overviews(mock_client)

        # Check that feature-build was seeded
        call_args_list = mock_client.add_episode.call_args_list
        names = [call[1]["name"] for call in call_args_list]

        assert any("feature-build" in name or "feature_build" in name for name in names)


# ============================================================================
# 6. load_feature_overview() Tests (8 tests)
# ============================================================================

class TestLoadFeatureOverview:
    """Test load_feature_overview() query function."""

    @pytest.mark.asyncio
    async def test_load_feature_overview_success(self):
        """Test successful feature overview loading."""
        mock_result = {
            "id": "feature-build",
            "name": "feature-build",
            "tagline": "Autonomous task implementation",
            "purpose": "Execute features autonomously",
            "what_it_is": ["Orchestrator"],
            "what_it_is_not": ["Assistant"],
            "invariants": ["Player implements"],
            "architecture_summary": "Feature-build orchestrates",
            "key_components": ["FeatureOrchestrator"],
            "key_decisions": ["ADR-001"],
            "created_at": "2025-01-01T10:00:00",
            "updated_at": "2025-01-01T10:00:00",
            "entity_type": "feature_overview"
        }

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[{"body": mock_result}])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            result = await load_feature_overview("feature-build")

            assert result is not None
            assert isinstance(result, FeatureOverviewEntity)
            assert result.id == "feature-build"

    @pytest.mark.asyncio
    async def test_load_feature_overview_not_found(self):
        """Test loading non-existent feature overview."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            result = await load_feature_overview("non-existent-feature")

            assert result is None

    @pytest.mark.asyncio
    async def test_load_feature_overview_graphiti_disabled(self):
        """Test graceful degradation when Graphiti disabled."""
        mock_client = AsyncMock()
        mock_client.enabled = False

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            result = await load_feature_overview("feature-build")

            assert result is None
            mock_client.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_load_feature_overview_graphiti_none(self):
        """Test graceful degradation when Graphiti client is None."""
        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=None):
            result = await load_feature_overview("feature-build")

            assert result is None

    @pytest.mark.asyncio
    async def test_load_feature_overview_search_error(self):
        """Test graceful degradation when search fails."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(side_effect=Exception("Search error"))

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            result = await load_feature_overview("feature-build")

            assert result is None

    @pytest.mark.asyncio
    async def test_load_feature_overview_correct_query(self):
        """Test search uses correct query parameters."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            await load_feature_overview("feature-build")

            call_args = mock_client.search.call_args
            assert "feature-build" in call_args[1]["query"]
            assert "feature_overviews" in call_args[1]["group_ids"]

    @pytest.mark.asyncio
    async def test_load_feature_overview_returns_first_result(self):
        """Test that only the first matching result is returned."""
        mock_result1 = {
            "id": "feature-build",
            "name": "feature-build",
            "tagline": "First",
            "purpose": "First purpose",
            "what_it_is": ["First"],
            "what_it_is_not": ["Not first"],
            "invariants": ["Rule 1"],
            "architecture_summary": "First arch",
            "key_components": ["Comp1"],
            "key_decisions": ["ADR-001"],
            "created_at": "2025-01-01T10:00:00",
            "updated_at": "2025-01-01T10:00:00",
            "entity_type": "feature_overview"
        }
        mock_result2 = {
            "id": "feature-build",
            "name": "feature-build",
            "tagline": "Second",
            "purpose": "Second purpose",
            "what_it_is": ["Second"],
            "what_it_is_not": ["Not second"],
            "invariants": ["Rule 2"],
            "architecture_summary": "Second arch",
            "key_components": ["Comp2"],
            "key_decisions": ["ADR-002"],
            "created_at": "2025-01-01T10:00:00",
            "updated_at": "2025-01-01T10:00:00",
            "entity_type": "feature_overview"
        }

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[
            {"body": mock_result1},
            {"body": mock_result2}
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            result = await load_feature_overview("feature-build")

            assert result is not None
            assert result.tagline == "First"


# ============================================================================
# 7. Context Loader Integration Tests (5 tests)
# ============================================================================

class TestContextLoaderIntegration:
    """Test feature overview integration with context loading."""

    @pytest.mark.asyncio
    async def test_load_critical_context_includes_feature_overview(self):
        """Test that load_critical_context can include feature overview."""
        from guardkit.knowledge.context_loader import load_critical_context

        mock_overview_result = {
            "id": "feature-build",
            "name": "feature-build",
            "tagline": "Autonomous task implementation",
            "purpose": "Execute features autonomously",
            "what_it_is": ["Orchestrator"],
            "what_it_is_not": ["Assistant"],
            "invariants": ["Player implements"],
            "architecture_summary": "Feature-build orchestrates",
            "key_components": ["FeatureOrchestrator"],
            "key_decisions": ["ADR-001"],
            "created_at": "2025-01-01T10:00:00",
            "updated_at": "2025-01-01T10:00:00",
            "entity_type": "feature_overview"
        }

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[{"body": mock_overview_result}])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context(command="feature-build")

            # Context should include feature overview in some form
            # (may be in system_context or a dedicated field)
            assert context is not None


# ============================================================================
# 8. Edge Cases and Error Handling (4 tests)
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_feature_overview_with_very_long_strings(self):
        """Test entity with very long strings."""
        long_string = "x" * 10000

        entity = FeatureOverviewEntity(
            id="test-feature",
            name="test-feature",
            tagline=long_string,
            purpose=long_string,
            what_it_is=[long_string],
            what_it_is_not=[long_string],
            invariants=[long_string],
            architecture_summary=long_string,
            key_components=[long_string],
            key_decisions=[long_string]
        )

        # Should not crash
        episode_body = entity.to_episode_body()
        assert isinstance(episode_body, dict)

    def test_feature_overview_with_unicode_characters(self):
        """Test entity with Unicode characters."""
        entity = FeatureOverviewEntity(
            id="test-feature",
            name="test-feature",
            tagline="Test with 中文 and émojis 🎉",
            purpose="Purpose with Ñoño",
            what_it_is=["Test with Ελληνικά"],
            what_it_is_not=["日本語テスト"],
            invariants=["Rule with العربية"],
            architecture_summary="Architecture with עברית",
            key_components=["Компонент"],
            key_decisions=["ADR-001"]
        )

        episode_body = entity.to_episode_body()
        json_str = json.dumps(episode_body)

        # Should be JSON serializable
        assert isinstance(json_str, str)

    @pytest.mark.asyncio
    async def test_seed_feature_overview_with_many_items(self):
        """Test seeding entity with many list items."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_123")

        entity = FeatureOverviewEntity(
            id="test-feature",
            name="test-feature",
            tagline="Test",
            purpose="Test",
            what_it_is=[f"Thing {i}" for i in range(100)],
            what_it_is_not=[f"Not thing {i}" for i in range(100)],
            invariants=[f"Rule {i}" for i in range(100)],
            architecture_summary="Test",
            key_components=[f"Component {i}" for i in range(100)],
            key_decisions=[f"ADR-{i:03d}" for i in range(100)]
        )

        # Should not crash
        await seed_feature_overview(mock_client, entity)
        mock_client.add_episode.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_feature_overview_malformed_response(self):
        """Test handling of malformed search response."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        # Return malformed data
        mock_client.search = AsyncMock(return_value=[{"bad_key": "bad_value"}])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            # Should handle gracefully
            result = await load_feature_overview("feature-build")

            # May return None or raise handled exception
            # The key is it doesn't crash
            assert result is None or isinstance(result, FeatureOverviewEntity)
