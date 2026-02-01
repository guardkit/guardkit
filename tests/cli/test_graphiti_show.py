"""
Tests for guardkit graphiti show command.

Test Coverage:
- show command registration
- Display feature specs (FEAT-XXX)
- Display ADRs (ADR-XXX)
- Display project overview
- Display patterns, constraints, guides
- Formatted colored output
- "Not found" error handling
- Graphiti disabled handling
- Help output

Coverage Target: >=85%
Test Count: 15+ tests
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


class TestGraphitiShowCommand:
    """Test guardkit graphiti show command."""

    def test_show_command_exists(self):
        """Test that graphiti show command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["graphiti", "show", "--help"])
        assert result.exit_code == 0
        assert "show" in result.output.lower() or "Show" in result.output

    def test_show_command_requires_knowledge_id(self):
        """Test that show command requires a knowledge_id argument."""
        runner = CliRunner()
        result = runner.invoke(cli, ["graphiti", "show"])
        # Should fail without knowledge_id
        assert result.exit_code != 0
        assert "knowledge_id" in result.output.lower() or "argument" in result.output.lower()

    def test_show_feature_spec_displays_details(self):
        """Test that show command displays feature spec details."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti.GraphitiClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.search = AsyncMock(return_value=[
                {
                    "name": "FEAT-GR-001",
                    "fact": "Feature spec: Implement graphiti search command",
                    "uuid": "123e4567-e89b-12d3-a456-426614174000",
                    "score": 0.95
                }
            ])
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "show", "FEAT-GR-001"])

            # Should have called search
            mock_client.search.assert_called_once()
            call_args = mock_client.search.call_args
            assert "FEAT-GR-001" in call_args[0][0]  # Query contains the ID

            assert result.exit_code == 0
            assert "FEAT-GR-001" in result.output

    def test_show_adr_displays_details(self):
        """Test that show command displays ADR details."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti.GraphitiClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.search = AsyncMock(return_value=[
                {
                    "name": "ADR-001",
                    "fact": "ADR: Use SDK for task-work invocation",
                    "uuid": "234e5678-e89b-12d3-a456-426614174001",
                    "score": 0.92
                }
            ])
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "show", "ADR-001"])

            # Should have called search
            mock_client.search.assert_called_once()
            call_args = mock_client.search.call_args
            assert "ADR-001" in call_args[0][0]

            assert result.exit_code == 0
            assert "ADR-001" in result.output

    def test_show_project_overview_displays_details(self):
        """Test that show command displays project overview."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti.GraphitiClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.search = AsyncMock(return_value=[
                {
                    "name": "guardkit_project_overview",
                    "fact": "GuardKit is a lightweight task workflow system",
                    "uuid": "345e6789-e89b-12d3-a456-426614174002",
                    "score": 0.98
                }
            ])
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "show", "project-overview"])

            # Should have called search
            mock_client.search.assert_called_once()
            call_args = mock_client.search.call_args
            assert "project" in call_args[0][0].lower() or "overview" in call_args[0][0].lower()

            assert result.exit_code == 0
            assert "GuardKit" in result.output or "project" in result.output.lower()

    def test_show_pattern_displays_details(self):
        """Test that show command displays pattern details."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti.GraphitiClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.search = AsyncMock(return_value=[
                {
                    "name": "singleton-pattern",
                    "fact": "Singleton pattern ensures a class has only one instance",
                    "uuid": "456e789a-e89b-12d3-a456-426614174003",
                    "score": 0.88
                }
            ])
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "show", "singleton-pattern"])

            # Should have called search
            mock_client.search.assert_called_once()

            assert result.exit_code == 0
            assert "singleton" in result.output.lower()

    def test_show_constraint_displays_details(self):
        """Test that show command displays constraint details."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti.GraphitiClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.search = AsyncMock(return_value=[
                {
                    "name": "no-graphql-constraint",
                    "fact": "Constraint: Do not use GraphQL in this project",
                    "uuid": "567e89ab-e89b-12d3-a456-426614174004",
                    "score": 0.91
                }
            ])
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "show", "no-graphql-constraint"])

            # Should have called search
            mock_client.search.assert_called_once()

            assert result.exit_code == 0
            assert "constraint" in result.output.lower() or "graphql" in result.output.lower()

    def test_show_guide_displays_details(self):
        """Test that show command displays guide details."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti.GraphitiClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.search = AsyncMock(return_value=[
                {
                    "name": "testing-guide",
                    "fact": "Guide: Testing best practices for GuardKit",
                    "uuid": "678e9abc-e89b-12d3-a456-426614174005",
                    "score": 0.87
                }
            ])
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "show", "testing-guide"])

            # Should have called search
            mock_client.search.assert_called_once()

            assert result.exit_code == 0
            assert "testing" in result.output.lower() or "guide" in result.output.lower()

    def test_show_not_found_displays_error(self):
        """Test that show command handles 'not found' gracefully."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti.GraphitiClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.search = AsyncMock(return_value=[])  # No results
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "show", "FEAT-NONEXISTENT"])

            # Should have called search
            mock_client.search.assert_called_once()

            # Should indicate not found
            assert "not found" in result.output.lower() or "no results" in result.output.lower()

    def test_show_handles_disabled_graphiti(self):
        """Test that show command handles disabled Graphiti gracefully."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti.GraphitiClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.enabled = False
            mock_client.initialize = AsyncMock(return_value=False)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "show", "FEAT-001"])

            # Should indicate Graphiti not available
            assert "not available" in result.output.lower() or \
                   "disabled" in result.output.lower() or \
                   "not enabled" in result.output.lower()

    def test_show_handles_connection_error(self):
        """Test that show command handles connection errors gracefully."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti.GraphitiClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.initialize = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "show", "FEAT-001"])

            # Should handle error gracefully
            assert result.exit_code != 0 or "error" in result.output.lower()

    def test_show_uses_correct_group_ids_for_feature(self):
        """Test that show command uses correct group_ids for feature specs."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti.GraphitiClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.search = AsyncMock(return_value=[
                {"name": "FEAT-GR-001", "fact": "Feature spec", "uuid": "123", "score": 0.9}
            ])
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "show", "FEAT-GR-001"])

            # Should have called search with feature_specs group_id
            mock_client.search.assert_called_once()
            call_kwargs = mock_client.search.call_args.kwargs
            assert call_kwargs.get('group_ids') is not None
            assert "feature_specs" in call_kwargs['group_ids']

    def test_show_uses_correct_group_ids_for_adr(self):
        """Test that show command uses correct group_ids for ADRs."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti.GraphitiClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.search = AsyncMock(return_value=[
                {"name": "ADR-001", "fact": "ADR content", "uuid": "234", "score": 0.9}
            ])
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "show", "ADR-001"])

            # Should have called search with architecture_decisions group_id
            mock_client.search.assert_called_once()
            call_kwargs = mock_client.search.call_args.kwargs
            assert call_kwargs.get('group_ids') is not None
            assert "architecture_decisions" in call_kwargs['group_ids'] or \
                   "project_decisions" in call_kwargs['group_ids']

    def test_show_uses_correct_group_ids_for_project_overview(self):
        """Test that show command uses correct group_ids for project overview."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti.GraphitiClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.search = AsyncMock(return_value=[
                {"name": "project-overview", "fact": "Overview", "uuid": "345", "score": 0.9}
            ])
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "show", "project-overview"])

            # Should have called search with project_overview group_id
            mock_client.search.assert_called_once()
            call_kwargs = mock_client.search.call_args.kwargs
            assert call_kwargs.get('group_ids') is not None
            assert "project_overview" in call_kwargs['group_ids']

    def test_show_displays_formatted_output(self):
        """Test that show command produces formatted colored output."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti.GraphitiClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.search = AsyncMock(return_value=[
                {
                    "name": "FEAT-GR-001",
                    "fact": "Feature: Implement search command\n\nDescription: Add search functionality",
                    "uuid": "123e4567-e89b-12d3-a456-426614174000",
                    "score": 0.95,
                    "created_at": "2024-01-15T10:30:00Z",
                    "valid_at": "2024-01-15T10:30:00Z"
                }
            ])
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["graphiti", "show", "FEAT-GR-001"])

            assert result.exit_code == 0
            # Should contain formatted sections
            # Check for some structured output (Rich formatting)
            assert "FEAT-GR-001" in result.output
            # Output should contain some structure (newlines, sections)
            assert result.output.count('\n') > 3

    def test_show_help_output(self):
        """Test that show command help is informative."""
        runner = CliRunner()
        result = runner.invoke(cli, ["graphiti", "show", "--help"])

        assert result.exit_code == 0
        # Help should mention supported knowledge types
        help_text = result.output.lower()
        assert "feature" in help_text or "adr" in help_text or "knowledge" in help_text
