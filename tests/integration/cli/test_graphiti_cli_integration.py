"""
Integration tests for graphiti CLI commands with mocked Graphiti.

Coverage Target: >=80%
Test Count: 20+ tests

Test Coverage:
- Integration tests with mocked Graphiti client
- Full CLI workflow tests
- Parser registry integration
- Error recovery scenarios
- Multi-file processing workflows
"""

import asyncio
import json
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, Mock, patch, MagicMock

import pytest
from click.testing import CliRunner

from guardkit.cli.main import cli
from guardkit.cli.graphiti import graphiti
from guardkit.integrations.graphiti.parsers.base import ParseResult, EpisodeData
from guardkit.integrations.graphiti.parsers.registry import ParserRegistry
from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner with isolated environment."""
    return CliRunner()


@pytest.fixture
def mock_graphiti_client():
    """Create a fully mocked GraphitiClient for integration testing."""
    client = AsyncMock(spec=GraphitiClient)
    client.enabled = True
    client.config = GraphitiConfig(enabled=True)
    client.initialize = AsyncMock(return_value=True)
    client.close = AsyncMock()
    client.health_check = AsyncMock(return_value=True)

    # Track all added episodes
    added_episodes = []

    async def mock_add_episode(name, episode_body, group_id, metadata=None):
        episode_id = f"episode-{len(added_episodes)+1}"
        added_episodes.append({
            "id": episode_id,
            "name": name,
            "body": episode_body,
            "group_id": group_id,
            "metadata": metadata or {},
        })
        return episode_id

    client.add_episode = AsyncMock(side_effect=mock_add_episode)
    client._added_episodes = added_episodes
    return client


@pytest.fixture
def mock_parser_registry_with_parsers():
    """Create a mock ParserRegistry with realistic parsers."""
    registry = Mock(spec=ParserRegistry)

    # Create mock parsers for different types
    adr_parser = Mock()
    adr_parser.parser_type = "adr"
    adr_parser.supported_extensions = [".md"]

    def adr_parse(content, file_path):
        # Extract ADR number from filename or content
        adr_match = "ADR" if "ADR" in content.upper() else "doc"
        entity_id = Path(file_path).stem.lower()

        return ParseResult(
            episodes=[
                EpisodeData(
                    content=content[:200],  # First 200 chars
                    group_id="architecture_decisions",
                    entity_type="adr",
                    entity_id=entity_id,
                    metadata={
                        "file": file_path,
                        "type": "architecture_decision",
                    },
                )
            ],
            warnings=[],
            success=True,
        )

    adr_parser.parse = Mock(side_effect=adr_parse)
    adr_parser.can_parse = Mock(return_value=True)

    feature_parser = Mock()
    feature_parser.parser_type = "feature-spec"
    feature_parser.supported_extensions = [".md"]

    def feature_parse(content, file_path):
        return ParseResult(
            episodes=[
                EpisodeData(
                    content=content[:200],
                    group_id="feature_specs",
                    entity_type="feature",
                    entity_id=Path(file_path).stem.lower(),
                    metadata={"file": file_path},
                )
            ],
            warnings=[],
            success=True,
        )

    feature_parser.parse = Mock(side_effect=feature_parse)

    # Registry methods
    def get_parser(parser_type: Optional[str]):
        if parser_type == "adr":
            return adr_parser
        elif parser_type == "feature-spec":
            return feature_parser
        return None

    def detect_parser(file_path: str, content: str):
        if "ADR" in content.upper() or "ADR" in file_path.upper():
            return adr_parser
        elif "FEATURE" in content.upper() or "FEATURE" in file_path.upper():
            return feature_parser
        return adr_parser  # Default fallback

    registry.get_parser = Mock(side_effect=get_parser)
    registry.detect_parser = Mock(side_effect=detect_parser)
    registry._parsers = {"adr": adr_parser, "feature-spec": feature_parser}

    return registry, adr_parser, feature_parser


@pytest.fixture
def sample_adr_files(tmp_path):
    """Create sample ADR files for testing."""
    docs_dir = tmp_path / "docs" / "architecture"
    docs_dir.mkdir(parents=True)

    adr_contents = {
        "ADR-001.md": "# ADR-001: Use Event Sourcing\n\n## Status\nAccepted\n\n## Context\nWe need a reliable way to track state changes.\n\n## Decision\nUse event sourcing pattern.",
        "ADR-002.md": "# ADR-002: Use GraphQL API\n\n## Status\nAccepted\n\n## Context\nNeed flexible API for frontend.\n\n## Decision\nUse GraphQL.",
        "ADR-003.md": "# ADR-003: Microservices Architecture\n\n## Status\nProposed\n\n## Context\nNeed to scale independently.\n\n## Decision\nAdopt microservices.",
    }

    for filename, content in adr_contents.items():
        (docs_dir / filename).write_text(content)

    return docs_dir


@pytest.fixture
def sample_mixed_files(tmp_path):
    """Create mixed file types for testing."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)

    files = {
        "ADR-001.md": "# ADR-001: Decision\n\nContent here.",
        "FEATURE-001.md": "# Feature: User Auth\n\nFeature description.",
        "README.md": "# Project Overview\n\nGeneral documentation.",
        "CHANGELOG.md": "# Changelog\n\nVersion history.",
    }

    for filename, content in files.items():
        (docs_dir / filename).write_text(content)

    return docs_dir


# ============================================================================
# TEST CLASS: Full CLI Integration
# ============================================================================


class TestAddContextCLIIntegration:
    """Integration tests for add-context via main CLI."""

    def test_add_context_via_main_cli(self, cli_runner, sample_adr_files,
                                       mock_graphiti_client,
                                       mock_parser_registry_with_parsers):
        """Test add-context accessible via main guardkit CLI."""
        registry, adr_parser, _ = mock_parser_registry_with_parsers
        single_file = sample_adr_files / "ADR-001.md"

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                result = cli_runner.invoke(
                    cli,
                    ["graphiti", "add-context", str(single_file)],
                )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert mock_graphiti_client.add_episode.called

    def test_add_context_directory_via_main_cli(self, cli_runner, sample_adr_files,
                                                  mock_graphiti_client,
                                                  mock_parser_registry_with_parsers):
        """Test add-context with directory via main CLI."""
        registry, adr_parser, _ = mock_parser_registry_with_parsers

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                result = cli_runner.invoke(
                    cli,
                    ["graphiti", "add-context", str(sample_adr_files)],
                )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Should process all 3 ADR files
        assert mock_graphiti_client.add_episode.call_count == 3


class TestAddContextWithMockedGraphiti:
    """Integration tests with mocked Graphiti service."""

    def test_full_workflow_single_file(self, cli_runner, sample_adr_files,
                                        mock_graphiti_client,
                                        mock_parser_registry_with_parsers):
        """Test complete workflow for single file."""
        registry, adr_parser, _ = mock_parser_registry_with_parsers
        single_file = sample_adr_files / "ADR-001.md"

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(single_file)],
                )

        assert result.exit_code == 0
        # Verify workflow steps
        mock_graphiti_client.initialize.assert_called_once()
        mock_graphiti_client.add_episode.assert_called_once()
        mock_graphiti_client.close.assert_called_once()

        # Verify episode was added correctly
        added = mock_graphiti_client._added_episodes[0]
        assert added["group_id"] == "architecture_decisions"
        assert "adr-001" in added["name"].lower()

    def test_full_workflow_directory(self, cli_runner, sample_adr_files,
                                      mock_graphiti_client,
                                      mock_parser_registry_with_parsers):
        """Test complete workflow for directory."""
        registry, adr_parser, _ = mock_parser_registry_with_parsers

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(sample_adr_files)],
                )

        assert result.exit_code == 0
        # All 3 files processed
        assert mock_graphiti_client.add_episode.call_count == 3
        # Verify all episodes tracked
        assert len(mock_graphiti_client._added_episodes) == 3

    def test_workflow_with_type_override(self, cli_runner, sample_adr_files,
                                          mock_graphiti_client,
                                          mock_parser_registry_with_parsers):
        """Test workflow with --type flag."""
        registry, adr_parser, _ = mock_parser_registry_with_parsers
        single_file = sample_adr_files / "ADR-001.md"

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(single_file), "--type", "adr"],
                )

        assert result.exit_code == 0
        registry.get_parser.assert_called_with("adr")

    def test_workflow_with_verbose(self, cli_runner, sample_adr_files,
                                    mock_graphiti_client,
                                    mock_parser_registry_with_parsers):
        """Test workflow with --verbose flag."""
        registry, adr_parser, _ = mock_parser_registry_with_parsers
        single_file = sample_adr_files / "ADR-001.md"

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(single_file), "--verbose"],
                )

        assert result.exit_code == 0
        assert "Parsing" in result.output
        assert "Found" in result.output or "episode" in result.output.lower()


# ============================================================================
# TEST CLASS: Parser Registry Integration
# ============================================================================


class TestParserRegistryIntegration:
    """Integration tests for parser registry behavior."""

    def test_auto_detect_parser_by_content(self, cli_runner, sample_adr_files,
                                            mock_graphiti_client,
                                            mock_parser_registry_with_parsers):
        """Test parser auto-detection based on file content."""
        registry, adr_parser, _ = mock_parser_registry_with_parsers
        single_file = sample_adr_files / "ADR-001.md"

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(single_file)],
                )

        assert result.exit_code == 0
        # Auto-detection should have been called
        registry.detect_parser.assert_called()

    def test_parser_type_in_output(self, cli_runner, sample_adr_files,
                                    mock_graphiti_client,
                                    mock_parser_registry_with_parsers):
        """Test that parser type is shown in output."""
        registry, adr_parser, _ = mock_parser_registry_with_parsers
        single_file = sample_adr_files / "ADR-001.md"

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(single_file)],
                )

        assert result.exit_code == 0
        assert "adr" in result.output.lower()


# ============================================================================
# TEST CLASS: Error Recovery Scenarios
# ============================================================================


class TestErrorRecoveryIntegration:
    """Integration tests for error recovery scenarios."""

    def test_partial_failure_continues(self, cli_runner, sample_adr_files,
                                        mock_graphiti_client,
                                        mock_parser_registry_with_parsers):
        """Test that partial failures don't stop processing."""
        registry, adr_parser, _ = mock_parser_registry_with_parsers

        # Make second add_episode call fail
        call_count = [0]
        original_side_effect = mock_graphiti_client.add_episode.side_effect

        async def failing_add_episode(name, episode_body, group_id, metadata=None):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("Simulated failure")
            result = await original_side_effect(name, episode_body, group_id, metadata)
            return result

        mock_graphiti_client.add_episode.side_effect = failing_add_episode

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(sample_adr_files)],
                )

        # Should show error but also process other files
        assert "error" in result.output.lower()
        # All 3 files attempted
        assert call_count[0] == 3

    def test_connection_failure_graceful_exit(self, cli_runner, sample_adr_files):
        """Test graceful exit on connection failure."""
        mock_client = AsyncMock(spec=GraphitiClient)
        mock_client.initialize = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client.close = AsyncMock()

        single_file = sample_adr_files / "ADR-001.md"

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_client):
            result = cli_runner.invoke(
                graphiti,
                ["add-context", str(single_file)],
            )

        assert result.exit_code != 0
        assert "error" in result.output.lower()
        # Should still attempt to close
        mock_client.close.assert_called()

    def test_disabled_client_graceful_message(self, cli_runner, sample_adr_files):
        """Test graceful message when Graphiti is disabled."""
        mock_client = AsyncMock(spec=GraphitiClient)
        mock_client.enabled = False
        mock_client.initialize = AsyncMock(return_value=False)
        mock_client.close = AsyncMock()

        single_file = sample_adr_files / "ADR-001.md"

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_client):
            result = cli_runner.invoke(
                graphiti,
                ["add-context", str(single_file)],
            )

        assert result.exit_code != 0
        assert "failed" in result.output.lower() or "disabled" in result.output.lower()


# ============================================================================
# TEST CLASS: Multi-File Processing Workflows
# ============================================================================


class TestMultiFileWorkflows:
    """Integration tests for multi-file processing."""

    def test_directory_with_custom_pattern(self, cli_runner, sample_mixed_files,
                                            mock_graphiti_client,
                                            mock_parser_registry_with_parsers):
        """Test directory processing with custom glob pattern."""
        registry, adr_parser, _ = mock_parser_registry_with_parsers

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(sample_mixed_files), "--pattern", "ADR-*.md"],
                )

        assert result.exit_code == 0
        # Only ADR file should be processed
        assert mock_graphiti_client.add_episode.call_count == 1

    def test_directory_recursive_glob(self, cli_runner, tmp_path, mock_graphiti_client,
                                       mock_parser_registry_with_parsers):
        """Test recursive glob pattern processing."""
        registry, adr_parser, _ = mock_parser_registry_with_parsers

        # Create nested structure
        root = tmp_path / "docs"
        (root / "level1").mkdir(parents=True)
        (root / "level1" / "level2").mkdir()

        (root / "ADR-001.md").write_text("# ADR-001\n\nContent")
        (root / "level1" / "ADR-002.md").write_text("# ADR-002\n\nContent")
        (root / "level1" / "level2" / "ADR-003.md").write_text("# ADR-003\n\nContent")

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(root), "--pattern", "**/*.md"],
                )

        assert result.exit_code == 0
        # All 3 files at different levels should be processed
        assert mock_graphiti_client.add_episode.call_count == 3

    def test_dry_run_directory(self, cli_runner, sample_adr_files,
                                mock_graphiti_client,
                                mock_parser_registry_with_parsers):
        """Test dry-run with directory."""
        registry, adr_parser, _ = mock_parser_registry_with_parsers

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(sample_adr_files), "--dry-run"],
                )

        assert result.exit_code == 0
        # NO episodes should actually be added
        mock_graphiti_client.add_episode.assert_not_called()
        # Output should show what would be added
        assert "3" in result.output
        assert "would" in result.output.lower() or "dry" in result.output.lower()


# ============================================================================
# TEST CLASS: Episode Data Validation
# ============================================================================


class TestEpisodeDataValidation:
    """Integration tests for episode data validation."""

    def test_episode_content_passed_correctly(self, cli_runner, sample_adr_files,
                                               mock_graphiti_client,
                                               mock_parser_registry_with_parsers):
        """Test that episode content is passed correctly to Graphiti."""
        registry, adr_parser, _ = mock_parser_registry_with_parsers
        single_file = sample_adr_files / "ADR-001.md"

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(single_file)],
                )

        assert result.exit_code == 0
        # Verify episode was added with correct data
        assert len(mock_graphiti_client._added_episodes) == 1
        episode = mock_graphiti_client._added_episodes[0]
        assert episode["group_id"] == "architecture_decisions"
        assert "name" in episode
        assert "body" in episode

    def test_metadata_passed_correctly(self, cli_runner, sample_adr_files,
                                        mock_graphiti_client,
                                        mock_parser_registry_with_parsers):
        """Test that metadata is passed correctly to Graphiti."""
        registry, adr_parser, _ = mock_parser_registry_with_parsers
        single_file = sample_adr_files / "ADR-001.md"

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(single_file)],
                )

        assert result.exit_code == 0
        episode = mock_graphiti_client._added_episodes[0]
        assert "metadata" in episode
        assert episode["metadata"].get("file") is not None


# ============================================================================
# TEST CLASS: CLI Output Format
# ============================================================================


class TestCLIOutputFormat:
    """Integration tests for CLI output formatting."""

    def test_success_message_format(self, cli_runner, sample_adr_files,
                                     mock_graphiti_client,
                                     mock_parser_registry_with_parsers):
        """Test success message format."""
        registry, adr_parser, _ = mock_parser_registry_with_parsers
        single_file = sample_adr_files / "ADR-001.md"

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(single_file)],
                )

        assert result.exit_code == 0
        # Should show summary with counts
        assert "1" in result.output
        assert "file" in result.output.lower() or "episode" in result.output.lower()

    def test_verbose_output_format(self, cli_runner, sample_adr_files,
                                    mock_graphiti_client,
                                    mock_parser_registry_with_parsers):
        """Test verbose output format."""
        registry, adr_parser, _ = mock_parser_registry_with_parsers
        single_file = sample_adr_files / "ADR-001.md"

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(single_file), "--verbose"],
                )

        assert result.exit_code == 0
        # Verbose should show parsing info
        assert "Parsing" in result.output
        assert "adr" in result.output.lower()

    def test_quiet_output_format(self, cli_runner, sample_adr_files,
                                  mock_graphiti_client,
                                  mock_parser_registry_with_parsers):
        """Test quiet output format."""
        registry, adr_parser, _ = mock_parser_registry_with_parsers
        single_file = sample_adr_files / "ADR-001.md"

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(single_file), "--quiet"],
                )

        assert result.exit_code == 0
        # Quiet should suppress most output
        assert "Parsing" not in result.output


# ============================================================================
# TEST CLASS: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Integration tests for edge cases."""

    def test_empty_directory(self, cli_runner, tmp_path, mock_graphiti_client):
        """Test handling empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            result = cli_runner.invoke(
                graphiti,
                ["add-context", str(empty_dir)],
            )

        # Should complete but indicate no files
        assert "no files" in result.output.lower() or result.exit_code == 0

    def test_file_with_empty_content(self, cli_runner, tmp_path, mock_graphiti_client,
                                      mock_parser_registry_with_parsers):
        """Test handling file with empty content."""
        registry, adr_parser, _ = mock_parser_registry_with_parsers

        empty_file = tmp_path / "empty.md"
        empty_file.write_text("")

        # Make parser return empty result for empty content
        adr_parser.parse.return_value = ParseResult(episodes=[], warnings=[], success=True)
        registry.detect_parser.return_value = adr_parser

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(empty_file)],
                )

        # Should complete without error
        assert result.exit_code == 0

    def test_special_characters_in_path(self, cli_runner, tmp_path, mock_graphiti_client,
                                         mock_parser_registry_with_parsers):
        """Test handling paths with special characters."""
        registry, adr_parser, _ = mock_parser_registry_with_parsers

        special_dir = tmp_path / "docs (copy)"
        special_dir.mkdir()
        (special_dir / "ADR-001.md").write_text("# ADR-001\n\nContent")

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(special_dir)],
                )

        assert result.exit_code == 0
        mock_graphiti_client.add_episode.assert_called_once()
