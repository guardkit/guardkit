"""Regression tests for orchestrator-induced ghost-path filtering.

Covers TASK-FIX-1B4C (Layer 3' of the FEAT-FFC3 false-fail fix). State_bridge
persists every move it performs to a per-task ``state_transitions.json``;
``AgentInvoker._create_player_report_from_task_work`` subtracts those pre-move
paths from the post-turn ``git diff --name-only`` enrichment so the
orchestrator-induced ghost never reaches the Coach.

Coverage Target: >=85%
Test Count: 5 tests (one per AC-C6 bullet)
"""

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import List

import pytest

from guardkit.orchestrator.paths import TaskArtifactPaths
from guardkit.tasks.state_bridge import TaskStateBridge

TASK_ID = "TASK-FIX-1B4C"
TASK_FILENAME = f"{TASK_ID}-filter-orchestrator-induced-ghosts.md"
SAMPLE_TASK_BODY = """---
id: TASK-FIX-1B4C
title: Layer 3' filter
status: backlog
---

# Sample
Body.
"""


def _make_worktree(tmp_path: Path) -> Path:
    """Create a minimal repo skeleton with the standard tasks/ layout."""
    for state in ("backlog", "in_progress", "design_approved"):
        (tmp_path / "tasks" / state).mkdir(parents=True, exist_ok=True)
    (tmp_path / ".claude" / "task-plans").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _write_state_transitions(
    repo_root: Path, task_id: str, records: List[dict]
) -> Path:
    """Write a hand-crafted state_transitions.json for the task."""
    autobuild_dir = TaskArtifactPaths.autobuild_dir(task_id, repo_root)
    autobuild_dir.mkdir(parents=True, exist_ok=True)
    transitions_path = autobuild_dir / "state_transitions.json"
    transitions_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return transitions_path


# ---------------------------------------------------------------------------
# AC-C6 #1 — transition_to_design_approved persists a record
# ---------------------------------------------------------------------------


class TestStateBridgePersistsTransitionRecord:
    """AC-C1: every state-bridge move appends to state_transitions.json."""

    def test_state_bridge_persists_transition_record(self, tmp_path: Path):
        worktree = _make_worktree(tmp_path)
        task_path = worktree / "tasks" / "backlog" / TASK_FILENAME
        task_path.write_text(SAMPLE_TASK_BODY)

        bridge = TaskStateBridge(TASK_ID, worktree, in_autobuild_context=True)
        bridge.transition_to_design_approved()

        transitions_path = (
            TaskArtifactPaths.autobuild_dir(TASK_ID, worktree)
            / "state_transitions.json"
        )
        assert transitions_path.exists(), (
            "transition_to_design_approved must persist state_transitions.json"
        )

        records = json.loads(transitions_path.read_text(encoding="utf-8"))
        assert isinstance(records, list)
        assert len(records) == 1

        record = records[0]
        assert record["task_id"] == TASK_ID
        assert record["pre_path"] == f"tasks/backlog/{TASK_FILENAME}"
        assert record["post_path"] == f"tasks/design_approved/{TASK_FILENAME}"
        assert record["kind"] == "design_approved_transition"
        assert "timestamp" in record and record["timestamp"]


# ---------------------------------------------------------------------------
# AC-C6 #2 — real worktree, real git: ghost path filtered out
# ---------------------------------------------------------------------------


def _git(worktree: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=worktree,
        check=True,
        capture_output=True,
        text=True,
    )


class TestOrchestratorInducedPathsFilteredFromFilesModified:
    """AC-C6 #2: end-to-end realism with real subprocess git + state-bridge."""

    def test_orchestrator_induced_paths_filtered_from_files_modified(
        self, tmp_path: Path
    ):
        # Skip when git is unavailable on the test host.
        if shutil.which("git") is None:
            pytest.skip("git not available")

        worktree = _make_worktree(tmp_path)

        # Initialise a real repo with the task file committed in tasks/backlog
        # so state_bridge.transition_to_design_approved triggers a tracked
        # rename → `git diff --name-only` will report the source path.
        _git(worktree, "init", "-q", "-b", "main")
        _git(worktree, "config", "user.email", "test@example.com")
        _git(worktree, "config", "user.name", "Test")

        task_path = worktree / "tasks" / "backlog" / TASK_FILENAME
        task_path.write_text(SAMPLE_TASK_BODY)
        _git(worktree, "add", "-A")
        _git(worktree, "commit", "-q", "-m", "baseline")

        baseline = _git(worktree, "rev-parse", "HEAD").stdout.strip()

        # Simulate the mid-turn orchestrator-induced move.
        bridge = TaskStateBridge(TASK_ID, worktree, in_autobuild_context=True)
        bridge.transition_to_design_approved()

        # Mirror AgentInvoker._create_player_report_from_task_work's enrichment:
        #  1. capture git_modified (post-baseline diff)
        #  2. union with the Player's empty self-report
        #  3. subtract orchestrator-induced paths
        diff_output = _git(
            worktree, "diff", "--name-only", baseline
        ).stdout.splitlines()
        git_modified = {line for line in diff_output if line}

        # Sanity check — the ghost path must actually appear in the diff so
        # the rest of the assertion is meaningful.
        ghost_path = f"tasks/backlog/{TASK_FILENAME}"
        assert ghost_path in git_modified, (
            "Test fixture invariant: state-bridge move should appear in "
            "`git diff --name-only` as the deleted source path."
        )

        # Player's self-report had no files modified.
        report = {"files_modified": [], "files_created": []}
        original_modified = set(report["files_modified"])
        report["files_modified"] = sorted(list(original_modified | git_modified))

        induced = TaskStateBridge.orchestrator_induced_paths_for(
            TASK_ID, repo_root=worktree
        )
        assert ghost_path in induced, (
            "orchestrator_induced_paths_for must surface the recorded "
            "pre-move path so the union-merge filter can subtract it."
        )

        report["files_modified"] = sorted(
            set(report["files_modified"]) - induced
        )

        assert ghost_path not in report["files_modified"], (
            "After Layer-3' filtering, the orchestrator-induced ghost path "
            "must not appear in the final Player report."
        )


# ---------------------------------------------------------------------------
# AC-C6 #3 — fail-open: missing state_transitions.json is a no-op
# ---------------------------------------------------------------------------


class TestFilterNoOpWhenStateTransitionsJsonMissing:
    """AC-C5 / AC-C6 #3: missing file ⇒ empty set, no exception."""

    def test_filter_no_op_when_state_transitions_json_missing(
        self, tmp_path: Path
    ):
        worktree = _make_worktree(tmp_path)
        # No state_transitions.json exists — confirm the path is missing.
        transitions_path = (
            TaskArtifactPaths.autobuild_dir(TASK_ID, worktree)
            / "state_transitions.json"
        )
        assert not transitions_path.exists()

        result = TaskStateBridge.orchestrator_induced_paths_for(
            TASK_ID, repo_root=worktree
        )

        assert result == set()


# ---------------------------------------------------------------------------
# AC-C6 #4 — fail-open: malformed JSON yields empty set + warning
# ---------------------------------------------------------------------------


class TestFilterNoOpWhenStateTransitionsJsonMalformed:
    """AC-C2 corruption case: malformed JSON ⇒ warning + empty set."""

    def test_filter_no_op_when_state_transitions_json_malformed(
        self, tmp_path: Path, caplog
    ):
        worktree = _make_worktree(tmp_path)
        autobuild_dir = TaskArtifactPaths.autobuild_dir(TASK_ID, worktree)
        autobuild_dir.mkdir(parents=True, exist_ok=True)
        transitions_path = autobuild_dir / "state_transitions.json"
        transitions_path.write_text("{this is not valid json", encoding="utf-8")

        with caplog.at_level(logging.WARNING, logger="guardkit.tasks.state_bridge"):
            result = TaskStateBridge.orchestrator_induced_paths_for(
                TASK_ID, repo_root=worktree
            )

        assert result == set()
        assert any(
            "malformed" in record.message and TASK_ID in record.message
            for record in caplog.records
        ), "Malformed JSON must emit a structured warning identifying the task."


# ---------------------------------------------------------------------------
# AC-C6 #5 — multi-move: every recorded pre-path is returned
# ---------------------------------------------------------------------------


class TestMultipleStateBridgeMovesInSameTurnAllFiltered:
    """AC-C6 #5: two transition records ⇒ both pre-paths in result set."""

    def test_multiple_state_bridge_moves_in_same_turn_all_filtered(
        self, tmp_path: Path
    ):
        worktree = _make_worktree(tmp_path)
        records = [
            {
                "task_id": TASK_ID,
                "pre_path": "tasks/backlog/TASK-FIX-1B4C-old-1.md",
                "post_path": "tasks/design_approved/TASK-FIX-1B4C-old-1.md",
                "timestamp": "2026-05-06T00:00:00+00:00",
                "kind": "design_approved_transition",
            },
            {
                "task_id": TASK_ID,
                "pre_path": "tasks/backlog/TASK-FIX-1B4C-old-2.md",
                "post_path": "tasks/design_approved/TASK-FIX-1B4C-old-2.md",
                "timestamp": "2026-05-06T00:01:00+00:00",
                "kind": "design_approved_transition",
            },
        ]
        _write_state_transitions(worktree, TASK_ID, records)

        result = TaskStateBridge.orchestrator_induced_paths_for(
            TASK_ID, repo_root=worktree
        )

        assert result == {
            "tasks/backlog/TASK-FIX-1B4C-old-1.md",
            "tasks/backlog/TASK-FIX-1B4C-old-2.md",
        }
