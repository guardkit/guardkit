"""
Unit tests for guardkit graphiti add-context CLI command.

Coverage Target: >=80%
Test Count: 25+ tests

Test Coverage:
- Unit tests for command logic
- Tests for all flags (--type, --force, --dry-run, --verbose, --quiet, --pattern)
- Error handling tests
- Parser registry interaction tests
- GraphitiClient interaction tests
"""

import asyncio
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, Mock, patch, mock_open, MagicMock

import pytest
from click.testing import CliRunner

from guardkit.cli.graphiti import graphiti, add_context, _cmd_add_context
from guardkit.integrations.graphiti.parsers.base import ParseResult, EpisodeData
from guardkit.integrations.graphiti.parsers.registry import ParserRegistry
from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_graphiti_client():
    """Create a mock GraphitiClient instance."""
    client = AsyncMock(spec=GraphitiClient)
    client.enabled = True
    client.config = GraphitiConfig(enabled=True)
    client.initialize = AsyncMock(return_value=True)
    client.close = AsyncMock()

    # Episode counter for unique IDs
    episode_counter = [0]

    async def mock_add_episode(name, episode_body, group_id, **kwargs):
        episode_counter[0] += 1
        return f"episode-uuid-{episode_counter[0]}"

    client.add_episode = AsyncMock(side_effect=mock_add_episode)
    return client


@pytest.fixture
def mock_disabled_client():
    """Create a mock disabled GraphitiClient."""
    client = AsyncMock(spec=GraphitiClient)
    client.enabled = False
    client.config = GraphitiConfig(enabled=False)
    client.initialize = AsyncMock(return_value=False)
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_parser():
    """Create a mock parser."""
    parser = Mock()
    parser.parser_type = "adr"
    parser.supported_extensions = [".md"]
    return parser


@pytest.fixture
def mock_parser_registry(mock_parser):
    """Create a mock ParserRegistry."""
    registry = Mock(spec=ParserRegistry)

    def get_parser(parser_type: Optional[str]):
        if parser_type == "adr":
            return mock_parser
        elif parser_type == "feature-spec":
            feature_parser = Mock()
            feature_parser.parser_type = "feature-spec"
            return feature_parser
        return None

    registry.get_parser = Mock(side_effect=get_parser)
    registry.detect_parser = Mock(return_value=mock_parser)
    return registry


@pytest.fixture
def sample_parse_result():
    """Create a sample successful ParseResult."""
    episode = EpisodeData(
        content="Test content for ADR-001",
        group_id="architecture_decisions",
        entity_type="adr",
        entity_id="adr-001",
        metadata={"source": "test", "title": "ADR-001"},
    )
    return ParseResult(
        episodes=[episode],
        warnings=[],
        success=True,
    )


@pytest.fixture
def tmp_file(tmp_path):
    """Create a temporary markdown file for testing."""
    test_file = tmp_path / "ADR-001.md"
    test_file.write_text("# ADR-001: Test Decision\n\nTest content.")
    return test_file


@pytest.fixture
def tmp_dir(tmp_path):
    """Create a temporary directory with markdown files."""
    (tmp_path / "ADR-001.md").write_text("# ADR-001\n\nContent 1")
    (tmp_path / "ADR-002.md").write_text("# ADR-002\n\nContent 2")
    (tmp_path / "README.md").write_text("# README\n\nProject info")
    return tmp_path


# ============================================================================
# TEST CLASS: Command Existence and Help
# ============================================================================


class TestAddContextCommandExists:
    """Test that add-context command is properly registered."""

    def test_add_context_command_exists(self, cli_runner):
        """Test that add-context command is registered."""
        result = cli_runner.invoke(graphiti, ["add-context", "--help"])
        assert result.exit_code == 0
        assert "add-context" in result.output.lower() or "Add context" in result.output

    def test_add_context_shows_options(self, cli_runner):
        """Test that add-context --help shows all required options."""
        result = cli_runner.invoke(graphiti, ["add-context", "--help"])
        assert result.exit_code == 0
        # Verify all options are documented
        assert "--type" in result.output
        assert "--force" in result.output
        assert "--dry-run" in result.output
        assert "--pattern" in result.output
        assert "--verbose" in result.output
        assert "--quiet" in result.output

    def test_add_context_shows_examples(self, cli_runner):
        """Test that help includes usage examples."""
        result = cli_runner.invoke(graphiti, ["add-context", "--help"])
        assert result.exit_code == 0
        # Should show examples section
        assert "example" in result.output.lower() or "Examples" in result.output


# ============================================================================
# TEST CLASS: Single File Processing
# ============================================================================


class TestAddContextSingleFile:
    """Test add-context with single file."""

    def test_add_single_file(self, cli_runner, tmp_file, mock_graphiti_client,
                             mock_parser_registry, mock_parser, sample_parse_result):
        """Test adding single file."""
        mock_parser.parse.return_value = sample_parse_result

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(tmp_file)],
                )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "1 file" in result.output or "1 episode" in result.output
        mock_parser.parse.assert_called_once()
        mock_graphiti_client.add_episode.assert_called_once()
        mock_graphiti_client.close.assert_called_once()

    def test_add_single_file_with_type_override(self, cli_runner, tmp_file,
                                                 mock_graphiti_client, mock_parser_registry,
                                                 mock_parser, sample_parse_result):
        """Test --type flag overrides auto-detection."""
        mock_parser.parse.return_value = sample_parse_result

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(tmp_file), "--type", "adr"],
                )

        assert result.exit_code == 0
        mock_parser_registry.get_parser.assert_called_with("adr")
        # detect_parser should NOT be called when --type is specified
        mock_parser_registry.detect_parser.assert_not_called()

    def test_add_single_file_file_not_found(self, cli_runner, tmp_path, mock_graphiti_client):
        """Test error when file does not exist."""
        nonexistent = tmp_path / "nonexistent.md"

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            result = cli_runner.invoke(
                graphiti,
                ["add-context", str(nonexistent)],
            )

        assert result.exit_code != 0
        assert "not exist" in result.output.lower() or "error" in result.output.lower()


# ============================================================================
# TEST CLASS: Directory Processing
# ============================================================================


class TestAddContextDirectory:
    """Test add-context with directory."""

    def test_add_directory(self, cli_runner, tmp_dir, mock_graphiti_client,
                           mock_parser_registry, mock_parser, sample_parse_result):
        """Test adding directory with pattern."""
        mock_parser.parse.return_value = sample_parse_result

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(tmp_dir)],
                )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Should process all 3 .md files
        assert mock_parser.parse.call_count == 3
        assert mock_graphiti_client.add_episode.call_count == 3

    def test_add_directory_with_custom_pattern(self, cli_runner, tmp_dir,
                                                mock_graphiti_client, mock_parser_registry,
                                                mock_parser, sample_parse_result):
        """Test --pattern flag for custom glob."""
        mock_parser.parse.return_value = sample_parse_result

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(tmp_dir), "--pattern", "ADR-*.md"],
                )

        assert result.exit_code == 0
        # Should only process ADR files, not README
        assert mock_parser.parse.call_count == 2

    def test_add_directory_no_matching_files(self, cli_runner, tmp_path, mock_graphiti_client):
        """Test handling when no files match pattern."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            result = cli_runner.invoke(
                graphiti,
                ["add-context", str(empty_dir)],
            )

        # Should complete but indicate no files found
        assert "no files" in result.output.lower() or result.exit_code == 0


# ============================================================================
# TEST CLASS: Dry-Run Mode
# ============================================================================


class TestAddContextDryRun:
    """Test --dry-run flag."""

    def test_dry_run(self, cli_runner, tmp_file, mock_graphiti_client,
                     mock_parser_registry, mock_parser, sample_parse_result):
        """Test dry-run mode."""
        mock_parser.parse.return_value = sample_parse_result

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(tmp_file), "--dry-run"],
                )

        assert result.exit_code == 0
        # Should NOT actually add episodes
        mock_graphiti_client.add_episode.assert_not_called()
        # Should show what would be added
        assert "would" in result.output.lower() or "dry" in result.output.lower()

    def test_dry_run_with_directory(self, cli_runner, tmp_dir, mock_graphiti_client,
                                     mock_parser_registry, mock_parser, sample_parse_result):
        """Test dry-run with directory processing."""
        mock_parser.parse.return_value = sample_parse_result

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(tmp_dir), "--dry-run"],
                )

        assert result.exit_code == 0
        mock_graphiti_client.add_episode.assert_not_called()
        # Should show count of files/episodes that would be added
        assert "3" in result.output


# ============================================================================
# TEST CLASS: Force Flag
# ============================================================================


class TestAddContextForceFlag:
    """Test --force flag."""

    def test_force_overwrite(self, cli_runner, tmp_file, mock_graphiti_client,
                              mock_parser_registry, mock_parser, sample_parse_result):
        """Test --force flag."""
        mock_parser.parse.return_value = sample_parse_result

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(tmp_file), "--force"],
                )

        assert result.exit_code == 0
        # Force should still add episodes
        mock_graphiti_client.add_episode.assert_called_once()


# ============================================================================
# TEST CLASS: Type Override
# ============================================================================


class TestAddContextTypeFlag:
    """Test --type flag."""

    def test_type_override(self, cli_runner, tmp_file, mock_graphiti_client,
                           mock_parser_registry, mock_parser, sample_parse_result):
        """Test --type flag."""
        mock_parser.parse.return_value = sample_parse_result

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(tmp_file), "--type", "adr"],
                )

        assert result.exit_code == 0
        mock_parser_registry.get_parser.assert_called_with("adr")

    def test_type_unknown_parser(self, cli_runner, tmp_file, mock_graphiti_client,
                                  mock_parser_registry):
        """Test --type with unknown parser type."""
        mock_parser_registry.get_parser.return_value = None

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(tmp_file), "--type", "unknown-type"],
                )

        # Should show warning about unknown parser
        assert "no parser" in result.output.lower() or result.exit_code == 0


# ============================================================================
# TEST CLASS: Unsupported Files
# ============================================================================


class TestAddContextUnsupportedFiles:
    """Test handling unsupported files."""

    def test_unsupported_file(self, cli_runner, tmp_path, mock_graphiti_client,
                               mock_parser_registry):
        """Test handling unsupported files."""
        # Create a file that no parser can handle
        unsupported = tmp_path / "data.xyz"
        unsupported.write_text("random content")

        mock_parser_registry.detect_parser.return_value = None

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(unsupported)],
                )

        # Should show warning about unsupported file
        assert "unsupported" in result.output.lower() or "no parser" in result.output.lower()
        mock_graphiti_client.add_episode.assert_not_called()


# ============================================================================
# TEST CLASS: Error Handling
# ============================================================================


class TestAddContextErrorHandling:
    """Tests for error handling."""

    def test_graphiti_unavailable(self, cli_runner, tmp_file, mock_disabled_client):
        """Test graceful degradation when Graphiti unavailable."""
        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_disabled_client):
            result = cli_runner.invoke(
                graphiti,
                ["add-context", str(tmp_file)],
            )

        assert result.exit_code != 0
        assert "failed" in result.output.lower() or "disabled" in result.output.lower()

    def test_graphiti_connection_error(self, cli_runner, tmp_file):
        """Test handling Graphiti connection errors."""
        mock_client = AsyncMock(spec=GraphitiClient)
        mock_client.initialize = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client.close = AsyncMock()

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_client):
            result = cli_runner.invoke(
                graphiti,
                ["add-context", str(tmp_file)],
            )

        assert result.exit_code != 0
        assert "error" in result.output.lower()

    def test_add_episode_error_continues_processing(self, cli_runner, tmp_dir,
                                                      mock_graphiti_client,
                                                      mock_parser_registry,
                                                      mock_parser, sample_parse_result):
        """Test that add_episode error doesn't stop processing other files."""
        mock_parser.parse.return_value = sample_parse_result

        # First call succeeds, second fails, third succeeds
        mock_graphiti_client.add_episode.side_effect = [
            "uuid-1",
            Exception("Add episode failed"),
            "uuid-3",
        ]

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(tmp_dir)],
                )

        # Should complete (exit code 0) but show errors
        assert "error" in result.output.lower()
        # Should have attempted all 3 files
        assert mock_graphiti_client.add_episode.call_count == 3

    def test_parse_error_continues_processing(self, cli_runner, tmp_dir,
                                               mock_graphiti_client,
                                               mock_parser_registry,
                                               mock_parser):
        """Test that parse error doesn't stop processing other files."""
        success_result = ParseResult(
            episodes=[EpisodeData(
                content="Success",
                group_id="test",
                entity_type="adr",
                entity_id="test-1",
                metadata={},
            )],
            warnings=[],
            success=True,
        )

        failure_result = ParseResult(
            episodes=[],
            warnings=["Parse error"],
            success=False,
        )

        # First succeeds, second fails, third succeeds
        mock_parser.parse.side_effect = [success_result, failure_result, success_result]

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(tmp_dir)],
                )

        # Should show both successes and failures
        assert mock_parser.parse.call_count == 3
        # Only 2 episodes should be added (first and third)
        assert mock_graphiti_client.add_episode.call_count == 2


# ============================================================================
# TEST CLASS: Verbose and Quiet Flags
# ============================================================================


class TestAddContextVerboseQuiet:
    """Test --verbose and --quiet flags."""

    def test_verbose_flag(self, cli_runner, tmp_file, mock_graphiti_client,
                          mock_parser_registry, mock_parser, sample_parse_result):
        """Test --verbose shows detailed output."""
        mock_parser.parse.return_value = sample_parse_result

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(tmp_file), "--verbose"],
                )

        assert result.exit_code == 0
        # Should show parsing details
        assert "Parsing" in result.output
        assert "Found" in result.output or "episode" in result.output

    def test_quiet_flag(self, cli_runner, tmp_file, mock_graphiti_client,
                        mock_parser_registry, mock_parser, sample_parse_result):
        """Test --quiet suppresses non-error output."""
        mock_parser.parse.return_value = sample_parse_result

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(tmp_file), "--quiet"],
                )

        assert result.exit_code == 0
        # Should NOT show verbose messages
        assert "Parsing" not in result.output
        assert "Found" not in result.output

    def test_verbose_and_quiet_mutual_exclusivity(self, cli_runner, tmp_file):
        """Test that --verbose and --quiet cannot be used together."""
        result = cli_runner.invoke(
            graphiti,
            ["add-context", str(tmp_file), "--verbose", "--quiet"],
        )

        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()

    def test_quiet_still_shows_errors(self, cli_runner, tmp_file, mock_graphiti_client,
                                       mock_parser_registry, mock_parser):
        """Test --quiet still shows error messages."""
        # Create parse result with errors
        error_result = ParseResult(
            episodes=[],
            warnings=["Parse error: Invalid format"],
            success=False,
        )
        mock_parser.parse.return_value = error_result

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(tmp_file), "--quiet"],
                )

        # Should still show error/warning
        assert "error" in result.output.lower() or "warning" in result.output.lower()


# ============================================================================
# TEST CLASS: Summary Output
# ============================================================================


class TestAddContextSummaryOutput:
    """Test summary output format."""

    def test_summary_shows_file_and_episode_counts(self, cli_runner, tmp_dir,
                                                    mock_graphiti_client,
                                                    mock_parser_registry,
                                                    mock_parser, sample_parse_result):
        """Test summary shows file and episode counts."""
        mock_parser.parse.return_value = sample_parse_result

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(tmp_dir)],
                )

        assert result.exit_code == 0
        # Should show counts in summary
        assert "3" in result.output  # 3 files or episodes
        assert "file" in result.output.lower() or "episode" in result.output.lower()

    def test_summary_shows_warnings(self, cli_runner, tmp_file, mock_graphiti_client,
                                     mock_parser_registry, mock_parser):
        """Test summary shows parser warnings."""
        result_with_warning = ParseResult(
            episodes=[EpisodeData(
                content="Content",
                group_id="test",
                entity_type="adr",
                entity_id="test-1",
                metadata={},
            )],
            warnings=["Warning: Missing metadata field"],
            success=True,
        )
        mock_parser.parse.return_value = result_with_warning

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                result = cli_runner.invoke(
                    graphiti,
                    ["add-context", str(tmp_file)],
                )

        assert result.exit_code == 0
        # Should show warnings
        assert "Warning" in result.output


# ============================================================================
# TEST CLASS: Async Command Implementation
# ============================================================================


class TestCmdAddContextAsync:
    """Test the async _cmd_add_context implementation directly."""

    @pytest.mark.asyncio
    async def test_cmd_add_context_basic(self, tmp_file, mock_graphiti_client,
                                          mock_parser_registry, mock_parser,
                                          sample_parse_result):
        """Test _cmd_add_context async function."""
        mock_parser.parse.return_value = sample_parse_result

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                await _cmd_add_context(
                    path=str(tmp_file),
                    parser_type=None,
                    force=False,
                    dry_run=False,
                    pattern="**/*.md",
                    verbose=False,
                    quiet=False,
                )

        mock_graphiti_client.initialize.assert_called_once()
        mock_graphiti_client.add_episode.assert_called_once()
        mock_graphiti_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_add_context_dry_run(self, tmp_file, mock_graphiti_client,
                                            mock_parser_registry, mock_parser,
                                            sample_parse_result):
        """Test _cmd_add_context with dry_run=True."""
        mock_parser.parse.return_value = sample_parse_result

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                await _cmd_add_context(
                    path=str(tmp_file),
                    parser_type=None,
                    force=False,
                    dry_run=True,
                    pattern="**/*.md",
                    verbose=False,
                    quiet=False,
                )

        # Should NOT add episodes in dry-run mode
        mock_graphiti_client.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_cmd_add_context_file_not_found(self, tmp_path):
        """Test _cmd_add_context with non-existent file."""
        nonexistent = tmp_path / "nonexistent.md"

        with pytest.raises(SystemExit):
            await _cmd_add_context(
                path=str(nonexistent),
                parser_type=None,
                force=False,
                dry_run=False,
                pattern="**/*.md",
                verbose=False,
                quiet=False,
            )

    @pytest.mark.asyncio
    async def test_cmd_add_context_connection_failure(self, tmp_file):
        """Test _cmd_add_context handles connection failure."""
        mock_client = AsyncMock(spec=GraphitiClient)
        mock_client.initialize = AsyncMock(side_effect=Exception("Connection failed"))
        mock_client.close = AsyncMock()

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_client):
            with pytest.raises(SystemExit):
                await _cmd_add_context(
                    path=str(tmp_file),
                    parser_type=None,
                    force=False,
                    dry_run=False,
                    pattern="**/*.md",
                    verbose=False,
                    quiet=False,
                )
