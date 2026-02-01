"""TDD tests for guardkit graphiti add-context CLI command.

These tests define the expected behavior of the add-context command
before implementation (RED phase of TDD).

Test Coverage:
1. Single file processing with known parser type
2. Directory processing with glob patterns
3. Auto-detection of parser type
4. --dry-run preview mode
5. --type flag to force specific parser
6. Error handling for unsupported files
7. Summary output format
8. --force flag behavior
9. Mock GraphitiClient to avoid network calls
10. Mock filesystem for isolation
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, mock_open
from typing import Optional

import pytest
from click.testing import CliRunner

from guardkit.cli.graphiti import graphiti
from guardkit.integrations.graphiti.parsers.base import ParseResult, EpisodeData
from guardkit.integrations.graphiti.parsers.registry import ParserRegistry
from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_graphiti_client():
    """Create a mock GraphitiClient instance."""
    client = AsyncMock(spec=GraphitiClient)
    client.enabled = True
    client.config = GraphitiConfig(enabled=True)

    # Mock initialize to return True
    async def mock_init():
        return True

    client.initialize = AsyncMock(side_effect=mock_init)

    # Mock add_episode to return UUIDs
    episode_counter = [0]

    async def mock_add_episode(name, episode_body, group_id, **kwargs):
        episode_counter[0] += 1
        return f"episode-uuid-{episode_counter[0]}"

    client.add_episode = AsyncMock(side_effect=mock_add_episode)

    # Mock close
    client.close = AsyncMock()

    return client


@pytest.fixture
def mock_parser_registry():
    """Create a mock ParserRegistry with test parsers."""
    registry = Mock(spec=ParserRegistry)

    # Create test parsers
    adr_parser = Mock()
    adr_parser.parser_type = "adr"
    adr_parser.supported_extensions = [".md"]

    feature_parser = Mock()
    feature_parser.parser_type = "feature-spec"
    feature_parser.supported_extensions = [".md"]

    # Mock get_parser to return parsers by type
    def get_parser(parser_type: Optional[str]):
        if parser_type == "adr":
            return adr_parser
        elif parser_type == "feature-spec":
            return feature_parser
        return None

    registry.get_parser = Mock(side_effect=get_parser)

    # Mock detect_parser to return ADR parser by default
    def detect_parser(file_path: str, content: str):
        if "adr" in file_path.lower():
            return adr_parser
        elif "feature" in file_path.lower():
            return feature_parser
        return adr_parser  # Default fallback

    registry.detect_parser = Mock(side_effect=detect_parser)

    return registry, adr_parser, feature_parser


@pytest.fixture
def sample_parse_result():
    """Create a sample successful ParseResult."""
    episode = EpisodeData(
        content="Test content",
        group_id="test_group",
        entity_type="adr",
        entity_id="test-001",
        metadata={"source": "test"},
    )

    return ParseResult(
        episodes=[episode],
        warnings=[],
        success=True,
    )


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


# ============================================================================
# TEST 1: SINGLE FILE PROCESSING WITH KNOWN PARSER
# ============================================================================


def test_add_context_single_file_with_known_parser(
    cli_runner,
    mock_graphiti_client,
    mock_parser_registry,
    sample_parse_result,
):
    """Test adding a single file with known parser type.

    Expected behavior:
    1. Read file content
    2. Detect or use specified parser
    3. Parse file into episodes
    4. Add episodes to Graphiti
    5. Display success summary
    """
    registry, adr_parser, _ = mock_parser_registry
    adr_parser.parse.return_value = sample_parse_result

    test_file = "docs/architecture/ADR-001.md"
    test_content = "# ADR-001: Test Decision\n\nDecision content here."

    with patch("guardkit.cli.graphiti.Path") as mock_path_cls:
        # Mock Path.exists() and Path.is_file()
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path_cls.return_value = mock_path

        with patch("guardkit.cli.graphiti.open", mock_open(read_data=test_content)):
            with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
                with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                    result = cli_runner.invoke(
                        graphiti,
                        ["add-context", test_file],
                    )

    # Assertions
    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert "Added 1 file" in result.output or "1 episode" in result.output
    assert "ADR-001" in result.output or test_file in result.output

    # Verify parser was called
    adr_parser.parse.assert_called_once_with(test_content, test_file)

    # Verify Graphiti client was used
    mock_graphiti_client.initialize.assert_called_once()
    mock_graphiti_client.add_episode.assert_called_once()
    mock_graphiti_client.close.assert_called_once()


# ============================================================================
# TEST 2: DIRECTORY PROCESSING WITH GLOB PATTERNS
# ============================================================================


def test_add_context_directory_with_default_pattern(
    cli_runner,
    mock_graphiti_client,
    mock_parser_registry,
    sample_parse_result,
):
    """Test adding a directory with default glob pattern (*.md).

    Expected behavior:
    1. Scan directory for matching files
    2. Process each file
    3. Display summary with file count
    """
    registry, adr_parser, _ = mock_parser_registry
    adr_parser.parse.return_value = sample_parse_result

    test_dir = "docs/architecture"
    test_files = [
        "docs/architecture/ADR-001.md",
        "docs/architecture/ADR-002.md",
        "docs/architecture/README.md",
    ]

    with patch("guardkit.cli.graphiti.Path") as mock_path_cls:
        # Mock directory path
        mock_dir = Mock()
        mock_dir.exists.return_value = True
        mock_dir.is_file.return_value = False
        mock_dir.is_dir.return_value = True

        # Mock glob to return test files
        mock_file_paths = [Mock(spec=Path) for _ in test_files]
        for i, mock_file in enumerate(mock_file_paths):
            mock_file.__str__ = Mock(return_value=test_files[i])
            mock_file.is_file.return_value = True

        mock_dir.glob.return_value = mock_file_paths
        mock_path_cls.return_value = mock_dir

        test_content = "# Test content"

        with patch("guardkit.cli.graphiti.open", mock_open(read_data=test_content)):
            with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
                with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                    result = cli_runner.invoke(
                        graphiti,
                        ["add-context", test_dir],
                    )

    # Assertions
    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert "3 files" in result.output or "3 episodes" in result.output

    # Verify parser called for each file
    assert adr_parser.parse.call_count == 3

    # Verify Graphiti client used for each episode
    assert mock_graphiti_client.add_episode.call_count == 3


def test_add_context_directory_with_custom_pattern(
    cli_runner,
    mock_graphiti_client,
    mock_parser_registry,
    sample_parse_result,
):
    """Test adding a directory with custom glob pattern.

    Expected behavior:
    1. Use provided glob pattern instead of default
    2. Process matching files
    """
    registry, adr_parser, _ = mock_parser_registry
    adr_parser.parse.return_value = sample_parse_result

    test_dir = "docs"
    test_pattern = "**/ADR-*.md"
    test_files = [
        "docs/architecture/ADR-001.md",
        "docs/decisions/ADR-002.md",
    ]

    with patch("guardkit.cli.graphiti.Path") as mock_path_cls:
        mock_dir = Mock()
        mock_dir.exists.return_value = True
        mock_dir.is_file.return_value = False
        mock_dir.is_dir.return_value = True

        mock_file_paths = [Mock(spec=Path) for _ in test_files]
        for i, mock_file in enumerate(mock_file_paths):
            mock_file.__str__ = Mock(return_value=test_files[i])
            mock_file.is_file.return_value = True

        mock_dir.glob.return_value = mock_file_paths
        mock_path_cls.return_value = mock_dir

        test_content = "# ADR content"

        with patch("guardkit.cli.graphiti.open", mock_open(read_data=test_content)):
            with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
                with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                    result = cli_runner.invoke(
                        graphiti,
                        ["add-context", test_dir, "--pattern", test_pattern],
                    )

    # Assertions
    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert "2 files" in result.output or "2 episodes" in result.output

    # Verify glob called with custom pattern
    mock_dir.glob.assert_called_with(test_pattern)


# ============================================================================
# TEST 3: AUTO-DETECTION OF PARSER TYPE
# ============================================================================


def test_add_context_auto_detect_parser_type(
    cli_runner,
    mock_graphiti_client,
    mock_parser_registry,
    sample_parse_result,
):
    """Test automatic parser type detection based on file content/path.

    Expected behavior:
    1. Call registry.detect_parser() when --type not provided
    2. Use detected parser
    3. Display parser type in output
    """
    registry, adr_parser, feature_parser = mock_parser_registry

    # Different parsers should be used for different files
    adr_result = ParseResult(
        episodes=[
            EpisodeData(
                content="ADR content",
                group_id="architecture_decisions",
                entity_type="adr",
                entity_id="adr-001",
                metadata={},
            )
        ],
        warnings=[],
        success=True,
    )

    feature_result = ParseResult(
        episodes=[
            EpisodeData(
                content="Feature content",
                group_id="feature_specs",
                entity_type="feature",
                entity_id="feat-001",
                metadata={},
            )
        ],
        warnings=[],
        success=True,
    )

    adr_parser.parse.return_value = adr_result
    feature_parser.parse.return_value = feature_result

    test_file = "docs/ADR-001.md"
    test_content = "# ADR-001"

    with patch("guardkit.cli.graphiti.Path") as mock_path_cls:
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path_cls.return_value = mock_path

        with patch("guardkit.cli.graphiti.open", mock_open(read_data=test_content)):
            with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
                with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                    result = cli_runner.invoke(
                        graphiti,
                        ["add-context", test_file],
                    )

    # Assertions
    assert result.exit_code == 0

    # Verify detect_parser was called
    registry.detect_parser.assert_called_once()

    # Verify correct parser was used
    adr_parser.parse.assert_called_once()
    feature_parser.parse.assert_not_called()


# ============================================================================
# TEST 4: DRY-RUN PREVIEW MODE
# ============================================================================


def test_add_context_dry_run_shows_preview_without_adding(
    cli_runner,
    mock_graphiti_client,
    mock_parser_registry,
    sample_parse_result,
):
    """Test --dry-run shows what would be added without actually adding.

    Expected behavior:
    1. Parse files
    2. Display what would be added
    3. DO NOT call GraphitiClient.add_episode()
    4. Exit successfully
    """
    registry, adr_parser, _ = mock_parser_registry
    adr_parser.parse.return_value = sample_parse_result

    test_file = "docs/ADR-001.md"
    test_content = "# Test"

    with patch("guardkit.cli.graphiti.Path") as mock_path_cls:
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path_cls.return_value = mock_path

        with patch("guardkit.cli.graphiti.open", mock_open(read_data=test_content)):
            with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
                with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                    result = cli_runner.invoke(
                        graphiti,
                        ["add-context", test_file, "--dry-run"],
                    )

    # Assertions
    assert result.exit_code == 0
    assert "Would add" in result.output or "Dry run" in result.output
    assert "1 episode" in result.output or "1 file" in result.output

    # Verify NO episodes were actually added
    mock_graphiti_client.add_episode.assert_not_called()

    # But client should still be initialized and closed
    mock_graphiti_client.initialize.assert_called_once()
    mock_graphiti_client.close.assert_called_once()


# ============================================================================
# TEST 5: --TYPE FLAG TO FORCE SPECIFIC PARSER
# ============================================================================


def test_add_context_type_flag_forces_parser(
    cli_runner,
    mock_graphiti_client,
    mock_parser_registry,
    sample_parse_result,
):
    """Test --type flag forces use of specific parser.

    Expected behavior:
    1. Use registry.get_parser(type) instead of detect_parser()
    2. Use forced parser even if auto-detection would choose differently
    """
    registry, adr_parser, feature_parser = mock_parser_registry
    feature_parser.parse.return_value = sample_parse_result

    # File looks like ADR but we force feature-spec parser
    test_file = "docs/ADR-001.md"
    test_content = "# ADR-001"

    with patch("guardkit.cli.graphiti.Path") as mock_path_cls:
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path_cls.return_value = mock_path

        with patch("guardkit.cli.graphiti.open", mock_open(read_data=test_content)):
            with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
                with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                    result = cli_runner.invoke(
                        graphiti,
                        ["add-context", test_file, "--type", "feature-spec"],
                    )

    # Assertions
    assert result.exit_code == 0

    # Verify get_parser was called with forced type
    registry.get_parser.assert_called_with("feature-spec")

    # Verify detect_parser was NOT called
    registry.detect_parser.assert_not_called()

    # Verify forced parser was used
    feature_parser.parse.assert_called_once()
    adr_parser.parse.assert_not_called()


# ============================================================================
# TEST 6: ERROR HANDLING FOR UNSUPPORTED FILES
# ============================================================================


def test_add_context_graceful_error_for_unsupported_file(
    cli_runner,
    mock_graphiti_client,
    mock_parser_registry,
):
    """Test graceful error handling when no parser can handle file.

    Expected behavior:
    1. Detect that no parser can handle file
    2. Display warning/error message
    3. Exit with appropriate code or continue with warning
    """
    registry, _, _ = mock_parser_registry

    # Mock detect_parser to return None (unsupported)
    registry.detect_parser.return_value = None

    test_file = "docs/unsupported.xyz"
    test_content = "Random content"

    with patch("guardkit.cli.graphiti.Path") as mock_path_cls:
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path_cls.return_value = mock_path

        with patch("guardkit.cli.graphiti.open", mock_open(read_data=test_content)):
            with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
                with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                    result = cli_runner.invoke(
                        graphiti,
                        ["add-context", test_file],
                    )

    # Should either exit with error or show warning
    assert "unsupported" in result.output.lower() or "no parser" in result.output.lower()

    # Should not have added any episodes
    mock_graphiti_client.add_episode.assert_not_called()


def test_add_context_file_not_found_error(
    cli_runner,
    mock_graphiti_client,
):
    """Test error handling when file does not exist.

    Expected behavior:
    1. Check file existence
    2. Display clear error message
    3. Exit with non-zero code
    """
    test_file = "docs/nonexistent.md"

    with patch("guardkit.cli.graphiti.Path") as mock_path_cls:
        mock_path = Mock()
        mock_path.exists.return_value = False
        mock_path_cls.return_value = mock_path

        with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
            result = cli_runner.invoke(
                graphiti,
                ["add-context", test_file],
            )

    # Should exit with error
    assert result.exit_code != 0
    assert "not found" in result.output.lower() or "does not exist" in result.output.lower()


# ============================================================================
# TEST 7: SUMMARY OUTPUT FORMAT
# ============================================================================


def test_add_context_summary_output_format(
    cli_runner,
    mock_graphiti_client,
    mock_parser_registry,
):
    """Test that summary output is informative and well-formatted.

    Expected output elements:
    - Number of files processed
    - Number of episodes added
    - Parser type(s) used
    - Success/warning indicators
    """
    registry, adr_parser, _ = mock_parser_registry

    # Create result with multiple episodes
    multi_episode_result = ParseResult(
        episodes=[
            EpisodeData(
                content="Content 1",
                group_id="test",
                entity_type="adr",
                entity_id="test-1",
                metadata={},
            ),
            EpisodeData(
                content="Content 2",
                group_id="test",
                entity_type="adr",
                entity_id="test-2",
                metadata={},
            ),
        ],
        warnings=["Warning: Test warning"],
        success=True,
    )

    adr_parser.parse.return_value = multi_episode_result

    test_file = "docs/ADR-001.md"
    test_content = "# Test"

    with patch("guardkit.cli.graphiti.Path") as mock_path_cls:
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path_cls.return_value = mock_path

        with patch("guardkit.cli.graphiti.open", mock_open(read_data=test_content)):
            with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
                with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                    result = cli_runner.invoke(
                        graphiti,
                        ["add-context", test_file],
                    )

    # Check for expected output elements
    assert result.exit_code == 0
    assert "2 episodes" in result.output or "2 episode" in result.output
    assert "Warning" in result.output  # Should show parser warnings
    assert "adr" in result.output.lower()  # Should mention parser type


# ============================================================================
# TEST 8: --FORCE FLAG BEHAVIOR
# ============================================================================


def test_add_context_force_flag_overwrites_existing(
    cli_runner,
    mock_graphiti_client,
    mock_parser_registry,
    sample_parse_result,
):
    """Test --force flag behavior for overwriting existing context.

    Expected behavior:
    1. When --force is used, overwrite existing episodes
    2. Display indication that episodes were overwritten
    """
    registry, adr_parser, _ = mock_parser_registry
    adr_parser.parse.return_value = sample_parse_result

    test_file = "docs/ADR-001.md"
    test_content = "# ADR-001"

    with patch("guardkit.cli.graphiti.Path") as mock_path_cls:
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path_cls.return_value = mock_path

        with patch("guardkit.cli.graphiti.open", mock_open(read_data=test_content)):
            with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
                with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                    result = cli_runner.invoke(
                        graphiti,
                        ["add-context", test_file, "--force"],
                    )

    # Assertions
    assert result.exit_code == 0

    # Verify add_episode was called (force should still add)
    mock_graphiti_client.add_episode.assert_called()

    # Output might mention "overwrite" or "force"
    # (Implementation detail - not strictly required for now)


# ============================================================================
# TEST 9: MULTIPLE FILES WITH MIXED RESULTS
# ============================================================================


def test_add_context_directory_with_mixed_success_and_failures(
    cli_runner,
    mock_graphiti_client,
    mock_parser_registry,
):
    """Test processing directory where some files succeed and others fail.

    Expected behavior:
    1. Continue processing after individual file failures
    2. Display both successes and failures in summary
    3. Exit with appropriate status code
    """
    registry, adr_parser, _ = mock_parser_registry

    # Mock parse to succeed on first call, fail on second
    success_result = ParseResult(
        episodes=[
            EpisodeData(
                content="Success",
                group_id="test",
                entity_type="adr",
                entity_id="test-1",
                metadata={},
            )
        ],
        warnings=[],
        success=True,
    )

    failure_result = ParseResult(
        episodes=[],
        warnings=["Parse error"],
        success=False,
    )

    adr_parser.parse.side_effect = [success_result, failure_result]

    test_dir = "docs"
    test_files = [
        "docs/ADR-001.md",
        "docs/ADR-002.md",
    ]

    with patch("guardkit.cli.graphiti.Path") as mock_path_cls:
        mock_dir = Mock()
        mock_dir.exists.return_value = True
        mock_dir.is_file.return_value = False
        mock_dir.is_dir.return_value = True

        mock_file_paths = [Mock(spec=Path) for _ in test_files]
        for i, mock_file in enumerate(mock_file_paths):
            mock_file.__str__ = Mock(return_value=test_files[i])
            mock_file.is_file.return_value = True

        mock_dir.glob.return_value = mock_file_paths
        mock_path_cls.return_value = mock_dir

        test_content = "# Test"

        with patch("guardkit.cli.graphiti.open", mock_open(read_data=test_content)):
            with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
                with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                    result = cli_runner.invoke(
                        graphiti,
                        ["add-context", test_dir],
                    )

    # Should show mixed results
    assert "1" in result.output  # 1 success
    assert "error" in result.output.lower() or "failed" in result.output.lower()


# ============================================================================
# TEST 10: GRAPHITI CLIENT ERROR HANDLING
# ============================================================================


def test_add_context_graphiti_connection_error(
    cli_runner,
    mock_parser_registry,
    sample_parse_result,
):
    """Test error handling when Graphiti connection fails.

    Expected behavior:
    1. Detect connection failure
    2. Display clear error message
    3. Exit gracefully with non-zero code
    """
    registry, adr_parser, _ = mock_parser_registry
    adr_parser.parse.return_value = sample_parse_result

    # Create client that fails to initialize
    failed_client = AsyncMock(spec=GraphitiClient)
    failed_client.enabled = False

    async def failed_init():
        return False

    failed_client.initialize = AsyncMock(side_effect=failed_init)
    failed_client.close = AsyncMock()

    test_file = "docs/ADR-001.md"
    test_content = "# Test"

    with patch("guardkit.cli.graphiti.Path") as mock_path_cls:
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path_cls.return_value = mock_path

        with patch("guardkit.cli.graphiti.open", mock_open(read_data=test_content)):
            with patch("guardkit.cli.graphiti.GraphitiClient", return_value=failed_client):
                with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                    result = cli_runner.invoke(
                        graphiti,
                        ["add-context", test_file],
                    )

    # Should exit with error
    assert result.exit_code != 0
    assert "connection" in result.output.lower() or "failed" in result.output.lower() or "disabled" in result.output.lower()


def test_add_context_graphiti_add_episode_error(
    cli_runner,
    mock_graphiti_client,
    mock_parser_registry,
    sample_parse_result,
):
    """Test error handling when add_episode() fails.

    Expected behavior:
    1. Detect add_episode failure
    2. Display error but continue processing other files
    3. Show failure in summary
    """
    registry, adr_parser, _ = mock_parser_registry
    adr_parser.parse.return_value = sample_parse_result

    # Mock add_episode to raise exception
    async def failing_add_episode(*args, **kwargs):
        raise RuntimeError("Graphiti add_episode failed")

    mock_graphiti_client.add_episode = AsyncMock(side_effect=failing_add_episode)

    test_file = "docs/ADR-001.md"
    test_content = "# Test"

    with patch("guardkit.cli.graphiti.Path") as mock_path_cls:
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path_cls.return_value = mock_path

        with patch("guardkit.cli.graphiti.open", mock_open(read_data=test_content)):
            with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
                with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                    result = cli_runner.invoke(
                        graphiti,
                        ["add-context", test_file],
                    )

    # Should show error
    assert "error" in result.output.lower() or "failed" in result.output.lower()


# ============================================================================
# TEST 11: INTEGRATION-LIKE TESTS
# ============================================================================


def test_add_context_end_to_end_workflow(
    cli_runner,
    mock_graphiti_client,
    mock_parser_registry,
):
    """Test realistic end-to-end workflow.

    Scenario:
    1. User adds a directory of ADR files
    2. Files are parsed successfully
    3. Episodes are added to Graphiti
    4. Summary is displayed
    """
    registry, adr_parser, _ = mock_parser_registry

    # Create realistic parse results
    adr_results = [
        ParseResult(
            episodes=[
                EpisodeData(
                    content=f"ADR-{i:03d} content",
                    group_id="architecture_decisions",
                    entity_type="adr",
                    entity_id=f"adr-{i:03d}",
                    metadata={"number": i},
                )
            ],
            warnings=[],
            success=True,
        )
        for i in range(1, 4)
    ]

    adr_parser.parse.side_effect = adr_results

    test_dir = "docs/architecture"
    test_files = [f"docs/architecture/ADR-{i:03d}.md" for i in range(1, 4)]

    with patch("guardkit.cli.graphiti.Path") as mock_path_cls:
        mock_dir = Mock()
        mock_dir.exists.return_value = True
        mock_dir.is_file.return_value = False
        mock_dir.is_dir.return_value = True

        mock_file_paths = [Mock(spec=Path) for _ in test_files]
        for i, mock_file in enumerate(mock_file_paths):
            mock_file.__str__ = Mock(return_value=test_files[i])
            mock_file.is_file.return_value = True

        mock_dir.glob.return_value = mock_file_paths
        mock_path_cls.return_value = mock_dir

        test_content = "# ADR content"

        with patch("guardkit.cli.graphiti.open", mock_open(read_data=test_content)):
            with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
                with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                    result = cli_runner.invoke(
                        graphiti,
                        ["add-context", test_dir],
                    )

    # Verify successful workflow
    assert result.exit_code == 0
    assert "3" in result.output  # 3 files or episodes
    assert mock_graphiti_client.add_episode.call_count == 3
    assert mock_graphiti_client.initialize.call_count == 1
    assert mock_graphiti_client.close.call_count == 1


# ============================================================================
# TEST 12: --VERBOSE FLAG SHOWS DETAILED OUTPUT
# ============================================================================


def test_add_context_verbose_flag_shows_detailed_output(
    cli_runner,
    mock_graphiti_client,
    mock_parser_registry,
    sample_parse_result,
):
    """Test --verbose flag shows detailed processing output.

    Expected behavior:
    1. Show "Parsing {file_path} with {parser_type}"
    2. Show "  Found {count} episodes"
    3. For each episode: "    - {entity_id} ({entity_type})"
    4. Show summary at end
    """
    registry, adr_parser, _ = mock_parser_registry

    # Create result with multiple episodes for verbose output
    verbose_result = ParseResult(
        episodes=[
            EpisodeData(
                content="Episode 1 content",
                group_id="test_group",
                entity_type="adr",
                entity_id="adr-001",
                metadata={"source": "test"},
            ),
            EpisodeData(
                content="Episode 2 content",
                group_id="test_group",
                entity_type="adr",
                entity_id="adr-002",
                metadata={"source": "test"},
            ),
        ],
        warnings=[],
        success=True,
    )

    adr_parser.parse.return_value = verbose_result

    test_file = "docs/ADR-001.md"
    test_content = "# ADR-001: Test Decision"

    with patch("guardkit.cli.graphiti.Path") as mock_path_cls:
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path_cls.return_value = mock_path

        with patch("guardkit.cli.graphiti.open", mock_open(read_data=test_content)):
            with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
                with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                    result = cli_runner.invoke(
                        graphiti,
                        ["add-context", test_file, "--verbose"],
                    )

    # Assertions for verbose output
    assert result.exit_code == 0

    # Should show parsing message
    assert "Parsing" in result.output
    assert test_file in result.output
    assert "adr" in result.output.lower()  # Parser type

    # Should show episode count
    assert "Found 2 episodes" in result.output or "2 episodes" in result.output

    # Should show individual episodes
    assert "adr-001" in result.output
    assert "adr-002" in result.output

    # Should still show summary
    assert "Added" in result.output or "Success" in result.output


def test_add_context_verbose_with_directory_processing(
    cli_runner,
    mock_graphiti_client,
    mock_parser_registry,
    sample_parse_result,
):
    """Test --verbose flag with directory processing shows details for each file.

    Expected behavior:
    1. Show parsing message for EACH file
    2. Show episode details for EACH file
    3. Show final summary
    """
    registry, adr_parser, _ = mock_parser_registry
    adr_parser.parse.return_value = sample_parse_result

    test_dir = "docs/architecture"
    test_files = [
        "docs/architecture/ADR-001.md",
        "docs/architecture/ADR-002.md",
    ]

    with patch("guardkit.cli.graphiti.Path") as mock_path_cls:
        mock_dir = Mock()
        mock_dir.exists.return_value = True
        mock_dir.is_file.return_value = False
        mock_dir.is_dir.return_value = True

        mock_file_paths = [Mock(spec=Path) for _ in test_files]
        for i, mock_file in enumerate(mock_file_paths):
            mock_file.__str__ = Mock(return_value=test_files[i])
            mock_file.is_file.return_value = True

        mock_dir.glob.return_value = mock_file_paths
        mock_path_cls.return_value = mock_dir

        test_content = "# Test content"

        with patch("guardkit.cli.graphiti.open", mock_open(read_data=test_content)):
            with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
                with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                    result = cli_runner.invoke(
                        graphiti,
                        ["add-context", test_dir, "--verbose"],
                    )

    # Assertions
    assert result.exit_code == 0

    # Should show parsing for each file
    assert result.output.count("Parsing") == 2 or "ADR-001" in result.output
    assert result.output.count("ADR-002") >= 1

    # Should show episode details multiple times
    assert "Found" in result.output or "episodes" in result.output

    # Should show final summary
    assert "2 files" in result.output or "2 episodes" in result.output


# ============================================================================
# TEST 13: --QUIET FLAG SUPPRESSES NON-ERROR OUTPUT
# ============================================================================


def test_add_context_quiet_flag_suppresses_non_error_output(
    cli_runner,
    mock_graphiti_client,
    mock_parser_registry,
    sample_parse_result,
):
    """Test --quiet flag suppresses informational output.

    Expected behavior:
    1. NO "Parsing..." messages
    2. NO "Found X episodes" messages
    3. NO success summary (unless error)
    4. Only show errors if present
    """
    registry, adr_parser, _ = mock_parser_registry
    adr_parser.parse.return_value = sample_parse_result

    test_file = "docs/ADR-001.md"
    test_content = "# ADR-001: Test Decision"

    with patch("guardkit.cli.graphiti.Path") as mock_path_cls:
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path_cls.return_value = mock_path

        with patch("guardkit.cli.graphiti.open", mock_open(read_data=test_content)):
            with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
                with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                    result = cli_runner.invoke(
                        graphiti,
                        ["add-context", test_file, "--quiet"],
                    )

    # Assertions for quiet mode
    assert result.exit_code == 0

    # Should NOT show verbose parsing messages
    assert "Parsing" not in result.output
    assert "Found" not in result.output

    # Output should be minimal (either empty or just brief status)
    # Allow for minimal output but no detailed messages
    assert len(result.output.strip()) < 100 or result.output.strip() == ""


def test_add_context_quiet_with_errors_still_shown(
    cli_runner,
    mock_graphiti_client,
    mock_parser_registry,
):
    """Test --quiet flag still shows error messages.

    Expected behavior:
    1. Suppress success messages
    2. SHOW error messages
    3. SHOW warnings (important information)
    4. Exit with error code on failure
    """
    registry, adr_parser, _ = mock_parser_registry

    # Create result with errors
    error_result = ParseResult(
        episodes=[],
        warnings=["Parse error: Invalid format"],
        success=False,
    )

    adr_parser.parse.return_value = error_result

    test_file = "docs/BAD-FILE.md"
    test_content = "Invalid content"

    with patch("guardkit.cli.graphiti.Path") as mock_path_cls:
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path_cls.return_value = mock_path

        with patch("guardkit.cli.graphiti.open", mock_open(read_data=test_content)):
            with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
                with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                    result = cli_runner.invoke(
                        graphiti,
                        ["add-context", test_file, "--quiet"],
                    )

    # Assertions
    # Should show error/warning even in quiet mode
    assert "error" in result.output.lower() or "warning" in result.output.lower()
    assert "Invalid format" in result.output or "Parse error" in result.output


# ============================================================================
# TEST 14: --VERBOSE AND --QUIET MUTUAL EXCLUSIVITY
# ============================================================================


def test_add_context_verbose_and_quiet_mutual_exclusivity(
    cli_runner,
):
    """Test that --verbose and --quiet cannot be used together.

    Expected behavior:
    1. Exit with error code
    2. Display clear error message
    3. Do not attempt to process files
    """
    test_file = "docs/ADR-001.md"

    result = cli_runner.invoke(
        graphiti,
        ["add-context", test_file, "--verbose", "--quiet"],
    )

    # Should exit with error
    assert result.exit_code != 0

    # Should show error about mutual exclusivity
    assert "mutually exclusive" in result.output.lower() or \
           "cannot be used together" in result.output.lower() or \
           "conflicting" in result.output.lower()


def test_add_context_quiet_flag_with_multiple_files(
    cli_runner,
    mock_graphiti_client,
    mock_parser_registry,
    sample_parse_result,
):
    """Test --quiet flag with directory processing.

    Expected behavior:
    1. Process all files silently
    2. No per-file output
    3. Minimal or no summary
    4. Only show errors if present
    """
    registry, adr_parser, _ = mock_parser_registry
    adr_parser.parse.return_value = sample_parse_result

    test_dir = "docs/architecture"
    test_files = [
        "docs/architecture/ADR-001.md",
        "docs/architecture/ADR-002.md",
        "docs/architecture/ADR-003.md",
    ]

    with patch("guardkit.cli.graphiti.Path") as mock_path_cls:
        mock_dir = Mock()
        mock_dir.exists.return_value = True
        mock_dir.is_file.return_value = False
        mock_dir.is_dir.return_value = True

        mock_file_paths = [Mock(spec=Path) for _ in test_files]
        for i, mock_file in enumerate(mock_file_paths):
            mock_file.__str__ = Mock(return_value=test_files[i])
            mock_file.is_file.return_value = True

        mock_dir.glob.return_value = mock_file_paths
        mock_path_cls.return_value = mock_dir

        test_content = "# Test content"

        with patch("guardkit.cli.graphiti.open", mock_open(read_data=test_content)):
            with patch("guardkit.cli.graphiti.GraphitiClient", return_value=mock_graphiti_client):
                with patch("guardkit.cli.graphiti.ParserRegistry", return_value=registry):
                    result = cli_runner.invoke(
                        graphiti,
                        ["add-context", test_dir, "--quiet"],
                    )

    # Assertions
    assert result.exit_code == 0

    # Should have minimal output (no per-file messages)
    assert "Parsing" not in result.output
    assert "Found" not in result.output

    # Verify all files were processed (by checking mock calls)
    assert adr_parser.parse.call_count == 3
    assert mock_graphiti_client.add_episode.call_count == 3
