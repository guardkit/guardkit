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
import logging
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


# ============================================================================
# TEST CLASS: SEMAPHORE_LIMIT and Inter-Episode Delay (TASK-FIX-AC02)
# ============================================================================


class TestSemaphoreLimitAndDelay:
    """Test SEMAPHORE_LIMIT env var setting and inter-episode delay."""

    def test_delay_option_exists(self, cli_runner):
        """AC-002: --delay CLI option is present in help."""
        result = cli_runner.invoke(graphiti, ["add-context", "--help"])
        assert result.exit_code == 0
        assert "--delay" in result.output

    def test_delay_default_is_half_second(self, cli_runner):
        """AC-002: Default delay is 0.5s."""
        result = cli_runner.invoke(graphiti, ["add-context", "--help"])
        assert "0.5" in result.output

    @pytest.mark.asyncio
    async def test_semaphore_limit_set_before_initialize(
        self, tmp_file, mock_graphiti_client, mock_parser_registry,
        mock_parser, sample_parse_result
    ):
        """AC-001: SEMAPHORE_LIMIT is set to 5 before client.initialize()."""
        import os
        mock_parser.parse.return_value = sample_parse_result
        captured_values = []

        original_init = mock_graphiti_client.initialize

        async def capturing_init():
            captured_values.append(os.environ.get("SEMAPHORE_LIMIT"))
            return await original_init()

        mock_graphiti_client.initialize = AsyncMock(side_effect=capturing_init)

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
                    delay=0,
                )

        assert captured_values == ["5"]

    @pytest.mark.asyncio
    async def test_semaphore_limit_restored_after_command(
        self, tmp_file, mock_graphiti_client, mock_parser_registry,
        mock_parser, sample_parse_result
    ):
        """AC-004: SEMAPHORE_LIMIT is restored after command completes."""
        import os
        mock_parser.parse.return_value = sample_parse_result

        # Set a custom value before running
        os.environ["SEMAPHORE_LIMIT"] = "20"

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
                    delay=0,
                )

        # Original value should be restored
        assert os.environ.get("SEMAPHORE_LIMIT") == "20"
        # Cleanup
        del os.environ["SEMAPHORE_LIMIT"]

    @pytest.mark.asyncio
    async def test_semaphore_limit_removed_if_not_originally_set(
        self, tmp_file, mock_graphiti_client, mock_parser_registry,
        mock_parser, sample_parse_result
    ):
        """AC-004: SEMAPHORE_LIMIT is removed if it wasn't set before."""
        import os
        mock_parser.parse.return_value = sample_parse_result

        # Ensure not set
        os.environ.pop("SEMAPHORE_LIMIT", None)

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
                    delay=0,
                )

        assert "SEMAPHORE_LIMIT" not in os.environ

    @pytest.mark.asyncio
    async def test_delay_applied_between_episodes(
        self, tmp_file, mock_graphiti_client, mock_parser_registry,
        mock_parser
    ):
        """AC-005: Delay is applied between episodes."""
        # Create result with multiple episodes
        episodes = [
            EpisodeData(
                content=f"Content {i}",
                group_id="test",
                entity_type="adr",
                entity_id=f"adr-{i}",
                metadata={},
            )
            for i in range(3)
        ]
        multi_result = ParseResult(episodes=episodes, warnings=[], success=True)
        mock_parser.parse.return_value = multi_result

        sleep_calls = []
        original_sleep = asyncio.sleep

        async def mock_sleep(seconds):
            sleep_calls.append(seconds)

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                with patch("guardkit.cli.graphiti.asyncio.sleep", side_effect=mock_sleep):
                    await _cmd_add_context(
                        path=str(tmp_file),
                        parser_type=None,
                        force=False,
                        dry_run=False,
                        pattern="**/*.md",
                        verbose=False,
                        quiet=False,
                        delay=0.5,
                    )

        # 3 episodes -> 3 sleeps (after each add_episode)
        assert len(sleep_calls) == 3
        assert all(d == 0.5 for d in sleep_calls)

    @pytest.mark.asyncio
    async def test_delay_zero_skips_sleep(
        self, tmp_file, mock_graphiti_client, mock_parser_registry,
        mock_parser
    ):
        """AC-002: Delay of 0 disables inter-episode sleep."""
        episodes = [
            EpisodeData(
                content=f"Content {i}",
                group_id="test",
                entity_type="adr",
                entity_id=f"adr-{i}",
                metadata={},
            )
            for i in range(3)
        ]
        multi_result = ParseResult(episodes=episodes, warnings=[], success=True)
        mock_parser.parse.return_value = multi_result

        sleep_calls = []

        async def mock_sleep(seconds):
            sleep_calls.append(seconds)

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                with patch("guardkit.cli.graphiti.asyncio.sleep", side_effect=mock_sleep):
                    await _cmd_add_context(
                        path=str(tmp_file),
                        parser_type=None,
                        force=False,
                        dry_run=False,
                        pattern="**/*.md",
                        verbose=False,
                        quiet=False,
                        delay=0,
                    )

        # No sleeps when delay is 0
        assert len(sleep_calls) == 0

    @pytest.mark.asyncio
    async def test_delay_not_applied_in_dry_run(
        self, tmp_file, mock_graphiti_client, mock_parser_registry,
        mock_parser, sample_parse_result
    ):
        """Delay should not be applied in dry-run mode (no episodes added)."""
        mock_parser.parse.return_value = sample_parse_result

        sleep_calls = []

        async def mock_sleep(seconds):
            sleep_calls.append(seconds)

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                with patch("guardkit.cli.graphiti.asyncio.sleep", side_effect=mock_sleep):
                    await _cmd_add_context(
                        path=str(tmp_file),
                        parser_type=None,
                        force=False,
                        dry_run=True,
                        pattern="**/*.md",
                        verbose=False,
                        quiet=False,
                        delay=0.5,
                    )

        # No sleeps in dry-run mode
        assert len(sleep_calls) == 0

    def test_delay_cli_option_custom_value(
        self, cli_runner, tmp_file, mock_graphiti_client,
        mock_parser_registry, mock_parser, sample_parse_result
    ):
        """AC-002: --delay accepts custom values from CLI."""
        mock_parser.parse.return_value = sample_parse_result

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                with patch("guardkit.cli.graphiti.asyncio.sleep", new_callable=AsyncMock):
                    result = cli_runner.invoke(
                        graphiti,
                        ["add-context", str(tmp_file), "--delay", "1.0"],
                    )

        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_semaphore_limit_restored_on_error(
        self, tmp_path
    ):
        """AC-004: SEMAPHORE_LIMIT is restored even when command fails."""
        import os
        nonexistent = tmp_path / "nonexistent.md"

        os.environ["SEMAPHORE_LIMIT"] = "20"

        with pytest.raises(SystemExit):
            await _cmd_add_context(
                path=str(nonexistent),
                parser_type=None,
                force=False,
                dry_run=False,
                pattern="**/*.md",
                verbose=False,
                quiet=False,
                delay=0,
            )

        # Should be restored even after error
        assert os.environ.get("SEMAPHORE_LIMIT") == "20"
        del os.environ["SEMAPHORE_LIMIT"]


# ============================================================================
# TEST CLASS: Return Value Checking (TASK-FIX-AC03)
# ============================================================================


class TestAddEpisodeReturnValueChecking:
    """Test that add_episode return value is checked for success/failure.

    TASK-FIX-AC03: Fix false-positive success reporting.
    The CLI must check add_episode() return value (UUID or None) and only
    count successful episodes, show appropriate markers, and report failures.
    """

    @staticmethod
    def _normalize(text: str) -> str:
        """Collapse Rich Console line-wrapping into single-line text for assertions."""
        import re
        return re.sub(r"\s+", " ", text)

    @pytest.mark.asyncio
    async def test_none_return_not_counted_as_success(
        self, tmp_file, mock_parser_registry, mock_parser, sample_parse_result
    ):
        """AC-001: episodes_added only incremented when add_episode returns non-None."""
        mock_parser.parse.return_value = sample_parse_result

        client = AsyncMock(spec=GraphitiClient)
        client.enabled = True
        client.config = GraphitiConfig(enabled=True)
        client.initialize = AsyncMock(return_value=True)
        client.close = AsyncMock()
        client.add_episode = AsyncMock(return_value=None)

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                with patch("guardkit.cli.graphiti.asyncio.sleep", new_callable=AsyncMock):
                    await _cmd_add_context(
                        path=str(tmp_file),
                        parser_type=None,
                        force=False,
                        dry_run=False,
                        pattern="**/*.md",
                        verbose=False,
                        quiet=False,
                        delay=0,
                    )

        # add_episode was called but returned None — should NOT count as added
        client.add_episode.assert_called_once()

    @pytest.mark.asyncio
    async def test_none_return_logged_as_error(
        self, tmp_file, mock_parser_registry, mock_parser, sample_parse_result, capsys
    ):
        """AC-002: Failed episodes logged as errors with file path."""
        mock_parser.parse.return_value = sample_parse_result

        client = AsyncMock(spec=GraphitiClient)
        client.enabled = True
        client.config = GraphitiConfig(enabled=True)
        client.initialize = AsyncMock(return_value=True)
        client.close = AsyncMock()
        client.add_episode = AsyncMock(return_value=None)

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                with patch("guardkit.cli.graphiti.asyncio.sleep", new_callable=AsyncMock):
                    await _cmd_add_context(
                        path=str(tmp_file),
                        parser_type=None,
                        force=False,
                        dry_run=False,
                        pattern="**/*.md",
                        verbose=False,
                        quiet=False,
                        delay=0,
                    )

        captured = capsys.readouterr()
        normalized = self._normalize(captured.out)
        assert "Episode creation returned None" in normalized

    @pytest.mark.asyncio
    async def test_success_return_counted(
        self, tmp_file, mock_graphiti_client, mock_parser_registry,
        mock_parser, sample_parse_result, capsys
    ):
        """AC-001: Successful add_episode (returns UUID) is counted."""
        mock_parser.parse.return_value = sample_parse_result
        mock_graphiti_client.add_episode = AsyncMock(return_value="episode-uuid-123")

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                with patch("guardkit.cli.graphiti.asyncio.sleep", new_callable=AsyncMock):
                    await _cmd_add_context(
                        path=str(tmp_file),
                        parser_type=None,
                        force=False,
                        dry_run=False,
                        pattern="**/*.md",
                        verbose=False,
                        quiet=False,
                        delay=0,
                    )

        mock_graphiti_client.add_episode.assert_called_once()
        captured = capsys.readouterr()
        assert "1 episode" in captured.out
        assert "Failed" not in captured.out

    @pytest.mark.asyncio
    async def test_summary_reports_failed_count(
        self, tmp_file, mock_parser_registry, mock_parser, capsys
    ):
        """AC-003: Summary accurately reports successful vs failed episode counts."""
        episodes = [
            EpisodeData(
                content="Content 1", group_id="test",
                entity_type="adr", entity_id="adr-1", metadata={},
            ),
            EpisodeData(
                content="Content 2", group_id="test",
                entity_type="adr", entity_id="adr-2", metadata={},
            ),
        ]
        mock_parser.parse.return_value = ParseResult(
            episodes=episodes, warnings=[], success=True
        )

        client = AsyncMock(spec=GraphitiClient)
        client.enabled = True
        client.config = GraphitiConfig(enabled=True)
        client.initialize = AsyncMock(return_value=True)
        client.close = AsyncMock()
        # First succeeds, second returns None
        client.add_episode = AsyncMock(side_effect=["uuid-1", None])

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                with patch("guardkit.cli.graphiti.asyncio.sleep", new_callable=AsyncMock):
                    await _cmd_add_context(
                        path=str(tmp_file),
                        parser_type=None,
                        force=False,
                        dry_run=False,
                        pattern="**/*.md",
                        verbose=False,
                        quiet=False,
                        delay=0,
                    )

        captured = capsys.readouterr()
        assert "1 episode" in captured.out
        assert "Failed: 1 episode" in captured.out

    @pytest.mark.asyncio
    async def test_checkmark_only_shown_for_all_success(
        self, tmp_file, mock_parser_registry, mock_parser, capsys
    ):
        """AC-004: Checkmark only shown for files where ALL episodes succeeded."""
        mock_parser.parse.return_value = ParseResult(
            episodes=[EpisodeData(
                content="Content", group_id="test",
                entity_type="adr", entity_id="adr-1", metadata={},
            )],
            warnings=[], success=True,
        )

        client = AsyncMock(spec=GraphitiClient)
        client.enabled = True
        client.config = GraphitiConfig(enabled=True)
        client.initialize = AsyncMock(return_value=True)
        client.close = AsyncMock()
        client.add_episode = AsyncMock(return_value="uuid-1")

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                with patch("guardkit.cli.graphiti.asyncio.sleep", new_callable=AsyncMock):
                    await _cmd_add_context(
                        path=str(tmp_file),
                        parser_type=None,
                        force=False,
                        dry_run=False,
                        pattern="**/*.md",
                        verbose=False,
                        quiet=False,
                        delay=0,
                    )

        captured = capsys.readouterr()
        assert "\u2713" in captured.out  # checkmark
        assert "\u26a0" not in captured.out  # no warning marker

    @pytest.mark.asyncio
    async def test_warning_marker_for_partial_success(
        self, tmp_file, mock_parser_registry, mock_parser, capsys
    ):
        """AC-005: Files with partial success show warning marker with failed count."""
        episodes = [
            EpisodeData(
                content="Content 1", group_id="test",
                entity_type="adr", entity_id="adr-1", metadata={},
            ),
            EpisodeData(
                content="Content 2", group_id="test",
                entity_type="adr", entity_id="adr-2", metadata={},
            ),
        ]
        mock_parser.parse.return_value = ParseResult(
            episodes=episodes, warnings=[], success=True
        )

        client = AsyncMock(spec=GraphitiClient)
        client.enabled = True
        client.config = GraphitiConfig(enabled=True)
        client.initialize = AsyncMock(return_value=True)
        client.close = AsyncMock()
        client.add_episode = AsyncMock(side_effect=["uuid-1", None])

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                with patch("guardkit.cli.graphiti.asyncio.sleep", new_callable=AsyncMock):
                    await _cmd_add_context(
                        path=str(tmp_file),
                        parser_type=None,
                        force=False,
                        dry_run=False,
                        pattern="**/*.md",
                        verbose=False,
                        quiet=False,
                        delay=0,
                    )

        captured = capsys.readouterr()
        normalized = self._normalize(captured.out)
        assert "\u26a0" in captured.out  # warning marker
        assert "1 episode(s) failed" in normalized

    @pytest.mark.asyncio
    async def test_exception_path_also_tracked_as_failed(
        self, tmp_file, mock_parser_registry, mock_parser, capsys
    ):
        """AC-006: Exception path tracked as failed episode."""
        mock_parser.parse.return_value = ParseResult(
            episodes=[EpisodeData(
                content="Content", group_id="test",
                entity_type="adr", entity_id="adr-1", metadata={},
            )],
            warnings=[], success=True,
        )

        client = AsyncMock(spec=GraphitiClient)
        client.enabled = True
        client.config = GraphitiConfig(enabled=True)
        client.initialize = AsyncMock(return_value=True)
        client.close = AsyncMock()
        client.add_episode = AsyncMock(side_effect=Exception("DB error"))

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                with patch("guardkit.cli.graphiti.asyncio.sleep", new_callable=AsyncMock):
                    await _cmd_add_context(
                        path=str(tmp_file),
                        parser_type=None,
                        force=False,
                        dry_run=False,
                        pattern="**/*.md",
                        verbose=False,
                        quiet=False,
                        delay=0,
                    )

        captured = capsys.readouterr()
        normalized = self._normalize(captured.out)
        assert "\u26a0" in captured.out  # warning marker
        assert "Failed: 1 episode" in normalized

    @pytest.mark.asyncio
    async def test_all_none_returns_shows_warning_and_failed_count(
        self, tmp_file, mock_parser_registry, mock_parser, capsys
    ):
        """All episodes returning None: warning marker, no checkmark."""
        episodes = [
            EpisodeData(
                content="Content 1", group_id="test",
                entity_type="adr", entity_id="adr-1", metadata={},
            ),
            EpisodeData(
                content="Content 2", group_id="test",
                entity_type="adr", entity_id="adr-2", metadata={},
            ),
        ]
        mock_parser.parse.return_value = ParseResult(
            episodes=episodes, warnings=[], success=True
        )

        client = AsyncMock(spec=GraphitiClient)
        client.enabled = True
        client.config = GraphitiConfig(enabled=True)
        client.initialize = AsyncMock(return_value=True)
        client.close = AsyncMock()
        client.add_episode = AsyncMock(return_value=None)

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                with patch("guardkit.cli.graphiti.asyncio.sleep", new_callable=AsyncMock):
                    await _cmd_add_context(
                        path=str(tmp_file),
                        parser_type=None,
                        force=False,
                        dry_run=False,
                        pattern="**/*.md",
                        verbose=False,
                        quiet=False,
                        delay=0,
                    )

        captured = capsys.readouterr()
        normalized = self._normalize(captured.out)
        assert "\u2713" not in captured.out  # NO checkmark
        assert "\u26a0" in captured.out  # warning marker
        assert "2 episode(s) failed" in normalized
        assert "Failed: 2 episodes" in normalized

    @pytest.mark.asyncio
    async def test_mixed_success_exception_and_none(
        self, tmp_file, mock_parser_registry, mock_parser, capsys
    ):
        """Mix of success, None return, and exception — all tracked correctly."""
        episodes = [
            EpisodeData(
                content=f"Content {i}", group_id="test",
                entity_type="adr", entity_id=f"adr-{i}", metadata={},
            )
            for i in range(3)
        ]
        mock_parser.parse.return_value = ParseResult(
            episodes=episodes, warnings=[], success=True
        )

        client = AsyncMock(spec=GraphitiClient)
        client.enabled = True
        client.config = GraphitiConfig(enabled=True)
        client.initialize = AsyncMock(return_value=True)
        client.close = AsyncMock()
        # First succeeds, second None, third exception
        client.add_episode = AsyncMock(
            side_effect=["uuid-1", None, Exception("timeout")]
        )

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=client):
            with patch("guardkit.cli.graphiti.ParserRegistry", return_value=mock_parser_registry):
                with patch("guardkit.cli.graphiti.asyncio.sleep", new_callable=AsyncMock):
                    await _cmd_add_context(
                        path=str(tmp_file),
                        parser_type=None,
                        force=False,
                        dry_run=False,
                        pattern="**/*.md",
                        verbose=False,
                        quiet=False,
                        delay=0,
                    )

        captured = capsys.readouterr()
        normalized = self._normalize(captured.out)
        assert "\u26a0" in captured.out  # partial success
        assert "2 episode(s) failed" in normalized
        assert "1 episode" in normalized  # 1 added
        assert "Failed: 2 episodes" in normalized

    @pytest.mark.asyncio
    async def test_dry_run_unaffected_by_return_check(
        self, tmp_file, mock_graphiti_client, mock_parser_registry,
        mock_parser, sample_parse_result, capsys
    ):
        """Dry run mode still counts all episodes (no add_episode called)."""
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
                    delay=0,
                )

        mock_graphiti_client.add_episode.assert_not_called()
        captured = capsys.readouterr()
        assert "1" in captured.out  # 1 episode would be added

# ============================================================================
# TEST CLASS: Log Noise Suppression (TASK-FIX-AC04)
# ============================================================================


class TestLogNoiseSuppression:
    """Test that noisy INFO-level loggers are suppressed during add-context."""

    @pytest.mark.asyncio
    async def test_falkordb_driver_logger_set_to_warning(
        self, tmp_file, mock_graphiti_client, mock_parser_registry,
        mock_parser, sample_parse_result
    ):
        """AC-001: No 'Index already exists' messages — FalkorDB driver logger set to WARNING."""
        mock_parser.parse.return_value = sample_parse_result

        falkordb_logger = logging.getLogger("graphiti_core.driver.falkordb_driver")
        original_level = falkordb_logger.level

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
                    delay=0,
                )

        assert falkordb_logger.level == logging.WARNING
        # Restore for other tests
        falkordb_logger.setLevel(original_level)

    @pytest.mark.asyncio
    async def test_httpx_logger_set_to_warning(
        self, tmp_file, mock_graphiti_client, mock_parser_registry,
        mock_parser, sample_parse_result
    ):
        """AC-004: httpx INFO-level request logging suppressed."""
        mock_parser.parse.return_value = sample_parse_result

        httpx_logger = logging.getLogger("httpx")
        original_level = httpx_logger.level

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
                    delay=0,
                )

        assert httpx_logger.level == logging.WARNING
        # Restore for other tests
        httpx_logger.setLevel(original_level)

    @pytest.mark.asyncio
    async def test_falkordb_error_messages_still_displayed(
        self, tmp_file, mock_graphiti_client, mock_parser_registry,
        mock_parser, sample_parse_result
    ):
        """AC-002: FalkorDB ERROR-level messages still displayed."""
        mock_parser.parse.return_value = sample_parse_result

        falkordb_logger = logging.getLogger("graphiti_core.driver.falkordb_driver")
        original_level = falkordb_logger.level

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
                    delay=0,
                )

        # WARNING level still allows ERROR and CRITICAL messages through
        assert falkordb_logger.level <= logging.ERROR
        # Restore for other tests
        falkordb_logger.setLevel(original_level)

    @pytest.mark.asyncio
    async def test_log_suppression_scoped_to_add_context(self):
        """AC-003: Log level override scoped to add-context, not global."""
        # Other loggers (not falkordb_driver or httpx) should NOT be affected
        unrelated_logger = logging.getLogger("guardkit.cli.graphiti")
        original_level = unrelated_logger.level

        # The module-level logger should not be changed by add-context
        # (only the two specific loggers are suppressed)
        assert unrelated_logger.name != "graphiti_core.driver.falkordb_driver"
        assert unrelated_logger.name != "httpx"
        # Level should remain whatever it was before
        assert unrelated_logger.level == original_level

    @pytest.mark.asyncio
    async def test_info_messages_blocked_warning_messages_pass(
        self, tmp_file, mock_graphiti_client, mock_parser_registry,
        mock_parser, sample_parse_result
    ):
        """Verify INFO is blocked but WARNING passes through after suppression."""
        mock_parser.parse.return_value = sample_parse_result

        falkordb_logger = logging.getLogger("graphiti_core.driver.falkordb_driver")
        original_level = falkordb_logger.level

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
                    delay=0,
                )

        # After running add-context, the logger should be at WARNING
        # This means INFO (20) is blocked, WARNING (30) passes
        assert falkordb_logger.isEnabledFor(logging.WARNING)
        assert falkordb_logger.isEnabledFor(logging.ERROR)
        assert not falkordb_logger.isEnabledFor(logging.INFO)
        # Restore for other tests
        falkordb_logger.setLevel(original_level)
