"""Unit tests for `guardkit graphiti capture-outcome` (TASK-FIX-CLI7).

Covers:
- Frontmatter parser: task-file → structured fields mapping.
- Explicit-flag invocation.
- `--from-task-file` invocation with frontmatter overrides.
- Validation errors when required fields are missing.
- Dry-run path (no Graphiti contact).
- No-op-vs-real-write distinction (default lenient + ``--strict``).
- Successful write delegation to ``capture_task_outcome``.

Live writes are NOT exercised here — we mock both the GraphitiClient
factory and ``capture_task_outcome`` so the tests run offline. A live
integration test gated on ``GUARDKIT_TEST_GRAPHITI_LIVE=1`` is filed
separately in the task; not part of this unit suite.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from guardkit.cli.graphiti import (
    _parse_task_file_for_outcome,
    capture_outcome,
    graphiti,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def task_file_full(tmp_path: Path) -> Path:
    """A well-formed completed task file with all the optional sections."""
    content = """---
id: TASK-FIX-EXAMPLE
title: Example completed task
status: completed
created: 2026-04-25T00:00:00Z
priority: medium
task_type: implementation
parent_review: TASK-REV-EXAMPLE
related_to:
  - TASK-REV-EXAMPLE
  - TASK-OTHER-XYZ
feature_id: FEAT-EXAMPLE
complexity: 4
---

# Task: Example completed task

## Why

We needed to fix the silent-no-op pattern in the outcome capture path
so that operators can tell a real write apart from a degraded fallback.

## Description

Original task description goes here.

## Acceptance Criteria

- [x] Some criterion that was satisfied.

## Implementation Summary

The change adds a defaulted `from_prior_run` boolean field on the
`Checkpoint` dataclass and updates `should_rollback()` to filter to
`from_prior_run is False` before counting consecutive failures.

A second paragraph that the parser should ignore.

## Implementation Notes

Manager-level fix at the single producer of the pollution signal.
Runtime tag, not persisted truth — load-time override resolves
session-boundary semantics unambiguously.

## Notes

- Manager-level fix beats classifier-level fix when callers consult
  the manager exclusively.
- When a persisted field's meaning differs across session boundaries,
  make it a runtime tag set at load-time rather than relying on the
  persisted value.
- Sibling task TASK-DIAG-EXAMPLE depends on this fix.
"""
    path = tmp_path / "TASK-FIX-EXAMPLE.md"
    path.write_text(content)
    return path


@pytest.fixture
def task_file_minimal(tmp_path: Path) -> Path:
    """A task file with frontmatter only — no `## Implementation Summary`."""
    content = """---
id: TASK-FIX-MIN
title: Minimal task
---

# Task: Minimal task

Body text without any structured sections the parser would pick up.
"""
    path = tmp_path / "TASK-FIX-MIN.md"
    path.write_text(content)
    return path


@pytest.fixture
def mock_client_enabled():
    """A mocked GraphitiClient that initialises successfully."""
    client = AsyncMock()
    client.enabled = True
    client.default_timeout_override = None
    client.initialize = AsyncMock(return_value=True)
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_client_disabled():
    """A mocked GraphitiClient that connects but is disabled."""
    client = AsyncMock()
    client.enabled = False
    client.default_timeout_override = None
    client.initialize = AsyncMock(return_value=True)
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.enabled = True
    return settings


@pytest.fixture
def patch_get_graphiti(mock_client_enabled):
    """Patch get_graphiti at every site that imports it.

    Both the CLI (`guardkit.cli.graphiti.get_graphiti`) and the inner
    Python API (`guardkit.knowledge.outcome_manager.get_graphiti`) need
    to return the same mocked client instance for the test to mirror the
    real shared-thread-local-client invariant.
    """
    with patch(
        "guardkit.cli.graphiti.get_graphiti", return_value=mock_client_enabled
    ), patch(
        "guardkit.knowledge.outcome_manager.get_graphiti",
        return_value=mock_client_enabled,
    ):
        yield mock_client_enabled


@pytest.fixture
def patch_get_graphiti_disabled(mock_client_disabled):
    """Patch get_graphiti at both call sites with a disabled client."""
    with patch(
        "guardkit.cli.graphiti.get_graphiti", return_value=mock_client_disabled
    ), patch(
        "guardkit.knowledge.outcome_manager.get_graphiti",
        return_value=mock_client_disabled,
    ):
        yield mock_client_disabled


@pytest.fixture
def patch_get_graphiti_none():
    """Patch get_graphiti to return None (config disabled / load failure)."""
    with patch(
        "guardkit.cli.graphiti.get_graphiti", return_value=None
    ), patch(
        "guardkit.knowledge.outcome_manager.get_graphiti", return_value=None
    ):
        yield


# ============================================================================
# Frontmatter parser
# ============================================================================


class TestParseTaskFileForOutcome:
    def test_extracts_core_frontmatter_fields(self, task_file_full):
        result = _parse_task_file_for_outcome(task_file_full)
        assert result["task_id"] == "TASK-FIX-EXAMPLE"
        assert result["task_title"] == "Example completed task"
        assert result["complexity"] == 4
        assert result["feature_id"] == "FEAT-EXAMPLE"

    def test_extracts_implementation_summary_first_paragraph(self, task_file_full):
        result = _parse_task_file_for_outcome(task_file_full)
        assert result["summary"] is not None
        assert "from_prior_run" in result["summary"]
        # Second paragraph in the section must be excluded.
        assert "ignore" not in result["summary"]

    def test_extracts_implementation_notes_as_approach(self, task_file_full):
        result = _parse_task_file_for_outcome(task_file_full)
        assert result["approach_used"] is not None
        assert "Manager-level fix" in result["approach_used"]

    def test_extracts_notes_bullets_as_lessons(self, task_file_full):
        result = _parse_task_file_for_outcome(task_file_full)
        assert len(result["lessons_learned"]) == 3
        assert "Manager-level fix" in result["lessons_learned"][0]
        assert "TASK-DIAG-EXAMPLE" in result["lessons_learned"][2]

    def test_related_adr_ids_combines_parent_review_and_related_to(self, task_file_full):
        result = _parse_task_file_for_outcome(task_file_full)
        assert "TASK-REV-EXAMPLE" in result["related_adr_ids"]
        assert "TASK-OTHER-XYZ" in result["related_adr_ids"]
        # parent_review duplicated in related_to should not appear twice.
        assert result["related_adr_ids"].count("TASK-REV-EXAMPLE") == 1

    def test_minimal_task_file_has_empty_optional_fields(self, task_file_minimal):
        result = _parse_task_file_for_outcome(task_file_minimal)
        assert result["task_id"] == "TASK-FIX-MIN"
        assert result["task_title"] == "Minimal task"
        assert result["summary"] is None
        assert result["approach_used"] is None
        assert result["lessons_learned"] == []
        assert result["related_adr_ids"] == []

    def test_invalid_frontmatter_raises_value_error(self, tmp_path):
        path = tmp_path / "no-frontmatter.md"
        path.write_text("Just a body, no frontmatter delimiters.")
        with pytest.raises(ValueError, match="missing YAML frontmatter delimiters"):
            _parse_task_file_for_outcome(path)


# ============================================================================
# CLI: validation and dry-run
# ============================================================================


class TestCaptureOutcomeValidation:
    def test_missing_required_fields_exits_2(self, cli_runner):
        # No --from-task-file, no --task-id — must fail validation.
        result = cli_runner.invoke(graphiti, ["capture-outcome", "--dry-run"])
        assert result.exit_code == 2
        assert "missing required field" in result.output

    def test_dry_run_with_task_file_does_not_contact_graphiti(
        self, cli_runner, task_file_full
    ):
        # Mock get_graphiti: must NOT be called during dry-run.
        with patch("guardkit.cli.graphiti.get_graphiti") as mock_factory:
            result = cli_runner.invoke(
                graphiti,
                ["capture-outcome", "--from-task-file", str(task_file_full), "--dry-run"],
            )
        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        assert "TASK-FIX-EXAMPLE" in result.output
        assert "task_outcomes" in result.output
        mock_factory.assert_not_called()

    def test_explicit_flags_override_task_file(self, cli_runner, task_file_full):
        with patch("guardkit.cli.graphiti.get_graphiti"):
            result = cli_runner.invoke(
                graphiti,
                [
                    "capture-outcome",
                    "--from-task-file",
                    str(task_file_full),
                    "--task-id",
                    "TASK-OVERRIDE",
                    "--summary",
                    "Override summary",
                    "--dry-run",
                ],
            )
        assert result.exit_code == 0
        assert "TASK-OVERRIDE" in result.output
        assert "Override summary" in result.output
        # Original task_id from frontmatter must NOT appear.
        assert "TASK-FIX-EXAMPLE" not in result.output


# ============================================================================
# CLI: no-op vs real write distinction
# ============================================================================


class TestCaptureOutcomeNoOpVsRealWrite:
    def test_unavailable_client_default_warns_exit_0(
        self, cli_runner, task_file_full, patch_get_graphiti_disabled
    ):
        result = cli_runner.invoke(
            graphiti,
            ["capture-outcome", "--from-task-file", str(task_file_full)],
        )
        assert result.exit_code == 0
        assert "outcome NOT captured" in result.output
        assert "Outcome captured" not in result.output

    def test_unavailable_client_strict_exits_1(
        self, cli_runner, task_file_full, patch_get_graphiti_disabled
    ):
        result = cli_runner.invoke(
            graphiti,
            ["capture-outcome", "--from-task-file", str(task_file_full), "--strict"],
        )
        assert result.exit_code == 1
        assert "outcome NOT captured" in result.output

    def test_get_graphiti_returns_none_default_warns_exit_0(
        self, cli_runner, task_file_full, patch_get_graphiti_none
    ):
        # Covers the new branch: factory says config is disabled / load
        # failed → get_graphiti() returns None. Must surface "unavailable"
        # not "Outcome captured", and exit 0 in lenient mode.
        result = cli_runner.invoke(
            graphiti,
            ["capture-outcome", "--from-task-file", str(task_file_full)],
        )
        assert result.exit_code == 0
        assert "Graphiti unavailable" in result.output
        assert "Outcome captured" not in result.output

    def test_get_graphiti_returns_none_strict_exits_1(
        self, cli_runner, task_file_full, patch_get_graphiti_none
    ):
        result = cli_runner.invoke(
            graphiti,
            ["capture-outcome", "--from-task-file", str(task_file_full), "--strict"],
        )
        assert result.exit_code == 1
        assert "Graphiti unavailable" in result.output


# ============================================================================
# CLI: real write delegation
# ============================================================================


class TestCaptureOutcomeRealWrite:
    def test_calls_capture_task_outcome_with_parsed_fields(
        self, cli_runner, task_file_full, patch_get_graphiti
    ):
        async def fake_capture(**kwargs):
            return "OUT-FAKE1234"

        with patch(
            "guardkit.knowledge.outcome_manager.capture_task_outcome",
            side_effect=fake_capture,
        ) as mock_capture:
            result = cli_runner.invoke(
                graphiti,
                ["capture-outcome", "--from-task-file", str(task_file_full)],
            )

        assert result.exit_code == 0, result.output
        assert "Outcome captured: OUT-FAKE1234" in result.output
        assert "task_outcomes" in result.output

        mock_capture.assert_called_once()
        kwargs = mock_capture.call_args.kwargs
        assert kwargs["task_id"] == "TASK-FIX-EXAMPLE"
        assert kwargs["task_title"] == "Example completed task"
        assert kwargs["success"] is True
        assert "from_prior_run" in kwargs["summary"]
        assert kwargs["feature_id"] == "FEAT-EXAMPLE"
        assert "TASK-REV-EXAMPLE" in (kwargs["related_adr_ids"] or [])
        # 3 lessons from the `## Notes` bullets.
        assert len(kwargs["lessons_learned"] or []) == 3

    def test_failure_flag_sets_task_failed_outcome_type(
        self, cli_runner, task_file_full, patch_get_graphiti
    ):
        async def fake_capture(**kwargs):
            return "OUT-FAIL5678"

        with patch(
            "guardkit.knowledge.outcome_manager.capture_task_outcome",
            side_effect=fake_capture,
        ) as mock_capture:
            result = cli_runner.invoke(
                graphiti,
                [
                    "capture-outcome",
                    "--from-task-file",
                    str(task_file_full),
                    "--failure",
                ],
            )

        assert result.exit_code == 0, result.output
        kwargs = mock_capture.call_args.kwargs
        assert kwargs["outcome_type"].name == "TASK_FAILED"
        assert kwargs["success"] is False

    def test_timeout_flag_applied_to_client(
        self, cli_runner, task_file_full, patch_get_graphiti, mock_client_enabled
    ):
        async def fake_capture(**kwargs):
            return "OUT-TO9999"

        with patch(
            "guardkit.knowledge.outcome_manager.capture_task_outcome",
            side_effect=fake_capture,
        ):
            result = cli_runner.invoke(
                graphiti,
                [
                    "capture-outcome",
                    "--from-task-file",
                    str(task_file_full),
                    "--timeout",
                    "450",
                ],
            )

        assert result.exit_code == 0, result.output
        # Timeout override applied to the factory-managed client (which is
        # also what capture_task_outcome would use if it weren't mocked).
        assert mock_client_enabled.default_timeout_override == 450.0

    def test_uses_factory_managed_client_not_fresh_client(
        self, cli_runner, task_file_full, patch_get_graphiti, mock_client_enabled
    ):
        """Regression: CLI must use get_graphiti() so capture_task_outcome's
        internal get_graphiti() returns the same (initialized) client.

        Earlier the CLI built a fresh client via _get_client_and_config(),
        which left the factory's thread-local store empty. capture_task_outcome
        then created a SECOND, uninitialised client via get_graphiti() and
        silently no-op'd while the CLI happily printed "captured" — phantom
        write. This test pins that the CLI now goes through get_graphiti().
        """
        async def fake_capture(**kwargs):
            return "OUT-SHARED"

        with patch(
            "guardkit.knowledge.outcome_manager.capture_task_outcome",
            side_effect=fake_capture,
        ):
            result = cli_runner.invoke(
                graphiti,
                ["capture-outcome", "--from-task-file", str(task_file_full)],
            )

        assert result.exit_code == 0, result.output
        # The factory-managed client received the timeout override and the
        # initialize() call — both touched the same instance.
        mock_client_enabled.initialize.assert_awaited_once()
        mock_client_enabled.close.assert_awaited_once()
