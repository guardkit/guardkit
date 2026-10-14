"""Proof that the coding model's own working files never enter a factory commit.

Plain words: the coding model's library writes two kinds of file of its own,
a summarised transcript of the conversation (``conversation_history/``) and
tool output too large to keep inline (``large_tool_results/``). A transcript
quotes every path the model saw. On 14 October 2026 a build's first
checkpoint committed one into a public project's branch. The factory now
keeps these files outside the worktree; these tests prove the guard behind
that: none of GuardKit's three commit sites commits them, whether they were
staged beforehand or not, while real changes still go in. Transcripts are
caught at the worktree root, where the model's libraries write them, so a
product's own ``src/conversation_history/`` is still committed; oversized
tool output is caught at any depth, as before.

The three sites, run through the same public entry points the build uses,
are shared with ``test_private_records_never_committed.py``.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from tests.orchestrator.test_private_records_never_committed import (  # noqa: F401
    _committed_names,
    _git,
    _init_repo,
    _write,
    site,
)


TRANSCRIPT = "conversation_history/x.md"
LARGE_RESULT = "large_tool_results/y"
NESTED_RESULT = "packages/app/large_tool_results/z"
PRODUCT_FOLDER = "src/conversation_history/store.py"
ORDINARY = "src/feature.txt"


def _model_warnings(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [
        r.getMessage()
        for r in caplog.records
        if r.levelno == logging.WARNING and "coding model" in r.getMessage()
    ]


def _tree(repo: Path) -> list[str]:
    return _git(repo, "ls-tree", "-r", "--name-only", "HEAD").stdout.splitlines()


def test_stray_model_files_are_not_committed_but_real_changes_are(
    site, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    repo = _init_repo(tmp_path / "repo")
    _write(repo, TRANSCRIPT, "## Summarized\n/placeholder/home/user/project\n")
    _write(repo, LARGE_RESULT, "a very large tool result\n")
    _write(repo, NESTED_RESULT, "a nested tool result\n")
    _write(repo, ORDINARY, "the Player's work\n")

    caplog.set_level(logging.WARNING)
    site(repo, tmp_path, 1)

    committed = _committed_names(repo)
    assert ORDINARY in committed, committed
    tree = _tree(repo)
    for path in (TRANSCRIPT, LARGE_RESULT, NESTED_RESULT):
        assert path not in tree, tree
        assert (repo / path).is_file(), "the file stays on disk"
    warnings = _model_warnings(caplog)
    assert warnings, "a plain warning names what was left out"
    assert TRANSCRIPT in warnings[0] and LARGE_RESULT in warnings[0]


def test_pre_staged_model_files_are_unstaged_before_the_commit(
    site, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    repo = _init_repo(tmp_path / "repo")
    _write(repo, TRANSCRIPT, "## Summarized\n")
    _write(repo, LARGE_RESULT, "a very large tool result\n")
    _write(repo, ORDINARY, "the Player's work\n")
    _git(repo, "add", "--", TRANSCRIPT, LARGE_RESULT, ORDINARY)

    caplog.set_level(logging.WARNING)
    site(repo, tmp_path, 1)

    committed = _committed_names(repo)
    assert ORDINARY in committed, committed
    assert TRANSCRIPT not in committed and LARGE_RESULT not in committed, committed
    status = _git(repo, "status", "--porcelain", "--untracked-files=all").stdout
    assert f"?? {TRANSCRIPT}" in status.splitlines(), status
    assert f"?? {LARGE_RESULT}" in status.splitlines(), status
    assert _model_warnings(caplog)


def test_no_warning_when_there_are_no_model_files(
    site, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    repo = _init_repo(tmp_path / "repo")
    _write(repo, ORDINARY, "the Player's work\n")
    # A file whose name only resembles the folders is ordinary work, and so
    # is a product folder of the same name below the root.
    _write(repo, "docs/conversation_history.md", "a design note\n")
    _write(repo, PRODUCT_FOLDER, "class Store: ...\n")

    caplog.set_level(logging.WARNING)
    site(repo, tmp_path, 1)

    committed = _committed_names(repo)
    assert ORDINARY in committed and "docs/conversation_history.md" in committed
    assert PRODUCT_FOLDER in committed, committed
    assert not _model_warnings(caplog)


def test_a_staged_product_conversation_history_folder_is_committed(
    site, tmp_path: Path
) -> None:
    repo = _init_repo(tmp_path / "repo")
    _write(repo, PRODUCT_FOLDER, "class Store: ...\n")
    _git(repo, "add", "--", PRODUCT_FOLDER)

    site(repo, tmp_path, 1)

    assert PRODUCT_FOLDER in _committed_names(repo)
