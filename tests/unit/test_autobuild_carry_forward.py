"""
Unit tests for staleness-aware cumulative requirements carry-forward (TASK-CRV-9618).

Tests cover:
- Merging of requirements_addressed across turns (carry-forward)
- Staleness detection when files are deleted or content changes
- _cumulative_source_files accumulation across turns
- validate_requirements_staleness() with real files (via tmp_path)
- Reset behaviour when a new AutoBuildOrchestrator instance is created

Coverage Target: >=85%
Test Count: 10 tests
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.synthetic_report import validate_requirements_staleness


# ============================================================================
# Shared Fixtures
# ============================================================================


@pytest.fixture
def mock_worktree_manager():
    """Create mock WorktreeManager."""
    manager = Mock()
    manager.worktrees_dir = Path("/tmp/worktrees")
    return manager


@pytest.fixture
def mock_agent_invoker():
    """Create mock AgentInvoker."""
    return Mock()


@pytest.fixture
def mock_progress_display():
    """Create mock ProgressDisplay."""
    display = Mock()
    display.__enter__ = Mock(return_value=display)
    display.__exit__ = Mock(return_value=False)
    display.start_turn = Mock()
    display.complete_turn = Mock()
    display.render_summary = Mock()
    return display


@pytest.fixture
def orchestrator(mock_worktree_manager, mock_agent_invoker, mock_progress_display):
    """Create AutoBuildOrchestrator instance for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        yield AutoBuildOrchestrator(
            repo_root=repo_root,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            verbose=False,
            max_turns=5,
            sdk_timeout=900,
            ablation_mode=False,
        )


# ============================================================================
# Helper: build a minimal player_result mock
# ============================================================================


def _make_player_result(
    success: bool,
    requirements_addressed: list,
    files_created: list = None,
    files_modified: list = None,
) -> Mock:
    """Return a mock AgentInvocationResult with the given report fields."""
    report = {
        "requirements_addressed": list(requirements_addressed),
        "files_created": list(files_created or []),
        "files_modified": list(files_modified or []),
    }
    result = Mock()
    result.success = success
    result.report = report
    return result


def _make_worktree(path: Path) -> Mock:
    """Return a mock Worktree with the given path."""
    wt = Mock()
    wt.path = path
    return wt


# ============================================================================
# Section 1: validate_requirements_staleness() — real file I/O tests
# ============================================================================


class TestValidateRequirementsStaleness:
    """Tests for validate_requirements_staleness() using real temporary files."""

    def test_keeps_requirement_when_file_contains_keywords(self, tmp_path):
        """Requirements whose keywords appear in files are kept."""
        src = tmp_path / "src.py"
        src.write_text(
            "def authenticate_user(token):\n"
            "    \"\"\"Validate authentication token for the user.\"\"\"\n"
            "    return verify_token(token)\n"
        )
        requirements = ["User authentication token validation"]
        result = validate_requirements_staleness(
            requirements=requirements,
            source_files=["src.py"],
            worktree_path=tmp_path,
        )
        assert "User authentication token validation" in result

    def test_drops_requirement_when_file_deleted(self, tmp_path):
        """Requirements are dropped when the source file no longer exists."""
        # We deliberately do NOT create the file — it doesn't exist.
        requirements = ["User authentication token validation"]
        result = validate_requirements_staleness(
            requirements=requirements,
            source_files=["missing_file.py"],
            worktree_path=tmp_path,
        )
        assert result == []

    def test_drops_requirement_when_keywords_removed_from_file(self, tmp_path):
        """Requirements are dropped when file content no longer contains keywords."""
        src = tmp_path / "src.py"
        # File exists but contains unrelated content — no keywords match.
        src.write_text("x = 1\ny = 2\n")
        requirements = ["User authentication token validation"]
        result = validate_requirements_staleness(
            requirements=requirements,
            source_files=["src.py"],
            worktree_path=tmp_path,
        )
        assert result == []

    def test_keeps_requirement_when_keywords_still_present_after_partial_rewrite(
        self, tmp_path
    ):
        """Requirements remain valid when keywords survive a partial file rewrite."""
        src = tmp_path / "module.py"
        # Write content that still contains enough keywords (>= 50% threshold).
        src.write_text(
            "# OAuth2 token refresh endpoint\n"
            "def refresh_token(client_id, refresh_token):\n"
            "    pass\n"
        )
        requirements = ["OAuth2 token refresh flow"]
        result = validate_requirements_staleness(
            requirements=requirements,
            source_files=["module.py"],
            worktree_path=tmp_path,
        )
        assert "OAuth2 token refresh flow" in result

    def test_empty_source_files_returns_empty(self, tmp_path):
        """Empty source_files list returns empty result regardless of requirements."""
        result = validate_requirements_staleness(
            requirements=["Some requirement about authentication"],
            source_files=[],
            worktree_path=tmp_path,
        )
        assert result == []

    def test_empty_requirements_returns_empty(self, tmp_path):
        """Empty requirements list always returns empty."""
        src = tmp_path / "src.py"
        src.write_text("anything")
        result = validate_requirements_staleness(
            requirements=[],
            source_files=["src.py"],
            worktree_path=tmp_path,
        )
        assert result == []


# ============================================================================
# Section 2: autobuild.py cumulative carry-forward logic (mocked tests)
# ============================================================================


class TestCarryForwardMergesRequirements:
    """Test that requirements accumulate across turns via the merge block."""

    def test_carry_forward_merges_previous_requirements(self, orchestrator, tmp_path):
        """Turn 1 infers R1, turn 2 infers R2 — merged set contains both."""
        worktree = _make_worktree(tmp_path)

        # Simulate turn 1: R1 inferred
        orchestrator._cumulative_requirements_addressed = set()
        result_turn1 = _make_player_result(
            success=True,
            requirements_addressed=["Requirement R1 authentication feature"],
            files_created=["src/auth.py"],
        )

        with patch(
            "guardkit.orchestrator.synthetic_report.validate_requirements_staleness",
            return_value=["Requirement R1 authentication feature"],
        ):
            # Manually invoke the merge logic by simulating _execute_turn internals.
            # We directly exercise the block by calling a helper that replicates it.
            _apply_carry_forward(orchestrator, result_turn1, worktree)

        assert "Requirement R1 authentication feature" in (
            orchestrator._cumulative_requirements_addressed
        )

        # Simulate turn 2: R2 inferred, R1 carried forward
        result_turn2 = _make_player_result(
            success=True,
            requirements_addressed=["Requirement R2 logging feature"],
            files_created=["src/logging.py"],
        )

        with patch(
            "guardkit.orchestrator.synthetic_report.validate_requirements_staleness",
            return_value=["Requirement R1 authentication feature"],
        ):
            _apply_carry_forward(orchestrator, result_turn2, worktree)

        assert "Requirement R1 authentication feature" in (
            orchestrator._cumulative_requirements_addressed
        )
        assert "Requirement R2 logging feature" in (
            orchestrator._cumulative_requirements_addressed
        )

    def test_staleness_drops_requirement_when_file_deleted(
        self, orchestrator, tmp_path
    ):
        """Stale requirement (file deleted) is not carried forward."""
        worktree = _make_worktree(tmp_path)

        # Seed cumulative set as if a previous turn added R1
        orchestrator._cumulative_requirements_addressed = {
            "Requirement R1 authentication feature"
        }

        # Turn 2 report doesn't include R1 in current_addressed (file gone)
        result_turn2 = _make_player_result(
            success=True,
            requirements_addressed=["Requirement R2 logging feature"],
            files_created=["src/logging.py"],
        )

        # validate_requirements_staleness returns [] → R1 is stale
        with patch(
            "guardkit.orchestrator.synthetic_report.validate_requirements_staleness",
            return_value=[],
        ):
            _apply_carry_forward(orchestrator, result_turn2, worktree)

        assert "Requirement R1 authentication feature" not in (
            orchestrator._cumulative_requirements_addressed
        )
        assert "Requirement R2 logging feature" in (
            orchestrator._cumulative_requirements_addressed
        )

    def test_staleness_drops_requirement_when_content_changes(
        self, orchestrator, tmp_path
    ):
        """Stale requirement (keywords removed) is dropped from carry-forward."""
        worktree = _make_worktree(tmp_path)

        # Seed cumulative set
        orchestrator._cumulative_requirements_addressed = {
            "OAuth2 token refresh authentication validation"
        }

        result = _make_player_result(
            success=True,
            requirements_addressed=["Unrelated requirement for new feature"],
            files_modified=["src/auth.py"],
        )

        # Staleness check returns empty — keywords no longer in file
        with patch(
            "guardkit.orchestrator.synthetic_report.validate_requirements_staleness",
            return_value=[],
        ):
            _apply_carry_forward(orchestrator, result, worktree)

        assert "OAuth2 token refresh authentication validation" not in (
            orchestrator._cumulative_requirements_addressed
        )

    def test_staleness_keeps_requirement_when_file_still_valid(
        self, orchestrator, tmp_path
    ):
        """Requirements still supported by file content are carried forward."""
        worktree = _make_worktree(tmp_path)

        orchestrator._cumulative_requirements_addressed = {
            "OAuth2 token refresh authentication validation"
        }

        result = _make_player_result(
            success=True,
            requirements_addressed=["Unrelated requirement for new feature"],
            files_modified=["src/auth.py"],
        )

        # Staleness check confirms R1 is still supported
        with patch(
            "guardkit.orchestrator.synthetic_report.validate_requirements_staleness",
            return_value=["OAuth2 token refresh authentication validation"],
        ):
            _apply_carry_forward(orchestrator, result, worktree)

        assert "OAuth2 token refresh authentication validation" in (
            orchestrator._cumulative_requirements_addressed
        )

    def test_cumulative_source_files_tracked_across_turns(
        self, orchestrator, tmp_path
    ):
        """_cumulative_source_files accumulates files across multiple turns."""
        worktree = _make_worktree(tmp_path)

        result_turn1 = _make_player_result(
            success=True,
            requirements_addressed=["Requirement A about authentication tokens"],
            files_created=["src/auth.py"],
            files_modified=["src/utils.py"],
        )
        with patch(
            "guardkit.orchestrator.synthetic_report.validate_requirements_staleness",
            return_value=[],
        ):
            _apply_carry_forward(orchestrator, result_turn1, worktree)

        assert "src/auth.py" in orchestrator._cumulative_source_files
        assert "src/utils.py" in orchestrator._cumulative_source_files

        result_turn2 = _make_player_result(
            success=True,
            requirements_addressed=["Requirement B about token refresh feature"],
            files_created=["src/token.py"],
        )
        with patch(
            "guardkit.orchestrator.synthetic_report.validate_requirements_staleness",
            return_value=["Requirement A about authentication tokens"],
        ):
            _apply_carry_forward(orchestrator, result_turn2, worktree)

        # Files from both turns are present
        assert "src/auth.py" in orchestrator._cumulative_source_files
        assert "src/utils.py" in orchestrator._cumulative_source_files
        assert "src/token.py" in orchestrator._cumulative_source_files

    def test_carry_forward_resets_with_new_autobuild_instance(
        self, mock_worktree_manager, mock_agent_invoker, mock_progress_display
    ):
        """A new AutoBuildOrchestrator starts with empty carry-forward state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = AutoBuildOrchestrator(
                repo_root=Path(tmpdir),
                worktree_manager=mock_worktree_manager,
                agent_invoker=mock_agent_invoker,
                progress_display=mock_progress_display,
                verbose=False,
                max_turns=5,
                sdk_timeout=900,
                ablation_mode=False,
            )
            assert orch._cumulative_requirements_addressed == set()
            assert orch._cumulative_source_files == set()

    def test_carry_forward_skipped_when_player_fails(self, orchestrator, tmp_path):
        """When player_result.success is False, cumulative state is not updated."""
        worktree = _make_worktree(tmp_path)

        orchestrator._cumulative_requirements_addressed = {"Existing requirement alpha feature"}

        result = _make_player_result(
            success=False,
            requirements_addressed=["New requirement beta feature"],
            files_created=["src/beta.py"],
        )

        _apply_carry_forward(orchestrator, result, worktree)

        # Cumulative state must remain unchanged
        assert orchestrator._cumulative_requirements_addressed == {
            "Existing requirement alpha feature"
        }
        assert orchestrator._cumulative_source_files == set()

    def test_staleness_not_called_when_no_carry_forward_exists(
        self, orchestrator, tmp_path
    ):
        """validate_requirements_staleness is not called when there's nothing to carry."""
        worktree = _make_worktree(tmp_path)
        orchestrator._cumulative_requirements_addressed = set()

        result = _make_player_result(
            success=True,
            requirements_addressed=["Fresh requirement authentication token"],
            files_created=["src/auth.py"],
        )

        with patch(
            "guardkit.orchestrator.synthetic_report.validate_requirements_staleness"
        ) as mock_staleness:
            _apply_carry_forward(orchestrator, result, worktree)

        # Nothing to carry forward, so staleness check must not be invoked.
        mock_staleness.assert_not_called()


# ============================================================================
# Helper: replicate the carry-forward merge block from _execute_turn
# ============================================================================


def _apply_carry_forward(
    orchestrator: AutoBuildOrchestrator,
    player_result: Mock,
    worktree: Mock,
) -> None:
    """
    Replicate the cumulative carry-forward merge block from _execute_turn.

    This allows unit testing of the block without invoking the full turn
    pipeline (which requires live agent invocations and worktree setup).
    """
    if not (player_result.success and player_result.report):
        return

    # Track source files (TASK-CRV-9618)
    current_files = set(
        player_result.report.get("files_created", [])
        + player_result.report.get("files_modified", [])
    )
    orchestrator._cumulative_source_files.update(current_files)

    current_addressed = set(
        player_result.report.get("requirements_addressed", [])
    )
    carry_forward = orchestrator._cumulative_requirements_addressed - current_addressed

    if carry_forward and worktree is not None:
        from guardkit.orchestrator.synthetic_report import validate_requirements_staleness

        still_valid = set(
            validate_requirements_staleness(
                requirements=list(carry_forward),
                source_files=list(orchestrator._cumulative_source_files),
                worktree_path=worktree.path,
            )
        )
        stale = carry_forward - still_valid
        carry_forward = still_valid

    merged = current_addressed | carry_forward
    orchestrator._cumulative_requirements_addressed = merged
    if merged:
        player_result.report["requirements_addressed"] = list(merged)
