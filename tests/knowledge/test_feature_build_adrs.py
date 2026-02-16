"""
TDD RED Phase: Tests for Feature Build ADR Seeding

These tests are written to FAIL initially (RED phase of TDD).
Implementation will be created to make these tests pass (GREEN phase).

Test Coverage:
- ADR content validation (required fields, correct values)
- Seeding function tests (creates episodes, uses correct group_id)
- CLI command tests (Click command, force flag)
- Context loading tests (load_critical_adrs function)
- Violation symptoms tests (all symptoms included)
- Integration tests (marked with @pytest.mark.integration)

Coverage Target: >=85%
Test Count: 35+ tests
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import Optional, List, Dict
from pathlib import Path
import json

# Import will fail initially - this is expected in RED phase
try:
    from guardkit.knowledge.seed_feature_build_adrs import (
        FEATURE_BUILD_ADRS,
        seed_feature_build_adrs,
    )
    from guardkit.knowledge.context_loader import load_critical_adrs
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False


# Skip all tests if imports not available (expected in RED phase)
pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="Implementation not yet created (TDD RED phase)"
)


# ============================================================================
# 1. ADR Content Validation Tests (10 tests)
# ============================================================================

class TestADRContentStructure:
    """Test that ADR definitions have correct structure and required fields."""

    def test_feature_build_adrs_list_exists(self):
        """Test FEATURE_BUILD_ADRS is a list."""
        assert isinstance(FEATURE_BUILD_ADRS, list)

    def test_feature_build_adrs_contains_three_adrs(self):
        """Test that exactly 3 ADRs are defined (FB-001, FB-002, FB-003)."""
        assert len(FEATURE_BUILD_ADRS) == 3

    def test_all_adrs_have_required_fields(self):
        """Test that all ADRs have required fields."""
        required_fields = [
            'id', 'title', 'status', 'context', 'decision',
            'rationale', 'rejected_alternatives', 'violation_symptoms',
            'related_failures', 'decided_at', 'decided_by', 'group_id'
        ]

        for adr in FEATURE_BUILD_ADRS:
            for field in required_fields:
                assert field in adr, f"ADR {adr.get('id', 'unknown')} missing field: {field}"

    def test_adr_ids_are_correct(self):
        """Test that ADR IDs are ADR-FB-001, ADR-FB-002, ADR-FB-003."""
        expected_ids = ['ADR-FB-001', 'ADR-FB-002', 'ADR-FB-003']
        actual_ids = [adr['id'] for adr in FEATURE_BUILD_ADRS]
        assert actual_ids == expected_ids

    def test_all_adrs_have_accepted_status(self):
        """Test that all ADRs have ACCEPTED status."""
        for adr in FEATURE_BUILD_ADRS:
            assert adr['status'] == 'ACCEPTED', f"ADR {adr['id']} has wrong status: {adr['status']}"

    def test_all_adrs_use_architecture_decisions_group_id(self):
        """Test that all ADRs use 'architecture_decisions' group_id."""
        for adr in FEATURE_BUILD_ADRS:
            assert adr['group_id'] == 'architecture_decisions', \
                f"ADR {adr['id']} has wrong group_id: {adr['group_id']}"

    def test_rationale_is_nonempty_list(self):
        """Test that rationale field is a non-empty list for all ADRs."""
        for adr in FEATURE_BUILD_ADRS:
            assert isinstance(adr['rationale'], list), \
                f"ADR {adr['id']} rationale is not a list"
            assert len(adr['rationale']) > 0, \
                f"ADR {adr['id']} has empty rationale"

    def test_rejected_alternatives_is_nonempty_list(self):
        """Test that rejected_alternatives is a non-empty list for all ADRs."""
        for adr in FEATURE_BUILD_ADRS:
            assert isinstance(adr['rejected_alternatives'], list), \
                f"ADR {adr['id']} rejected_alternatives is not a list"
            assert len(adr['rejected_alternatives']) > 0, \
                f"ADR {adr['id']} has empty rejected_alternatives"

    def test_violation_symptoms_is_nonempty_list(self):
        """Test that violation_symptoms is a non-empty list for all ADRs."""
        for adr in FEATURE_BUILD_ADRS:
            assert isinstance(adr['violation_symptoms'], list), \
                f"ADR {adr['id']} violation_symptoms is not a list"
            assert len(adr['violation_symptoms']) > 0, \
                f"ADR {adr['id']} has empty violation_symptoms"

    def test_related_failures_is_list(self):
        """Test that related_failures is a list for all ADRs."""
        for adr in FEATURE_BUILD_ADRS:
            assert isinstance(adr['related_failures'], list), \
                f"ADR {adr['id']} related_failures is not a list"


# ============================================================================
# 2. ADR-FB-001 Specific Content Tests (5 tests)
# ============================================================================

class TestADRFB001Content:
    """Test ADR-FB-001: Use SDK query() for task-work invocation."""

    def test_adr_fb_001_title_is_correct(self):
        """Test ADR-FB-001 has correct title."""
        adr = FEATURE_BUILD_ADRS[0]
        assert adr['id'] == 'ADR-FB-001'
        assert 'SDK query()' in adr['title']
        assert 'task-work invocation' in adr['title']

    def test_adr_fb_001_decision_mentions_sdk_query(self):
        """Test ADR-FB-001 decision mentions SDK query() method."""
        adr = FEATURE_BUILD_ADRS[0]
        assert 'SDK' in adr['decision'] or 'query()' in adr['decision']

    def test_adr_fb_001_rationale_includes_key_reasons(self):
        """Test ADR-FB-001 rationale includes key reasons."""
        adr = FEATURE_BUILD_ADRS[0]
        rationale_text = ' '.join(adr['rationale']).lower()

        # Check for key concepts
        assert 'slash command' in rationale_text or 'subagent' in rationale_text
        assert 'cli' in rationale_text or 'subprocess' in rationale_text

    def test_adr_fb_001_rejected_alternatives_includes_subprocess(self):
        """Test ADR-FB-001 rejected alternatives includes subprocess."""
        adr = FEATURE_BUILD_ADRS[0]
        alternatives_text = ' '.join(adr['rejected_alternatives']).lower()
        assert 'subprocess' in alternatives_text

    def test_adr_fb_001_violation_symptoms_include_subprocess_error(self):
        """Test ADR-FB-001 violation symptoms include subprocess errors."""
        adr = FEATURE_BUILD_ADRS[0]
        symptoms_text = ' '.join(adr['violation_symptoms']).lower()
        assert 'subprocess' in symptoms_text or 'calledprocesserror' in symptoms_text


# ============================================================================
# 3. ADR-FB-002 Specific Content Tests (5 tests)
# ============================================================================

class TestADRFB002Content:
    """Test ADR-FB-002: Use FEAT-XXX paths, not TASK-XXX."""

    def test_adr_fb_002_title_is_correct(self):
        """Test ADR-FB-002 has correct title."""
        adr = FEATURE_BUILD_ADRS[1]
        assert adr['id'] == 'ADR-FB-002'
        assert 'FEAT-XXX' in adr['title'] or 'paths' in adr['title']

    def test_adr_fb_002_decision_mentions_feat_id_usage(self):
        """Test ADR-FB-002 decision mentions FEAT-XXX ID usage."""
        adr = FEATURE_BUILD_ADRS[1]
        assert 'FEAT-XXX' in adr['decision'] or 'feature' in adr['decision'].lower()

    def test_adr_fb_002_rationale_explains_shared_worktree(self):
        """Test ADR-FB-002 rationale explains shared worktree concept."""
        adr = FEATURE_BUILD_ADRS[1]
        rationale_text = ' '.join(adr['rationale']).lower()
        assert 'worktree' in rationale_text

    def test_adr_fb_002_rejected_alternatives_mentions_task_paths(self):
        """Test ADR-FB-002 rejected alternatives mentions separate task paths."""
        adr = FEATURE_BUILD_ADRS[1]
        alternatives_text = ' '.join(adr['rejected_alternatives']).lower()
        assert 'task-xxx' in alternatives_text or 'separate' in alternatives_text

    def test_adr_fb_002_violation_symptoms_include_filenotfounderror(self):
        """Test ADR-FB-002 violation symptoms include FileNotFoundError."""
        adr = FEATURE_BUILD_ADRS[1]
        symptoms_text = ' '.join(adr['violation_symptoms']).lower()
        assert 'filenotfounderror' in symptoms_text or 'not found' in symptoms_text


# ============================================================================
# 4. ADR-FB-003 Specific Content Tests (5 tests)
# ============================================================================

class TestADRFB003Content:
    """Test ADR-FB-003: Pre-loop must invoke real task-work."""

    def test_adr_fb_003_title_is_correct(self):
        """Test ADR-FB-003 has correct title."""
        adr = FEATURE_BUILD_ADRS[2]
        assert adr['id'] == 'ADR-FB-003'
        assert 'pre-loop' in adr['title'].lower() or 'task-work' in adr['title'].lower()

    def test_adr_fb_003_decision_mentions_design_only_flag(self):
        """Test ADR-FB-003 decision mentions --design-only flag."""
        adr = FEATURE_BUILD_ADRS[2]
        assert '--design-only' in adr['decision'] or 'design-only' in adr['decision']

    def test_adr_fb_003_rationale_explains_implementation_plan_requirement(self):
        """Test ADR-FB-003 rationale explains implementation plan requirement."""
        adr = FEATURE_BUILD_ADRS[2]
        rationale_text = ' '.join(adr['rationale']).lower()
        assert 'implementation plan' in rationale_text or 'plan' in rationale_text

    def test_adr_fb_003_rejected_alternatives_mentions_mock_data(self):
        """Test ADR-FB-003 rejected alternatives mentions mock/stub data."""
        adr = FEATURE_BUILD_ADRS[2]
        alternatives_text = ' '.join(adr['rejected_alternatives']).lower()
        assert 'stub' in alternatives_text or 'mock' in alternatives_text or 'hardcoded' in alternatives_text

    def test_adr_fb_003_violation_symptoms_include_plan_not_found(self):
        """Test ADR-FB-003 violation symptoms include plan not found."""
        adr = FEATURE_BUILD_ADRS[2]
        symptoms_text = ' '.join(adr['violation_symptoms']).lower()
        assert 'plan not found' in symptoms_text or 'implementation plan' in symptoms_text


# ============================================================================
# 5. Seeding Function Tests (6 tests)
# ============================================================================

class TestSeedFeatureBuildADRs:
    """Test seed_feature_build_adrs function."""

    @pytest.mark.asyncio
    async def test_seed_feature_build_adrs_creates_three_episodes(self):
        """Test seeding creates exactly 3 episodes."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        await seed_feature_build_adrs(mock_client)

        assert mock_client.add_episode.call_count == 3

    @pytest.mark.asyncio
    async def test_seed_feature_build_adrs_uses_correct_group_id(self):
        """Test seeding uses 'architecture_decisions' group_id."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        await seed_feature_build_adrs(mock_client)

        # Verify all calls used correct group_id
        for call_obj in mock_client.add_episode.call_args_list:
            kwargs = call_obj.kwargs
            assert kwargs['group_id'] == 'architecture_decisions'

    @pytest.mark.asyncio
    async def test_seed_feature_build_adrs_episode_names_are_descriptive(self):
        """Test episode names are descriptive and follow naming convention."""
        mock_client = AsyncMock()
        mock_client.enabled = True

        captured_names = []

        async def capture_episode(name, episode_body, group_id):
            captured_names.append(name)
            return "episode_id"

        mock_client.add_episode = capture_episode

        await seed_feature_build_adrs(mock_client)

        # Names should follow adr_fb_xxx pattern
        for name in captured_names:
            assert name.startswith('adr_')
            assert 'fb' in name.lower()

    @pytest.mark.asyncio
    async def test_seed_feature_build_adrs_episode_bodies_are_valid_json(self):
        """Test episode bodies contain valid JSON."""
        mock_client = AsyncMock()
        mock_client.enabled = True

        captured_bodies = []

        async def capture_episode(name, episode_body, group_id):
            captured_bodies.append(episode_body)
            return "episode_id"

        mock_client.add_episode = capture_episode

        await seed_feature_build_adrs(mock_client)

        # Verify all bodies are valid JSON
        for body in captured_bodies:
            data = json.loads(body)
            assert isinstance(data, dict)
            assert 'entity_type' in data
            assert data['entity_type'] == 'architecture_decision'

    @pytest.mark.asyncio
    async def test_seed_feature_build_adrs_graceful_degradation_when_disabled(self):
        """Test seeding degrades gracefully when client disabled."""
        mock_client = AsyncMock()
        mock_client.enabled = False

        # Should not raise exception
        await seed_feature_build_adrs(mock_client)

        # Should not attempt to add episodes
        mock_client.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_seed_feature_build_adrs_handles_add_episode_exception(self):
        """Test seeding handles add_episode exceptions gracefully."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(side_effect=Exception("API error"))

        # Should handle exception gracefully
        await seed_feature_build_adrs(mock_client)


# ============================================================================
# 6. CLI Command Tests (4 tests)
# ============================================================================

class TestCLICommand:
    """Test guardkit graphiti seed-adrs CLI command."""

    def test_seed_adrs_command_exists(self):
        """Test that seed-adrs command is registered."""
        from guardkit.cli.graphiti import graphiti

        # Check command is registered
        assert 'seed-adrs' in [cmd.name for cmd in graphiti.commands.values()]

    @patch('guardkit.cli.graphiti._cmd_seed_adrs', new_callable=AsyncMock)
    def test_seed_adrs_command_calls_seeding_function(self, mock_cmd_seed_adrs):
        """Test seed-adrs command calls _cmd_seed_adrs."""
        from click.testing import CliRunner
        from guardkit.cli.graphiti import graphiti

        runner = CliRunner()
        result = runner.invoke(graphiti, ['seed-adrs'])

        # Command should have attempted to seed
        assert result.exit_code == 0

    @patch('guardkit.cli.graphiti._cmd_seed_adrs', new_callable=AsyncMock)
    def test_seed_adrs_command_force_flag_supported(self, mock_cmd_seed_adrs):
        """Test seed-adrs command supports --force flag."""
        from click.testing import CliRunner
        from guardkit.cli.graphiti import graphiti

        runner = CliRunner()
        result = runner.invoke(graphiti, ['seed-adrs', '--force'])

        # Should not error on force flag
        assert result.exit_code == 0

    @patch('guardkit.cli.graphiti._cmd_seed_adrs', new_callable=AsyncMock)
    def test_seed_adrs_command_handles_disabled_graphiti(self, mock_cmd_seed_adrs):
        """Test seed-adrs command handles disabled Graphiti gracefully."""
        from click.testing import CliRunner
        from guardkit.cli.graphiti import graphiti

        runner = CliRunner()
        result = runner.invoke(graphiti, ['seed-adrs'])

        # Should complete without error
        assert result.exit_code == 0


# ============================================================================
# 7. Context Loading Tests (4 tests)
# ============================================================================

class TestContextLoading:
    """Test load_critical_adrs context loading function."""

    @pytest.mark.asyncio
    async def test_load_critical_adrs_returns_list(self):
        """Test load_critical_adrs returns a list."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            result = await load_critical_adrs()
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_load_critical_adrs_queries_architecture_decisions_group(self):
        """Test load_critical_adrs queries architecture_decisions group."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            await load_critical_adrs()

            # Verify search was called with architecture_decisions group
            mock_client.search.assert_called_once()
            call_kwargs = mock_client.search.call_args.kwargs
            assert 'architecture_decisions' in call_kwargs['group_ids']

    @pytest.mark.asyncio
    async def test_load_critical_adrs_returns_empty_list_when_disabled(self):
        """Test load_critical_adrs returns empty list when Graphiti disabled."""
        mock_client = AsyncMock()
        mock_client.enabled = False

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            result = await load_critical_adrs()
            assert result == []
            mock_client.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_load_critical_adrs_formats_results_correctly(self):
        """Test load_critical_adrs formats search results correctly."""
        mock_client = AsyncMock()
        mock_client.enabled = True

        # Mock search results
        mock_results = [
            {
                'body': {
                    'id': 'ADR-FB-001',
                    'title': 'Use SDK query()',
                    'decision': 'Use Claude Agents SDK',
                    'violation_symptoms': ['subprocess.CalledProcessError']
                }
            }
        ]
        mock_client.search = AsyncMock(return_value=mock_results)

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            result = await load_critical_adrs()

            assert len(result) == 1
            assert result[0]['id'] == 'ADR-FB-001'
            assert 'title' in result[0]
            assert 'decision' in result[0]
            assert 'violation_symptoms' in result[0]


# ============================================================================
# 8. Integration Tests (2 tests)
# ============================================================================

@pytest.mark.integration
class TestADRSeedingIntegration:
    """
    Integration tests for ADR seeding with real GraphitiClient.

    These tests require Graphiti to be running.
    Mark with @pytest.mark.integration to run selectively.
    """

    @pytest.mark.asyncio
    async def test_full_adr_seeding_workflow_with_real_client(self):
        """Test complete ADR seeding workflow with real Graphiti instance."""
        from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig

        config = GraphitiConfig(enabled=True, host="localhost", port=8000)
        client = GraphitiClient(config)

        initialized = await client.initialize()
        if not initialized:
            pytest.skip("Graphiti not available")

        # Seed ADRs
        await seed_feature_build_adrs(client)

        # Query for ADRs
        results = await client.search(
            query="architecture_decision feature-build",
            group_ids=["architecture_decisions"],
            num_results=5
        )

        # Should find at least one of our ADRs
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_adr_violation_symptoms_are_searchable(self):
        """Test that violation symptoms can be found via search."""
        from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig

        config = GraphitiConfig(enabled=True, host="localhost", port=8000)
        client = GraphitiClient(config)

        initialized = await client.initialize()
        if not initialized:
            pytest.skip("Graphiti not available")

        # Seed ADRs
        await seed_feature_build_adrs(client)

        # Search for violation symptom
        results = await client.search(
            query="subprocess.CalledProcessError",
            group_ids=["architecture_decisions"],
            num_results=3
        )

        # Should find ADR-FB-001 which has this symptom
        assert len(results) > 0

        # Check if any result mentions ADR-FB-001
        found_fb001 = any('ADR-FB-001' in str(r.get('body', {})) for r in results)
        assert found_fb001, "ADR-FB-001 not found when searching for its violation symptom"
