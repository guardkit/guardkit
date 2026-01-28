"""
Tests for guardkit graphiti CLI commands.

Test Coverage:
- graphiti seed command
- graphiti status command
- graphiti verify command
- Error handling and graceful degradation
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


class TestGraphitiSeedCommand:
    """Test guardkit graphiti seed command."""

    def test_seed_command_exists(self):
        """Test that graphiti seed command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["graphiti", "seed", "--help"])
        assert result.exit_code == 0
        assert "seed" in result.output.lower() or "Seed" in result.output

    def test_seed_runs_seeding_functions(self):
        """Test that seed command invokes seed_all_system_context."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti.seed_all_system_context', new_callable=AsyncMock) as mock_seed, \
             patch('guardkit.cli.graphiti.GraphitiClient') as mock_client_class:

            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client_class.return_value = mock_client
            mock_seed.return_value = True

            result = runner.invoke(cli, ["graphiti", "seed"])

            # Should have called seeding
            mock_seed.assert_called_once()
            assert result.exit_code == 0

    def test_seed_with_force_flag(self):
        """Test that --force flag passes through to seeding."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti.seed_all_system_context', new_callable=AsyncMock) as mock_seed, \
             patch('guardkit.cli.graphiti.GraphitiClient') as mock_client_class:

            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client_class.return_value = mock_client
            mock_seed.return_value = True

            result = runner.invoke(cli, ["graphiti", "seed", "--force"])

            # Should have called seeding with force=True
            mock_seed.assert_called_once()
            call_kwargs = mock_seed.call_args.kwargs
            assert call_kwargs.get('force') is True

    def test_seed_handles_disabled_client(self):
        """Test seed command handles disabled Graphiti client gracefully."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti.GraphitiClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.enabled = False
            mock_client.initialize = AsyncMock(return_value=False)
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "seed"])

            # Should not fail, but indicate Graphiti not available
            assert "not available" in result.output.lower() or \
                   "disabled" in result.output.lower() or \
                   "skipped" in result.output.lower()

    def test_seed_handles_connection_error(self):
        """Test seed command handles connection errors gracefully."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti.GraphitiClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.initialize = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "seed"])

            # Should handle error gracefully
            assert result.exit_code != 0 or "error" in result.output.lower()


class TestGraphitiStatusCommand:
    """Test guardkit graphiti status command."""

    def test_status_command_exists(self):
        """Test that graphiti status command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["graphiti", "status", "--help"])
        assert result.exit_code == 0

    def test_status_shows_seeding_state(self):
        """Test that status shows whether seeding is complete."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti.is_seeded', return_value=True), \
             patch('guardkit.cli.graphiti.GraphitiClient') as mock_client_class:

            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.health_check = AsyncMock(return_value=True)
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "status"])

            assert result.exit_code == 0
            # Should indicate seeded status
            assert "seeded" in result.output.lower()


class TestGraphitiVerifyCommand:
    """Test guardkit graphiti verify command."""

    def test_verify_command_exists(self):
        """Test that graphiti verify command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["graphiti", "verify", "--help"])
        assert result.exit_code == 0

    def test_verify_runs_test_queries(self):
        """Test that verify command runs test queries against seeded data."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti.GraphitiClient') as mock_client_class, \
             patch('guardkit.cli.graphiti.is_seeded', return_value=True):

            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.search = AsyncMock(return_value=[
                {"name": "guardkit_overview", "score": 0.95}
            ])
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "verify"])

            # Should have run search queries
            mock_client.search.assert_called()
            assert result.exit_code == 0

    def test_verify_requires_seeding(self):
        """Test that verify requires seeding to be complete."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti.is_seeded', return_value=False):
            result = runner.invoke(cli, ["graphiti", "verify"])

            # Should indicate seeding required
            assert "not seeded" in result.output.lower() or \
                   "seed first" in result.output.lower() or \
                   "run seed" in result.output.lower()


class TestGraphitiGroupCommands:
    """Test graphiti group-related commands."""

    def test_graphiti_group_exists(self):
        """Test that graphiti command group is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["graphiti", "--help"])
        assert result.exit_code == 0
        assert "graphiti" in result.output.lower() or "Graphiti" in result.output

    def test_graphiti_shows_subcommands(self):
        """Test that graphiti --help shows available subcommands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["graphiti", "--help"])

        # Should list available commands
        assert "seed" in result.output.lower()
        assert "status" in result.output.lower()
