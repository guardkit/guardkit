"""
Seam test configuration and fixtures.

Provides fixtures for seam (technology boundary) testing:
- Protocol-level mocks for Graphiti client
- CLI runner configured for seam testing
- Temporary task directory with proper structure
- Architecture spec fixtures

Follow the pattern from tests/e2e/conftest.py for fixture organization.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock

from click.testing import CliRunner

if TYPE_CHECKING:
    from typing import Generator, Any


def pytest_configure(config: Any) -> None:
    """Register custom markers for seam tests."""
    config.addinivalue_line(
        "markers", "seam: Seam (technology boundary) integration tests"
    )


@pytest.fixture
def graphiti_mock_client() -> Mock:
    """
    Create a protocol-level AsyncMock that records upsert calls.

    This mock simulates an enabled Graphiti client with:
    - `.enabled = True` so SystemPlanGraphiti treats it as a real client
    - `.upsert_episode` as AsyncMock that records calls
    - `.search` as AsyncMock returning empty results
    - `.get_group_id` returning properly prefixed group IDs

    The mock records all calls for test assertions.

    Returns:
        Mock: A configured mock client that behaves like an enabled Graphiti client.
    """
    mock_client = Mock()
    mock_client.enabled = True

    # Track all upsert calls for test assertions
    mock_client._upsert_calls: list[dict[str, Any]] = []

    async def record_upsert(**kwargs: Any) -> Mock:
        """Record upsert call and return a mock result with uuid."""
        mock_client._upsert_calls.append(kwargs)
        result = Mock()
        result.uuid = f"mock-uuid-{len(mock_client._upsert_calls)}"
        return result

    mock_client.upsert_episode = AsyncMock(side_effect=record_upsert)

    # Search returns empty by default but can be configured
    mock_client.search = AsyncMock(return_value=[])

    # Group ID prefixing follows the pattern: {project_id}__{group_name}
    def get_group_id(group_name: str) -> str:
        project_id = getattr(mock_client, "_project_id", "test-project")
        return f"{project_id}__{group_name}"

    mock_client.get_group_id = Mock(side_effect=get_group_id)
    mock_client._project_id = "test-project"

    return mock_client


@pytest.fixture
def cli_runner() -> CliRunner:
    """
    Create a Click CliRunner configured for seam testing.

    The runner is configured with:
    - mix_stderr=False for clean output separation
    - Isolated environment for predictable testing

    Returns:
        CliRunner: A configured Click test runner.
    """
    return CliRunner(mix_stderr=False)


@pytest.fixture
def tmp_task_dir(tmp_path: Path) -> dict[str, Path]:
    """
    Create a temporary task directory with proper GuardKit structure.

    Creates the complete directory structure needed for task operations:
    - tasks/{backlog,in_progress,in_review,completed,blocked,design_approved}/
    - .claude/task-plans/
    - .guardkit/autobuild/

    Args:
        tmp_path: Pytest's tmp_path fixture.

    Returns:
        dict[str, Path]: Dictionary mapping directory names to paths.
    """
    dirs: dict[str, Path] = {
        "root": tmp_path,
        # Task state directories
        "backlog": tmp_path / "tasks" / "backlog",
        "in_progress": tmp_path / "tasks" / "in_progress",
        "in_review": tmp_path / "tasks" / "in_review",
        "completed": tmp_path / "tasks" / "completed",
        "blocked": tmp_path / "tasks" / "blocked",
        "design_approved": tmp_path / "tasks" / "design_approved",
        # GuardKit directories
        "task_plans": tmp_path / ".claude" / "task-plans",
        "autobuild": tmp_path / ".guardkit" / "autobuild",
        # Documentation
        "docs": tmp_path / "docs" / "architecture",
    }

    # Create all directories
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)

    return dirs


@pytest.fixture
def minimal_spec_fixture() -> Path:
    """
    Return path to the minimal architecture spec fixture file.

    This fixture is used for system-plan seam tests that need a minimal
    valid architecture specification for parsing and processing.

    Returns:
        Path: Absolute path to the minimal-spec.md fixture file.
    """
    fixture_path = Path(__file__).parent.parent / "fixtures" / "minimal-spec.md"
    if not fixture_path.exists():
        raise FileNotFoundError(
            f"Fixture file not found: {fixture_path}. "
            "Ensure tests/fixtures/minimal-spec.md exists."
        )
    return fixture_path
