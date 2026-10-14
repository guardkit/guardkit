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


# ===========================================================================
# Every one of GuardKit's records stays out of factory commits (14 October 2026)
# ===========================================================================
#
# Plain words: GuardKit writes many records about a build inside the build's
# folder (each turn, the judge's decisions, the test baseline, the shadow
# judge's queue, the memory query log, its inner build folders). Before this
# change only the private folder above was kept out of commits, so a project
# that does not ignore ``.guardkit/autobuild/`` had every record committed,
# and a merge then published them. These tests run the same three commit
# sites on real git, through GuardKit's own git helper.

NEW_RECORDS = (
    ".guardkit/autobuild/x.json",
    ".guardkit/autobuild/TASK-1/player_turn_1.json",
    ".guardkit/qav-shadow/queue.jsonl",
    ".guardkit/memory-query-log.jsonl",
    ".guardkit/memory-query-log.jsonl.1",
    "packages/app/.guardkit/autobuild/baseline.json",
)
TRACKED_RECORD = ".guardkit/autobuild/old.json"
MOVED_TO = "notes/old.json"
PRODUCT = "src/app.txt"
#: A made-up private folder, standing in for an owner's home folder.
MADE_UP_HOME = "/home/example/project"


def _tree(repo: Path) -> list[str]:
    return _git(repo, "ls-tree", "-r", "--name-only", "HEAD").stdout.splitlines()


def _warnings(caplog: pytest.LogCaptureFixture, *needles: str) -> list[str]:
    return [
        r.getMessage()
        for r in caplog.records
        if r.levelno == logging.WARNING
        and all(n in r.getMessage() for n in needles)
    ]


def _record_json(lines: int = 20) -> str:
    body = ",\n".join(f'  "field_{i}": "ordinary value number {i}"' for i in range(lines - 2))
    return "{\n" + body + "\n}\n"


def test_new_records_are_not_checkpointed(site, tmp_path: Path) -> None:
    """Design tests 1, 2 and 11: a project that ignores nothing."""
    repo = _init_repo(tmp_path / "repo")
    for path in NEW_RECORDS:
        _write(repo, path, f'{{"cwd": "{MADE_UP_HOME}"}}\n')
    _write(repo, ORDINARY, "the Player's work\n")

    site(repo, tmp_path, 1)

    assert ORDINARY in _committed_names(repo)
    tree = _tree(repo)
    for path in NEW_RECORDS:
        assert path not in tree, (path, tree)
        assert (repo / path).is_file(), "the record stays on disk"
    assert not [p for p in tree if "/.guardkit/autobuild/" in f"/{p}"], tree


def test_a_force_added_record_is_taken_out_with_a_warning(
    site, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Design test 3."""
    repo = _init_repo(tmp_path / "repo")
    record = ".guardkit/autobuild/x.json"
    _write(repo, record, '{"turn": 1}\n')
    _write(repo, ORDINARY, "the Player's work\n")
    _git(repo, "add", "-f", "--", record, ORDINARY)

    caplog.set_level(logging.WARNING)
    site(repo, tmp_path, 1)

    committed = _committed_names(repo)
    assert ORDINARY in committed and record not in committed, committed
    assert (repo / record).is_file()
    status = _git(repo, "status", "--porcelain", "--untracked-files=all").stdout
    assert f"?? {record}" in status.splitlines(), status
    assert _warnings(caplog, record), [r.getMessage() for r in caplog.records]


def test_an_edited_tracked_record_is_left_at_heads_copy(
    site, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Design test 4: the edit is not staged beforehand."""
    repo = _init_repo(tmp_path / "repo")
    _write(repo, TRACKED_RECORD, "content A\n")
    _git(repo, "add", "--", TRACKED_RECORD)
    _git(repo, "commit", "-m", "an older build committed the record")

    caplog.set_level(logging.WARNING)
    _write(repo, TRACKED_RECORD, "content B\n")
    for turn in (1, 2):
        _write(repo, ORDINARY, f"the Player's work, turn {turn}\n")
        site(repo, tmp_path, turn)

    assert _git(repo, "show", f"HEAD:{TRACKED_RECORD}").stdout == "content A\n"
    assert (repo / TRACKED_RECORD).read_text(encoding="utf-8") == "content B\n"
    assert ORDINARY in _committed_names(repo)
    warnings = _warnings(caplog, TRACKED_RECORD, "tracked")
    assert len(warnings) == 1, warnings


def test_what_the_next_stage_reads_is_still_committed(site, tmp_path: Path) -> None:
    """Design test 9."""
    repo = _init_repo(tmp_path / "repo")
    needed = (
        ".guardkit/features/F.yaml",
        "tasks/backlog/TASK-1.md",
        ".guardkit/config.yaml",
        ".guardkit/seam-checks.yaml",
        "docs/state/notes.md",
        "src/main.go",
    )
    for path in needed:
        _write(repo, path, f"{path}\n")

    site(repo, tmp_path, 1)

    committed = _committed_names(repo)
    for path in needed:
        assert path in committed, (path, committed)


# --- Design test 20: a record moved out of its folder, at checkpoint -------


def _base_with_tracked_record(repo: Path) -> None:
    _write(repo, TRACKED_RECORD, _record_json())
    _write(repo, PRODUCT, "".join(f"product line {i}\n" for i in range(20)))
    _git(repo, "add", "--", TRACKED_RECORD, PRODUCT)
    _git(repo, "commit", "-m", "an older build committed a record")


def _move_record(repo: Path, how: str) -> None:
    if how == "git-mv":
        (repo / MOVED_TO).parent.mkdir(parents=True, exist_ok=True)
        _git(repo, "mv", TRACKED_RECORD, MOVED_TO)
    else:
        (repo / MOVED_TO).parent.mkdir(parents=True, exist_ok=True)
        (repo / TRACKED_RECORD).rename(repo / MOVED_TO)
    with open(repo / MOVED_TO, "a", encoding="utf-8") as handle:
        handle.write('{"added": "one more line"}\n')


@pytest.mark.parametrize("how", ["git-mv", "plain-move"])
def test_a_record_moved_out_and_lightly_edited_is_not_committed(
    site, how: str, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    repo = _init_repo(tmp_path / "repo")
    _base_with_tracked_record(repo)
    _move_record(repo, how)
    _write(repo, PRODUCT, "the Player changed the product\n")

    caplog.set_level(logging.WARNING)
    site(repo, tmp_path, 1)

    committed = _committed_names(repo)
    assert PRODUCT in committed, committed
    assert MOVED_TO not in committed, committed
    assert MOVED_TO not in _tree(repo)
    assert TRACKED_RECORD in _tree(repo), "the committed record is left as it was"
    assert (repo / MOVED_TO).is_file(), "the moved file stays on disk"
    warnings = _warnings(caplog, MOVED_TO, "moves or copies")
    assert len(warnings) == 1, [r.getMessage() for r in caplog.records]


def test_deleting_a_record_is_not_taken_for_a_move(
    site, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Control: a deletion and a product change, nothing moved."""
    repo = _init_repo(tmp_path / "repo")
    _base_with_tracked_record(repo)
    _git(repo, "rm", "-q", "--", TRACKED_RECORD)
    _write(repo, PRODUCT, "the Player changed the product\n")

    caplog.set_level(logging.WARNING)
    site(repo, tmp_path, 1)

    assert PRODUCT in _committed_names(repo)
    assert not _warnings(caplog, "moves or copies")


def test_a_product_file_copied_from_another_is_committed(
    site, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Control: a copy whose source is a product file is ordinary work."""
    repo = _init_repo(tmp_path / "repo")
    _base_with_tracked_record(repo)
    copy = "src/app_copy.txt"
    _write(repo, copy, (repo / PRODUCT).read_text(encoding="utf-8") + "one more\n")

    caplog.set_level(logging.WARNING)
    site(repo, tmp_path, 1)

    assert copy in _committed_names(repo)
    assert not _warnings(caplog, "moves or copies")


# --- Design test 10: embedded repositories, through the production helper --


def _nested_repository(repo: Path) -> str:
    nested = repo / ".guardkit" / "worktrees" / "FEAT-1"
    _init_repo(nested)
    return ".guardkit/worktrees/FEAT-1"


def _checkpoint(repo: Path, turn: int = 1):
    manager = WorktreeCheckpointManager(worktree_path=repo, task_id="TASK-001")
    return manager.create_checkpoint(turn=turn, tests_passed=True, test_count=1)


def test_an_untracked_inner_build_folder_does_not_stop_the_checkpoint(
    tmp_path: Path,
) -> None:
    repo = _init_repo(tmp_path / "repo")
    nested = _nested_repository(repo)
    _write(repo, ORDINARY, "the Player's work\n")

    _checkpoint(repo)

    assert ORDINARY in _committed_names(repo)
    listing = _git(repo, "ls-files", "-s").stdout
    assert "160000" not in listing and nested not in listing, listing


@pytest.mark.parametrize("state", ["staged", "tracked"])
def test_a_staged_or_tracked_inner_build_folder_is_refused(
    state: str, tmp_path: Path
) -> None:
    from guardkit.lib.project_git import SUBMODULE_REFUSAL

    repo = _init_repo(tmp_path / "repo")
    nested = _nested_repository(repo)
    _git(repo, "add", "--", nested)
    if state == "tracked":
        _git(repo, "commit", "-m", "an older build committed the inner folder")
    head_before = _git(repo, "rev-parse", "HEAD").stdout
    _write(repo, ORDINARY, "the Player's work\n")

    with pytest.raises(subprocess.CalledProcessError) as refused:
        _checkpoint(repo)

    sentence = SUBMODULE_REFUSAL.format(command="add")
    assert refused.value.stderr == sentence
    assert _git(repo, "rev-parse", "HEAD").stdout == head_before, "nothing committed"


# --- Design test 8: no exclusion is ever refused by git ---------------------


def _sample_for(spec: str) -> tuple[str, str]:
    """A file the exclusion covers, and an ignore line covering it."""
    from guardkit.orchestrator.worktree_checkpoints import CHECKPOINT_EXCLUDE_PATHSPECS

    assert spec in CHECKPOINT_EXCLUDE_PATHSPECS
    body = spec[len(":(exclude,glob)"):]
    if body.startswith("**/"):
        body = body[3:]
    if body.endswith("/**"):
        folder = body[:-3]
        return f"{folder}/x.txt", f"{folder}/"
    if body.startswith("*"):
        return "a" + body[1:], body
    if body.endswith("*"):
        return body[:-1], body
    return body, body


def _exclusion_specs() -> list[str]:
    from guardkit.orchestrator.worktree_checkpoints import CHECKPOINT_EXCLUDE_PATHSPECS

    return [str(s) for s in CHECKPOINT_EXCLUDE_PATHSPECS]


@pytest.mark.parametrize("spec", _exclusion_specs())
def test_no_exclusion_is_refused_where_the_project_ignores_it(
    site, spec: str, tmp_path: Path
) -> None:
    repo = _init_repo(tmp_path / "repo")
    sample, ignore_line = _sample_for(spec)
    _write(repo, ".gitignore", ignore_line + "\n")
    _git(repo, "add", "--", ".gitignore")
    _git(repo, "commit", "-m", "the project ignores the folder")
    _write(repo, sample, "present on disk\n")
    _write(repo, ORDINARY, "the Player's work\n")

    site(repo, tmp_path, 1)

    committed = _committed_names(repo)
    assert ORDINARY in committed, committed
    assert sample not in _tree(repo)


#: The ignore rules the web lane asked to be checked, each with every record
#: and model folder present on disk.
IGNORE_RULES = (
    "large_tool_results/",
    "/large_tool_results",
    ".guardkit/",
    ".guardkit/autobuild/",
    "/.guardkit/autobuild",
    ".guardkit/autobuild-private/",
    ".guardkit/qav-shadow/",
    "*.jsonl",
    ".guardkit/memory-query-log.jsonl",
    ".guardkit/bootstrap_state.json",
    "node_modules/",
    ".claude/task-plans/",
    "conversation_history/",
)


@pytest.mark.parametrize("rule", IGNORE_RULES)
def test_no_ignore_rule_makes_the_checkpoint_fail(
    site, rule: str, tmp_path: Path
) -> None:
    repo = _init_repo(tmp_path / "repo")
    _write(repo, ".gitignore", rule + "\n")
    _git(repo, "add", "--", ".gitignore")
    _git(repo, "commit", "-m", "the project ignores a factory folder")
    for path in (
        *NEW_RECORDS,
        ".guardkit/autobuild-private/feature_check.json",
        ".guardkit/bootstrap_state.json",
        "large_tool_results/y",
        "conversation_history/x.md",
        "node_modules/a/index.js",
        ".claude/task-plans/TASK-1-implementation-plan.md",
    ):
        _write(repo, path, "present on disk\n")
    _write(repo, ORDINARY, "the Player's work\n")

    site(repo, tmp_path, 1)

    assert ORDINARY in _committed_names(repo)


# --- Design test 27 (GuardKit's half): the list is pinned ------------------


def test_the_eight_record_paths_are_pinned() -> None:
    from guardkit.orchestrator import worktree_checkpoints as wc

    assert wc.FACTORY_RECORD_PATHS == (
        "**/.guardkit/autobuild/**",
        "**/.guardkit/autobuild-private/**",
        "**/.guardkit/qav-shadow/**",
        "**/.guardkit/memory-query-log.jsonl*",
        "**/.guardkit/worktrees/**",
        "**/.guardkit/bootstrap_state.json",
        "conversation_history/**",
        "**/large_tool_results/**",
    )
    # Each folder path is also matched by its bare name, so a symbolic link
    # of that name is a record too (fix pass 1).
    assert wc.FACTORY_RECORD_PATHSPECS == tuple(
        f":(glob){p}" for p in (
            *wc.FACTORY_RECORD_PATHS[:6],
            "**/.guardkit/autobuild",
            "**/.guardkit/autobuild-private",
            "**/.guardkit/qav-shadow",
            "**/.guardkit/worktrees",
        )
    )
    assert wc.MODEL_ARTIFACT_PATHSPECS == (
        ":(glob)conversation_history/**",
        ":(glob)**/large_tool_results/**",
        ":(glob)conversation_history",
        ":(glob)**/large_tool_results",
    )
    excluded = {str(s) for s in wc.CHECKPOINT_EXCLUDE_PATHSPECS}
    for path in wc.FACTORY_RECORD_PATHS:
        forms = [path] + ([path[:-3]] if path.endswith("/**") else [])
        for form in forms:
            if path == "conversation_history/**":
                # Never named in the add: git refuses the add in a project
                # that ignores the folder. The unstaging step keeps it out.
                assert f":(exclude,glob){form}" not in excluded
            else:
                assert f":(exclude,glob){form}" in excluded, form


MATCHER_PATHS = (
    ".guardkit/autobuild/x.json",
    "a/b/.guardkit/autobuild/T/p.json",
    "t1/.guardkit/autobuild",
    ".guardkit/autobuildx/y",
    ".guardkit/autobuild-private/f.json",
    ".guardkit/qav-shadow/queue.jsonl",
    "t2/.guardkit/qav-shadow",
    ".guardkit/memory-query-log.jsonl",
    ".guardkit/memory-query-log.jsonl.1",
    "p/.guardkit/memory-query-log.jsonl.2",
    ".guardkit/memory-query-log.json",
    "t3/.guardkit/memory-query-log.jsonl.d/x",
    ".guardkit/worktrees/FEAT-1/a",
    ".guardkit/bootstrap_state.json",
    "p/.guardkit/bootstrap_state.json",
    ".guardkit/bootstrap_state.json.bak",
    "conversation_history/x.md",
    "conversation_history/d/y.md",
    "src/conversation_history/k.go",
    "t4/conversation_history",
    "large_tool_results/y",
    "p/q/large_tool_results/z",
    "t5/large_tool_results",
    "t6/large_tool_results.py",
    "t7/.guardkit/worktrees.md",
    "t8/.guardkit/autobuild.yaml",
    "x.guardkit/autobuild/z",
    "guardkit/autobuild/x",
    ".guardkit/AUTOBUILD/x",
    ".guardkit/features/F.yaml",
    ".guardkit/config.yaml",
    "docs/state/notes.md",
    "tasks/backlog/TASK-1.md",
    "notes/old.json",
)


def test_is_factory_record_agrees_with_git(tmp_path: Path) -> None:
    from guardkit.lib.project_git import pattern_pathspec, run_git
    from guardkit.orchestrator import worktree_checkpoints as wc

    repo = _init_repo(tmp_path / "repo")
    for path in MATCHER_PATHS:
        _write(repo, path, "x\n")
    globs = list(wc.FACTORY_RECORD_PATHS) + [
        p[:-3] for p in wc.FACTORY_RECORD_PATHS if p.endswith("/**")
    ]
    listed = run_git(
        ["ls-files", "--others", "-z", "--",
         *[pattern_pathspec(f":(glob){p}") for p in globs]],
        cwd=repo, check=True,
    ).stdout
    by_git = {p for p in listed.split("\0") if p}
    assert by_git, "git matched something"
    assert {p for p in MATCHER_PATHS if wc.is_factory_record(p)} == by_git


# --- Fix pass 1: exact copies of records that were never committed ---------
#
# Records are no longer committed, so git's own copy detection (which only
# looks at files HEAD or the index holds) cannot see a copy of one. The
# unstaging step compares what is staged with every record file on disk.

UNTRACKED_TURN = ".guardkit/autobuild/TASK-1/player_turn_1.json"
SHORT_RECORD = ".guardkit/autobuild-private/feature_check.json"


@pytest.mark.parametrize(
    "record, copy, text",
    [
        (UNTRACKED_TURN, "notes/turn.json", _record_json()),
        (SHORT_RECORD, "docs/check.json", "{}"),
    ],
    ids=["turn-record", "short-record"],
)
def test_an_exact_copy_of_an_untracked_record_is_not_committed(
    site, record: str, copy: str, text: str, tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    repo = _init_repo(tmp_path / "repo")
    _write(repo, record, text)
    _write(repo, copy, text)
    _write(repo, ORDINARY, "the Player's work\n")

    caplog.set_level(logging.WARNING)
    site(repo, tmp_path, 1)

    committed = _committed_names(repo)
    assert ORDINARY in committed, committed
    assert copy not in _tree(repo), committed
    assert (repo / copy).is_file(), "the copy stays on disk"
    assert _warnings(caplog, copy, "moves or copies"), [
        r.getMessage() for r in caplog.records
    ]


def test_a_copy_of_an_ignored_record_is_not_committed(
    site, tmp_path: Path
) -> None:
    """A project that ignores the record folder (a factory test project's
    shape): the record is ignored, the copy is not."""
    repo = _init_repo(tmp_path / "repo")
    _write(repo, ".gitignore", ".guardkit/autobuild/\n")
    _git(repo, "add", "--", ".gitignore")
    _git(repo, "commit", "-m", "the project ignores records")
    _write(repo, UNTRACKED_TURN, _record_json())
    _write(repo, "notes/turn.json", _record_json())
    _write(repo, ORDINARY, "the Player's work\n")

    site(repo, tmp_path, 1)

    assert ORDINARY in _committed_names(repo)
    assert "notes/turn.json" not in _tree(repo)


def test_a_file_one_byte_away_from_a_record_and_empty_files_are_committed(
    site, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    repo = _init_repo(tmp_path / "repo")
    text = _record_json()
    _write(repo, UNTRACKED_TURN, text)
    _write(repo, "notes/near.json", text.replace("value", "valuE", 1))
    _write(repo, ".guardkit/autobuild/TASK-1/empty.json", "")
    _write(repo, "src/empty.txt", "")

    caplog.set_level(logging.WARNING)
    site(repo, tmp_path, 1)

    committed = _committed_names(repo)
    assert "notes/near.json" in committed, committed
    assert "src/empty.txt" in committed, committed
    assert not _warnings(caplog, "moves or copies")


# --- Fix pass 1: a symbolic link named exactly like a record folder ---------

LINK_NAMES = (
    ".guardkit/autobuild",
    ".guardkit/autobuild-private",
    ".guardkit/qav-shadow",
    ".guardkit/worktrees",
    "conversation_history",
    "large_tool_results",
    "packages/app/large_tool_results",
)


@pytest.mark.parametrize("name", LINK_NAMES)
def test_a_link_named_like_a_record_folder_is_not_committed(
    site, name: str, tmp_path: Path
) -> None:
    repo = _init_repo(tmp_path / "repo")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    link = repo / name
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(elsewhere, target_is_directory=True)
    _write(repo, ORDINARY, "the Player's work\n")

    site(repo, tmp_path, 1)

    assert ORDINARY in _committed_names(repo)
    assert name not in _tree(repo)
    assert link.is_symlink(), "the link stays on disk"


def test_a_pre_staged_link_named_like_a_record_folder_is_taken_out(
    site, tmp_path: Path
) -> None:
    repo = _init_repo(tmp_path / "repo")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    for name in LINK_NAMES:
        link = repo / name
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(elsewhere, target_is_directory=True)
    _write(repo, ORDINARY, "the Player's work\n")
    _git(repo, "add", "--", *LINK_NAMES, ORDINARY)

    site(repo, tmp_path, 1)

    tree = _tree(repo)
    assert ORDINARY in tree
    for name in LINK_NAMES:
        assert name not in tree, (name, tree)


# --- Empty files are never taken for copies of an empty record --------------
#
# git pairs empty files with each other as copies. An empty record that HEAD
# tracks, or one already staged, must not make a new empty product file (an
# ``__init__.py``, a ``.gitkeep``) look like a copy of it.

EMPTY_RECORD = ".guardkit/autobuild/TASK-1/empty.json"


@pytest.mark.parametrize("record_state", ["tracked", "staged"])
def test_a_new_empty_product_file_is_not_taken_for_a_record_copy(
    site, record_state: str, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    repo = _init_repo(tmp_path / "repo")
    _write(repo, EMPTY_RECORD, "")
    _git(repo, "add", "-f", "--", EMPTY_RECORD)
    if record_state == "tracked":
        _git(repo, "commit", "-m", "an older build committed an empty record")
    _write(repo, "src/__init__.py", "")
    _write(repo, "src/pkg/.gitkeep", "")
    _write(repo, ORDINARY, "the Player's work\n")

    caplog.set_level(logging.WARNING)
    site(repo, tmp_path, 1)

    tree = _tree(repo)
    assert "src/__init__.py" in tree, tree
    assert "src/pkg/.gitkeep" in tree, tree
    assert ORDINARY in tree
    assert not _warnings(caplog, "moves or copies"), [
        r.getMessage() for r in caplog.records
    ]


# --- Fix pass 3: records written while the checkpoint runs ------------------
#
# GuardKit writes a record to a temporary file and renames it over the
# record. Tasks in a parallel wave share one worktree, so a record can vanish
# between being listed and being read. That must never fail a checkpoint.


def test_records_renamed_during_the_checkpoint_never_fail_it(tmp_path: Path) -> None:
    import os
    import threading

    repo = _init_repo(tmp_path / "repo")
    folder = repo / ".guardkit" / "autobuild" / "TASK-2"
    folder.mkdir(parents=True)
    for index in range(50):
        (folder / f"old_{index}.json").write_text(
            f'{{"i": {index}}}\n' * 50, encoding="utf-8"
        )
    stop = threading.Event()

    def writer() -> None:
        count = 0
        record = folder / "coach_turn_1.json"
        temporary = folder / "coach_turn_1.json.tmp"
        while not stop.is_set():
            count += 1
            temporary.write_text(f'{{"n": {count}}}\n' * 200, encoding="utf-8")
            os.replace(temporary, record)

    thread = threading.Thread(target=writer, daemon=True)
    thread.start()
    manager = WorktreeCheckpointManager(worktree_path=repo, task_id="TASK-001")
    failures = []
    try:
        for turn in range(1, 151):
            _write(repo, f"src/f{turn}.txt", f"{turn}\n")
            try:
                manager.create_checkpoint(turn=turn, tests_passed=True, test_count=1)
            except Exception as exc:  # noqa: BLE001 - counted, then asserted
                failures.append(f"turn {turn}: {type(exc).__name__}")
    finally:
        stop.set()
        thread.join(timeout=10)
    assert failures == [], failures
    assert not [p for p in _tree(repo) if p.startswith(".guardkit/autobuild/")]


# --- Fix pass 3: a copy of a record inside an inner build repository --------


def test_a_copy_of_an_inner_build_repositorys_record_is_not_committed(
    site, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    repo = _init_repo(tmp_path / "repo")
    inner = repo / ".guardkit" / "worktrees" / "FEAT-1"
    _init_repo(inner)
    product_text = "package main\n\nfunc main() {}\n"
    _write(inner, "src/main.go", product_text)
    _git(inner, "add", "--", "src/main.go")
    _git(inner, "commit", "-m", "the inner build's product")
    record_text = _record_json()
    _write(inner, ".guardkit/autobuild/TASK-1/player_turn_1.json", record_text)
    _write(repo, "notes/turn.json", record_text)
    # A product file identical to one of the inner build's product files is
    # ordinary work: the inner build's product files are never compared.
    _write(repo, "src/main.go", product_text)

    caplog.set_level(logging.WARNING)
    site(repo, tmp_path, 1)

    tree = _tree(repo)
    assert "notes/turn.json" not in tree, tree
    assert (repo / "notes/turn.json").is_file()
    assert "src/main.go" in tree, tree
    assert _warnings(caplog, "notes/turn.json", "moves or copies")
