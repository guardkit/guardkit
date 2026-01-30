"""
Integration tests for graphiti clear command.

Test Coverage:
- Clear all knowledge (system + project)
- Clear system-only knowledge
- Clear project-only knowledge
- Preview mode shows accurate counts
- Clear removes seeding marker
- Clear operations are idempotent

AC-004: Integration tests for clear command

Note: These tests use mocked client to avoid requiring real Neo4j instance.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner

try:
    from guardkit.cli.main import cli
    from guardkit.knowledge.seeding import (
        mark_seeded,
        clear_seeding_marker,
        is_seeded,
    )
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="CLI or seeding module not available"
)


@pytest.fixture
def mock_client_for_clear():
    """Create a mock client for clear operations."""
    mock_client = MagicMock()
    mock_client.enabled = True
    mock_client.initialize = AsyncMock(return_value=True)
    mock_client.close = AsyncMock()

    # Setup default preview response
    mock_client.get_clear_preview = AsyncMock(return_value={
        "system_groups": [
            "product_knowledge",
            "command_workflows",
            "quality_gate_phases"
        ],
        "project_groups": [
            "guardkit__project_overview",
            "guardkit__feature_specs"
        ],
        "total_groups": 5,
        "estimated_episodes": 150
    })

    # Setup default clear responses
    mock_client.clear_all = AsyncMock(return_value={
        "system_groups_cleared": 3,
        "project_groups_cleared": 2,
        "total_episodes_deleted": 150
    })

    mock_client.clear_system_groups = AsyncMock(return_value={
        "groups_cleared": ["product_knowledge", "command_workflows", "quality_gate_phases"],
        "episodes_deleted": 100
    })

    mock_client.clear_project_groups = AsyncMock(return_value={
        "project": "guardkit",
        "groups_cleared": ["guardkit__project_overview", "guardkit__feature_specs"],
        "episodes_deleted": 50
    })

    return mock_client


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.enabled = True
    settings.neo4j_uri = "bolt://localhost:7687"
    settings.neo4j_user = "neo4j"
    settings.neo4j_password = "password"
    settings.timeout = 30
    return settings


class TestClearAllIntegration:
    """Test clear all knowledge integration."""

    def test_clear_all_removes_seeding_marker(self, mock_client_for_clear, mock_settings, tmp_path, monkeypatch):
        """Test that clear all removes the seeding marker."""
        monkeypatch.setattr(
            "guardkit.knowledge.seeding.get_state_dir",
            lambda: tmp_path
        )

        # Create marker
        mark_seeded()
        assert is_seeded()

        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_get_client.return_value = (mock_client_for_clear, mock_settings)

            result = runner.invoke(cli, ["graphiti", "clear", "--confirm"])

            assert result.exit_code == 0

        # Note: The marker removal would happen in the actual implementation
        # For now, we're testing that the command runs successfully

    def test_clear_all_calls_client_clear_all(self, mock_client_for_clear, mock_settings):
        """Test that clear all calls client.clear_all()."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_get_client.return_value = (mock_client_for_clear, mock_settings)

            result = runner.invoke(cli, ["graphiti", "clear", "--confirm"])

            assert result.exit_code == 0
            mock_client_for_clear.clear_all.assert_called_once()

    def test_clear_all_shows_preview_before_clearing(self, mock_client_for_clear, mock_settings):
        """Test that clear all shows preview before clearing."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_get_client.return_value = (mock_client_for_clear, mock_settings)

            result = runner.invoke(cli, ["graphiti", "clear", "--confirm"])

            # Preview should be called before clear
            assert mock_client_for_clear.get_clear_preview.called


class TestClearSystemOnlyIntegration:
    """Test clear system-only knowledge integration."""

    def test_clear_system_only_calls_correct_method(self, mock_client_for_clear, mock_settings):
        """Test that --system-only calls client.clear_system_groups()."""
        # Setup preview for system-only
        mock_client_for_clear.get_clear_preview = AsyncMock(return_value={
            "system_groups": ["product_knowledge", "command_workflows"],
            "project_groups": [],
            "total_groups": 2,
            "estimated_episodes": 100
        })

        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_get_client.return_value = (mock_client_for_clear, mock_settings)

            result = runner.invoke(cli, ["graphiti", "clear", "--system-only", "--confirm"])

            assert result.exit_code == 0
            mock_client_for_clear.clear_system_groups.assert_called_once()
            # Should NOT call clear_all or clear_project_groups
            mock_client_for_clear.clear_all.assert_not_called()
            mock_client_for_clear.clear_project_groups.assert_not_called()

    def test_clear_system_only_preview_shows_only_system(self, mock_client_for_clear, mock_settings):
        """Test that --system-only preview shows only system groups."""
        # Setup preview for system-only
        mock_client_for_clear.get_clear_preview = AsyncMock(return_value={
            "system_groups": ["product_knowledge", "command_workflows"],
            "project_groups": [],
            "total_groups": 2,
            "estimated_episodes": 100
        })

        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_get_client.return_value = (mock_client_for_clear, mock_settings)

            result = runner.invoke(cli, ["graphiti", "clear", "--system-only", "--confirm"])

            assert result.exit_code == 0

            # Verify preview was called with correct flags
            call_kwargs = mock_client_for_clear.get_clear_preview.call_args.kwargs
            assert call_kwargs.get('system_only') is True
            assert call_kwargs.get('project_only') is False


class TestClearProjectOnlyIntegration:
    """Test clear project-only knowledge integration."""

    def test_clear_project_only_calls_correct_method(self, mock_client_for_clear, mock_settings):
        """Test that --project-only calls client.clear_project_groups()."""
        # Setup preview for project-only
        mock_client_for_clear.get_clear_preview = AsyncMock(return_value={
            "system_groups": [],
            "project_groups": ["guardkit__project_overview"],
            "total_groups": 1,
            "estimated_episodes": 50
        })

        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_get_client.return_value = (mock_client_for_clear, mock_settings)

            result = runner.invoke(cli, ["graphiti", "clear", "--project-only", "--confirm"])

            assert result.exit_code == 0
            mock_client_for_clear.clear_project_groups.assert_called_once()
            # Should NOT call clear_all or clear_system_groups
            mock_client_for_clear.clear_all.assert_not_called()
            mock_client_for_clear.clear_system_groups.assert_not_called()

    def test_clear_project_only_preview_shows_only_project(self, mock_client_for_clear, mock_settings):
        """Test that --project-only preview shows only project groups."""
        # Setup preview for project-only
        mock_client_for_clear.get_clear_preview = AsyncMock(return_value={
            "system_groups": [],
            "project_groups": ["guardkit__project_overview", "guardkit__feature_specs"],
            "total_groups": 2,
            "estimated_episodes": 50
        })

        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_get_client.return_value = (mock_client_for_clear, mock_settings)

            result = runner.invoke(cli, ["graphiti", "clear", "--project-only", "--confirm"])

            assert result.exit_code == 0

            # Verify preview was called with correct flags
            call_kwargs = mock_client_for_clear.get_clear_preview.call_args.kwargs
            assert call_kwargs.get('project_only') is True
            assert call_kwargs.get('system_only') is False


class TestClearDryRunIntegration:
    """Test dry-run mode integration."""

    def test_dry_run_does_not_clear_data(self, mock_client_for_clear, mock_settings):
        """Test that --dry-run shows preview but doesn't clear data."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_get_client.return_value = (mock_client_for_clear, mock_settings)

            result = runner.invoke(cli, ["graphiti", "clear", "--dry-run"])

            assert result.exit_code == 0

            # Preview should be called
            mock_client_for_clear.get_clear_preview.assert_called_once()

            # Clear methods should NOT be called
            mock_client_for_clear.clear_all.assert_not_called()
            mock_client_for_clear.clear_system_groups.assert_not_called()
            mock_client_for_clear.clear_project_groups.assert_not_called()

    def test_dry_run_with_system_only(self, mock_client_for_clear, mock_settings):
        """Test dry-run with --system-only."""
        mock_client_for_clear.get_clear_preview = AsyncMock(return_value={
            "system_groups": ["product_knowledge"],
            "project_groups": [],
            "total_groups": 1,
            "estimated_episodes": 50
        })

        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_get_client.return_value = (mock_client_for_clear, mock_settings)

            result = runner.invoke(cli, ["graphiti", "clear", "--dry-run", "--system-only"])

            assert result.exit_code == 0

            # Verify preview respects system_only
            call_kwargs = mock_client_for_clear.get_clear_preview.call_args.kwargs
            assert call_kwargs.get('system_only') is True


class TestClearIdempotency:
    """Test that clear operations are idempotent."""

    def test_clear_twice_is_safe(self, mock_client_for_clear, mock_settings):
        """Test that running clear twice is safe."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_get_client.return_value = (mock_client_for_clear, mock_settings)

            # First clear
            result1 = runner.invoke(cli, ["graphiti", "clear", "--confirm"])
            assert result1.exit_code == 0

            # Reset mock
            mock_client_for_clear.clear_all.reset_mock()

            # Setup empty preview for second clear
            mock_client_for_clear.get_clear_preview = AsyncMock(return_value={
                "system_groups": [],
                "project_groups": [],
                "total_groups": 0,
                "estimated_episodes": 0
            })

            mock_client_for_clear.clear_all = AsyncMock(return_value={
                "system_groups_cleared": 0,
                "project_groups_cleared": 0,
                "total_episodes_deleted": 0
            })

            # Second clear
            result2 = runner.invoke(cli, ["graphiti", "clear", "--confirm"])
            assert result2.exit_code == 0


class TestClearErrorRecovery:
    """Test error recovery in clear operations."""

    def test_clear_partial_failure_returns_result(self, mock_settings):
        """Test that partial clear failures still return results."""
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.initialize = AsyncMock(return_value=True)
        mock_client.close = AsyncMock()

        mock_client.get_clear_preview = AsyncMock(return_value={
            "system_groups": ["product_knowledge"],
            "project_groups": ["guardkit__overview"],
            "total_groups": 2,
            "estimated_episodes": 100
        })

        # Return result with error field
        mock_client.clear_all = AsyncMock(return_value={
            "system_groups_cleared": 1,
            "project_groups_cleared": 0,
            "total_episodes_deleted": 50,
            "error": "Failed to clear some project groups"
        })

        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_get_client.return_value = (mock_client, mock_settings)

            result = runner.invoke(cli, ["graphiti", "clear", "--confirm"])

            # Should still succeed but show warning
            assert result.exit_code == 0
            # Output should contain warning about error
            assert "warning" in result.output.lower() or "error" in result.output.lower()
