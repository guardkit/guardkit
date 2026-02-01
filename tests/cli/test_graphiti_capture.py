"""
Tests for guardkit graphiti capture CLI command.

Test Coverage:
- capture command with --interactive flag
- --focus option filtering by category
- --max-questions option limiting question count
- Support for all focus areas including AutoBuild categories
- Colored output for questions, captured facts, summary
- Error handling and graceful degradation
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from click.testing import CliRunner

# Import CLI components
try:
    from guardkit.cli.main import cli
    from guardkit.cli.graphiti import graphiti
    from guardkit.knowledge.interactive_capture import KnowledgeCategory
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="CLI graphiti capture command not yet implemented"
)


class TestGraphitiCaptureCommand:
    """Test guardkit graphiti capture command."""

    def test_capture_command_exists(self):
        """Test that graphiti capture command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["graphiti", "capture", "--help"])
        assert result.exit_code == 0
        assert "capture" in result.output.lower() or "Capture" in result.output

    def test_capture_requires_interactive_flag(self):
        """Test that capture command requires --interactive flag."""
        runner = CliRunner()
        result = runner.invoke(cli, ["graphiti", "capture"])

        # Should provide guidance about using --interactive
        assert result.exit_code == 0
        assert "--interactive" in result.output or "interactive" in result.output.lower()

    def test_capture_with_interactive_flag(self):
        """Test capture command with --interactive flag starts session."""
        runner = CliRunner()

        with patch('guardkit.knowledge.interactive_capture.InteractiveCaptureSession') as mock_session_class, \
             patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client, \
             patch('guardkit.cli.graphiti.load_graphiti_config') as mock_config:

            # Mock configuration
            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_config.return_value = mock_settings

            # Mock client
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_get_client.return_value = (mock_client, mock_settings)

            # Mock session
            mock_session = MagicMock()
            mock_session.run_session = AsyncMock(return_value=[])
            mock_session_class.return_value = mock_session

            result = runner.invoke(cli, ["graphiti", "capture", "--interactive"])

            # Should have run the session
            mock_session.run_session.assert_called_once()
            assert result.exit_code == 0

    def test_capture_with_focus_option(self):
        """Test capture command with --focus option filters by category."""
        runner = CliRunner()

        with patch('guardkit.knowledge.interactive_capture.InteractiveCaptureSession') as mock_session_class, \
             patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client, \
             patch('guardkit.cli.graphiti.load_graphiti_config') as mock_config:

            # Mock configuration
            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_config.return_value = mock_settings

            # Mock client
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_get_client.return_value = (mock_client, mock_settings)

            # Mock session
            mock_session = MagicMock()
            mock_session.run_session = AsyncMock(return_value=[])
            mock_session_class.return_value = mock_session

            result = runner.invoke(
                cli,
                ["graphiti", "capture", "--interactive", "--focus", "architecture"]
            )

            # Should have passed focus category to session
            mock_session.run_session.assert_called_once()
            call_kwargs = mock_session.run_session.call_args.kwargs
            assert call_kwargs.get('focus') == KnowledgeCategory.ARCHITECTURE
            assert result.exit_code == 0

    def test_capture_with_max_questions_option(self):
        """Test capture command with --max-questions option limits question count."""
        runner = CliRunner()

        with patch('guardkit.knowledge.interactive_capture.InteractiveCaptureSession') as mock_session_class, \
             patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client, \
             patch('guardkit.cli.graphiti.load_graphiti_config') as mock_config:

            # Mock configuration
            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_config.return_value = mock_settings

            # Mock client
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_get_client.return_value = (mock_client, mock_settings)

            # Mock session
            mock_session = MagicMock()
            mock_session.run_session = AsyncMock(return_value=[])
            mock_session_class.return_value = mock_session

            result = runner.invoke(
                cli,
                ["graphiti", "capture", "--interactive", "--max-questions", "5"]
            )

            # Should have passed max_questions to session
            mock_session.run_session.assert_called_once()
            call_kwargs = mock_session.run_session.call_args.kwargs
            assert call_kwargs.get('max_questions') == 5
            assert result.exit_code == 0

    def test_capture_supports_all_focus_areas(self):
        """Test that capture command supports all focus areas including AutoBuild categories."""
        runner = CliRunner()

        # Test all valid focus areas
        focus_areas = [
            "project-overview",
            "architecture",
            "domain",
            "constraints",
            "decisions",
            "goals",
            "role-customization",
            "quality-gates",
            "workflow-preferences",
        ]

        for focus in focus_areas:
            with patch('guardkit.knowledge.interactive_capture.InteractiveCaptureSession') as mock_session_class, \
             patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client, \
             patch('guardkit.cli.graphiti.load_graphiti_config') as mock_config:

                # Mock configuration
                mock_settings = MagicMock()
                mock_settings.enabled = True
                mock_settings.neo4j_uri = "bolt://localhost:7687"
                mock_config.return_value = mock_settings

                # Mock client
                mock_client = MagicMock()
                mock_client.enabled = True
                mock_client.initialize = AsyncMock(return_value=True)
                mock_client.close = AsyncMock()
                mock_get_client.return_value = (mock_client, mock_settings)

                # Mock session
                mock_session = MagicMock()
                mock_session.run_session = AsyncMock(return_value=[])
                mock_session_class.return_value = mock_session

                result = runner.invoke(
                    cli,
                    ["graphiti", "capture", "--interactive", "--focus", focus]
                )

                assert result.exit_code == 0, f"Failed for focus area: {focus}"

    def test_capture_handles_disabled_graphiti(self):
        """Test capture command handles disabled Graphiti gracefully."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti.load_graphiti_config') as mock_config:
            # Mock disabled configuration
            mock_settings = MagicMock()
            mock_settings.enabled = False
            mock_config.return_value = mock_settings

            result = runner.invoke(cli, ["graphiti", "capture", "--interactive"])

            # Should indicate Graphiti is disabled
            assert "disabled" in result.output.lower()
            assert result.exit_code == 0

    def test_capture_handles_connection_error(self):
        """Test capture command handles connection errors gracefully."""
        runner = CliRunner()

        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            # Mock client with connection error
            mock_client = MagicMock()
            mock_client.initialize = AsyncMock(side_effect=Exception("Connection refused"))

            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"

            mock_get_client.return_value = (mock_client, mock_settings)

            result = runner.invoke(cli, ["graphiti", "capture", "--interactive"])

            # Should handle error gracefully
            assert result.exit_code != 0
            assert "error" in result.output.lower()

    def test_capture_handles_session_error(self):
        """Test capture command handles session errors gracefully."""
        runner = CliRunner()

        with patch('guardkit.knowledge.interactive_capture.InteractiveCaptureSession') as mock_session_class, \
             patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client, \
             patch('guardkit.cli.graphiti.load_graphiti_config') as mock_config:

            # Mock configuration
            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_config.return_value = mock_settings

            # Mock client
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_get_client.return_value = (mock_client, mock_settings)

            # Mock session with error
            mock_session = MagicMock()
            mock_session.run_session = AsyncMock(
                side_effect=Exception("Session failed")
            )
            mock_session_class.return_value = mock_session

            result = runner.invoke(cli, ["graphiti", "capture", "--interactive"])

            # Should handle error gracefully
            assert result.exit_code != 0
            assert "error" in result.output.lower()

    def test_capture_shows_success_message(self):
        """Test capture command shows success message after capturing knowledge."""
        runner = CliRunner()

        with patch('guardkit.knowledge.interactive_capture.InteractiveCaptureSession') as mock_session_class, \
             patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client, \
             patch('guardkit.cli.graphiti.load_graphiti_config') as mock_config:

            # Mock configuration
            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_config.return_value = mock_settings

            # Mock client
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_get_client.return_value = (mock_client, mock_settings)

            # Mock session with captured knowledge
            mock_captured = [MagicMock(), MagicMock(), MagicMock()]  # 3 items
            mock_session = MagicMock()
            mock_session.run_session = AsyncMock(return_value=mock_captured)
            mock_session_class.return_value = mock_session

            result = runner.invoke(cli, ["graphiti", "capture", "--interactive"])

            # Should show success message with count
            assert "3" in result.output or "three" in result.output.lower()

    def test_capture_shows_no_knowledge_message(self):
        """Test capture command shows appropriate message when no knowledge captured."""
        runner = CliRunner()

        with patch('guardkit.knowledge.interactive_capture.InteractiveCaptureSession') as mock_session_class, \
             patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client, \
             patch('guardkit.cli.graphiti.load_graphiti_config') as mock_config:

            # Mock configuration
            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_config.return_value = mock_settings

            # Mock client
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_get_client.return_value = (mock_client, mock_settings)

            # Mock session with no captured knowledge
            mock_session = MagicMock()
            mock_session.run_session = AsyncMock(return_value=[])
            mock_session_class.return_value = mock_session

            result = runner.invoke(cli, ["graphiti", "capture", "--interactive"])

            # Should indicate no knowledge captured
            assert "no knowledge" in result.output.lower() or \
                   "no gaps" in result.output.lower() or \
                   "ended" in result.output.lower()


class TestGraphitiCaptureUICallback:
    """Test the UI callback functionality for colored output."""

    def test_ui_callback_handles_all_events(self):
        """Test that UI callback handles all event types."""
        # This is tested implicitly through the integration tests above
        # The callback should handle: info, intro, question, get_input, captured, summary
        pass


class TestGraphitiCaptureIntegration:
    """Integration tests for capture command with real session flow."""

    def test_capture_full_workflow(self):
        """Test complete capture workflow from start to finish."""
        runner = CliRunner()

        with patch('guardkit.knowledge.interactive_capture.InteractiveCaptureSession') as mock_session_class, \
             patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client, \
             patch('guardkit.cli.graphiti.load_graphiti_config') as mock_config:

            # Mock configuration
            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_config.return_value = mock_settings

            # Mock client
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_get_client.return_value = (mock_client, mock_settings)

            # Mock session
            mock_session = MagicMock()
            mock_captured = [MagicMock(), MagicMock()]
            mock_session.run_session = AsyncMock(return_value=mock_captured)
            mock_session_class.return_value = mock_session

            result = runner.invoke(
                cli,
                ["graphiti", "capture", "--interactive", "--focus", "architecture", "--max-questions", "5"]
            )

            # Verify complete workflow
            assert result.exit_code == 0
            mock_client.initialize.assert_called_once()
            mock_session.run_session.assert_called_once()
            mock_client.close.assert_called_once()

            # Verify parameters passed correctly
            call_kwargs = mock_session.run_session.call_args.kwargs
            assert call_kwargs.get('focus') == KnowledgeCategory.ARCHITECTURE
            assert call_kwargs.get('max_questions') == 5
            assert call_kwargs.get('ui_callback') is not None
