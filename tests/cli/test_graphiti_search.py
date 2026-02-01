"""
Tests for guardkit graphiti search command.

TDD: Tests written first for TASK-GR5-002.

Test Coverage:
- search command registration
- search all groups (no --group option)
- search with --group option to limit to specific group
- search with --limit option to control max results
- relevance score color coding
- truncation of long facts with "..."
- error handling for disabled Graphiti
- error handling for connection errors
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


class TestSearchCommandRegistration:
    """Test search command is properly registered."""

    def test_search_command_exists(self):
        """Test that graphiti search command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["graphiti", "search", "--help"])
        assert result.exit_code == 0
        assert "search" in result.output.lower() or "Search" in result.output

    def test_search_requires_query_argument(self):
        """Test that search command requires a query argument."""
        runner = CliRunner()
        result = runner.invoke(cli, ["graphiti", "search"])
        # Should fail because query is required
        assert result.exit_code != 0
        assert "missing" in result.output.lower() or "required" in result.output.lower()

    def test_search_help_shows_options(self):
        """Test that search --help shows all options."""
        runner = CliRunner()
        result = runner.invoke(cli, ["graphiti", "search", "--help"])
        assert result.exit_code == 0
        # Should show --group and --limit options
        assert "--group" in result.output or "-g" in result.output
        assert "--limit" in result.output or "-n" in result.output


class TestSearchAllGroups:
    """Test search across all groups (default behavior)."""

    def test_search_all_groups_with_results(self):
        """Test search across all groups returns results."""
        runner = CliRunner()

        mock_results = [
            {"name": "auth_pattern", "fact": "JWT authentication using bearer tokens", "score": 0.92},
            {"name": "adr_003", "fact": "Chose OAuth2 over API keys because of security", "score": 0.85},
            {"name": "feat_auth", "fact": "Feature FEAT-AUTH-001: User authentication system", "score": 0.71},
        ]

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.search = AsyncMock(return_value=mock_results)
            mock_client.close = AsyncMock()
            mock_get_client.return_value = (mock_client, MagicMock(enabled=True))

            result = runner.invoke(cli, ["graphiti", "search", "authentication"])

            assert result.exit_code == 0
            # Should show results count
            assert "3" in result.output or "results" in result.output.lower()
            # Should show facts
            assert "JWT" in result.output or "authentication" in result.output.lower()
            # Should have called search
            mock_client.search.assert_called()

    def test_search_all_groups_no_results(self):
        """Test search with no matching results."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.search = AsyncMock(return_value=[])
            mock_client.close = AsyncMock()
            mock_get_client.return_value = (mock_client, MagicMock(enabled=True))

            result = runner.invoke(cli, ["graphiti", "search", "nonexistent_query_xyz"])

            assert result.exit_code == 0
            # Should indicate no results
            assert "no result" in result.output.lower() or "0" in result.output


class TestSearchWithGroupOption:
    """Test search with --group option to limit to specific group."""

    def test_search_with_group_option(self):
        """Test search limited to specific group."""
        runner = CliRunner()

        mock_results = [
            {"name": "pattern1", "fact": "Error handling pattern", "score": 0.88},
        ]

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.search = AsyncMock(return_value=mock_results)
            mock_client.close = AsyncMock()
            mock_get_client.return_value = (mock_client, MagicMock(enabled=True))

            result = runner.invoke(cli, ["graphiti", "search", "error handling", "--group", "patterns"])

            assert result.exit_code == 0
            # Should have called search with specific group
            mock_client.search.assert_called()
            call_kwargs = mock_client.search.call_args.kwargs
            assert call_kwargs.get('group_ids') == ["patterns"]

    def test_search_with_g_short_option(self):
        """Test search with -g short option."""
        runner = CliRunner()

        mock_results = [
            {"name": "feature1", "fact": "Walking skeleton feature", "score": 0.95},
        ]

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.search = AsyncMock(return_value=mock_results)
            mock_client.close = AsyncMock()
            mock_get_client.return_value = (mock_client, MagicMock(enabled=True))

            result = runner.invoke(cli, ["graphiti", "search", "walking skeleton", "-g", "feature_specs"])

            assert result.exit_code == 0
            mock_client.search.assert_called()
            call_kwargs = mock_client.search.call_args.kwargs
            assert call_kwargs.get('group_ids') == ["feature_specs"]


class TestSearchWithLimitOption:
    """Test search with --limit option to control max results."""

    def test_search_with_limit_option(self):
        """Test search with limited results."""
        runner = CliRunner()

        mock_results = [
            {"name": "result1", "fact": "First result", "score": 0.9},
            {"name": "result2", "fact": "Second result", "score": 0.8},
            {"name": "result3", "fact": "Third result", "score": 0.7},
            {"name": "result4", "fact": "Fourth result", "score": 0.6},
            {"name": "result5", "fact": "Fifth result", "score": 0.5},
        ]

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.search = AsyncMock(return_value=mock_results[:5])
            mock_client.close = AsyncMock()
            mock_get_client.return_value = (mock_client, MagicMock(enabled=True))

            result = runner.invoke(cli, ["graphiti", "search", "test", "--limit", "5"])

            assert result.exit_code == 0
            mock_client.search.assert_called()
            call_kwargs = mock_client.search.call_args.kwargs
            assert call_kwargs.get('num_results') == 5

    def test_search_with_n_short_option(self):
        """Test search with -n short option for limit."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.search = AsyncMock(return_value=[])
            mock_client.close = AsyncMock()
            mock_get_client.return_value = (mock_client, MagicMock(enabled=True))

            result = runner.invoke(cli, ["graphiti", "search", "test", "-n", "3"])

            assert result.exit_code == 0
            call_kwargs = mock_client.search.call_args.kwargs
            assert call_kwargs.get('num_results') == 3

    def test_search_default_limit_is_10(self):
        """Test that default limit is 10 when not specified."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.search = AsyncMock(return_value=[])
            mock_client.close = AsyncMock()
            mock_get_client.return_value = (mock_client, MagicMock(enabled=True))

            result = runner.invoke(cli, ["graphiti", "search", "test"])

            assert result.exit_code == 0
            call_kwargs = mock_client.search.call_args.kwargs
            assert call_kwargs.get('num_results') == 10


class TestSearchOutputFormatting:
    """Test search output formatting including color coding and truncation."""

    def test_search_shows_relevance_score(self):
        """Test that search results show relevance score."""
        runner = CliRunner()

        mock_results = [
            {"name": "high_score", "fact": "Highly relevant result", "score": 0.92},
            {"name": "mid_score", "fact": "Moderately relevant result", "score": 0.65},
            {"name": "low_score", "fact": "Less relevant result", "score": 0.35},
        ]

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.search = AsyncMock(return_value=mock_results)
            mock_client.close = AsyncMock()
            mock_get_client.return_value = (mock_client, MagicMock(enabled=True))

            result = runner.invoke(cli, ["graphiti", "search", "relevant"], color=True)

            assert result.exit_code == 0
            # Should show scores
            assert "0.92" in result.output or "92" in result.output
            assert "0.65" in result.output or "65" in result.output

    def test_search_truncates_long_facts(self):
        """Test that long facts are truncated with '...'."""
        runner = CliRunner()

        long_fact = "A" * 200  # Very long fact
        mock_results = [
            {"name": "long_result", "fact": long_fact, "score": 0.8},
        ]

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.search = AsyncMock(return_value=mock_results)
            mock_client.close = AsyncMock()
            mock_get_client.return_value = (mock_client, MagicMock(enabled=True))

            result = runner.invoke(cli, ["graphiti", "search", "test"])

            assert result.exit_code == 0
            # Should truncate with "..."
            assert "..." in result.output
            # Should not show full 200 characters
            assert long_fact not in result.output

    def test_search_shows_numbered_results(self):
        """Test that search results are numbered."""
        runner = CliRunner()

        mock_results = [
            {"name": "result1", "fact": "First result fact", "score": 0.9},
            {"name": "result2", "fact": "Second result fact", "score": 0.8},
            {"name": "result3", "fact": "Third result fact", "score": 0.7},
        ]

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.search = AsyncMock(return_value=mock_results)
            mock_client.close = AsyncMock()
            mock_get_client.return_value = (mock_client, MagicMock(enabled=True))

            result = runner.invoke(cli, ["graphiti", "search", "test"])

            assert result.exit_code == 0
            # Should show numbered results
            assert "1." in result.output
            assert "2." in result.output
            assert "3." in result.output


class TestSearchErrorHandling:
    """Test error handling for search command."""

    def test_search_handles_disabled_graphiti(self):
        """Test search handles disabled Graphiti gracefully."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = False
            mock_client.initialize = AsyncMock(return_value=False)
            mock_client.close = AsyncMock()
            mock_settings = MagicMock()
            mock_settings.enabled = False
            mock_get_client.return_value = (mock_client, mock_settings)

            result = runner.invoke(cli, ["graphiti", "search", "test"])

            # Should not crash, should indicate disabled
            assert "disabled" in result.output.lower() or "not enabled" in result.output.lower() or "not available" in result.output.lower()

    def test_search_handles_connection_error(self):
        """Test search handles connection errors gracefully."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.initialize = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client.close = AsyncMock()
            mock_get_client.return_value = (mock_client, MagicMock(enabled=True))

            result = runner.invoke(cli, ["graphiti", "search", "test"])

            # Should handle error gracefully
            assert result.exit_code != 0 or "error" in result.output.lower()

    def test_search_handles_search_error(self):
        """Test search handles search errors gracefully."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.search = AsyncMock(side_effect=Exception("Search failed"))
            mock_client.close = AsyncMock()
            mock_get_client.return_value = (mock_client, MagicMock(enabled=True))

            result = runner.invoke(cli, ["graphiti", "search", "test"])

            # Should handle error gracefully
            assert result.exit_code != 0 or "error" in result.output.lower()


class TestSearchIntegration:
    """Integration tests for search command combining multiple features."""

    def test_search_with_group_and_limit(self):
        """Test search with both --group and --limit options."""
        runner = CliRunner()

        mock_results = [
            {"name": "pattern1", "fact": "Error handling pattern one", "score": 0.9},
            {"name": "pattern2", "fact": "Error handling pattern two", "score": 0.85},
            {"name": "pattern3", "fact": "Error handling pattern three", "score": 0.8},
        ]

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.search = AsyncMock(return_value=mock_results)
            mock_client.close = AsyncMock()
            mock_get_client.return_value = (mock_client, MagicMock(enabled=True))

            result = runner.invoke(cli, [
                "graphiti", "search", "error handling",
                "--group", "patterns",
                "--limit", "3"
            ])

            assert result.exit_code == 0
            call_kwargs = mock_client.search.call_args.kwargs
            assert call_kwargs.get('group_ids') == ["patterns"]
            assert call_kwargs.get('num_results') == 3
