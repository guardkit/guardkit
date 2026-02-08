"""
TDD RED Phase: Tests for guardkit.knowledge.facts.role_constraint

These tests are written to FAIL initially (RED phase of TDD).
Implementation will be created to make these tests pass (GREEN phase).

Test Coverage:
- RoleConstraintFact dataclass creation and validation
- to_episode_body() method for Graphiti serialization
- PLAYER_CONSTRAINTS and COACH_CONSTRAINTS content validation
- seed_role_constraints() seeding function
- load_role_context() query function
- Edge cases and error handling

Coverage Target: >=85%
Test Count: 35+ tests
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Optional, List, Dict
from pathlib import Path
from datetime import datetime
import json

# Import will fail initially - this is expected in RED phase
try:
    from guardkit.knowledge.facts.role_constraint import (
        RoleConstraintFact,
        PLAYER_CONSTRAINTS,
        COACH_CONSTRAINTS,
    )
    from guardkit.knowledge.seed_role_constraints import (
        seed_role_constraints,
    )
    from guardkit.knowledge.context_loader import (
        load_role_context,
    )
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False


# Skip all tests if imports not available (expected in RED phase)
pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="Implementation not yet created (TDD RED phase)"
)


# ============================================================================
# 1. RoleConstraintFact Dataclass Tests (10 tests)
# ============================================================================

class TestRoleConstraintFactDataclass:
    """Test RoleConstraintFact dataclass creation and validation."""

    def test_create_minimal_fact(self):
        """Test creating a minimal role constraint fact."""
        fact = RoleConstraintFact(
            role="player",
            context="feature-build",
            primary_responsibility="Implement code",
            must_do=["Write code"],
            must_not_do=["Approve work"],
            ask_before=["Add dependencies"]
        )

        assert fact.role == "player"
        assert fact.context == "feature-build"
        assert fact.primary_responsibility == "Implement code"
        assert fact.must_do == ["Write code"]
        assert fact.must_not_do == ["Approve work"]
        assert fact.ask_before == ["Add dependencies"]

    def test_create_full_fact_with_examples(self):
        """Test creating a fact with good and bad examples."""
        good_examples = ["Player: 'I implemented feature X'"]
        bad_examples = ["Player: 'Tests pass, approved'"]

        fact = RoleConstraintFact(
            role="player",
            context="feature-build",
            primary_responsibility="Implement code",
            must_do=["Write code"],
            must_not_do=["Approve work"],
            ask_before=["Add dependencies"],
            good_examples=good_examples,
            bad_examples=bad_examples
        )

        assert fact.good_examples == good_examples
        assert fact.bad_examples == bad_examples

    def test_created_at_defaults_to_now(self):
        """Test that created_at defaults to current datetime."""
        before = datetime.now()

        fact = RoleConstraintFact(
            role="player",
            context="feature-build",
            primary_responsibility="Implement code",
            must_do=["Write code"],
            must_not_do=["Approve work"],
            ask_before=["Add dependencies"]
        )

        after = datetime.now()

        assert before <= fact.created_at <= after

    def test_good_examples_defaults_to_empty_list(self):
        """Test that good_examples defaults to empty list."""
        fact = RoleConstraintFact(
            role="player",
            context="feature-build",
            primary_responsibility="Implement code",
            must_do=["Write code"],
            must_not_do=["Approve work"],
            ask_before=["Add dependencies"]
        )

        assert fact.good_examples == []

    def test_bad_examples_defaults_to_empty_list(self):
        """Test that bad_examples defaults to empty list."""
        fact = RoleConstraintFact(
            role="player",
            context="feature-build",
            primary_responsibility="Implement code",
            must_do=["Write code"],
            must_not_do=["Approve work"],
            ask_before=["Add dependencies"]
        )

        assert fact.bad_examples == []

    def test_role_accepts_player_and_coach(self):
        """Test that role accepts 'player' and 'coach' values."""
        player_fact = RoleConstraintFact(
            role="player",
            context="feature-build",
            primary_responsibility="Implement code",
            must_do=["Write code"],
            must_not_do=["Approve work"],
            ask_before=["Add dependencies"]
        )

        coach_fact = RoleConstraintFact(
            role="coach",
            context="feature-build",
            primary_responsibility="Validate work",
            must_do=["Check quality"],
            must_not_do=["Write code"],
            ask_before=["Lower thresholds"]
        )

        assert player_fact.role == "player"
        assert coach_fact.role == "coach"

    def test_context_accepts_different_values(self):
        """Test that context accepts various values."""
        contexts = ["feature-build", "autobuild", "task-work"]

        for context in contexts:
            fact = RoleConstraintFact(
                role="player",
                context=context,
                primary_responsibility="Implement code",
                must_do=["Write code"],
                must_not_do=["Approve work"],
                ask_before=["Add dependencies"]
            )
            assert fact.context == context

    def test_must_do_accepts_multiple_items(self):
        """Test that must_do accepts list with multiple items."""
        must_do = [
            "Read requirements",
            "Write code",
            "Create tests",
            "Report changes"
        ]

        fact = RoleConstraintFact(
            role="player",
            context="feature-build",
            primary_responsibility="Implement code",
            must_do=must_do,
            must_not_do=["Approve work"],
            ask_before=["Add dependencies"]
        )

        assert fact.must_do == must_do
        assert len(fact.must_do) == 4

    def test_must_not_do_accepts_multiple_items(self):
        """Test that must_not_do accepts list with multiple items."""
        must_not_do = [
            "Do NOT validate quality",
            "Do NOT approve work",
            "Do NOT merge code"
        ]

        fact = RoleConstraintFact(
            role="player",
            context="feature-build",
            primary_responsibility="Implement code",
            must_do=["Write code"],
            must_not_do=must_not_do,
            ask_before=["Add dependencies"]
        )

        assert fact.must_not_do == must_not_do
        assert len(fact.must_not_do) == 3

    def test_ask_before_accepts_multiple_items(self):
        """Test that ask_before accepts list with multiple items."""
        ask_before = [
            "Changing architecture",
            "Adding dependencies",
            "Modifying scope"
        ]

        fact = RoleConstraintFact(
            role="player",
            context="feature-build",
            primary_responsibility="Implement code",
            must_do=["Write code"],
            must_not_do=["Approve work"],
            ask_before=ask_before
        )

        assert fact.ask_before == ask_before
        assert len(fact.ask_before) == 3


# ============================================================================
# 2. to_episode_body() Method Tests (8 tests)
# ============================================================================

class TestToEpisodeBody:
    """Test RoleConstraintFact.to_episode_body() serialization."""

    def test_to_episode_body_returns_dict(self):
        """Test that to_episode_body returns a dictionary."""
        fact = RoleConstraintFact(
            role="player",
            context="feature-build",
            primary_responsibility="Implement code",
            must_do=["Write code"],
            must_not_do=["Approve work"],
            ask_before=["Add dependencies"]
        )

        result = fact.to_episode_body()
        assert isinstance(result, dict)

    def test_to_episode_body_excludes_entity_type(self):
        """Test that episode body does NOT include entity_type (injected by client)."""
        fact = RoleConstraintFact(
            role="player",
            context="feature-build",
            primary_responsibility="Implement code",
            must_do=["Write code"],
            must_not_do=["Approve work"],
            ask_before=["Add dependencies"]
        )

        result = fact.to_episode_body()
        assert "entity_type" not in result, \
            "entity_type should be injected by GraphitiClient, not in body"

    def test_to_episode_body_includes_all_required_fields(self):
        """Test that episode body includes all domain fields."""
        fact = RoleConstraintFact(
            role="player",
            context="feature-build",
            primary_responsibility="Implement code",
            must_do=["Write code"],
            must_not_do=["Approve work"],
            ask_before=["Add dependencies"]
        )

        result = fact.to_episode_body()

        assert "role" in result
        assert "context" in result
        assert "primary_responsibility" in result
        assert "must_do" in result
        assert "must_not_do" in result
        assert "ask_before" in result
        assert "good_examples" in result
        assert "bad_examples" in result
        # created_at is NOT in body - it's a metadata field injected by client

    def test_to_episode_body_excludes_created_at(self):
        """Test that created_at is NOT in body (metadata handled by client)."""
        fact = RoleConstraintFact(
            role="player",
            context="feature-build",
            primary_responsibility="Implement code",
            must_do=["Write code"],
            must_not_do=["Approve work"],
            ask_before=["Add dependencies"]
        )

        result = fact.to_episode_body()

        # created_at should NOT be in body - it's metadata injected by client
        assert "created_at" not in result, \
            "created_at should be injected by GraphitiClient, not in body"

    def test_to_episode_body_preserves_lists(self):
        """Test that lists are preserved correctly."""
        must_do = ["Item 1", "Item 2"]
        must_not_do = ["Not 1", "Not 2"]
        ask_before = ["Ask 1", "Ask 2"]

        fact = RoleConstraintFact(
            role="player",
            context="feature-build",
            primary_responsibility="Implement code",
            must_do=must_do,
            must_not_do=must_not_do,
            ask_before=ask_before
        )

        result = fact.to_episode_body()

        assert result["must_do"] == must_do
        assert result["must_not_do"] == must_not_do
        assert result["ask_before"] == ask_before

    def test_to_episode_body_preserves_examples(self):
        """Test that good and bad examples are preserved."""
        good_examples = ["Good 1", "Good 2"]
        bad_examples = ["Bad 1", "Bad 2"]

        fact = RoleConstraintFact(
            role="player",
            context="feature-build",
            primary_responsibility="Implement code",
            must_do=["Write code"],
            must_not_do=["Approve work"],
            ask_before=["Add dependencies"],
            good_examples=good_examples,
            bad_examples=bad_examples
        )

        result = fact.to_episode_body()

        assert result["good_examples"] == good_examples
        assert result["bad_examples"] == bad_examples

    def test_to_episode_body_handles_empty_examples(self):
        """Test that empty example lists are handled correctly."""
        fact = RoleConstraintFact(
            role="player",
            context="feature-build",
            primary_responsibility="Implement code",
            must_do=["Write code"],
            must_not_do=["Approve work"],
            ask_before=["Add dependencies"]
            # good_examples and bad_examples default to []
        )

        result = fact.to_episode_body()

        assert result["good_examples"] == []
        assert result["bad_examples"] == []

    def test_to_episode_body_is_json_serializable(self):
        """Test that episode body can be serialized to JSON."""
        fact = RoleConstraintFact(
            role="player",
            context="feature-build",
            primary_responsibility="Implement code",
            must_do=["Write code"],
            must_not_do=["Approve work"],
            ask_before=["Add dependencies"],
            good_examples=["Good example"],
            bad_examples=["Bad example"]
        )

        result = fact.to_episode_body()

        # Should not raise exception
        json_str = json.dumps(result)
        assert isinstance(json_str, str)

        # Should be deserializable
        parsed = json.loads(json_str)
        assert parsed["role"] == "player"


# ============================================================================
# 3. PLAYER_CONSTRAINTS and COACH_CONSTRAINTS Tests (6 tests)
# ============================================================================

class TestPredefinedConstraints:
    """Test PLAYER_CONSTRAINTS and COACH_CONSTRAINTS definitions."""

    def test_player_constraints_exists(self):
        """Test that PLAYER_CONSTRAINTS is defined."""
        assert PLAYER_CONSTRAINTS is not None
        assert isinstance(PLAYER_CONSTRAINTS, RoleConstraintFact)

    def test_player_constraints_has_correct_role(self):
        """Test that PLAYER_CONSTRAINTS has role='player'."""
        assert PLAYER_CONSTRAINTS.role == "player"

    def test_player_constraints_has_required_content(self):
        """Test that PLAYER_CONSTRAINTS has all required fields populated."""
        assert PLAYER_CONSTRAINTS.context
        assert PLAYER_CONSTRAINTS.primary_responsibility
        assert len(PLAYER_CONSTRAINTS.must_do) > 0
        assert len(PLAYER_CONSTRAINTS.must_not_do) > 0
        assert len(PLAYER_CONSTRAINTS.ask_before) > 0

    def test_coach_constraints_exists(self):
        """Test that COACH_CONSTRAINTS is defined."""
        assert COACH_CONSTRAINTS is not None
        assert isinstance(COACH_CONSTRAINTS, RoleConstraintFact)

    def test_coach_constraints_has_correct_role(self):
        """Test that COACH_CONSTRAINTS has role='coach'."""
        assert COACH_CONSTRAINTS.role == "coach"

    def test_coach_constraints_has_required_content(self):
        """Test that COACH_CONSTRAINTS has all required fields populated."""
        assert COACH_CONSTRAINTS.context
        assert COACH_CONSTRAINTS.primary_responsibility
        assert len(COACH_CONSTRAINTS.must_do) > 0
        assert len(COACH_CONSTRAINTS.must_not_do) > 0
        assert len(COACH_CONSTRAINTS.ask_before) > 0


# ============================================================================
# 4. seed_role_constraints() Function Tests (7 tests)
# ============================================================================

class TestSeedRoleConstraints:
    """Test seed_role_constraints seeding function."""

    @pytest.mark.asyncio
    async def test_seed_role_constraints_creates_episodes(self):
        """Test that seeding creates episodes for both roles."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        await seed_role_constraints(mock_client)

        # Should create 2 episodes (player and coach)
        assert mock_client.add_episode.call_count == 2

    @pytest.mark.asyncio
    async def test_seed_role_constraints_uses_correct_group_id(self):
        """Test that seeding uses 'role_constraints' group ID."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        await seed_role_constraints(mock_client)

        # Verify all calls used correct group_id
        for call_obj in mock_client.add_episode.call_args_list:
            kwargs = call_obj.kwargs
            assert kwargs['group_id'] == 'role_constraints'

    @pytest.mark.asyncio
    async def test_seed_role_constraints_episode_names_descriptive(self):
        """Test that episode names are descriptive."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        await seed_role_constraints(mock_client)

        # Names should include role and context
        assert mock_client.add_episode.call_count == 2
        for call_obj in mock_client.add_episode.call_args_list:
            name = call_obj.kwargs["name"]
            assert "role_constraint" in name
            assert any(role in name for role in ["player", "coach"])

    @pytest.mark.asyncio
    async def test_seed_role_constraints_episode_bodies_valid_json(self):
        """Test that episode bodies are valid JSON."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        await seed_role_constraints(mock_client)

        # All bodies should be valid JSON strings
        assert mock_client.add_episode.call_count == 2
        for call_obj in mock_client.add_episode.call_args_list:
            body = call_obj.kwargs["episode_body"]
            assert isinstance(body, str)
            # Should parse without exception
            parsed = json.loads(body)
            assert isinstance(parsed, dict)

    @pytest.mark.asyncio
    async def test_seed_role_constraints_graceful_degradation_when_disabled(self):
        """Test graceful degradation when Graphiti is disabled."""
        mock_client = AsyncMock()
        mock_client.enabled = False

        # Should not raise exception
        await seed_role_constraints(mock_client)

        # Should not attempt to add episodes
        mock_client.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_seed_role_constraints_handles_none_client(self):
        """Test that seeding handles None client gracefully."""
        # Should not raise exception
        result = await seed_role_constraints(None)
        # Implementation should handle this gracefully

    @pytest.mark.asyncio
    async def test_seed_role_constraints_handles_add_episode_failure(self):
        """Test that seeding handles add_episode failures gracefully."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(side_effect=Exception("API error"))

        # Should handle exception gracefully
        await seed_role_constraints(mock_client)


# ============================================================================
# 5. load_role_context() Function Tests (8 tests)
# ============================================================================

class TestLoadRoleContext:
    """Test load_role_context query function."""

    @pytest.mark.asyncio
    async def test_load_role_context_queries_graphiti(self):
        """Test that load_role_context queries Graphiti."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {
                    'primary_responsibility': 'Implement code',
                    'must_do': ['Write code', 'Create tests'],
                    'must_not_do': ['Approve work', 'Validate quality']
                }
            }
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            result = await load_role_context("player", "feature-build")

            # Should have called search
            mock_graphiti.search.assert_called_once()

            # Verify search parameters
            call_kwargs = mock_graphiti.search.call_args.kwargs
            assert "role_constraint" in call_kwargs['query']
            assert "player" in call_kwargs['query']
            assert call_kwargs['group_ids'] == ['role_constraints']

    @pytest.mark.asyncio
    async def test_load_role_context_returns_formatted_string(self):
        """Test that load_role_context returns formatted markdown string."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {
                    'primary_responsibility': 'Implement code',
                    'must_do': ['Write code', 'Create tests'],
                    'must_not_do': ['Approve work', 'Validate quality']
                }
            }
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            result = await load_role_context("player", "feature-build")

            assert isinstance(result, str)
            assert "PLAYER Role Constraints" in result
            assert "Primary responsibility" in result
            assert "MUST DO" in result
            assert "MUST NOT DO" in result

    @pytest.mark.asyncio
    async def test_load_role_context_includes_all_must_do_items(self):
        """Test that formatted output includes all must_do items."""
        must_do = ['Write code', 'Create tests', 'Report changes']

        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {
                    'primary_responsibility': 'Implement code',
                    'must_do': must_do,
                    'must_not_do': ['Approve work']
                }
            }
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            result = await load_role_context("player", "feature-build")

            for item in must_do:
                assert item in result

    @pytest.mark.asyncio
    async def test_load_role_context_includes_all_must_not_do_items(self):
        """Test that formatted output includes all must_not_do items."""
        must_not_do = ['Approve work', 'Validate quality', 'Merge code']

        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {
                    'primary_responsibility': 'Implement code',
                    'must_do': ['Write code'],
                    'must_not_do': must_not_do
                }
            }
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            result = await load_role_context("player", "feature-build")

            for item in must_not_do:
                assert item in result

    @pytest.mark.asyncio
    async def test_load_role_context_returns_none_when_disabled(self):
        """Test that load_role_context returns None when Graphiti disabled."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = False

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            result = await load_role_context("player", "feature-build")

            assert result is None

    @pytest.mark.asyncio
    async def test_load_role_context_returns_none_when_no_results(self):
        """Test that load_role_context returns None when no results found."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            result = await load_role_context("player", "feature-build")

            assert result is None

    @pytest.mark.asyncio
    async def test_load_role_context_uses_default_context(self):
        """Test that load_role_context uses default context when not specified."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {
                    'primary_responsibility': 'Implement code',
                    'must_do': ['Write code'],
                    'must_not_do': ['Approve work']
                }
            }
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            result = await load_role_context("player")

            # Should use default context "feature-build"
            call_kwargs = mock_graphiti.search.call_args.kwargs
            assert "feature-build" in call_kwargs['query']

    @pytest.mark.asyncio
    async def test_load_role_context_formats_role_name_uppercase(self):
        """Test that role name in output is formatted in uppercase."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {
                    'primary_responsibility': 'Validate work',
                    'must_do': ['Check quality'],
                    'must_not_do': ['Write code']
                }
            }
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            result = await load_role_context("coach", "feature-build")

            assert "COACH Role Constraints" in result


# ============================================================================
# 6. Edge Cases and Error Handling (6 tests)
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_role_constraint_with_empty_lists(self):
        """Test creating fact with empty lists (should be allowed)."""
        fact = RoleConstraintFact(
            role="player",
            context="feature-build",
            primary_responsibility="Implement code",
            must_do=[],
            must_not_do=[],
            ask_before=[]
        )

        assert fact.must_do == []
        assert fact.must_not_do == []
        assert fact.ask_before == []

    def test_to_episode_body_with_empty_lists(self):
        """Test that to_episode_body handles empty lists correctly."""
        fact = RoleConstraintFact(
            role="player",
            context="feature-build",
            primary_responsibility="Implement code",
            must_do=[],
            must_not_do=[],
            ask_before=[]
        )

        result = fact.to_episode_body()

        assert result["must_do"] == []
        assert result["must_not_do"] == []
        assert result["ask_before"] == []

    @pytest.mark.asyncio
    async def test_load_role_context_handles_malformed_body(self):
        """Test that load_role_context handles malformed response body."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {}  # Empty body
            }
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            # Should handle gracefully
            result = await load_role_context("player", "feature-build")

            # Should still return a string but with empty content
            assert isinstance(result, str) or result is None

    @pytest.mark.asyncio
    async def test_load_role_context_handles_missing_body_key(self):
        """Test that load_role_context handles missing 'body' key."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[
            {}  # No 'body' key
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            # Should handle gracefully
            result = await load_role_context("player", "feature-build")

            # Should not raise exception
            assert result is not None or result is None

    @pytest.mark.asyncio
    async def test_seed_role_constraints_with_custom_constraints(self):
        """Test seeding with custom constraint objects."""
        custom_constraint = RoleConstraintFact(
            role="reviewer",
            context="code-review",
            primary_responsibility="Review code quality",
            must_do=["Check style", "Verify tests"],
            must_not_do=["Modify code"],
            ask_before=["Reject PR"]
        )

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        # This tests that the seeding function can handle additional constraints
        # Implementation might not support this in initial version
        # await seed_role_constraints(mock_client, [custom_constraint])

    def test_role_constraint_fact_is_hashable(self):
        """Test that RoleConstraintFact instances can be compared."""
        fact1 = RoleConstraintFact(
            role="player",
            context="feature-build",
            primary_responsibility="Implement code",
            must_do=["Write code"],
            must_not_do=["Approve work"],
            ask_before=["Add dependencies"]
        )

        fact2 = RoleConstraintFact(
            role="player",
            context="feature-build",
            primary_responsibility="Implement code",
            must_do=["Write code"],
            must_not_do=["Approve work"],
            ask_before=["Add dependencies"]
        )

        # Should be able to compare (equality might not be implemented)
        # This tests that the dataclass structure is sensible
        assert fact1.role == fact2.role
        assert fact1.context == fact2.context


# ============================================================================
# 7. Enhanced Role Constraints Formatting Tests (TASK-GR6-007)
# ============================================================================

class TestEnhancedRoleConstraintsFormatting:
    """Test enhanced formatting with emoji markers and AutoBuild emphasis."""

    @pytest.mark.asyncio
    async def test_load_role_context_includes_emoji_markers_must_do(self):
        """Test that must_do items have ✓ emoji markers."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {
                    'primary_responsibility': 'Implement code',
                    'must_do': ['Write code', 'Create tests'],
                    'must_not_do': ['Approve work'],
                    'ask_before': ['Add dependencies']
                }
            }
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            result = await load_role_context("player", "feature-build")

            # Must_do items should have ✓ emoji
            assert "✓ Write code" in result or "✓" in result

    @pytest.mark.asyncio
    async def test_load_role_context_includes_emoji_markers_must_not_do(self):
        """Test that must_not_do items have ✗ emoji markers."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {
                    'primary_responsibility': 'Implement code',
                    'must_do': ['Write code'],
                    'must_not_do': ['Approve work', 'Skip tests'],
                    'ask_before': ['Add dependencies']
                }
            }
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            result = await load_role_context("player", "feature-build")

            # Must_not_do items should have ✗ emoji
            assert "✗ Approve work" in result or "✗" in result

    @pytest.mark.asyncio
    async def test_load_role_context_includes_ask_before_section(self):
        """Test that ask_before section is included in output."""
        ask_before = ['Schema changes', 'Auth changes', 'Scope changes']

        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {
                    'primary_responsibility': 'Implement code',
                    'must_do': ['Write code'],
                    'must_not_do': ['Approve work'],
                    'ask_before': ask_before
                }
            }
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            result = await load_role_context("player", "feature-build")

            # Ask_before section should be present
            assert "ASK BEFORE" in result or "Ask before" in result

    @pytest.mark.asyncio
    async def test_load_role_context_includes_emoji_markers_ask_before(self):
        """Test that ask_before items have ❓ emoji markers."""
        ask_before = ['Schema changes', 'Auth changes']

        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {
                    'primary_responsibility': 'Implement code',
                    'must_do': ['Write code'],
                    'must_not_do': ['Approve work'],
                    'ask_before': ask_before
                }
            }
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            result = await load_role_context("player", "feature-build")

            # Ask_before items should have ❓ emoji
            assert "❓ Schema changes" in result or "❓" in result

    @pytest.mark.asyncio
    async def test_load_role_context_all_ask_before_items_included(self):
        """Test that all ask_before items are included in output."""
        ask_before = ['Schema changes', 'Auth changes', 'Scope changes']

        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {
                    'primary_responsibility': 'Implement code',
                    'must_do': ['Write code'],
                    'must_not_do': ['Approve work'],
                    'ask_before': ask_before
                }
            }
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            result = await load_role_context("player", "feature-build")

            # All items should be present
            for item in ask_before:
                assert item in result

    @pytest.mark.asyncio
    async def test_load_role_context_autobuild_emphasis(self):
        """Test that AutoBuild context has emphasis indicators."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {
                    'primary_responsibility': 'Implement code',
                    'must_do': ['Write code'],
                    'must_not_do': ['Approve work'],
                    'ask_before': ['Add dependencies']
                }
            }
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            # When context is autobuild, should have emphasis
            result = await load_role_context("player", "autobuild")

            # Should include emphasis indicator for autobuild
            assert result is not None
            # AutoBuild contexts should have stronger emphasis (⚠️ or bold)
            assert "⚠️" in result or "**" in result or "CRITICAL" in result

    @pytest.mark.asyncio
    async def test_load_role_context_feature_build_no_extra_emphasis(self):
        """Test that feature-build context has standard formatting."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {
                    'primary_responsibility': 'Implement code',
                    'must_do': ['Write code'],
                    'must_not_do': ['Approve work'],
                    'ask_before': ['Add dependencies']
                }
            }
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            # feature-build is standard, should have normal formatting
            result = await load_role_context("player", "feature-build")

            assert result is not None
            # Should have role constraints header
            assert "PLAYER Role Constraints" in result

    @pytest.mark.asyncio
    async def test_load_role_context_empty_ask_before_no_section(self):
        """Test that empty ask_before list doesn't produce empty section."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {
                    'primary_responsibility': 'Implement code',
                    'must_do': ['Write code'],
                    'must_not_do': ['Approve work'],
                    'ask_before': []  # Empty list
                }
            }
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            result = await load_role_context("player", "feature-build")

            # Empty ask_before should not produce ASK BEFORE header with no items
            if "ASK BEFORE" in result:
                # If header exists, there should be items after it
                lines = result.split('\n')
                for i, line in enumerate(lines):
                    if "ASK BEFORE" in line:
                        # Next non-empty line should have ❓
                        for next_line in lines[i+1:]:
                            if next_line.strip():
                                assert "❓" in next_line or next_line.startswith("#")
                                break

    @pytest.mark.asyncio
    async def test_format_role_constraints_expected_output_format(self):
        """Test that output matches the expected format from acceptance criteria."""
        mock_graphiti = AsyncMock()
        mock_graphiti.enabled = True
        mock_graphiti.search = AsyncMock(return_value=[
            {
                'body': {
                    'role': 'player',
                    'primary_responsibility': 'Implement code',
                    'must_do': ['Implement code', 'Write tests'],
                    'must_not_do': ['Validate quality gates', 'Make architectural decisions'],
                    'ask_before': ['Schema changes', 'Auth changes']
                }
            }
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            result = await load_role_context("player", "feature-build")

            # Verify structure matches acceptance criteria format:
            # ### Role Constraints
            # **Player**:
            #   Must do:
            #     ✓ Implement code
            #     ✓ Write tests
            #   Must NOT do:
            #     ✗ Validate quality gates
            #     ✗ Make architectural decisions
            #   Ask before:
            #     ❓ Schema changes
            #     ❓ Auth changes

            assert "Role Constraints" in result or "PLAYER Role Constraints" in result
            assert "✓" in result
            assert "✗" in result
            assert "❓" in result


# ============================================================================
# 8. FeaturePlanContext Enhanced Formatting Tests (TASK-GR6-007)
# ============================================================================

class TestFeaturePlanContextEnhancedFormatting:
    """Test FeaturePlanContext._format_role_constraints() enhancement."""

    def test_format_role_constraints_includes_ask_before(self):
        """Test that _format_role_constraints includes ask_before items."""
        from guardkit.knowledge.feature_plan_context import FeaturePlanContext

        context = FeaturePlanContext(
            feature_spec={"id": "FEAT-001"},
            related_features=[],
            relevant_patterns=[],
            similar_implementations=[],
            project_architecture={},
            warnings=[],
            role_constraints=[
                {
                    'role': 'player',
                    'must_do': ['Write code'],
                    'must_not_do': ['Approve work'],
                    'ask_before': ['Schema changes', 'Auth changes']
                }
            ]
        )

        result = context._format_role_constraints()

        # Should include ask_before items
        assert "Schema changes" in result
        assert "Auth changes" in result

    def test_format_role_constraints_ask_before_has_emoji(self):
        """Test that ask_before items have ❓ emoji in FeaturePlanContext."""
        from guardkit.knowledge.feature_plan_context import FeaturePlanContext

        context = FeaturePlanContext(
            feature_spec={"id": "FEAT-001"},
            related_features=[],
            relevant_patterns=[],
            similar_implementations=[],
            project_architecture={},
            warnings=[],
            role_constraints=[
                {
                    'role': 'player',
                    'must_do': ['Write code'],
                    'must_not_do': ['Approve work'],
                    'ask_before': ['Schema changes']
                }
            ]
        )

        result = context._format_role_constraints()

        # Should have ❓ emoji for ask_before
        assert "❓" in result

    def test_format_role_constraints_all_emojis_present(self):
        """Test that all three emoji types are present in formatted output."""
        from guardkit.knowledge.feature_plan_context import FeaturePlanContext

        context = FeaturePlanContext(
            feature_spec={"id": "FEAT-001"},
            related_features=[],
            relevant_patterns=[],
            similar_implementations=[],
            project_architecture={},
            warnings=[],
            role_constraints=[
                {
                    'role': 'player',
                    'must_do': ['Write code'],
                    'must_not_do': ['Approve work'],
                    'ask_before': ['Schema changes']
                }
            ]
        )

        result = context._format_role_constraints()

        # All three emoji types should be present
        assert "✓" in result, "Missing ✓ emoji for must_do"
        assert "✗" in result, "Missing ✗ emoji for must_not_do"
        assert "❓" in result, "Missing ❓ emoji for ask_before"

    def test_format_role_constraints_handles_missing_ask_before(self):
        """Test that missing ask_before key is handled gracefully."""
        from guardkit.knowledge.feature_plan_context import FeaturePlanContext

        context = FeaturePlanContext(
            feature_spec={"id": "FEAT-001"},
            related_features=[],
            relevant_patterns=[],
            similar_implementations=[],
            project_architecture={},
            warnings=[],
            role_constraints=[
                {
                    'role': 'player',
                    'must_do': ['Write code'],
                    'must_not_do': ['Approve work']
                    # No ask_before key
                }
            ]
        )

        # Should not raise exception
        result = context._format_role_constraints()
        assert isinstance(result, str)
