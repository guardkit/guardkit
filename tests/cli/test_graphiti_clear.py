"""
Tests for guardkit graphiti clear CLI command.

Test Coverage:
- Clear all knowledge with --confirm
- Clear system-only knowledge with --system-only --confirm
- Clear project-only knowledge with --project-only --confirm
- --confirm flag is required (safety check)
- --dry-run shows what would be deleted without deleting
- Dry-run respects project namespace boundaries
- Error handling and graceful degradation

TDD: RED phase - these tests are written first before implementation.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from click.testing import CliRunner

# Import will succeed once implemented
try:
    from guardkit.cli.main import cli
    from guardkit.cli.graphiti import graphiti
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="CLI graphiti command not yet implemented"
)


class TestGraphitiClearCommandExists:
    """Test that graphiti clear command is registered."""

    def test_clear_command_exists(self):
        """Test that graphiti clear command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["graphiti", "clear", "--help"])
        assert result.exit_code == 0
        assert "clear" in result.output.lower() or "Clear" in result.output

    def test_clear_shows_options(self):
        """Test that clear --help shows all required options."""
        runner = CliRunner()
        result = runner.invoke(cli, ["graphiti", "clear", "--help"])
        assert result.exit_code == 0
        # Verify options are documented
        assert "--confirm" in result.output
        assert "--system-only" in result.output
        assert "--project-only" in result.output
        assert "--dry-run" in result.output
        assert "--force" in result.output


class TestGraphitiClearRequiresConfirm:
    """Test that --confirm flag is required for safety."""

    def test_clear_without_confirm_fails(self):
        """Test that clear without --confirm shows error and doesn't delete."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti.GraphitiClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.clear_all = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "clear"])

            # Should fail or show error message
            assert result.exit_code != 0 or "confirm" in result.output.lower() or \
                   "required" in result.output.lower()
            # Should NOT have called clear
            mock_client.clear_all.assert_not_called()

    def test_clear_with_confirm_proceeds(self):
        """Test that clear with --confirm proceeds to clear."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti.GraphitiClient') as mock_client_class, \
             patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:

            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.get_clear_preview = AsyncMock(return_value={
                "system_groups": ["guardkit_templates", "guardkit_patterns"],
                "project_groups": ["guardkit__project_overview"],
                "total_groups": 3,
                "estimated_episodes": 100
            })
            mock_client.clear_all = AsyncMock(return_value={
                "system_groups_cleared": 3,
                "project_groups_cleared": 4,
                "total_episodes_deleted": 100
            })
            mock_client_class.return_value = mock_client

            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_get_client.return_value = (mock_client, mock_settings)

            result = runner.invoke(cli, ["graphiti", "clear", "--confirm"])

            # Should succeed and call clear
            assert result.exit_code == 0
            mock_client.clear_all.assert_called_once()


class TestGraphitiClearAll:
    """Test clear all knowledge (project + system)."""

    def test_clear_all_with_confirm(self):
        """Test that clear --confirm clears ALL knowledge."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.get_clear_preview = AsyncMock(return_value={
                "system_groups": ["guardkit_templates", "guardkit_patterns"],
                "project_groups": ["guardkit__project_overview"],
                "total_groups": 3,
                "estimated_episodes": 100
            })
            mock_client.clear_all = AsyncMock(return_value={
                "system_groups_cleared": 3,
                "project_groups_cleared": 4,
                "total_episodes_deleted": 100
            })

            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_get_client.return_value = (mock_client, mock_settings)

            result = runner.invoke(cli, ["graphiti", "clear", "--confirm"])

            assert result.exit_code == 0
            mock_client.clear_all.assert_called_once()
            # Should show success message
            assert "cleared" in result.output.lower() or "deleted" in result.output.lower()


class TestGraphitiClearSystemOnly:
    """Test clear system-only knowledge."""

    def test_clear_system_only(self):
        """Test that --system-only clears only system knowledge."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.get_clear_preview = AsyncMock(return_value={
                "system_groups": ["guardkit_templates", "guardkit_patterns", "guardkit_workflows"],
                "project_groups": [],
                "total_groups": 3,
                "estimated_episodes": 50
            })
            mock_client.clear_system_groups = AsyncMock(return_value={
                "groups_cleared": ["guardkit_templates", "guardkit_patterns", "guardkit_workflows"],
                "episodes_deleted": 50
            })

            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_get_client.return_value = (mock_client, mock_settings)

            result = runner.invoke(cli, ["graphiti", "clear", "--system-only", "--confirm"])

            assert result.exit_code == 0
            mock_client.clear_system_groups.assert_called_once()
            # Should show system-specific output
            assert "system" in result.output.lower()


class TestGraphitiClearProjectOnly:
    """Test clear project-only knowledge."""

    def test_clear_project_only(self):
        """Test that --project-only clears only project knowledge."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.get_clear_preview = AsyncMock(return_value={
                "system_groups": [],
                "project_groups": ["guardkit__project_overview", "guardkit__project_architecture"],
                "total_groups": 2,
                "estimated_episodes": 30
            })
            mock_client.clear_project_groups = AsyncMock(return_value={
                "project": "guardkit",
                "groups_cleared": ["guardkit__project_overview", "guardkit__project_architecture"],
                "episodes_deleted": 30
            })

            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_get_client.return_value = (mock_client, mock_settings)

            result = runner.invoke(cli, ["graphiti", "clear", "--project-only", "--confirm"])

            assert result.exit_code == 0
            mock_client.clear_project_groups.assert_called_once()
            # Should show project-specific output
            assert "project" in result.output.lower()


class TestGraphitiClearDryRun:
    """Test dry-run mode."""

    def test_dry_run_shows_what_would_be_deleted(self):
        """Test that --dry-run shows what would be deleted without deleting."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.get_clear_preview = AsyncMock(return_value={
                "system_groups": ["guardkit_templates", "guardkit_patterns"],
                "project_groups": ["guardkit__project_overview"],
                "total_groups": 3,
                "estimated_episodes": 150
            })
            mock_client.clear_all = AsyncMock()

            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_get_client.return_value = (mock_client, mock_settings)

            result = runner.invoke(cli, ["graphiti", "clear", "--dry-run"])

            assert result.exit_code == 0
            # Should show preview
            assert "would" in result.output.lower() or "dry" in result.output.lower()
            # Should NOT actually clear
            mock_client.clear_all.assert_not_called()

    def test_dry_run_with_system_only(self):
        """Test dry-run with --system-only shows only system groups."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.get_clear_preview = AsyncMock(return_value={
                "system_groups": ["guardkit_templates", "guardkit_patterns"],
                "project_groups": [],
                "total_groups": 2,
                "estimated_episodes": 50
            })

            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_get_client.return_value = (mock_client, mock_settings)

            result = runner.invoke(cli, ["graphiti", "clear", "--dry-run", "--system-only"])

            assert result.exit_code == 0
            mock_client.get_clear_preview.assert_called_once()
            call_kwargs = mock_client.get_clear_preview.call_args
            # Verify it was called with system_only=True
            assert call_kwargs.kwargs.get('system_only') is True or \
                   (call_kwargs.args and call_kwargs.args[0] is True)


class TestGraphitiClearErrorHandling:
    """Test error handling and graceful degradation."""

    def test_clear_handles_disabled_client(self):
        """Test clear handles disabled Graphiti client gracefully."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = False
            mock_client.initialize = AsyncMock(return_value=False)
            mock_client.close = AsyncMock()

            mock_settings = MagicMock()
            mock_settings.enabled = False
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_get_client.return_value = (mock_client, mock_settings)

            result = runner.invoke(cli, ["graphiti", "clear", "--confirm"])

            # Should not fail, but indicate Graphiti not available
            assert "not available" in result.output.lower() or \
                   "disabled" in result.output.lower() or \
                   "skipped" in result.output.lower()

    def test_clear_handles_connection_error(self):
        """Test clear handles connection errors gracefully."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.initialize = AsyncMock(side_effect=Exception("Connection refused"))
            mock_get_client.return_value = (mock_client, MagicMock())

            result = runner.invoke(cli, ["graphiti", "clear", "--confirm"])

            # Should handle error gracefully
            assert result.exit_code != 0 or "error" in result.output.lower()

    def test_clear_handles_clear_error(self):
        """Test clear handles errors during clearing gracefully."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.get_clear_preview = AsyncMock(return_value={
                "system_groups": ["guardkit_templates"],
                "project_groups": [],
                "total_groups": 1,
                "estimated_episodes": 10
            })
            mock_client.clear_all = AsyncMock(side_effect=Exception("Database error"))

            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_get_client.return_value = (mock_client, mock_settings)

            result = runner.invoke(cli, ["graphiti", "clear", "--confirm"])

            # Should handle error gracefully
            assert result.exit_code != 0 or "error" in result.output.lower()


class TestGraphitiClearForceFlag:
    """Test --force flag for automation."""

    def test_force_skips_confirmation_prompt(self):
        """Test that --force skips any confirmation prompts."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.get_clear_preview = AsyncMock(return_value={
                "system_groups": ["guardkit_templates", "guardkit_patterns"],
                "project_groups": ["guardkit__project_overview"],
                "total_groups": 3,
                "estimated_episodes": 100
            })
            mock_client.clear_all = AsyncMock(return_value={
                "system_groups_cleared": 3,
                "project_groups_cleared": 4,
                "total_episodes_deleted": 100
            })

            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_get_client.return_value = (mock_client, mock_settings)

            # With --force and --confirm, should work without any prompts
            result = runner.invoke(cli, ["graphiti", "clear", "--confirm", "--force"])

            assert result.exit_code == 0
            mock_client.clear_all.assert_called_once()


class TestGraphitiClearOutput:
    """Test clear command output formatting."""

    def test_clear_shows_summary_before_proceeding(self):
        """Test that clear shows summary of what will be deleted."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.get_clear_preview = AsyncMock(return_value={
                "system_groups": ["guardkit_templates", "guardkit_patterns"],
                "project_groups": ["guardkit__project_overview"],
                "total_groups": 3,
                "estimated_episodes": 150
            })
            mock_client.clear_all = AsyncMock(return_value={
                "system_groups_cleared": 2,
                "project_groups_cleared": 1,
                "total_episodes_deleted": 150
            })

            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_get_client.return_value = (mock_client, mock_settings)

            result = runner.invoke(cli, ["graphiti", "clear", "--confirm"])

            assert result.exit_code == 0
            # Should show some summary info
            output_lower = result.output.lower()
            assert "group" in output_lower or "episode" in output_lower or \
                   "delete" in output_lower or "clear" in output_lower


class TestGraphitiClearMutualExclusivity:
    """Test mutual exclusivity of --system-only and --project-only."""

    def test_system_and_project_only_are_exclusive(self):
        """Test that --system-only and --project-only cannot be used together."""
        runner = CliRunner()

        result = runner.invoke(cli, ["graphiti", "clear", "--system-only", "--project-only", "--confirm"])

        # Should fail with an error message
        assert result.exit_code != 0 or \
               "exclusive" in result.output.lower() or \
               "cannot" in result.output.lower() or \
               "error" in result.output.lower()
