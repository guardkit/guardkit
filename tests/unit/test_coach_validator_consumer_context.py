"""
Unit tests for consumer_context validation in CoachValidator (TASK-IC-DD44).

Verifies that CoachValidator reads consumer_context from task metadata,
validates artifact format against format_note constraints, and reports
mismatches as non-blocking warnings.

Coverage Target: >=85%
Test Count: 12 tests
"""

import re
from pathlib import Path
from typing import Any, Dict

import pytest

from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def coach_validator(tmp_path: Path) -> CoachValidator:
    """Create a CoachValidator instance with a temporary worktree."""
    return CoachValidator(worktree_path=str(tmp_path))


@pytest.fixture
def task_with_consumer_context() -> Dict[str, Any]:
    """Create a task with consumer_context metadata."""
    return {
        "acceptance_criteria": ["AC-001: Models work"],
        "task_type": "feature",
        "requires_infrastructure": [],
        "_docker_available": False,
        "consumer_context": [
            {
                "task": "TASK-DB-001",
                "consumes": "DATABASE_URL",
                "framework": "SQLAlchemy async (create_async_engine)",
                "driver": "asyncpg",
                "format_note": "URL must include +asyncpg dialect suffix for async engine",
            }
        ],
    }


@pytest.fixture
def task_without_consumer_context() -> Dict[str, Any]:
    """Create a task without consumer_context."""
    return {
        "acceptance_criteria": ["AC-001: Tests pass"],
        "task_type": "feature",
        "requires_infrastructure": [],
        "_docker_available": False,
        "consumer_context": [],
    }


@pytest.fixture
def worktree_with_compose(tmp_path: Path) -> Path:
    """Create a worktree with docker-compose.yml containing DATABASE_URL."""
    compose = tmp_path / "docker-compose.yml"
    compose.write_text(
        "services:\n"
        "  postgres:\n"
        "    environment:\n"
        '      DATABASE_URL: "postgresql+asyncpg://user:pass@localhost:5432/testdb"\n'
    )
    return tmp_path


@pytest.fixture
def worktree_with_wrong_dialect(tmp_path: Path) -> Path:
    """Create a worktree with docker-compose.yml using wrong dialect."""
    compose = tmp_path / "docker-compose.yml"
    compose.write_text(
        "services:\n"
        "  postgres:\n"
        "    environment:\n"
        '      DATABASE_URL: "postgresql://user:pass@localhost:5432/testdb"\n'
    )
    return tmp_path


@pytest.fixture
def worktree_with_env_file(tmp_path: Path) -> Path:
    """Create a worktree with .env file containing DATABASE_URL."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/testdb\n"
    )
    return tmp_path


# ============================================================================
# _validate_consumer_context tests
# ============================================================================


def test_validate_consumer_context_empty(
    coach_validator: CoachValidator,
    task_without_consumer_context: Dict[str, Any],
) -> None:
    """No consumer_context in task returns empty issues."""
    issues = coach_validator._validate_consumer_context(
        task_without_consumer_context, {}
    )
    assert issues == []


def test_validate_consumer_context_no_artifact_found(
    coach_validator: CoachValidator,
    task_with_consumer_context: Dict[str, Any],
) -> None:
    """consumer_context present but artifact not in worktree returns empty."""
    issues = coach_validator._validate_consumer_context(
        task_with_consumer_context, {}
    )
    assert issues == []


def test_validate_consumer_context_match(
    worktree_with_compose: Path,
    task_with_consumer_context: Dict[str, Any],
) -> None:
    """DATABASE_URL matches format_note — no issues."""
    validator = CoachValidator(worktree_path=str(worktree_with_compose))
    issues = validator._validate_consumer_context(
        task_with_consumer_context, {}
    )
    assert issues == []


def test_validate_consumer_context_mismatch(
    worktree_with_wrong_dialect: Path,
    task_with_consumer_context: Dict[str, Any],
) -> None:
    """DATABASE_URL uses wrong dialect — produces warning issue."""
    validator = CoachValidator(worktree_path=str(worktree_with_wrong_dialect))
    issues = validator._validate_consumer_context(
        task_with_consumer_context, {}
    )
    assert len(issues) == 1
    assert issues[0]["severity"] == "consider"
    assert issues[0]["category"] == "consumer_context_mismatch"
    assert "postgresql://" in issues[0]["description"]
    assert "TASK-DB-001" in issues[0]["description"]


def test_validate_consumer_context_missing_fields(
    coach_validator: CoachValidator,
) -> None:
    """consumer_context entries with missing fields are skipped."""
    task = {
        "consumer_context": [
            {"task": "TASK-001"},  # Missing consumes and format_note
            {"consumes": "DB_URL"},  # Missing format_note
        ],
    }
    issues = coach_validator._validate_consumer_context(task, {})
    assert issues == []


def test_validate_consumer_context_non_dict_entry(
    coach_validator: CoachValidator,
) -> None:
    """Non-dict entries in consumer_context are skipped."""
    task = {
        "consumer_context": ["not a dict", 42, None],
    }
    issues = coach_validator._validate_consumer_context(task, {})
    assert issues == []


# ============================================================================
# _find_artifact_value tests
# ============================================================================


def test_find_artifact_value_docker_compose(
    worktree_with_compose: Path,
) -> None:
    """Finds artifact value in docker-compose.yml."""
    validator = CoachValidator(worktree_path=str(worktree_with_compose))
    value = validator._find_artifact_value("DATABASE_URL")
    assert value is not None
    assert "postgresql+asyncpg://" in value


def test_find_artifact_value_env_file(
    worktree_with_env_file: Path,
) -> None:
    """Finds artifact value in .env file."""
    validator = CoachValidator(worktree_path=str(worktree_with_env_file))
    value = validator._find_artifact_value("DATABASE_URL")
    assert value is not None
    assert "postgresql+asyncpg://" in value


def test_find_artifact_value_docker_compose_yaml_extension(
    tmp_path: Path,
) -> None:
    """Finds artifact value in docker-compose.yaml (yaml extension)."""
    compose = tmp_path / "docker-compose.yaml"
    compose.write_text(
        "services:\n"
        "  postgres:\n"
        "    environment:\n"
        "      DATABASE_URL: postgresql+asyncpg://u:p@host/db\n"
    )
    validator = CoachValidator(worktree_path=str(tmp_path))
    value = validator._find_artifact_value("DATABASE_URL")
    assert value is not None
    assert "+asyncpg" in value


def test_find_artifact_value_env_test_file(
    tmp_path: Path,
) -> None:
    """Finds artifact value in .env.test file."""
    env_file = tmp_path / ".env.test"
    env_file.write_text("DATABASE_URL=postgresql+asyncpg://u:p@host/db\n")
    validator = CoachValidator(worktree_path=str(tmp_path))
    value = validator._find_artifact_value("DATABASE_URL")
    assert value is not None
    assert "+asyncpg" in value


def test_find_artifact_value_not_found(
    coach_validator: CoachValidator,
) -> None:
    """Returns None when artifact not in any file."""
    value = coach_validator._find_artifact_value("NONEXISTENT_VAR")
    assert value is None


def test_find_artifact_value_unreadable_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns None when file raises OSError."""
    compose = tmp_path / "docker-compose.yml"
    compose.write_text("DATABASE_URL: some_value\n")

    # Make the file unreadable by patching read_text to raise
    original_read_text = Path.read_text

    def mock_read_text(self, *args, **kwargs):
        if self.name == "docker-compose.yml":
            raise OSError("Permission denied")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", mock_read_text)
    validator = CoachValidator(worktree_path=str(tmp_path))
    value = validator._find_artifact_value("DATABASE_URL")
    assert value is None


# ============================================================================
# _format_note_matches tests
# ============================================================================


def test_format_note_matches_url_pattern(
    coach_validator: CoachValidator,
) -> None:
    """Extracts +asyncpg pattern and matches."""
    assert coach_validator._format_note_matches(
        "postgresql+asyncpg://user:pass@host/db",
        "URL must include +asyncpg dialect suffix for async engine",
    )


def test_format_note_mismatch(
    coach_validator: CoachValidator,
) -> None:
    """format_note says +asyncpg but value has plain postgresql://."""
    assert not coach_validator._format_note_matches(
        "postgresql://user:pass@host/db",
        "URL must include +asyncpg dialect suffix for async engine",
    )


def test_format_note_no_extractable_pattern(
    coach_validator: CoachValidator,
) -> None:
    """format_note with no URL pattern returns True (safe default)."""
    assert coach_validator._format_note_matches(
        "some_value",
        "Value should be a valid configuration string",
    )
