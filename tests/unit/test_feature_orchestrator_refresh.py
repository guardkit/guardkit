"""
Unit tests for FeatureOrchestrator --refresh flag.

Tests the worktree refresh-on-resume feature (TASK-FIX-7533):
- Init parameter validation (refresh/fresh mutual exclusion, refresh implies resume)
- _refresh_worktree method (fetch, rebase, conflict abort)
- Integration with _setup_phase resume paths
- Extended _prompt_resume with [U]pdate option

Coverage Target: >=80%
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    FeatureOrchestrationError,
)
from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureTask,
    FeatureOrchestration,
    FeatureExecution,
    FeatureLoader,
)
from guardkit.worktrees import Worktree


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_worktree_manager():
    """Provide a mock WorktreeManager."""
    manager = MagicMock()
    manager.worktrees_dir = Path("/tmp/worktrees")
    return manager


@pytest.fixture
def sample_worktree(tmp_path) -> Worktree:
    """Provide a sample Worktree for testing."""
    wt_path = tmp_path / "worktree"
    wt_path.mkdir()
    return Worktree(
        task_id="FEAT-TEST",
        branch_name="autobuild/FEAT-TEST",
        path=wt_path,
        base_branch="main",
    )


@pytest.fixture
def sample_feature() -> Feature:
    """Provide a sample Feature for testing."""
    return Feature(
        id="FEAT-TEST",
        name="Test Feature",
        description="Test feature for refresh tests",
        created="2025-12-31T12:00:00Z",
        status="in_progress",
        complexity=5,
        estimated_tasks=2,
        tasks=[
            FeatureTask(
                id="TASK-T-001",
                name="First Task",
                file_path=Path("tasks/backlog/TASK-T-001.md"),
                complexity=3,
                dependencies=[],
                status="completed",
                implementation_mode="task-work",
                estimated_minutes=30,
            ),
            FeatureTask(
                id="TASK-T-002",
                name="Second Task",
                file_path=Path("tasks/backlog/TASK-T-002.md"),
                complexity=5,
                dependencies=["TASK-T-001"],
                status="pending",
                implementation_mode="task-work",
                estimated_minutes=45,
            ),
        ],
        orchestration=FeatureOrchestration(
            parallel_groups=[
                ["TASK-T-001"],
                ["TASK-T-002"],
            ],
            estimated_duration_minutes=75,
            recommended_parallel=1,
        ),
        execution=FeatureExecution(),
    )


# ============================================================================
# TestRefreshInit - Parameter validation
# ============================================================================


class TestRefreshInit:
    """Test refresh parameter in FeatureOrchestrator.__init__."""

    def test_refresh_default_is_false(self, mock_worktree_manager):
        """Verify refresh defaults to False."""
        orch = FeatureOrchestrator(
            repo_root=Path("/tmp"),
            worktree_manager=mock_worktree_manager,
        )
        assert orch.refresh is False

    def test_refresh_auto_enables_resume(self, mock_worktree_manager):
        """Verify refresh=True sets resume=True."""
        orch = FeatureOrchestrator(
            repo_root=Path("/tmp"),
            refresh=True,
            worktree_manager=mock_worktree_manager,
        )
        assert orch.refresh is True
        assert orch.resume is True

    def test_refresh_and_fresh_raises_value_error(self, mock_worktree_manager):
        """Verify ValueError when both refresh and fresh are True."""
        with pytest.raises(ValueError, match="Cannot use both --refresh and --fresh"):
            FeatureOrchestrator(
                repo_root=Path("/tmp"),
                refresh=True,
                fresh=True,
                worktree_manager=mock_worktree_manager,
            )

    def test_refresh_without_explicit_resume(self, mock_worktree_manager):
        """Verify refresh works without explicitly setting resume."""
        orch = FeatureOrchestrator(
            repo_root=Path("/tmp"),
            refresh=True,
            resume=False,  # refresh should override this
            worktree_manager=mock_worktree_manager,
        )
        assert orch.resume is True
        assert orch.refresh is True


# ============================================================================
# TestRefreshWorktree - _refresh_worktree method
# ============================================================================


class TestRefreshWorktree:
    """Test _refresh_worktree method."""

    def test_refresh_success_path(self, mock_worktree_manager, sample_worktree):
        """Verify successful fetch + rebase completes without error."""
        orch = FeatureOrchestrator(
            repo_root=Path("/tmp"),
            refresh=True,
            worktree_manager=mock_worktree_manager,
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            orch._refresh_worktree(sample_worktree, "main")

        assert mock_run.call_count == 2
        # First call: git fetch
        fetch_call = mock_run.call_args_list[0]
        assert fetch_call[0][0] == ["git", "fetch", "origin", "main"]
        assert fetch_call[1]["cwd"] == sample_worktree.path
        # Second call: git rebase
        rebase_call = mock_run.call_args_list[1]
        assert rebase_call[0][0] == ["git", "rebase", "origin/main"]
        assert rebase_call[1]["cwd"] == sample_worktree.path

    def test_refresh_fetch_failure(self, mock_worktree_manager, sample_worktree):
        """Verify FeatureOrchestrationError raised when fetch fails."""
        orch = FeatureOrchestrator(
            repo_root=Path("/tmp"),
            refresh=True,
            worktree_manager=mock_worktree_manager,
        )

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "git fetch", stderr="fatal: could not read from remote"
            )
            with pytest.raises(
                FeatureOrchestrationError, match="Failed to fetch origin/main"
            ):
                orch._refresh_worktree(sample_worktree, "main")

    def test_refresh_rebase_conflict_aborts(
        self, mock_worktree_manager, sample_worktree
    ):
        """Verify rebase conflict triggers abort and raises error."""
        orch = FeatureOrchestrator(
            repo_root=Path("/tmp"),
            refresh=True,
            worktree_manager=mock_worktree_manager,
        )

        def side_effect(*args, **kwargs):
            cmd = args[0]
            if cmd == ["git", "fetch", "origin", "main"]:
                return MagicMock(returncode=0)
            elif cmd == ["git", "rebase", "origin/main"]:
                raise subprocess.CalledProcessError(1, "git rebase")
            elif cmd == ["git", "rebase", "--abort"]:
                return MagicMock(returncode=0)
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=side_effect) as mock_run:
            with pytest.raises(
                FeatureOrchestrationError,
                match="Rebase onto origin/main failed due to conflicts",
            ):
                orch._refresh_worktree(sample_worktree, "main")

        # Verify abort was called
        abort_call = mock_run.call_args_list[2]
        assert abort_call[0][0] == ["git", "rebase", "--abort"]

    def test_refresh_rebase_conflict_abort_also_fails(
        self, mock_worktree_manager, sample_worktree
    ):
        """Verify error raised even if rebase --abort also fails."""
        orch = FeatureOrchestrator(
            repo_root=Path("/tmp"),
            refresh=True,
            worktree_manager=mock_worktree_manager,
        )

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            cmd = args[0]
            if cmd == ["git", "fetch", "origin", "main"]:
                return MagicMock(returncode=0)
            elif cmd == ["git", "rebase", "origin/main"]:
                raise subprocess.CalledProcessError(1, "git rebase")
            elif cmd == ["git", "rebase", "--abort"]:
                raise subprocess.CalledProcessError(1, "git rebase --abort")
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=side_effect):
            with pytest.raises(
                FeatureOrchestrationError,
                match="Rebase onto origin/main failed due to conflicts",
            ):
                orch._refresh_worktree(sample_worktree, "main")

    def test_refresh_custom_base_branch(
        self, mock_worktree_manager, sample_worktree
    ):
        """Verify refresh uses custom base branch."""
        orch = FeatureOrchestrator(
            repo_root=Path("/tmp"),
            refresh=True,
            worktree_manager=mock_worktree_manager,
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            orch._refresh_worktree(sample_worktree, "develop")

        fetch_call = mock_run.call_args_list[0]
        assert fetch_call[0][0] == ["git", "fetch", "origin", "develop"]
        rebase_call = mock_run.call_args_list[1]
        assert rebase_call[0][0] == ["git", "rebase", "origin/develop"]


# ============================================================================
# TestRefreshInSetupPhase - Integration with _setup_phase
# ============================================================================


class TestRefreshInSetupPhase:
    """Test refresh integration with the _setup_phase resume path."""

    def test_resume_with_refresh_calls_refresh_worktree(
        self, mock_worktree_manager, sample_feature, tmp_path
    ):
        """Verify _refresh_worktree is called when refresh=True during resume."""
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        sample_feature.execution.worktree_path = str(worktree_path)

        orch = FeatureOrchestrator(
            repo_root=tmp_path,
            refresh=True,
            worktree_manager=mock_worktree_manager,
        )

        resume_point = {
            "completed_tasks": ["TASK-T-001"],
            "pending_tasks": ["TASK-T-002"],
            "task_id": None,
            "turn": 0,
            "wave": 2,
            "worktree_path": str(worktree_path),
        }

        with (
            patch.object(FeatureLoader, "load_feature", return_value=sample_feature),
            patch.object(FeatureLoader, "validate_feature", return_value=[]),
            patch.object(FeatureLoader, "is_incomplete", return_value=True),
            patch.object(FeatureLoader, "get_resume_point", return_value=resume_point),
            patch.object(orch, "_refresh_worktree") as mock_refresh,
        ):
            feature, worktree = orch._setup_phase("FEAT-TEST", "main")

        mock_refresh.assert_called_once()
        assert worktree.path == worktree_path

    def test_resume_without_refresh_skips_refresh_worktree(
        self, mock_worktree_manager, sample_feature, tmp_path
    ):
        """Verify _refresh_worktree is NOT called when refresh=False."""
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        sample_feature.execution.worktree_path = str(worktree_path)

        orch = FeatureOrchestrator(
            repo_root=tmp_path,
            resume=True,
            refresh=False,
            worktree_manager=mock_worktree_manager,
        )

        resume_point = {
            "completed_tasks": ["TASK-T-001"],
            "pending_tasks": ["TASK-T-002"],
            "task_id": None,
            "turn": 0,
            "wave": 2,
            "worktree_path": str(worktree_path),
        }

        with (
            patch.object(FeatureLoader, "load_feature", return_value=sample_feature),
            patch.object(FeatureLoader, "validate_feature", return_value=[]),
            patch.object(FeatureLoader, "is_incomplete", return_value=True),
            patch.object(FeatureLoader, "get_resume_point", return_value=resume_point),
            patch.object(orch, "_refresh_worktree") as mock_refresh,
        ):
            feature, worktree = orch._setup_phase("FEAT-TEST", "main")

        mock_refresh.assert_not_called()


# ============================================================================
# TestRefreshPrompt - Extended _prompt_resume
# ============================================================================


class TestRefreshPrompt:
    """Test extended _prompt_resume with [U]pdate option."""

    def test_prompt_update_sets_refresh_flag(
        self, mock_worktree_manager, sample_feature
    ):
        """Verify choosing 'u' sets self.refresh = True and returns True."""
        orch = FeatureOrchestrator(
            repo_root=Path("/tmp"),
            worktree_manager=mock_worktree_manager,
        )
        resume_point = {
            "completed_tasks": ["TASK-T-001"],
            "pending_tasks": ["TASK-T-002"],
            "task_id": None,
            "turn": 0,
            "wave": 2,
        }

        with patch("builtins.input", return_value="u"), patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            result = orch._prompt_resume(sample_feature, resume_point)

        assert result is True
        assert orch.refresh is True

    def test_prompt_resume_does_not_set_refresh(
        self, mock_worktree_manager, sample_feature
    ):
        """Verify choosing 'r' returns True but does not set refresh."""
        orch = FeatureOrchestrator(
            repo_root=Path("/tmp"),
            worktree_manager=mock_worktree_manager,
        )
        resume_point = {
            "completed_tasks": ["TASK-T-001"],
            "pending_tasks": ["TASK-T-002"],
            "task_id": None,
            "turn": 0,
            "wave": 2,
        }

        with patch("builtins.input", return_value="r"), patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            result = orch._prompt_resume(sample_feature, resume_point)

        assert result is True
        assert orch.refresh is False

    def test_prompt_fresh_returns_false(
        self, mock_worktree_manager, sample_feature
    ):
        """Verify choosing 'f' returns False."""
        orch = FeatureOrchestrator(
            repo_root=Path("/tmp"),
            worktree_manager=mock_worktree_manager,
        )
        resume_point = {
            "completed_tasks": ["TASK-T-001"],
            "pending_tasks": ["TASK-T-002"],
            "task_id": None,
            "turn": 0,
            "wave": 2,
        }

        with patch("builtins.input", return_value="f"), patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            result = orch._prompt_resume(sample_feature, resume_point)

        assert result is False

    def test_prompt_default_is_resume(
        self, mock_worktree_manager, sample_feature
    ):
        """Verify empty input defaults to resume (not refresh)."""
        orch = FeatureOrchestrator(
            repo_root=Path("/tmp"),
            worktree_manager=mock_worktree_manager,
        )
        resume_point = {
            "completed_tasks": ["TASK-T-001"],
            "pending_tasks": ["TASK-T-002"],
            "task_id": None,
            "turn": 0,
            "wave": 2,
        }

        with patch("builtins.input", return_value=""), patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            result = orch._prompt_resume(sample_feature, resume_point)

        assert result is True
        assert orch.refresh is False


# ============================================================================
# TestRefreshBanner - Banner display
# ============================================================================


class TestRefreshBanner:
    """Test that banner shows correct mode text for refresh."""

    def test_banner_shows_refreshing_when_refresh_set(
        self, mock_worktree_manager, sample_feature, tmp_path
    ):
        """Verify banner includes 'Refreshing & Resuming' when refresh=True."""
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        sample_feature.execution.worktree_path = str(worktree_path)

        orch = FeatureOrchestrator(
            repo_root=tmp_path,
            refresh=True,
            worktree_manager=mock_worktree_manager,
        )

        resume_point = {
            "completed_tasks": ["TASK-T-001"],
            "pending_tasks": ["TASK-T-002"],
            "task_id": None,
            "turn": 0,
            "wave": 2,
            "worktree_path": str(worktree_path),
        }

        with (
            patch.object(FeatureLoader, "load_feature", return_value=sample_feature),
            patch.object(FeatureLoader, "validate_feature", return_value=[]),
            patch.object(FeatureLoader, "is_incomplete", return_value=True),
            patch.object(FeatureLoader, "get_resume_point", return_value=resume_point),
            patch.object(orch, "_refresh_worktree"),
            patch("guardkit.orchestrator.feature_orchestrator.console") as mock_console,
        ):
            orch._setup_phase("FEAT-TEST", "main")

        # Check that the first Panel contains "Refreshing & Resuming"
        from rich.panel import Panel as RichPanel
        panel_args = [
            c.args[0] for c in mock_console.print.call_args_list
            if c.args and isinstance(c.args[0], RichPanel)
        ]
        assert len(panel_args) > 0, "No Panel objects found in console output"
        # The first Panel is the banner - check its renderable content
        banner_panel = panel_args[0]
        assert "Refreshing" in str(banner_panel.renderable)
