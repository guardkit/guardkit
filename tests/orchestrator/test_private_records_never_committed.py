"""Proof that GuardKit's private records never enter a factory commit.

Plain words: the final whole-feature check record lives under
``.guardkit/autobuild-private/`` in the build's worktree, and it keeps the
last 40 lines of whatever the project's check printed. Those lines can carry a
credential. A project whose ignore file does not cover that folder would
otherwise have it staged and committed by the factory's own
commits, and from there it could reach a public repository's history.

GuardKit commits in exactly three places:

1. the task checkpoint in the build's worktree;
2. the checkpoint of each declared sibling evidence repository;
3. the outer-tree commit of a fix run (``work_runner.commit_outer_tree``).

Each test below runs on real git in ``tmp_path`` and is parametrised over all
three, through the same public entry points the build uses.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Callable, Dict

import pytest

from guardkit.orchestrator import work_runner
from guardkit.orchestrator.evidence_repos import EvidenceRepo
from guardkit.orchestrator.worktree_checkpoints import WorktreeCheckpointManager


RECORD = ".guardkit/autobuild-private/feature_check.json"
ORDINARY = "src/feature.txt"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(root), check=True, capture_output=True, text=True
    )


def _init_repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    (root / "README").write_text("base\n", encoding="utf-8")
    _git(root, "add", "README")
    _git(root, "commit", "-m", "base")
    return root


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# The three commit sites, each run the way the build runs it
# ---------------------------------------------------------------------------


def _run_task_checkpoint(repo: Path, tmp_path: Path, turn: int) -> None:
    manager = WorktreeCheckpointManager(worktree_path=repo, task_id="TASK-001")
    manager.create_checkpoint(turn=turn, tests_passed=True, test_count=1)


def _run_sibling_evidence_checkpoint(repo: Path, tmp_path: Path, turn: int) -> None:
    # The build's own worktree is a separate repository; ``repo`` is the
    # declared sibling whose working tree each checkpoint also commits.
    worktree = tmp_path / "build-worktree"
    if not worktree.exists():
        _init_repo(worktree)
    manager = WorktreeCheckpointManager(
        worktree_path=worktree,
        task_id="TASK-001",
        evidence_repos=[EvidenceRepo(name="sibling", root=repo)],
    )
    checkpoint = manager.create_checkpoint(
        turn=turn, tests_passed=True, test_count=1
    )
    assert "sibling" in checkpoint.evidence_commits, "the sibling was committed"


def _run_outer_tree_commit(repo: Path, tmp_path: Path, turn: int) -> None:
    info = work_runner.commit_outer_tree(
        repo_root=repo, fix_task_id="TASK-FIX-0001", title=f"turn {turn}"
    )
    assert "error" not in info, info.get("error")


SITES: Dict[str, Callable[[Path, Path, int], None]] = {
    "task-checkpoint": _run_task_checkpoint,
    "sibling-evidence-checkpoint": _run_sibling_evidence_checkpoint,
    "outer-tree-commit": _run_outer_tree_commit,
}


@pytest.fixture(params=sorted(SITES))
def site(request) -> Callable[[Path, Path, int], None]:
    return SITES[request.param]


def _committed_names(repo: Path) -> list[str]:
    out = _git(repo, "show", "--name-only", "--format=", "HEAD").stdout
    return [line for line in out.splitlines() if line.strip()]


def _private_warnings(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [
        r
        for r in caplog.records
        if r.levelno == logging.WARNING and RECORD in r.getMessage()
    ]


# ---------------------------------------------------------------------------
# The tests
# ---------------------------------------------------------------------------


def test_a_pre_staged_new_private_record_is_not_committed(
    site, tmp_path: Path
) -> None:
    repo = _init_repo(tmp_path / "repo")
    _write(repo, RECORD, '{"stdout_tail": "password=out-secret"}\n')
    _write(repo, ORDINARY, "the Player's work\n")
    _git(repo, "add", "--", RECORD, ORDINARY)

    site(repo, tmp_path, 1)

    committed = _committed_names(repo)
    assert ORDINARY in committed, committed
    assert RECORD not in committed, committed
    assert (repo / RECORD).is_file(), "the record stays on disk"
    status = _git(repo, "status", "--porcelain", "--untracked-files=all").stdout
    assert f"?? {RECORD}" in status.splitlines(), status


def test_a_pre_staged_change_to_a_tracked_private_record_is_not_committed(
    site, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    repo = _init_repo(tmp_path / "repo")
    _write(repo, RECORD, "content A\n")
    _git(repo, "add", "--", RECORD)
    _git(repo, "commit", "-m", "an older build committed the record")

    caplog.set_level(logging.WARNING)
    _write(repo, RECORD, "content B\n")
    for turn in (1, 2):
        _write(repo, ORDINARY, f"the Player's work, turn {turn}\n")
        _git(repo, "add", "--", RECORD, ORDINARY)
        site(repo, tmp_path, turn)

    head_copy = _git(repo, "show", f"HEAD:{RECORD}").stdout
    assert head_copy == "content A\n", "the committed copy is left as it was"
    assert (repo / RECORD).read_text(encoding="utf-8") == "content B\n"
    assert ORDINARY in _committed_names(repo)
    warnings = _private_warnings(caplog)
    assert len(warnings) == 1, [w.getMessage() for w in warnings]


def test_a_new_private_record_left_unstaged_is_not_picked_up(
    site, tmp_path: Path
) -> None:
    repo = _init_repo(tmp_path / "repo")
    _write(repo, RECORD, '{"stdout_tail": "password=out-secret"}\n')
    _write(repo, ORDINARY, "the Player's work\n")

    site(repo, tmp_path, 1)

    committed = _committed_names(repo)
    assert ORDINARY in committed, committed
    assert RECORD not in committed, committed
    tree = _git(repo, "ls-tree", "-r", "--name-only", "HEAD").stdout.splitlines()
    assert RECORD not in tree
    assert (repo / RECORD).is_file()
