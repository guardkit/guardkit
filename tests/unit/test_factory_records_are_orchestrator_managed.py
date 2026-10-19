"""GuardKit's own records never count as the builder's work.

Build FEAT-D31F's repair (19 October 2026) ran at the repository root, where
the Coach's private records folder (``.guardkit/autobuild-private/``) sits
inside the build folder. The orchestrator-managed path list did not name it,
nor the memory query log, so 13 Coach records and the log were listed as files
the builder created: the code reviewer was sent to read them, and they made
every turn look busy to the stall check.

The checkpoint's ``FACTORY_RECORD_PATHS`` already lists every folder GuardKit
and the coding model write records to. This pins that the managed path list
matches each of them, and that the narrow anchors still let real work through.
Real git repository for the stall-check probe; invented names; no network, no
model.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from guardkit.orchestrator.agent_invoker import (
    _is_orchestrator_managed_path,
    _strip_orchestrator_managed_paths,
)
from guardkit.orchestrator.autobuild import _worktree_change_snapshot
from guardkit.orchestrator.worktree_checkpoints import FACTORY_RECORD_PATHS


def _root_form(glob: str) -> str:
    """``**/.guardkit/x/**`` -> ``.guardkit/x/record.json``; files kept as is."""
    path = glob[3:] if glob.startswith("**/") else glob
    if path.endswith("/**"):
        path = path[:-3] + "/record.json"
    return path.replace("*", "")


@pytest.mark.parametrize("glob", FACTORY_RECORD_PATHS)
def test_every_factory_record_folder_is_orchestrator_managed(glob: str) -> None:
    assert _is_orchestrator_managed_path(_root_form(glob)), glob


@pytest.mark.parametrize(
    "path",
    [
        ".guardkit/autobuild-private/TASK-X-002/coach_turn_1.json",
        ".guardkit/autobuild-private/build-FEAT-X/coach_project_documents_start.json",
        ".guardkit/memory-query-log.jsonl",
        ".guardkit/memory-query-log.jsonl.1",
        "apps/shelf/.guardkit/memory-query-log.jsonl",
        ".guardkit/qav-shadow/queue/item.json",
        ".guardkit/worktrees/FEAT-X/README.md",
        "conversation_history/session-1.md",
    ],
)
def test_the_records_seen_in_the_repair_build_match(path: str) -> None:
    assert _is_orchestrator_managed_path(path)


@pytest.mark.parametrize(
    "path",
    [
        ".guardkit/features/FEAT-X.yaml",
        ".guardkit/autobuild-private-notes.md",
        "docs/conversation_history.md",
        "apps/chat/src/conversation_history/store.ts",
        "apps/shelf/src/memory-query-log.ts",
        "apps/shelf/src/Shelf.tsx",
    ],
)
def test_real_work_still_passes_through(path: str) -> None:
    assert not _is_orchestrator_managed_path(path)


def test_the_builders_report_loses_the_records_and_keeps_the_work() -> None:
    report = {
        "files_created": [
            ".guardkit/autobuild-private/TASK-X-002/coach_turn_1.json",
            ".guardkit/memory-query-log.jsonl",
            "apps/shelf/src/ShelfCount.tsx",
        ],
        "files_modified": ["apps/shelf/src/Shelf.tsx"],
        "tests_written": [],
    }

    _strip_orchestrator_managed_paths(report, "TASK-X-002")

    assert report["files_created"] == ["apps/shelf/src/ShelfCount.tsx"]
    assert report["files_modified"] == ["apps/shelf/src/Shelf.tsx"]


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def test_the_stall_check_does_not_count_coach_records(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _git("init", "-q", cwd=root)
    _git("config", "user.email", "test@example.com", cwd=root)
    _git("config", "user.name", "Test", cwd=root)
    (root / "README.md").write_text("base\n")
    _git("add", "-A", cwd=root)
    _git("commit", "-q", "-m", "base", cwd=root)

    private = root / ".guardkit" / "autobuild-private" / "TASK-X-002"
    private.mkdir(parents=True)
    (private / "coach_turn_1.json").write_text("{}\n")
    (root / ".guardkit" / "memory-query-log.jsonl").write_text("{}\n")

    assert _worktree_change_snapshot(root) == {}
