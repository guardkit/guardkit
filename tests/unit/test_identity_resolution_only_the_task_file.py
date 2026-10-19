"""The existence check resolves only the task's own document, not any missing file.

TASK-FIX-1B4A (May 2026) let the existence check accept a missing claimed path
when the task document could be found elsewhere: the orchestrator moves the
task file between state folders, and a report could still name the old place.
But the check accepted ANY missing path once the task document existed. In
build FEAT-D31F (19 October 2026) a deleted page component was recorded as
"resolved" to the task markdown. Only the claim check stood between a phantom
file and an approval.

Now a missing path is resolved only when it names the task's own document
(same file name). Invented names; no network, no model.
"""

from __future__ import annotations

from pathlib import Path

from guardkit.orchestrator.coach_verification import CoachVerifier
from guardkit.tasks.state_bridge import TaskStateBridge


TASK_ID = "TASK-SHELF-003"
TASK_FILE = f"{TASK_ID}-build-the-shelf.md"


def _worktree(tmp_path: Path) -> Path:
    for state in ("backlog", "design_approved", "in_progress"):
        (tmp_path / "tasks" / state).mkdir(parents=True)
    # The orchestrator has moved the task document to design_approved.
    (tmp_path / "tasks" / "design_approved" / TASK_FILE).write_text("# task\n")
    return tmp_path


def _verifier(worktree: Path) -> CoachVerifier:
    bridge = TaskStateBridge(TASK_ID, worktree, in_autobuild_context=True)
    return CoachVerifier(worktree, task_id=TASK_ID, state_bridge=bridge)


def test_a_missing_source_file_is_not_resolved_to_the_task_document(
    tmp_path: Path,
) -> None:
    worktree = _worktree(tmp_path)
    verifier = _verifier(worktree)

    records = verifier._verify_files_exist(
        {"files_modified": ["apps/shelf/src/pages/ShelfForm.tsx"]}
    )

    assert [(r.claim_type, r.severity) for r in records] == [
        ("file_existence", "critical")
    ]
    assert verifier._resolved_paths == []


def test_the_task_document_at_its_old_place_is_still_resolved(
    tmp_path: Path,
) -> None:
    worktree = _worktree(tmp_path)
    verifier = _verifier(worktree)

    records = verifier._verify_files_exist(
        {"files_modified": [f"tasks/backlog/{TASK_FILE}"]}
    )

    assert records == []
    assert [rp.claimed for rp in verifier._resolved_paths] == [
        f"tasks/backlog/{TASK_FILE}"
    ]
    assert "design_approved" in verifier._resolved_paths[0].resolved_to


def test_one_report_with_both_resolves_only_the_task_document(
    tmp_path: Path,
) -> None:
    worktree = _worktree(tmp_path)
    verifier = _verifier(worktree)

    records = verifier._verify_files_exist(
        {
            "files_modified": [
                f"tasks/backlog/{TASK_FILE}",
                "apps/shelf/src/Ghost.tsx",
            ]
        }
    )

    assert [r.player_claim for r in records] == [
        "files_modified: apps/shelf/src/Ghost.tsx"
    ]
    assert [rp.claimed for rp in verifier._resolved_paths] == [
        f"tasks/backlog/{TASK_FILE}"
    ]
