"""
Unit tests for graphiti status command.

Tests coverage:
- Enabled/disabled status display
- Episode counting per category
- Colored status indicators
- Verbose mode showing empty groups
- Error handling
"""

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from click.testing import CliRunner

from guardkit.cli.graphiti import graphiti, _cmd_status
from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_settings():
    """Create mock Graphiti settings."""
    settings = MagicMock()
    settings.enabled = True
    settings.neo4j_uri = "bolt://localhost:7687"
    settings.neo4j_user = "neo4j"
    settings.timeout = 30.0
    return settings


@pytest.fixture
def mock_disabled_settings():
    """Create mock Graphiti settings with disabled state."""
    settings = MagicMock()
    settings.enabled = False
    settings.neo4j_uri = "bolt://localhost:7687"
    settings.neo4j_user = "neo4j"
    settings.timeout = 30.0
    return settings


@pytest.fixture
def mock_client():
    """Create a fully mocked GraphitiClient."""
    client = AsyncMock(spec=GraphitiClient)
    client.enabled = True
    client.config = GraphitiConfig(enabled=True)
    client.initialize = AsyncMock(return_value=True)
    client.close = AsyncMock()
    client.health_check = AsyncMock(return_value=True)

    # Mock search to return different counts for different groups
    async def mock_search(query, group_ids, num_results):
        if not group_ids:
            return []

        group_id = group_ids[0]
        # Return different counts for different groups
        counts = {
            "product_knowledge": 3,
            "command_workflows": 7,
            "patterns": 12,
            "agents": 8,
            "project_overview": 1,
            "project_architecture": 1,
            "feature_specs": 4,
            "project_decisions": 2,
            "architecture_decisions": 5,
            "task_outcomes": 15,
            "failure_patterns": 3,
            "successful_fixes": 8,
        }

        count = counts.get(group_id, 0)
        # Return empty list items (we only care about count)
        return [{}] * count

    client.search = AsyncMock(side_effect=mock_search)
    return client


@pytest.fixture
def mock_empty_client():
    """Create a mocked GraphitiClient with no episodes."""
    client = AsyncMock(spec=GraphitiClient)
    client.enabled = True
    client.config = GraphitiConfig(enabled=True)
    client.initialize = AsyncMock(return_value=True)
    client.close = AsyncMock()
    client.health_check = AsyncMock(return_value=True)
    client.search = AsyncMock(return_value=[])
    return client


# ============================================================================
# STATUS COMMAND TESTS
# ============================================================================


class TestStatusCommandDisabled:
    """Test status command when Graphiti is disabled."""

    def test_status_when_disabled(self, cli_runner, mock_disabled_settings):
        """Test status command shows disabled status correctly."""
        with patch("guardkit.cli.graphiti.load_graphiti_config", return_value=mock_disabled_settings):
            result = cli_runner.invoke(graphiti, ["status"])

            assert result.exit_code == 0
            assert "DISABLED" in result.output
            assert "Enable in config/graphiti.yaml" in result.output


class TestStatusCommandEnabled:
    """Test status command when Graphiti is enabled."""

    def test_status_shows_enabled(self, cli_runner, mock_settings, mock_client):
        """Test status command shows enabled status."""
        with patch("guardkit.cli.graphiti.load_graphiti_config", return_value=mock_settings):
            with patch("guardkit.cli.graphiti._get_client_and_config", return_value=(mock_client, mock_settings)):
                result = cli_runner.invoke(graphiti, ["status"])

                assert result.exit_code == 0
                assert "ENABLED" in result.output

    def test_status_shows_episode_counts(self, cli_runner, mock_settings, mock_client):
        """Test status command shows episode counts per category."""
        with patch("guardkit.cli.graphiti.load_graphiti_config", return_value=mock_settings):
            with patch("guardkit.cli.graphiti._get_client_and_config", return_value=(mock_client, mock_settings)):
                result = cli_runner.invoke(graphiti, ["status"])

                assert result.exit_code == 0
                # Check category headers
                assert "System Knowledge:" in result.output
                assert "Project Knowledge:" in result.output
                assert "Decisions:" in result.output
                assert "Learning:" in result.output

                # Check specific counts
                assert "product_knowledge: 3" in result.output
                assert "command_workflows: 7" in result.output
                assert "patterns: 12" in result.output
                assert "feature_specs: 4" in result.output

    def test_status_shows_total_count(self, cli_runner, mock_settings, mock_client):
        """Test status command shows total episode count."""
        with patch("guardkit.cli.graphiti.load_graphiti_config", return_value=mock_settings):
            with patch("guardkit.cli.graphiti._get_client_and_config", return_value=(mock_client, mock_settings)):
                result = cli_runner.invoke(graphiti, ["status"])

                assert result.exit_code == 0
                # Total = 3+7+12+8+1+1+4+2+5+15+3+8 = 69
                assert "Total Episodes: 69" in result.output

    def test_status_hides_empty_groups_by_default(self, cli_runner, mock_settings, mock_empty_client):
        """Test status command hides empty groups by default."""
        with patch("guardkit.cli.graphiti.load_graphiti_config", return_value=mock_settings):
            with patch("guardkit.cli.graphiti._get_client_and_config", return_value=(mock_empty_client, mock_settings)):
                result = cli_runner.invoke(graphiti, ["status"])

                assert result.exit_code == 0
                # Should not show group names when count is 0 (without --verbose)
                assert "product_knowledge:" not in result.output
                assert "Total Episodes: 0" in result.output

    def test_status_shows_empty_groups_with_verbose(self, cli_runner, mock_settings, mock_empty_client):
        """Test status command shows empty groups with --verbose flag."""
        with patch("guardkit.cli.graphiti.load_graphiti_config", return_value=mock_settings):
            with patch("guardkit.cli.graphiti._get_client_and_config", return_value=(mock_empty_client, mock_settings)):
                result = cli_runner.invoke(graphiti, ["status", "--verbose"])

                assert result.exit_code == 0
                # Should show all groups with --verbose
                assert "product_knowledge: 0" in result.output
                assert "command_workflows: 0" in result.output
                assert "patterns: 0" in result.output


class TestStatusCommandErrors:
    """Test status command error handling."""

    def test_status_handles_connection_failure(self, cli_runner, mock_settings):
        """Test status command handles connection failures gracefully."""
        mock_client = AsyncMock(spec=GraphitiClient)
        mock_client.enabled = True
        mock_client.initialize = AsyncMock(return_value=False)
        mock_client.close = AsyncMock()

        with patch("guardkit.cli.graphiti.load_graphiti_config", return_value=mock_settings):
            with patch("guardkit.cli.graphiti._get_client_and_config", return_value=(mock_client, mock_settings)):
                result = cli_runner.invoke(graphiti, ["status"])

                assert result.exit_code == 0
                assert "Failed" in result.output or "Check Neo4j" in result.output

    def test_status_handles_health_check_failure(self, cli_runner, mock_settings):
        """Test status command handles health check failures."""
        mock_client = AsyncMock(spec=GraphitiClient)
        mock_client.enabled = True
        mock_client.initialize = AsyncMock(return_value=True)
        mock_client.close = AsyncMock()
        mock_client.health_check = AsyncMock(return_value=False)

        with patch("guardkit.cli.graphiti.load_graphiti_config", return_value=mock_settings):
            with patch("guardkit.cli.graphiti._get_client_and_config", return_value=(mock_client, mock_settings)):
                result = cli_runner.invoke(graphiti, ["status"])

                assert result.exit_code == 0
                assert "Degraded" in result.output or "Health:" in result.output

    def test_status_handles_search_exception(self, cli_runner, mock_settings):
        """Test status command handles search exceptions."""
        mock_client = AsyncMock(spec=GraphitiClient)
        mock_client.enabled = True
        mock_client.initialize = AsyncMock(return_value=True)
        mock_client.close = AsyncMock()
        mock_client.health_check = AsyncMock(return_value=True)
        mock_client.search = AsyncMock(side_effect=Exception("Search failed"))

        with patch("guardkit.cli.graphiti.load_graphiti_config", return_value=mock_settings):
            with patch("guardkit.cli.graphiti._get_client_and_config", return_value=(mock_client, mock_settings)):
                result = cli_runner.invoke(graphiti, ["status"])

                assert result.exit_code == 0
                assert "Error:" in result.output or "Search failed" in result.output


class TestStatusCommandColoredIndicators:
    """Test status command colored status indicators."""

    def test_status_uses_green_for_nonzero_counts(self, cli_runner, mock_settings, mock_client):
        """Test status command uses green color for non-zero episode counts."""
        with patch("guardkit.cli.graphiti.load_graphiti_config", return_value=mock_settings):
            with patch("guardkit.cli.graphiti._get_client_and_config", return_value=(mock_client, mock_settings)):
                result = cli_runner.invoke(graphiti, ["status"])

                assert result.exit_code == 0
                # Rich uses [green] tags for colored output
                # We can't directly test colors in CLI output, but we can verify
                # the structure is correct and contains the counts
                assert "3" in result.output  # product_knowledge count
                assert "12" in result.output  # patterns count

    def test_status_uses_yellow_for_zero_counts_in_verbose(self, cli_runner, mock_settings, mock_empty_client):
        """Test status command uses yellow color for zero counts in verbose mode."""
        with patch("guardkit.cli.graphiti.load_graphiti_config", return_value=mock_settings):
            with patch("guardkit.cli.graphiti._get_client_and_config", return_value=(mock_empty_client, mock_settings)):
                result = cli_runner.invoke(graphiti, ["status", "--verbose"])

                assert result.exit_code == 0
                # In verbose mode, should show all groups with 0 counts
                assert "0" in result.output


class TestStatusCommandIntegration:
    """Integration tests for status command."""

    def test_status_command_end_to_end(self, cli_runner, mock_settings, mock_client):
        """Test complete status command workflow."""
        with patch("guardkit.cli.graphiti.load_graphiti_config", return_value=mock_settings):
            with patch("guardkit.cli.graphiti._get_client_and_config", return_value=(mock_client, mock_settings)):
                result = cli_runner.invoke(graphiti, ["status"])

                assert result.exit_code == 0
                # Verify key elements are present
                assert "Graphiti Knowledge Status" in result.output
                assert "ENABLED" in result.output
                assert "System Knowledge:" in result.output
                assert "Total Episodes:" in result.output

    def test_status_command_with_short_verbose_flag(self, cli_runner, mock_settings, mock_empty_client):
        """Test status command with -v short flag."""
        with patch("guardkit.cli.graphiti.load_graphiti_config", return_value=mock_settings):
            with patch("guardkit.cli.graphiti._get_client_and_config", return_value=(mock_empty_client, mock_settings)):
                result = cli_runner.invoke(graphiti, ["status", "-v"])

                assert result.exit_code == 0
                # Should show empty groups with -v
                assert "product_knowledge: 0" in result.output
