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


def _git(*args, cwd, check=True):
    return subprocess.run(
        ["git", *args], cwd=str(cwd), check=check,
        capture_output=True, text=True,
    )


def _build_refresh_repo(tmp_path: Path):
    """Build origin(bare) + clone with `main` and a `feat` branch.

    The clone's checkout on `feat` stands in for the autobuild worktree
    (``_refresh_worktree`` just runs git in ``worktree.path``). Returns
    ``(clone_path, worktree)``.
    """
    origin = tmp_path / "origin.git"
    # NOTE: do NOT `git init` with cwd=tmp_path.parent. That is pytest's SHARED
    # basetemp (/tmp/pytest-of-<user>/pytest-N), the parent of every other
    # test's tmp_path. A stray repo there is silently discovered by any later
    # test that runs git in a directory which is deliberately NOT a repo, so
    # `git rev-parse HEAD` stops failing and starts echoing "HEAD" — which is
    # exactly how test_worktree_checkpoints_evidence.py's
    # test_failed_sibling_commit_does_not_abort_checkpoint was failing in CI
    # while passing when run on its own. The line below does the real work.
    subprocess.run(
        ["git", "init", "--bare", "--initial-branch=main", str(origin)],
        check=True, capture_output=True, text=True,
    )

    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", str(origin), str(clone)],
        check=True, capture_output=True, text=True,
    )
    _git("config", "user.email", "t@e.com", cwd=clone)
    _git("config", "user.name", "T", cwd=clone)

    # Base commit on main, pushed to origin.
    (clone / "base.txt").write_text("base\n")
    (clone / "app.py").write_text("VALUE = 1\n")
    _git("add", "-A", cwd=clone)
    _git("commit", "-m", "base", cwd=clone)
    _git("push", "origin", "main", cwd=clone)

    # Feature branch off main with its own commit.
    _git("checkout", "-b", "feat", cwd=clone)
    (clone / "feature.txt").write_text("feature work\n")
    _git("add", "-A", cwd=clone)
    _git("commit", "-m", "feature", cwd=clone)

    worktree = Worktree(
        task_id="FEAT-TEST",
        branch_name="feat",
        path=clone,
        base_branch="main",
    )
    return clone, worktree


class TestResolveRefreshTarget:
    """Item 4: prefer local <base> when it is ahead of origin/<base>."""

    def test_prefers_local_when_ahead(
        self, tmp_path, mock_worktree_manager,
    ):
        clone, _ = _build_refresh_repo(tmp_path)
        # Advance local main WITHOUT pushing (the operator's unpushed fix).
        _git("checkout", "main", cwd=clone)
        (clone / "app.py").write_text("VALUE = 2  # baseline fix\n")
        _git("commit", "-am", "fix baseline", cwd=clone)
        _git("checkout", "feat", cwd=clone)

        orch = FeatureOrchestrator(
            repo_root=tmp_path, refresh=True,
            worktree_manager=mock_worktree_manager,
        )
        target, desc = orch._resolve_refresh_target(clone, "main")
        assert target == "main"
        assert "ahead of origin/main" in desc

    def test_falls_back_to_origin_when_not_ahead(
        self, tmp_path, mock_worktree_manager,
    ):
        clone, _ = _build_refresh_repo(tmp_path)
        orch = FeatureOrchestrator(
            repo_root=tmp_path, refresh=True,
            worktree_manager=mock_worktree_manager,
        )
        target, desc = orch._resolve_refresh_target(clone, "main")
        assert target == "origin/main"


class TestRefreshWorktreeRealGit:
    """Items 4 + 5 exercised end-to-end against real git repos."""

    def test_refresh_success_onto_origin(
        self, tmp_path, mock_worktree_manager,
    ):
        clone, worktree = _build_refresh_repo(tmp_path)
        orch = FeatureOrchestrator(
            repo_root=tmp_path, refresh=True,
            worktree_manager=mock_worktree_manager,
        )
        # Should not raise; feat is already on top of origin/main.
        orch._refresh_worktree(worktree, "main")

    def test_refresh_brings_unpushed_local_baseline_fix(
        self, tmp_path, mock_worktree_manager,
    ):
        """Item 4 core: the operator's local, unpushed baseline fix reaches
        the feature branch via --refresh (it did NOT pre-fix, when we
        rebased onto stale origin/main)."""
        clone, worktree = _build_refresh_repo(tmp_path)
        _git("checkout", "main", cwd=clone)
        (clone / "app.py").write_text("VALUE = 2  # baseline fix\n")
        _git("commit", "-am", "fix baseline (unpushed)", cwd=clone)
        _git("checkout", "feat", cwd=clone)
        # Pre-refresh the feature branch does NOT have the fix.
        assert (clone / "app.py").read_text() == "VALUE = 1\n"

        orch = FeatureOrchestrator(
            repo_root=tmp_path, refresh=True,
            worktree_manager=mock_worktree_manager,
        )
        orch._refresh_worktree(worktree, "main")

        # The unpushed fix is now on the feature branch.
        assert "VALUE = 2" in (clone / "app.py").read_text()

    def test_refresh_autostashes_dirty_autobuild_artifact(
        self, tmp_path, mock_worktree_manager,
    ):
        """Item 5a: a dirty tracked file (checkpoints.json class) no longer
        blows up the rebase; --autostash restores it afterwards."""
        clone, worktree = _build_refresh_repo(tmp_path)
        # Commit an autobuild-managed artifact on feat.
        ab_dir = clone / ".guardkit" / "autobuild" / "TASK-T-001"
        ab_dir.mkdir(parents=True)
        cp = ab_dir / "checkpoints.json"
        cp.write_text('{"turn": 1}\n')
        _git("add", "-A", cwd=clone)
        _git("commit", "-m", "checkpoint", cwd=clone)

        # Advance origin/main so a real rebase happens (while the tree is
        # clean — do this BEFORE dirtying the checkpoint).
        _git("checkout", "main", cwd=clone)
        (clone / "base.txt").write_text("base v2\n")
        _git("commit", "-am", "advance main", cwd=clone)
        _git("push", "origin", "main", cwd=clone)
        _git("reset", "--hard", "HEAD~1", cwd=clone)  # local main back to stale
        _git("checkout", "feat", cwd=clone)

        # Now dirty the checkpoint (the FEAT-VOICE-003 unstaged-artifact class).
        cp.write_text('{"turn": 2}\n')

        orch = FeatureOrchestrator(
            repo_root=tmp_path, refresh=True,
            worktree_manager=mock_worktree_manager,
        )
        # Would raise "cannot rebase: you have unstaged changes" pre-fix.
        orch._refresh_worktree(worktree, "main")

        # Rebase applied AND the dirty checkpoint change was restored.
        assert "base v2" in (clone / "base.txt").read_text()
        assert cp.read_text() == '{"turn": 2}\n'

    def test_refresh_conflict_aborts_and_reports_truthful_state(
        self, tmp_path, mock_worktree_manager, capsys,
    ):
        """Item 5b: on conflict the abort restores the worktree and the
        message reflects the VERIFIED state, not an unverified 'inconsistent'
        assertion."""
        clone, worktree = _build_refresh_repo(tmp_path)
        # Conflicting edits to app.py on origin/main and on feat.
        _git("checkout", "main", cwd=clone)
        (clone / "app.py").write_text("VALUE = 99  # main\n")
        _git("commit", "-am", "main edits app", cwd=clone)
        _git("push", "origin", "main", cwd=clone)
        _git("reset", "--hard", "HEAD~1", cwd=clone)
        _git("checkout", "feat", cwd=clone)
        (clone / "app.py").write_text("VALUE = 42  # feat\n")
        _git("commit", "-am", "feat edits app", cwd=clone)
        feat_head = _git("rev-parse", "HEAD", cwd=clone).stdout.strip()

        orch = FeatureOrchestrator(
            repo_root=tmp_path, refresh=True,
            worktree_manager=mock_worktree_manager,
        )
        with pytest.raises(FeatureOrchestrationError, match="failed due to conflicts"):
            orch._refresh_worktree(worktree, "main")

        # The worktree was restored: HEAD unchanged, no rebase in progress.
        assert _git("rev-parse", "HEAD", cwd=clone).stdout.strip() == feat_head
        is_clean, msg = orch._describe_worktree_git_state(clone)
        assert is_clean is True
        assert "verified restored" in msg
        out = capsys.readouterr().out
        assert "may be in inconsistent state" not in out


class TestDescribeWorktreeGitState:
    """Item 5b: truthful state description."""

    def test_clean_repo_reports_verified(
        self, tmp_path, mock_worktree_manager,
    ):
        clone, _ = _build_refresh_repo(tmp_path)
        orch = FeatureOrchestrator(
            repo_root=tmp_path, refresh=True,
            worktree_manager=mock_worktree_manager,
        )
        is_clean, msg = orch._describe_worktree_git_state(clone)
        assert is_clean is True
        assert "no rebase in progress" in msg


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
