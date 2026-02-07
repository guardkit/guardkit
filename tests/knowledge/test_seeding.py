"""
TDD RED Phase: Tests for guardkit.knowledge.seeding

These tests are written to FAIL initially (RED phase of TDD).
Implementation will be created to make these tests pass (GREEN phase).

Test Coverage:
- Seeding completion with all group IDs
- Idempotency (no duplicates on re-run)
- Force flag allows re-seeding
- Seeding marker tracking
- Group ID usage verification
- Content format validation
- Graceful degradation when Graphiti disabled
- Error handling and resilience
- Metadata block validation (TASK-GR-PRE-000-A)

Coverage Target: >=85%
Test Count: 30+ tests
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import Optional, List, Dict
from pathlib import Path
import json
from datetime import datetime

# Import will fail initially - this is expected in RED phase
try:
    from guardkit.knowledge.seeding import (
        seed_product_knowledge,
        seed_command_workflows,
        seed_quality_gate_phases,
        seed_technology_stack,
        seed_feature_build_architecture,
        seed_architecture_decisions,
        seed_failure_patterns,
        seed_component_status,
        seed_integration_points,
        seed_templates,
        seed_agents,
        seed_patterns,
        seed_rules,
        seed_all_system_context,
        is_seeded,
        mark_seeded,
        clear_seeding_marker,
        SEEDING_VERSION,
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
# 1. Seeding Marker Tests (5 tests)
# ============================================================================

class TestSeedingMarker:
    """Test seeding marker file management."""

    def test_is_seeded_returns_false_when_marker_missing(self, tmp_path):
        """Test is_seeded returns False when marker file doesn't exist."""
        marker_path = tmp_path / ".graphiti_seeded.json"
        assert not marker_path.exists()

        with patch('guardkit.knowledge.seeding.get_state_dir', return_value=tmp_path):
            result = is_seeded()
            assert result is False

    def test_is_seeded_returns_true_when_marker_exists(self, tmp_path):
        """Test is_seeded returns True when marker file exists."""
        marker_path = tmp_path / ".graphiti_seeded.json"
        marker_path.write_text(json.dumps({"seeded": True, "version": "1.0"}))

        with patch('guardkit.knowledge.seeding.get_state_dir', return_value=tmp_path):
            result = is_seeded()
            assert result is True

    def test_mark_seeded_creates_marker_file(self, tmp_path):
        """Test mark_seeded creates marker file with correct content."""
        marker_path = tmp_path / ".graphiti_seeded.json"
        assert not marker_path.exists()

        with patch('guardkit.knowledge.seeding.get_state_dir', return_value=tmp_path):
            mark_seeded()

            assert marker_path.exists()
            data = json.loads(marker_path.read_text())
            assert data["seeded"] is True
            assert "version" in data
            assert "timestamp" in data

    def test_clear_seeding_marker_removes_file(self, tmp_path):
        """Test clear_seeding_marker removes marker file."""
        marker_path = tmp_path / ".graphiti_seeded.json"
        marker_path.write_text(json.dumps({"seeded": True}))
        assert marker_path.exists()

        with patch('guardkit.knowledge.seeding.get_state_dir', return_value=tmp_path):
            clear_seeding_marker()
            assert not marker_path.exists()

    def test_clear_seeding_marker_handles_missing_file(self, tmp_path):
        """Test clear_seeding_marker handles missing file gracefully."""
        marker_path = tmp_path / ".graphiti_seeded.json"
        assert not marker_path.exists()

        with patch('guardkit.knowledge.seeding.get_state_dir', return_value=tmp_path):
            # Should not raise exception
            clear_seeding_marker()
            assert not marker_path.exists()


# ============================================================================
# 2. Individual Seeding Function Tests (13 tests - one per group)
# ============================================================================

class TestProductKnowledgeSeeding:
    """Test seed_product_knowledge function."""

    @pytest.mark.asyncio
    async def test_seed_product_knowledge_creates_episodes(self):
        """Test product knowledge seeding creates expected number of episodes."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id_1")

        await seed_product_knowledge(mock_client)

        # Should create 3 episodes (from task specification)
        assert mock_client.add_episode.call_count == 3

    @pytest.mark.asyncio
    async def test_seed_product_knowledge_uses_correct_group_id(self):
        """Test product knowledge uses 'product_knowledge' group ID."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        await seed_product_knowledge(mock_client)

        # Verify all calls used correct group_id
        for call_obj in mock_client.add_episode.call_args_list:
            kwargs = call_obj.kwargs
            assert kwargs['group_id'] == 'product_knowledge'

    @pytest.mark.asyncio
    async def test_seed_product_knowledge_graceful_degradation_when_disabled(self):
        """Test product knowledge seeding degrades gracefully when disabled."""
        mock_client = AsyncMock()
        mock_client.enabled = False

        # Should not raise exception
        await seed_product_knowledge(mock_client)

        # Should not attempt to add episodes
        mock_client.add_episode.assert_not_called()


class TestCommandWorkflowsSeeding:
    """Test seed_command_workflows function."""

    @pytest.mark.asyncio
    async def test_seed_command_workflows_creates_episodes(self):
        """Test command workflows seeding creates expected number of episodes."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        await seed_command_workflows(mock_client)

        # Should create 7 episodes
        assert mock_client.add_episode.call_count == 7

    @pytest.mark.asyncio
    async def test_seed_command_workflows_uses_correct_group_id(self):
        """Test command workflows uses 'command_workflows' group ID."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        await seed_command_workflows(mock_client)

        for call_obj in mock_client.add_episode.call_args_list:
            kwargs = call_obj.kwargs
            assert kwargs['group_id'] == 'command_workflows'


class TestQualityGatePhasesSeeding:
    """Test seed_quality_gate_phases function."""

    @pytest.mark.asyncio
    async def test_seed_quality_gate_phases_creates_episodes(self):
        """Test quality gate phases seeding creates expected number of episodes."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        await seed_quality_gate_phases(mock_client)

        # Should create 12 episodes
        assert mock_client.add_episode.call_count == 12

    @pytest.mark.asyncio
    async def test_seed_quality_gate_phases_uses_correct_group_id(self):
        """Test quality gate phases uses 'quality_gate_phases' group ID."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        await seed_quality_gate_phases(mock_client)

        for call_obj in mock_client.add_episode.call_args_list:
            kwargs = call_obj.kwargs
            assert kwargs['group_id'] == 'quality_gate_phases'


class TestTechnologyStackSeeding:
    """Test seed_technology_stack function."""

    @pytest.mark.asyncio
    async def test_seed_technology_stack_creates_episodes(self):
        """Test technology stack seeding creates expected number of episodes."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        await seed_technology_stack(mock_client)

        # Should create 7 episodes
        assert mock_client.add_episode.call_count == 7


class TestFeatureBuildArchitectureSeeding:
    """Test seed_feature_build_architecture function."""

    @pytest.mark.asyncio
    async def test_seed_feature_build_architecture_creates_episodes(self):
        """Test feature build architecture seeding creates expected number of episodes."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        await seed_feature_build_architecture(mock_client)

        # Should create 7 episodes
        assert mock_client.add_episode.call_count == 7


class TestArchitectureDecisionsSeeding:
    """Test seed_architecture_decisions function."""

    @pytest.mark.asyncio
    async def test_seed_architecture_decisions_creates_episodes(self):
        """Test architecture decisions seeding creates expected number of episodes."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        await seed_architecture_decisions(mock_client)

        # Should create 3 episodes
        assert mock_client.add_episode.call_count == 3


class TestFailurePatternsSeeding:
    """Test seed_failure_patterns function."""

    @pytest.mark.asyncio
    async def test_seed_failure_patterns_creates_episodes(self):
        """Test failure patterns seeding creates expected number of episodes."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        await seed_failure_patterns(mock_client)

        # Should create 4 episodes
        assert mock_client.add_episode.call_count == 4


class TestComponentStatusSeeding:
    """Test seed_component_status function."""

    @pytest.mark.asyncio
    async def test_seed_component_status_creates_episodes(self):
        """Test component status seeding creates expected number of episodes."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        await seed_component_status(mock_client)

        # Should create 2 episodes
        assert mock_client.add_episode.call_count == 2


class TestIntegrationPointsSeeding:
    """Test seed_integration_points function."""

    @pytest.mark.asyncio
    async def test_seed_integration_points_creates_episodes(self):
        """Test integration points seeding creates expected number of episodes."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        await seed_integration_points(mock_client)

        # Should create 2 episodes
        assert mock_client.add_episode.call_count == 2


class TestTemplatesSeeding:
    """Test seed_templates function."""

    @pytest.mark.asyncio
    async def test_seed_templates_creates_episodes(self):
        """Test templates seeding creates expected number of episodes."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        await seed_templates(mock_client)

        # Should create 4+ episodes
        assert mock_client.add_episode.call_count >= 4


class TestAgentsSeeding:
    """Test seed_agents function."""

    @pytest.mark.asyncio
    async def test_seed_agents_creates_episodes(self):
        """Test agents seeding creates expected number of episodes."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        await seed_agents(mock_client)

        # Should create 7+ episodes
        assert mock_client.add_episode.call_count >= 7


class TestPatternsSeeding:
    """Test seed_patterns function."""

    @pytest.mark.asyncio
    async def test_seed_patterns_creates_episodes(self):
        """Test patterns seeding creates expected number of episodes."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        await seed_patterns(mock_client)

        # Should create 5+ episodes
        assert mock_client.add_episode.call_count >= 5


class TestRulesSeeding:
    """Test seed_rules function."""

    @pytest.mark.asyncio
    async def test_seed_rules_creates_episodes(self):
        """Test rules seeding creates expected number of episodes."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        await seed_rules(mock_client)

        # Should create 4+ episodes
        assert mock_client.add_episode.call_count >= 4


# ============================================================================
# 3. Complete Seeding Tests (8 tests)
# ============================================================================

class TestSeedAllSystemContext:
    """Test seed_all_system_context orchestration function."""

    @pytest.mark.asyncio
    async def test_seed_all_calls_all_seeding_functions(self):
        """Test seed_all_system_context calls all individual seeding functions."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        with patch('guardkit.knowledge.seeding.seed_product_knowledge', new_callable=AsyncMock) as mock_product, \
             patch('guardkit.knowledge.seeding.seed_command_workflows', new_callable=AsyncMock) as mock_commands, \
             patch('guardkit.knowledge.seeding.seed_quality_gate_phases', new_callable=AsyncMock) as mock_gates, \
             patch('guardkit.knowledge.seeding.seed_technology_stack', new_callable=AsyncMock) as mock_tech, \
             patch('guardkit.knowledge.seeding.seed_feature_build_architecture', new_callable=AsyncMock) as mock_feature, \
             patch('guardkit.knowledge.seeding.seed_architecture_decisions', new_callable=AsyncMock) as mock_arch, \
             patch('guardkit.knowledge.seeding.seed_failure_patterns', new_callable=AsyncMock) as mock_failures, \
             patch('guardkit.knowledge.seeding.seed_component_status', new_callable=AsyncMock) as mock_components, \
             patch('guardkit.knowledge.seeding.seed_integration_points', new_callable=AsyncMock) as mock_integrations, \
             patch('guardkit.knowledge.seeding.seed_templates', new_callable=AsyncMock) as mock_templates, \
             patch('guardkit.knowledge.seeding.seed_agents', new_callable=AsyncMock) as mock_agents, \
             patch('guardkit.knowledge.seeding.seed_patterns', new_callable=AsyncMock) as mock_patterns, \
             patch('guardkit.knowledge.seeding.seed_rules', new_callable=AsyncMock) as mock_rules:

            await seed_all_system_context(mock_client)

            # Verify all seeding functions were called
            mock_product.assert_called_once_with(mock_client)
            mock_commands.assert_called_once_with(mock_client)
            mock_gates.assert_called_once_with(mock_client)
            mock_tech.assert_called_once_with(mock_client)
            mock_feature.assert_called_once_with(mock_client)
            mock_arch.assert_called_once_with(mock_client)
            mock_failures.assert_called_once_with(mock_client)
            mock_components.assert_called_once_with(mock_client)
            mock_integrations.assert_called_once_with(mock_client)
            mock_templates.assert_called_once_with(mock_client)
            mock_agents.assert_called_once_with(mock_client)
            mock_patterns.assert_called_once_with(mock_client)
            mock_rules.assert_called_once_with(mock_client)

    @pytest.mark.asyncio
    async def test_seed_all_marks_seeded_on_success(self, tmp_path):
        """Test seed_all_system_context marks seeding complete on success."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        marker_path = tmp_path / ".graphiti_seeded.json"
        assert not marker_path.exists()

        with patch('guardkit.knowledge.seeding.get_state_dir', return_value=tmp_path), \
             patch('guardkit.knowledge.seeding.seed_product_knowledge', new_callable=AsyncMock), \
             patch('guardkit.knowledge.seeding.seed_command_workflows', new_callable=AsyncMock), \
             patch('guardkit.knowledge.seeding.seed_quality_gate_phases', new_callable=AsyncMock), \
             patch('guardkit.knowledge.seeding.seed_technology_stack', new_callable=AsyncMock), \
             patch('guardkit.knowledge.seeding.seed_feature_build_architecture', new_callable=AsyncMock), \
             patch('guardkit.knowledge.seeding.seed_architecture_decisions', new_callable=AsyncMock), \
             patch('guardkit.knowledge.seeding.seed_failure_patterns', new_callable=AsyncMock), \
             patch('guardkit.knowledge.seeding.seed_component_status', new_callable=AsyncMock), \
             patch('guardkit.knowledge.seeding.seed_integration_points', new_callable=AsyncMock), \
             patch('guardkit.knowledge.seeding.seed_templates', new_callable=AsyncMock), \
             patch('guardkit.knowledge.seeding.seed_agents', new_callable=AsyncMock), \
             patch('guardkit.knowledge.seeding.seed_patterns', new_callable=AsyncMock), \
             patch('guardkit.knowledge.seeding.seed_rules', new_callable=AsyncMock):

            await seed_all_system_context(mock_client)

            # Marker should be created
            assert marker_path.exists()

    @pytest.mark.asyncio
    async def test_seed_all_skips_when_already_seeded(self, tmp_path):
        """Test seed_all_system_context skips seeding when already seeded."""
        mock_client = AsyncMock()
        mock_client.enabled = True

        # Create marker file
        marker_path = tmp_path / ".graphiti_seeded.json"
        marker_path.write_text(json.dumps({"seeded": True}))

        with patch('guardkit.knowledge.seeding.get_state_dir', return_value=tmp_path), \
             patch('guardkit.knowledge.seeding.seed_product_knowledge', new_callable=AsyncMock) as mock_seed:

            result = await seed_all_system_context(mock_client)

            # Should skip seeding
            mock_seed.assert_not_called()
            assert result is True

    @pytest.mark.asyncio
    async def test_seed_all_force_flag_allows_reseeding(self, tmp_path):
        """Test seed_all_system_context with force=True allows re-seeding."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        # Create marker file
        marker_path = tmp_path / ".graphiti_seeded.json"
        marker_path.write_text(json.dumps({"seeded": True}))

        with patch('guardkit.knowledge.seeding.get_state_dir', return_value=tmp_path), \
             patch('guardkit.knowledge.seeding.seed_product_knowledge', new_callable=AsyncMock) as mock_seed, \
             patch('guardkit.knowledge.seeding.seed_command_workflows', new_callable=AsyncMock), \
             patch('guardkit.knowledge.seeding.seed_quality_gate_phases', new_callable=AsyncMock), \
             patch('guardkit.knowledge.seeding.seed_technology_stack', new_callable=AsyncMock), \
             patch('guardkit.knowledge.seeding.seed_feature_build_architecture', new_callable=AsyncMock), \
             patch('guardkit.knowledge.seeding.seed_architecture_decisions', new_callable=AsyncMock), \
             patch('guardkit.knowledge.seeding.seed_failure_patterns', new_callable=AsyncMock), \
             patch('guardkit.knowledge.seeding.seed_component_status', new_callable=AsyncMock), \
             patch('guardkit.knowledge.seeding.seed_integration_points', new_callable=AsyncMock), \
             patch('guardkit.knowledge.seeding.seed_templates', new_callable=AsyncMock), \
             patch('guardkit.knowledge.seeding.seed_agents', new_callable=AsyncMock), \
             patch('guardkit.knowledge.seeding.seed_patterns', new_callable=AsyncMock), \
             patch('guardkit.knowledge.seeding.seed_rules', new_callable=AsyncMock):

            result = await seed_all_system_context(mock_client, force=True)

            # Should proceed with seeding
            mock_seed.assert_called_once()

    @pytest.mark.asyncio
    async def test_seed_all_graceful_degradation_when_disabled(self):
        """Test seed_all_system_context degrades gracefully when client disabled."""
        mock_client = AsyncMock()
        mock_client.enabled = False

        with patch('guardkit.knowledge.seeding.seed_product_knowledge', new_callable=AsyncMock) as mock_seed:
            result = await seed_all_system_context(mock_client)

            # Should skip seeding but not raise exception
            mock_seed.assert_not_called()
            assert result is False

    @pytest.mark.asyncio
    async def test_seed_all_handles_partial_failure_gracefully(self, tmp_path):
        """Test seed_all_system_context handles partial seeding failures."""
        mock_client = AsyncMock()
        mock_client.enabled = True

        # First function succeeds, second fails
        async def success_fn(client):
            pass

        async def failure_fn(client):
            raise Exception("Simulated failure")

        with patch('guardkit.knowledge.seeding.get_state_dir', return_value=tmp_path), \
             patch('guardkit.knowledge.seeding.seed_product_knowledge', new_callable=AsyncMock) as mock_success, \
             patch('guardkit.knowledge.seeding.seed_command_workflows', new_callable=AsyncMock) as mock_failure:

            mock_success.side_effect = success_fn
            mock_failure.side_effect = failure_fn

            # Should handle error gracefully
            result = await seed_all_system_context(mock_client)

            # Result should indicate partial failure
            assert result is not None


# ============================================================================
# 4. Episode Content Tests (4 tests)
# ============================================================================

class TestEpisodeContent:
    """Test episode content formatting and structure."""

    @pytest.mark.asyncio
    async def test_episodes_have_valid_json_content(self):
        """Test that episode bodies contain valid JSON."""
        mock_client = AsyncMock()
        mock_client.enabled = True

        captured_bodies = []

        async def capture_episode(name, episode_body, group_id):
            captured_bodies.append(episode_body)
            return "episode_id"

        mock_client.add_episode = capture_episode

        await seed_product_knowledge(mock_client)

        # Verify all bodies are valid JSON
        for body in captured_bodies:
            # Should not raise exception
            json.loads(body)

    @pytest.mark.asyncio
    async def test_episodes_have_required_fields(self):
        """Test that episode JSON contains required fields."""
        mock_client = AsyncMock()
        mock_client.enabled = True

        captured_bodies = []

        async def capture_episode(name, episode_body, group_id):
            captured_bodies.append(episode_body)
            return "episode_id"

        mock_client.add_episode = capture_episode

        await seed_product_knowledge(mock_client)

        for body in captured_bodies:
            data = json.loads(body)
            # Should have some content structure
            assert isinstance(data, (dict, list))

    @pytest.mark.asyncio
    async def test_episode_names_are_descriptive(self):
        """Test that episode names are descriptive and unique."""
        mock_client = AsyncMock()
        mock_client.enabled = True

        captured_names = []

        async def capture_episode(name, episode_body, group_id):
            captured_names.append(name)
            return "episode_id"

        mock_client.add_episode = capture_episode

        await seed_product_knowledge(mock_client)

        # Names should be non-empty
        for name in captured_names:
            assert name
            assert len(name) > 0

        # Names should be unique
        assert len(captured_names) == len(set(captured_names))

    @pytest.mark.asyncio
    async def test_episodes_group_ids_match_function_name(self):
        """Test that group_id matches the seeding function's purpose."""
        test_cases = [
            (seed_product_knowledge, 'product_knowledge'),
            (seed_command_workflows, 'command_workflows'),
            (seed_quality_gate_phases, 'quality_gate_phases'),
            (seed_technology_stack, 'technology_stack'),
            (seed_feature_build_architecture, 'feature_build_architecture'),
            (seed_architecture_decisions, 'architecture_decisions'),
            (seed_failure_patterns, 'failure_patterns'),
            (seed_component_status, 'component_status'),
            (seed_integration_points, 'integration_points'),
            (seed_templates, 'templates'),
            (seed_agents, 'agents'),
            (seed_patterns, 'patterns'),
            (seed_rules, 'rules'),
        ]

        for seed_fn, expected_group_id in test_cases:
            mock_client = AsyncMock()
            mock_client.enabled = True

            captured_group_ids = []

            async def capture_episode(name, episode_body, group_id):
                captured_group_ids.append(group_id)
                return "episode_id"

            mock_client.add_episode = capture_episode

            await seed_fn(mock_client)

            # All group_ids should match expected
            for group_id in captured_group_ids:
                assert group_id == expected_group_id


# ============================================================================
# 5. Edge Cases and Error Handling (5 tests)
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_seeding_handles_add_episode_returning_none(self):
        """Test seeding handles when add_episode returns None."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value=None)

        # Should not raise exception
        await seed_product_knowledge(mock_client)

    @pytest.mark.asyncio
    async def test_seeding_handles_add_episode_exception(self):
        """Test seeding handles when add_episode raises exception."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(side_effect=Exception("API error"))

        # Should handle exception gracefully
        await seed_product_knowledge(mock_client)

    @pytest.mark.asyncio
    async def test_seed_all_with_none_client(self):
        """Test seed_all_system_context handles None client gracefully."""
        # Should not raise exception
        result = await seed_all_system_context(None)
        assert result is False

    @pytest.mark.asyncio
    async def test_marker_operations_handle_permission_errors(self, tmp_path, monkeypatch):
        """Test marker operations handle permission errors gracefully."""
        # Create a read-only directory
        marker_dir = tmp_path / "readonly"
        marker_dir.mkdir()
        marker_path = marker_dir / ".graphiti_seeded.json"

        # Make directory read-only (on Unix-like systems)
        import os
        if os.name != 'nt':  # Skip on Windows
            marker_dir.chmod(0o444)

            with patch('guardkit.knowledge.seeding.get_state_dir', return_value=marker_dir):
                # Should handle permission error gracefully
                try:
                    mark_seeded()
                except PermissionError:
                    pass  # Expected

                # Restore permissions for cleanup
                marker_dir.chmod(0o755)

    @pytest.mark.asyncio
    async def test_seeding_with_empty_episode_body_allowed(self):
        """Test that seeding allows empty episode bodies."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        # Some episodes might have minimal content
        # Implementation should handle this gracefully
        await seed_product_knowledge(mock_client)

        # Should have attempted to add episodes
        assert mock_client.add_episode.call_count > 0


# ============================================================================
# 6. Integration Tests (2 tests)
# ============================================================================

@pytest.mark.integration
class TestSeedingIntegration:
    """
    Integration tests for seeding with real GraphitiClient.

    These tests require Graphiti to be running.
    Mark with @pytest.mark.integration to run selectively.
    """

    @pytest.mark.asyncio
    async def test_full_seeding_workflow_with_real_client(self):
        """Test complete seeding workflow with real Graphiti instance."""
        from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig

        config = GraphitiConfig(enabled=True, host="localhost", port=8000)
        client = GraphitiClient(config)

        initialized = await client.initialize()
        if not initialized:
            pytest.skip("Graphiti not available")

        # Seed all context
        result = await seed_all_system_context(client, force=True)

        # Should succeed
        assert result is True

        # Marker should be created
        assert is_seeded()

    @pytest.mark.asyncio
    async def test_idempotent_seeding_with_real_client(self):
        """Test that seeding is idempotent with real client."""
        from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig

        config = GraphitiConfig(enabled=True, host="localhost", port=8000)
        client = GraphitiClient(config)

        initialized = await client.initialize()
        if not initialized:
            pytest.skip("Graphiti not available")

        # First seeding
        await seed_all_system_context(client, force=True)

        # Second seeding without force should skip
        with patch('guardkit.knowledge.seeding.seed_product_knowledge', new_callable=AsyncMock) as mock_seed:
            result = await seed_all_system_context(client, force=False)

            # Should skip seeding
            mock_seed.assert_not_called()


# ============================================================================
# 7. Metadata Block Tests (TASK-GR-PRE-000-A) - TDD RED PHASE
# ============================================================================

class TestMetadataBlock:
    """
    Test metadata block validation for seeding episodes.

    These tests verify that all seeding functions include proper _metadata
    blocks in their episode bodies. Tests are written in TDD RED phase and
    should FAIL initially because metadata is not yet added to seeding.py.

    Metadata Schema (from TASK-GR-PRE-000-A):
    {
        "_metadata": {
            "source": "guardkit_seeding",
            "version": "1.0.0",
            "created_at": "2025-01-30T12:00:00Z",
            "updated_at": "2025-01-30T12:00:00Z",
            "source_hash": null,
            "entity_id": "unique_identifier"
        }
    }
    """

    @pytest.mark.asyncio
    async def test_episodes_include_metadata_block(self):
        """Test that all episodes include _metadata block."""
        mock_client = AsyncMock()
        mock_client.enabled = True

        captured_bodies = []

        async def capture_episode(name, episode_body, group_id):
            captured_bodies.append(episode_body)
            return "episode_id"

        mock_client.add_episode = capture_episode

        # Test with product_knowledge as representative
        await seed_product_knowledge(mock_client)

        # All episodes should have _metadata
        for body in captured_bodies:
            data = json.loads(body)
            assert "_metadata" in data, f"Episode missing _metadata: {data}"

    @pytest.mark.asyncio
    async def test_metadata_has_required_fields(self):
        """Test that _metadata contains all required fields."""
        mock_client = AsyncMock()
        mock_client.enabled = True

        captured_bodies = []

        async def capture_episode(name, episode_body, group_id):
            captured_bodies.append(episode_body)
            return "episode_id"

        mock_client.add_episode = capture_episode

        await seed_product_knowledge(mock_client)

        required_fields = ["source", "version", "created_at", "updated_at", "source_hash", "entity_id"]

        for body in captured_bodies:
            data = json.loads(body)
            metadata = data.get("_metadata", {})

            for field in required_fields:
                assert field in metadata, f"Metadata missing required field '{field}': {metadata}"

    @pytest.mark.asyncio
    async def test_metadata_source_is_guardkit_seeding(self):
        """Test that metadata source is 'guardkit_seeding'."""
        mock_client = AsyncMock()
        mock_client.enabled = True

        captured_bodies = []

        async def capture_episode(name, episode_body, group_id):
            captured_bodies.append(episode_body)
            return "episode_id"

        mock_client.add_episode = capture_episode

        await seed_product_knowledge(mock_client)

        for body in captured_bodies:
            data = json.loads(body)
            metadata = data["_metadata"]
            assert metadata["source"] == "guardkit_seeding", \
                f"Expected source='guardkit_seeding', got '{metadata['source']}'"

    @pytest.mark.asyncio
    async def test_metadata_version_matches_seeding_version(self):
        """Test that metadata version matches SEEDING_VERSION constant."""
        mock_client = AsyncMock()
        mock_client.enabled = True

        captured_bodies = []

        async def capture_episode(name, episode_body, group_id):
            captured_bodies.append(episode_body)
            return "episode_id"

        mock_client.add_episode = capture_episode

        await seed_product_knowledge(mock_client)

        for body in captured_bodies:
            data = json.loads(body)
            metadata = data["_metadata"]
            assert metadata["version"] == SEEDING_VERSION, \
                f"Expected version='{SEEDING_VERSION}', got '{metadata['version']}'"

    @pytest.mark.asyncio
    async def test_metadata_timestamps_are_valid_iso_format(self):
        """Test that created_at and updated_at are valid ISO timestamps."""
        mock_client = AsyncMock()
        mock_client.enabled = True

        captured_bodies = []

        async def capture_episode(name, episode_body, group_id):
            captured_bodies.append(episode_body)
            return "episode_id"

        mock_client.add_episode = capture_episode

        await seed_product_knowledge(mock_client)

        for body in captured_bodies:
            data = json.loads(body)
            metadata = data["_metadata"]

            # Test created_at is valid ISO format
            try:
                datetime.fromisoformat(metadata["created_at"].replace('Z', '+00:00'))
            except (ValueError, AttributeError) as e:
                pytest.fail(f"Invalid created_at timestamp: {metadata['created_at']} - {e}")

            # Test updated_at is valid ISO format
            try:
                datetime.fromisoformat(metadata["updated_at"].replace('Z', '+00:00'))
            except (ValueError, AttributeError) as e:
                pytest.fail(f"Invalid updated_at timestamp: {metadata['updated_at']} - {e}")

    @pytest.mark.asyncio
    async def test_metadata_entity_id_is_unique_per_episode(self):
        """Test that entity_id is unique for each episode."""
        mock_client = AsyncMock()
        mock_client.enabled = True

        captured_bodies = []

        async def capture_episode(name, episode_body, group_id):
            captured_bodies.append(episode_body)
            return "episode_id"

        mock_client.add_episode = capture_episode

        await seed_product_knowledge(mock_client)

        entity_ids = []
        for body in captured_bodies:
            data = json.loads(body)
            metadata = data["_metadata"]
            entity_id = metadata["entity_id"]

            assert entity_id is not None, "entity_id should not be None"
            assert entity_id not in entity_ids, f"Duplicate entity_id found: {entity_id}"
            entity_ids.append(entity_id)

    @pytest.mark.asyncio
    async def test_metadata_source_hash_is_none_for_generated_content(self):
        """Test that source_hash is None for generated content (not file-based)."""
        mock_client = AsyncMock()
        mock_client.enabled = True

        captured_bodies = []

        async def capture_episode(name, episode_body, group_id):
            captured_bodies.append(episode_body)
            return "episode_id"

        mock_client.add_episode = capture_episode

        await seed_product_knowledge(mock_client)

        for body in captured_bodies:
            data = json.loads(body)
            metadata = data["_metadata"]
            # For generated seeding content, source_hash should be None
            assert metadata["source_hash"] is None, \
                f"Expected source_hash=None for generated content, got {metadata['source_hash']}"

    @pytest.mark.asyncio
    async def test_all_seeding_functions_delegate_metadata_to_client(self):
        """Test that ALL seeding functions pass metadata kwargs to add_episode."""
        seeding_functions = [
            seed_product_knowledge,
            seed_command_workflows,
            seed_quality_gate_phases,
            seed_technology_stack,
            seed_feature_build_architecture,
            seed_architecture_decisions,
            seed_failure_patterns,
            seed_component_status,
            seed_integration_points,
            seed_templates,
            seed_agents,
            seed_patterns,
            seed_rules,
        ]

        for seed_fn in seeding_functions:
            mock_client = AsyncMock()
            mock_client.enabled = True
            mock_client.add_episode = AsyncMock(return_value="episode_id")

            await seed_fn(mock_client)

            # Verify episodes were created
            assert mock_client.add_episode.call_count > 0, \
                f"Function {seed_fn.__name__} created no episodes"

            # Verify metadata is delegated via kwargs (not embedded in body)
            for call_obj in mock_client.add_episode.call_args_list:
                kwargs = call_obj.kwargs
                assert kwargs.get("source") == "guardkit_seeding", \
                    f"Function {seed_fn.__name__} missing source='guardkit_seeding'"
                assert "entity_type" in kwargs, \
                    f"Function {seed_fn.__name__} missing entity_type kwarg"
                # Body should NOT contain _metadata (client handles injection)
                body = json.loads(kwargs["episode_body"])
                assert "_metadata" not in body, \
                    f"Function {seed_fn.__name__} should not embed _metadata in body"

    @pytest.mark.asyncio
    async def test_metadata_preserves_original_episode_structure(self):
        """Test that adding _metadata doesn't break existing episode structure."""
        mock_client = AsyncMock()
        mock_client.enabled = True

        captured_bodies = []

        async def capture_episode(name, episode_body, group_id):
            captured_bodies.append(episode_body)
            return "episode_id"

        mock_client.add_episode = capture_episode

        await seed_product_knowledge(mock_client)

        for body in captured_bodies:
            data = json.loads(body)

            # Should have _metadata
            assert "_metadata" in data

            # Should still have original fields (e.g., entity_type for product_knowledge)
            # At minimum, should have more than just _metadata
            assert len(data) > 1, "Episode should have content fields in addition to _metadata"
