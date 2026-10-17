"""Protected paths hold the build's committed content before every Coach run.

17 October 2026. The Player's shell can change a protected path without any
file tool noticing. Before every Coach run (and so before the turn's
checkpoint commit) GuardKit compares each path declared in the build's source
commit with that commit and puts it back. Checked on real git repositories;
the changes are made directly on disk, as a shell command would make them.
All content here is invented.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

from guardkit.orchestrator import protected_paths
from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.exceptions import AgentInvocationError
from guardkit.orchestrator.harness.selector import _parse_player_project_inputs
from guardkit.orchestrator.protected_paths import (
    ProtectedPathsError,
    load_protected_reference,
    restore_protected_paths,
)
from guardkit.worktrees.manager import Worktree

BRANCH = "autobuild/TASK-PP-001"
CONFIG = (
    "autobuild:\n  player:\n    protected_paths:\n      - reference\n      - qa/check.sh\n"
)
APP = "export const App = () => 'sample';\n"
CHECK = "#!/bin/sh\necho checked\n"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=Factory Test",
         "-c", "user.email=factory@example.invalid", *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A build worktree on its branch; ``main`` is the commit it started from."""
    root = tmp_path / "wt"
    (root / ".guardkit").mkdir(parents=True)
    (root / ".guardkit" / "config.yaml").write_text(CONFIG)
    (root / ".gitignore").write_text("node_modules/\n__pycache__/\n")
    src = root / "reference" / "prototype" / "src"
    src.mkdir(parents=True)
    (src / "App.tsx").write_text(APP)
    (root / "reference" / "notes.txt").write_text("invented notes\n")
    (root / "reference" / "link-to-notes").symlink_to("notes.txt")
    (root / "qa").mkdir()
    (root / "qa" / "check.sh").write_text(CHECK)
    (root / "qa" / "check.sh").chmod(0o755)
    (root / "app.txt").write_text("product\n")
    _git(root, "init", "-q", "-b", "main")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "start")
    _git(root, "checkout", "-q", "-b", BRANCH)
    return root.resolve()


def _snapshot(root: Path) -> Dict[str, Any]:
    found: Dict[str, Any] = {}
    for folder, names, files in os.walk(root):
        for name in sorted(names + files):
            path = Path(folder) / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                found[rel] = ("link", os.readlink(path))
            elif path.is_dir():
                found[rel] = ("dir",)
            else:
                found[rel] = ("file", os.stat(path).st_mode & 0o111, path.read_bytes())
    return found


def _protected(repo: Path) -> Dict[str, Any]:
    return {"reference": _snapshot(repo / "reference"), "check": _snapshot(repo / "qa")}


def _reference(repo: Path):
    return load_protected_reference(repo, _git(repo, "rev-parse", "main"))


def _restore(repo: Path) -> Any:
    return restore_protected_paths(repo, _reference(repo))


def _assert_note(note: Any, *parts: str) -> None:
    assert note is not None
    assert note.startswith("Protected paths are read-only; these were found changed: ")
    assert note.endswith("; they were put back.")
    for part in parts:
        assert part in note


# ---------------------------------------------------------------------------
# The comparison and the restore
# ---------------------------------------------------------------------------


def test_nothing_changed_gives_no_note(repo: Path) -> None:
    (repo / "app.txt").write_text("the turn's own work\n")
    inode = os.lstat(repo / "qa" / "check.sh").st_ino
    assert _restore(repo) is None
    assert os.lstat(repo / "qa" / "check.sh").st_ino == inode
    assert (repo / "app.txt").read_text() == "the turn's own work\n"


def test_edit_is_put_back(repo: Path) -> None:
    before = _protected(repo)
    (repo / "reference" / "prototype" / "src" / "App.tsx").write_text("changed\n")
    _assert_note(_restore(repo), "reference/prototype/src/App.tsx (edited)")
    assert _protected(repo) == before


def test_added_file_is_removed(repo: Path) -> None:
    before = _protected(repo)
    (repo / "reference" / "x.txt").write_text("new\n")
    _assert_note(_restore(repo), "reference/x.txt (added)")
    assert _protected(repo) == before


def test_deleted_file_is_put_back(repo: Path) -> None:
    before = _protected(repo)
    (repo / "reference" / "notes.txt").unlink()
    _assert_note(_restore(repo), "reference/notes.txt (deleted)")
    assert _protected(repo) == before


def test_deleted_folder_is_put_back(repo: Path) -> None:
    before = _protected(repo)
    shutil.rmtree(repo / "reference")
    note = _restore(repo)
    _assert_note(note, "reference (deleted or moved)")
    assert "App.tsx" not in note
    assert _protected(repo) == before


def test_renamed_folder_is_put_back(repo: Path) -> None:
    before = _protected(repo)
    (repo / "reference").rename(repo / "elsewhere")
    _assert_note(_restore(repo), "reference (deleted or moved)")
    assert _protected(repo) == before
    assert (repo / "elsewhere" / "notes.txt").is_file()  # not protected, left alone


def test_executable_bit_change_is_put_back(repo: Path) -> None:
    (repo / "qa" / "check.sh").chmod(0o644)
    _assert_note(_restore(repo), "qa/check.sh (executable bit changed)")
    assert os.stat(repo / "qa" / "check.sh").st_mode & 0o111


def test_file_swapped_for_a_link_and_a_retargeted_link_are_put_back(
    repo: Path, tmp_path: Path
) -> None:
    before = _protected(repo)
    outside = tmp_path / "outside.txt"
    outside.write_text(APP)  # same bytes: only the kind differs
    app = repo / "reference" / "prototype" / "src" / "App.tsx"
    app.unlink()
    app.symlink_to(outside)
    link = repo / "reference" / "link-to-notes"
    link.unlink()
    link.symlink_to("prototype")
    _assert_note(
        _restore(repo),
        "reference/prototype/src/App.tsx (replaced)",
        "reference/link-to-notes (edited)",
    )
    assert _protected(repo) == before
    assert outside.read_text() == APP


def test_parent_folder_replaced_by_a_link_is_put_back(repo: Path) -> None:
    (repo / "qa").rename(repo / "qa-moved")
    (repo / "qa").symlink_to("qa-moved")  # same content reachable through a link
    _assert_note(_restore(repo), "qa/check.sh (deleted or moved)")
    assert not (repo / "qa").is_symlink() and (repo / "qa").is_dir()
    assert (repo / "qa" / "check.sh").read_text() == CHECK


def test_huge_sparse_file_is_judged_by_size_without_reading_it(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = repo / "reference" / "prototype" / "src" / "App.tsx"
    os.truncate(app, 8 * 1024 ** 3)  # sparse: no real disk use

    def guarded_open(path: Any, *args: Any, **kwargs: Any) -> Any:
        if os.path.getsize(path) > 1024 ** 2:
            raise AssertionError("a size mismatch must not read the file")
        return open(path, *args, **kwargs)

    monkeypatch.setattr(protected_paths, "open", guarded_open, raising=False)
    _assert_note(_restore(repo), "reference/prototype/src/App.tsx (edited)")
    assert app.read_text() == APP


def test_ignored_files_are_removed_and_only_counted(repo: Path) -> None:
    before = _protected(repo)
    (repo / "reference" / "node_modules" / "pkg").mkdir(parents=True)
    (repo / "reference" / "node_modules" / "pkg" / "index.js").write_text("x\n")
    (repo / "reference" / "node_modules" / "other.js").write_text("x\n")
    (repo / "reference" / "__pycache__").mkdir()
    (repo / "reference" / "__pycache__" / "mod.pyc").write_bytes(b"\0")
    (repo / "reference" / "new.txt").write_text("x\n")
    note = _restore(repo)
    _assert_note(note, "reference/new.txt (added)", "and 3 generated files that git ignores")
    assert "node_modules" not in note and "__pycache__" not in note
    assert _protected(repo) == before


def test_long_lists_are_shortened(repo: Path) -> None:
    for index in range(12):
        (repo / "reference" / f"extra-{index:02d}.txt").write_text("x\n")
    note = _restore(repo)
    assert note.count("(added)") == 10 and "2 more" in note


def test_replacement_objects_are_not_used(repo: Path) -> None:
    (repo / "decoy.txt").write_text("decoy\n")
    decoy = _git(repo, "hash-object", "-w", "decoy.txt")
    original = _git(repo, "rev-parse", "main:qa/check.sh")
    _git(repo, "replace", original, decoy)
    assert _restore(repo) is None
    (repo / "qa" / "check.sh").write_text("decoy\n")
    _assert_note(_restore(repo), "qa/check.sh (edited)")
    assert (repo / "qa" / "check.sh").read_text() == CHECK


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores folder permissions")
def test_a_path_that_cannot_be_put_back_is_an_error(repo: Path) -> None:
    (repo / "qa" / "check.sh").unlink()
    (repo / "qa").chmod(0o555)
    try:
        with pytest.raises(ProtectedPathsError, match="qa/check.sh was changed and could not be put back"):
            _restore(repo)
    finally:
        (repo / "qa").chmod(0o755)


# ---------------------------------------------------------------------------
# The declaration
# ---------------------------------------------------------------------------


def test_the_declaration_is_read_from_the_source_commit(repo: Path) -> None:
    # The Player drops the declaration in its worktree and commits that.
    (repo / ".guardkit" / "config.yaml").write_text("autobuild:\n  player: {}\n")
    _git(repo, "commit", "-qam", "player turn")
    orch = _orchestrator(repo)
    assert orch._load_protected_reference(_worktree(repo)) is None
    assert orch._protected_reference.paths == ("reference", "qa/check.sh")
    (repo / "qa" / "check.sh").write_text("exit 0\n")
    _assert_note(restore_protected_paths(repo, orch._protected_reference), "qa/check.sh (edited)")


@pytest.mark.parametrize("value", [".", "./", "reference/..", "../outside"])
def test_the_whole_repository_or_outside_it_is_refused(value: str) -> None:
    text = f"autobuild:\n  player:\n    protected_paths:\n      - '{value}'\n"
    with pytest.raises(AgentInvocationError, match="whole repository or outside it"):
        _parse_player_project_inputs(text, config_path="config.yaml", has_file=lambda _r: False)


def test_a_path_missing_from_the_source_commit_is_refused(repo: Path) -> None:
    _git(repo, "checkout", "-q", "main")
    (repo / ".guardkit" / "config.yaml").write_text(CONFIG + "      - docs/missing\n")
    _git(repo, "commit", "-qam", "declare a missing path")
    _git(repo, "checkout", "-q", "-b", "autobuild/TASK-PP-002")
    refusal = _orchestrator(repo)._load_protected_reference(_worktree(repo))
    assert refusal is not None
    assert "'docs/missing'" in refusal and "not in the commit this build started from" in refusal


def test_orchestrate_stops_before_any_model_call(repo: Path, tmp_path: Path) -> None:
    _git(repo, "checkout", "-q", "main")
    (repo / ".guardkit" / "config.yaml").write_text(CONFIG + "      - docs/missing\n")
    _git(repo, "commit", "-qam", "declare a missing path")
    _git(repo, "checkout", "-q", "-b", "autobuild/TASK-PP-003")
    manager = MagicMock()
    manager.create.return_value = _worktree(repo)
    manager.worktrees_dir = tmp_path / "worktrees"
    invoker = MagicMock()
    orch = AutoBuildOrchestrator(
        repo_root=repo, max_turns=3, worktree_manager=manager, agent_invoker=invoker,
        progress_display=MagicMock(), pre_loop_gates=MagicMock(),
        enable_checkpoints=False, enable_context=False,
    )
    result = orch.orchestrate(task_id="TASK-PP-003", requirements="r", acceptance_criteria=["AC-001: x"])
    assert result.final_decision == "configuration_error"
    assert "docs/missing" in result.error
    invoker.invoke_player.assert_not_called()


# ---------------------------------------------------------------------------
# In the turn: before the Coach, before the checkpoint commit
# ---------------------------------------------------------------------------


def _worktree(repo: Path) -> Worktree:
    return Worktree(task_id="TASK-PP-001", branch_name=_git(repo, "branch", "--show-current"),
                    path=repo, base_branch="main")


def _orchestrator(repo: Path, **kwargs: Any) -> AutoBuildOrchestrator:
    display = MagicMock()
    display.__enter__ = Mock(return_value=display)
    display.__exit__ = Mock(return_value=False)
    invoker = MagicMock()
    invoker._get_implementation_mode.return_value = "direct"  # no Phase 4/5 specialists
    return AutoBuildOrchestrator(
        repo_root=repo, max_turns=kwargs.pop("max_turns", 3), worktree_manager=Mock(),
        agent_invoker=invoker, progress_display=display,
        pre_loop_gates=MagicMock(), enable_context=False, **kwargs,
    )


def _result(agent: str, success: bool = True, **report: Any) -> AgentInvocationResult:
    return AgentInvocationResult(
        task_id="TASK-PP-001", turn=1, agent_type=agent, success=success,
        report={"files_modified": [], "files_created": [], "concerns": [], **report},
        duration_seconds=0.1, error=None if success else "Player report not found",
    )


class _Coach:
    """Records what the Coach would see: the worktree and the Player report."""

    def __init__(self, repo: Path, decisions: List[str]) -> None:
        self.repo, self.decisions, self.seen = repo, decisions, []

    def __call__(self, **kwargs: Any) -> AgentInvocationResult:
        self.seen.append({
            "check": (self.repo / "qa" / "check.sh").read_text(),
            "concerns": list(kwargs["player_report"].get("concerns", [])),
        })
        decision = self.decisions[len(self.seen) - 1]
        return _result("coach", decision=decision, rationale="r",
                       issues=[] if decision == "approve" else [
                           {"severity": "must_fix", "description": "finish the work"}])


def _shell_edit(repo: Path, result: AgentInvocationResult):
    def player(**_kwargs: Any) -> AgentInvocationResult:
        (repo / "qa" / "check.sh").write_text("exit 0\n")  # what `sed -i` would do
        return result
    return player


def _turn(orch: AutoBuildOrchestrator, repo: Path) -> Any:
    return orch._execute_turn(turn=1, task_id="TASK-PP-001", requirements="r",
                              worktree=_worktree(repo), previous_feedback=None,
                              acceptance_criteria=["AC-001: x"])


def test_the_coach_sees_committed_content_and_the_note(repo: Path) -> None:
    orch = _orchestrator(repo, enable_checkpoints=False)
    assert orch._load_protected_reference(_worktree(repo)) is None
    coach = _Coach(repo, ["feedback"])
    with patch.object(orch, "_invoke_player_safely", side_effect=_shell_edit(repo, _result("player"))), \
            patch.object(orch, "_invoke_coach_safely", side_effect=coach):
        record = _turn(orch, repo)
    assert record.decision == "feedback"
    assert coach.seen[0]["check"] == CHECK
    _assert_note(coach.seen[0]["concerns"][-1], "qa/check.sh (edited)")


def test_a_recovered_player_turn_is_checked_too(repo: Path) -> None:
    orch = _orchestrator(repo, enable_checkpoints=False)
    orch._load_protected_reference(_worktree(repo))
    coach = _Coach(repo, ["feedback"])
    failed = _result("player", success=False)
    with patch.object(orch, "_invoke_player_safely", side_effect=_shell_edit(repo, failed)), \
            patch.object(orch, "_attempt_state_recovery", return_value=_result("player")) as recovery, \
            patch.object(orch, "_invoke_coach_safely", side_effect=coach):
        _turn(orch, repo)
    recovery.assert_called_once()
    assert coach.seen[0]["check"] == CHECK
    _assert_note(coach.seen[0]["concerns"][-1], "qa/check.sh (edited)")


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores folder permissions")
def test_a_failed_restore_stops_the_task_and_is_never_recovered(repo: Path) -> None:
    orch = _orchestrator(repo, enable_checkpoints=False)
    orch._load_protected_reference(_worktree(repo))

    def player(**_kwargs: Any) -> AgentInvocationResult:
        (repo / "qa" / "check.sh").unlink()
        (repo / "qa").chmod(0o555)
        return _result("player")

    try:
        with patch.object(orch, "_invoke_player_safely", side_effect=player), \
                patch.object(orch, "_attempt_state_recovery") as recovery, \
                patch.object(orch, "_invoke_coach_safely") as coach, \
                patch.object(orch, "_capture_turn_state"), \
                patch.object(orch, "_record_honesty"), \
                patch.object(orch, "_display_criteria_progress"):
            history, final = orch._loop_phase(
                task_id="TASK-PP-001", requirements="r", acceptance_criteria=["AC-001: x"],
                worktree=_worktree(repo),
            )
    finally:
        (repo / "qa").chmod(0o755)
    assert final == "error" and len(history) == 1
    coach.assert_not_called()
    recovery.assert_not_called()
    message = orch._build_error_message(final, history)
    assert message.startswith("Task TASK-PP-001 stopped: Protected path qa/check.sh")


def test_the_checkpoint_commit_never_carries_the_change_and_the_next_turn_is_told(
    repo: Path,
) -> None:
    orch = _orchestrator(repo, enable_checkpoints=True, max_turns=2)
    orch._load_protected_reference(_worktree(repo))
    coach = _Coach(repo, ["feedback", "approve"])
    feedback_seen: List[Any] = []

    def player(**kwargs: Any) -> AgentInvocationResult:
        feedback_seen.append(kwargs.get("feedback"))
        (repo / "qa" / "check.sh").write_text("exit 0\n")
        (repo / "app.txt").write_text(f"turn {len(feedback_seen)}\n")
        return _result("player")

    with patch.object(orch, "_invoke_player_safely", side_effect=player), \
            patch.object(orch, "_invoke_coach_safely", side_effect=coach), \
            patch.object(orch, "_capture_turn_state"), \
            patch.object(orch, "_record_honesty"), \
            patch.object(orch, "_display_criteria_progress"):
        history, final = orch._loop_phase(
            task_id="TASK-PP-001", requirements="r", acceptance_criteria=["AC-001: x"],
            worktree=_worktree(repo),
        )
    assert final == "approved" and len(history) == 2
    # Two checkpoint commits, each made after that turn's Coach run; neither
    # carries the protected change, while the turn's own work is committed.
    log = _git(repo, "log", "--format=%s", "main..HEAD").splitlines()
    assert len(log) == 2 and all(s.startswith("[guardkit-checkpoint] Turn") for s in log)
    for rev in ("HEAD~1", "HEAD"):
        assert _git(repo, "show", f"{rev}:qa/check.sh") + "\n" == CHECK
    assert _git(repo, "show", "HEAD:app.txt") == "turn 2"
    assert _git(repo, "diff", "--name-only", "main", "HEAD") == "app.txt"
    # The next turn is told what was put back, ahead of the Coach's feedback.
    assert feedback_seen[0] is None
    _assert_note(feedback_seen[1].split("\n\n")[0], "qa/check.sh (edited)")


def test_a_change_made_after_the_coach_check_is_put_back_before_the_commit(
    repo: Path,
) -> None:
    orch = _orchestrator(repo, enable_checkpoints=True, max_turns=1)
    orch._load_protected_reference(_worktree(repo))
    coach = _Coach(repo, ["approve"])

    def coach_then_parallel_change(**kwargs: Any) -> AgentInvocationResult:
        result = coach(**kwargs)
        # After the check: the Coach's own run, or another task in the wave.
        (repo / "qa" / "check.sh").write_text("changed after the check\n")
        return result

    with patch.object(orch, "_invoke_player_safely", return_value=_result("player")), \
            patch.object(orch, "_invoke_coach_safely", side_effect=coach_then_parallel_change), \
            patch.object(orch, "_capture_turn_state"), \
            patch.object(orch, "_record_honesty"), \
            patch.object(orch, "_display_criteria_progress"):
        _history, final = orch._loop_phase(
            task_id="TASK-PP-001", requirements="r", acceptance_criteria=["AC-001: x"],
            worktree=_worktree(repo),
        )
    assert final == "approved"
    assert _git(repo, "log", "-1", "--format=%s").startswith("[guardkit-checkpoint] Turn 1")
    assert _git(repo, "show", "HEAD:qa/check.sh") + "\n" == CHECK
    assert (repo / "qa" / "check.sh").read_text() == CHECK


def test_a_task_cancelled_between_player_and_coach_ends_with_paths_restored(
    repo: Path, tmp_path: Path
) -> None:
    manager = MagicMock()
    manager.create.return_value = _worktree(repo)
    manager.worktrees_dir = tmp_path / "worktrees"
    invoker = MagicMock()
    invoker._get_implementation_mode.return_value = "direct"
    cancel = threading.Event()
    orch = AutoBuildOrchestrator(
        repo_root=repo, max_turns=3, worktree_manager=manager, agent_invoker=invoker,
        progress_display=MagicMock(), pre_loop_gates=MagicMock(), enable_pre_loop=False,
        enable_checkpoints=False, enable_context=False, cancellation_event=cancel,
    )

    def player(**_kwargs: Any) -> AgentInvocationResult:
        (repo / "qa" / "check.sh").write_text("exit 0\n")
        (repo / "reference" / "extra.txt").write_text("x\n")
        cancel.set()  # the wave is stopped before the Coach runs
        return _result("player", success=False)

    with patch.object(AutoBuildOrchestrator, "_invoke_player_safely", side_effect=player), \
            patch.object(AutoBuildOrchestrator, "_attempt_state_recovery", return_value=None), \
            patch.object(AutoBuildOrchestrator, "_invoke_coach_safely") as coach:
        result = orch.orchestrate(
            task_id="TASK-PP-004", requirements="r", acceptance_criteria=["AC-001: x"]
        )
    coach.assert_not_called()
    assert result.final_decision == "cancelled"
    assert (repo / "qa" / "check.sh").read_text() == CHECK
    assert not (repo / "reference" / "extra.txt").exists()
