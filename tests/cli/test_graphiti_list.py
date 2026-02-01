"""
Tests for guardkit graphiti list command.

Test Coverage:
- List features command
- List ADRs command
- List patterns command
- List constraints command
- List all categories command
- Count per category display
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from click.testing import CliRunner

from guardkit.cli.main import cli


class TestGraphitiListCommand:
    """Test guardkit graphiti list command."""

    def test_list_command_exists(self):
        """Test that graphiti list command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["graphiti", "list", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output.lower() or "List" in result.output

    def test_list_features(self):
        """Test listing feature specifications."""
        runner = CliRunner()

        mock_results = [
            {
                "name": "FEAT-001",
                "fact": '{"id": "FEAT-001", "title": "Walking Skeleton"}',
                "score": 0.9,
            },
            {
                "name": "FEAT-002",
                "fact": '{"id": "FEAT-002", "title": "Video Info Tool"}',
                "score": 0.85,
            },
        ]

        with patch("guardkit.cli.graphiti.GraphitiClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.search = AsyncMock(return_value=mock_results)
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "list", "features"])

            # Should show feature specs
            assert result.exit_code == 0
            assert "Feature Specifications" in result.output
            assert "(2 items)" in result.output
            assert "FEAT-001" in result.output
            assert "Walking Skeleton" in result.output
            assert "FEAT-002" in result.output
            assert "Video Info Tool" in result.output

    def test_list_adrs(self):
        """Test listing architecture decision records."""
        runner = CliRunner()

        mock_results = [
            {
                "name": "ADR-001",
                "fact": '{"id": "ADR-001", "title": "Use SDK query() for task-work"}',
                "score": 0.9,
            },
        ]

        with patch("guardkit.cli.graphiti.GraphitiClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.search = AsyncMock(return_value=mock_results)
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "list", "adrs"])

            # Should show ADRs
            assert result.exit_code == 0
            assert "Architecture Decision Records" in result.output
            assert "(1 items)" in result.output or "(1 item)" in result.output
            assert "ADR-001" in result.output

    def test_list_patterns(self):
        """Test listing patterns."""
        runner = CliRunner()

        mock_results = [
            {
                "name": "singleton-pattern",
                "fact": '{"id": "singleton", "title": "Singleton Pattern"}',
                "score": 0.9,
            },
            {
                "name": "factory-pattern",
                "fact": '{"id": "factory", "title": "Factory Pattern"}',
                "score": 0.85,
            },
        ]

        with patch("guardkit.cli.graphiti.GraphitiClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.search = AsyncMock(return_value=mock_results)
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "list", "patterns"])

            # Should show patterns
            assert result.exit_code == 0
            assert "Patterns" in result.output
            assert "(2 items)" in result.output
            assert "Singleton Pattern" in result.output
            assert "Factory Pattern" in result.output

    def test_list_constraints(self):
        """Test listing constraints."""
        runner = CliRunner()

        mock_results = [
            {
                "name": "constraint-1",
                "fact": '{"id": "no-graphql", "title": "No GraphQL"}',
                "score": 0.9,
            },
        ]

        with patch("guardkit.cli.graphiti.GraphitiClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.search = AsyncMock(return_value=mock_results)
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "list", "constraints"])

            # Should show constraints
            assert result.exit_code == 0
            assert "Constraints" in result.output
            assert "(1 items)" in result.output or "(1 item)" in result.output

    def test_list_all(self):
        """Test listing all categories."""
        runner = CliRunner()

        # Different results for each category
        mock_results_features = [
            {"name": "FEAT-001", "fact": '{"id": "FEAT-001", "title": "Feature 1"}', "score": 0.9}
        ]
        mock_results_adrs = [
            {"name": "ADR-001", "fact": '{"id": "ADR-001", "title": "ADR 1"}', "score": 0.9}
        ]
        mock_results_patterns = [
            {"name": "pattern-1", "fact": '{"id": "pattern-1", "title": "Pattern 1"}', "score": 0.9}
        ]
        mock_results_constraints = []

        with patch("guardkit.cli.graphiti.GraphitiClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()

            # Mock search to return different results based on group_ids
            async def search_side_effect(query, group_ids, num_results):
                if group_ids == ["feature_specs"]:
                    return mock_results_features
                elif group_ids == ["architecture_decisions"]:
                    return mock_results_adrs
                elif group_ids == ["patterns"]:
                    return mock_results_patterns
                elif group_ids == ["project_constraints"]:
                    return mock_results_constraints
                return []

            mock_client.search = AsyncMock(side_effect=search_side_effect)
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "list", "all"])

            # Should show all categories
            assert result.exit_code == 0
            assert "Feature Specifications" in result.output
            assert "Architecture Decision Records" in result.output
            assert "Patterns" in result.output
            assert "Project Constraints" in result.output

    def test_list_empty_category(self):
        """Test listing an empty category."""
        runner = CliRunner()

        with patch("guardkit.cli.graphiti.GraphitiClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.search = AsyncMock(return_value=[])
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "list", "features"])

            # Should show empty message
            assert result.exit_code == 0
            assert "(0 items)" in result.output
            assert "(empty)" in result.output

    def test_list_handles_disabled_graphiti(self):
        """Test list command handles disabled Graphiti gracefully."""
        runner = CliRunner()

        with patch("guardkit.cli.graphiti.load_graphiti_config") as mock_config, \
             patch("guardkit.cli.graphiti.GraphitiClient") as mock_client_class:
            mock_settings = MagicMock()
            mock_settings.enabled = False
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.neo4j_password = "password"
            mock_settings.timeout = 30
            mock_config.return_value = mock_settings

            mock_client = MagicMock()
            mock_client.enabled = False
            mock_client.initialize = AsyncMock(return_value=False)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "list", "features"])

            # Should indicate Graphiti is not enabled
            assert "not enabled" in result.output.lower() or "disabled" in result.output.lower()

    def test_list_handles_connection_error(self):
        """Test list command handles connection errors gracefully."""
        runner = CliRunner()

        with patch("guardkit.cli.graphiti.GraphitiClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.initialize = AsyncMock(side_effect=Exception("Connection failed"))
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "list", "features"])

            # Should handle error gracefully
            assert result.exit_code == 1
            assert "Error connecting" in result.output or "Connection failed" in result.output

    def test_list_handles_search_error(self):
        """Test list command handles search errors gracefully."""
        runner = CliRunner()

        with patch("guardkit.cli.graphiti.GraphitiClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.search = AsyncMock(side_effect=Exception("Search failed"))
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "list", "features"])

            # Should handle error gracefully (no crash)
            assert "Error searching" in result.output or "Search failed" in result.output

    def test_list_handles_malformed_json(self):
        """Test list command handles malformed JSON facts gracefully."""
        runner = CliRunner()

        mock_results = [
            {
                "name": "FEAT-001",
                "fact": "Not valid JSON",  # Malformed
                "score": 0.9,
            },
        ]

        with patch("guardkit.cli.graphiti.GraphitiClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.search = AsyncMock(return_value=mock_results)
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "list", "features"])

            # Should handle gracefully and show truncated fact
            assert result.exit_code == 0
            assert "Not valid JSON" in result.output or "FEAT-001" in result.output

    def test_list_shows_count(self):
        """Test that list command shows item count."""
        runner = CliRunner()

        mock_results = [
            {"name": f"FEAT-{i:03d}", "fact": f'{{"id": "FEAT-{i:03d}", "title": "Feature {i}"}}', "score": 0.9}
            for i in range(1, 6)  # 5 items
        ]

        with patch("guardkit.cli.graphiti.GraphitiClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.search = AsyncMock(return_value=mock_results)
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "list", "features"])

            # Should show count
            assert result.exit_code == 0
            assert "(5 items)" in result.output

    def test_list_invalid_category(self):
        """Test list command with invalid category."""
        runner = CliRunner()

        result = runner.invoke(cli, ["graphiti", "list", "invalid"])

        # Should show error about invalid choice
        assert result.exit_code != 0
        assert "Invalid value" in result.output or "invalid" in result.output.lower()
