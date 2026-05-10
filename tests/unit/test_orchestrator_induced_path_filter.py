"""Regression tests for orchestrator-induced ghost-path filtering.

Covers TASK-FIX-1B4C (Layer 3' of the FEAT-FFC3 false-fail fix). State_bridge
persists every move it performs to a per-task ``state_transitions.json``;
``AgentInvoker._create_player_report_from_task_work`` subtracts those pre-move
paths from the post-turn ``git diff --name-only`` enrichment so the
orchestrator-induced ghost never reaches the Coach.

Also covers TASK-FIX-PCN (sibling pattern-based filter for orchestrator-
managed namespaces): ``.guardkit/autobuild/<TASK-ID>/*.json``,
``.guardkit/bootstrap_state.json``, and
``tasks/(backlog|design_approved|in_progress|in_review|completed)/*.md`` are
stripped from Player-report claim lists before the report reaches the Coach.

Coverage Target: >=85%
Test Count: 5 (TASK-FIX-1B4C) + 6 (TASK-FIX-PCN) = 11 tests
"""

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import pytest

from guardkit.orchestrator.agent_invoker import (
    _is_orchestrator_managed_path,
    _strip_orchestrator_managed_paths,
)
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


# ===========================================================================
# TASK-FIX-PCN — Pattern-based filter for orchestrator-managed namespaces
# ===========================================================================
#
# Sibling of the state_transitions.json filter above. Where that filter
# handles *recorded* state-bridge moves, this one handles the broader class
# of paths the orchestrator owns: .guardkit/autobuild/* sidecars,
# .guardkit/bootstrap_state.json, and tasks/<state>/*.md scaffold files
# (including subfolder variants under feature folders). See TASK-FIX-PCN
# acceptance criteria AC-1 through AC-5.

PCN_TASK_ID = "TASK-FIX-PCN"
PCN_FEAT_ID = "FEAT-39E1"


# ---------------------------------------------------------------------------
# AC-3 #1 — _is_orchestrator_managed_path matches every AC-2 path class
# ---------------------------------------------------------------------------


class TestIsOrchestratorManagedPathMatcher:
    """AC-3 (matcher unit): every AC-2 path class is recognised."""

    @pytest.mark.parametrize(
        "path",
        [
            # AC-2 bullet 1 — .guardkit/autobuild/<TASK-ID>/*.json
            f".guardkit/autobuild/{PCN_TASK_ID}/coach_turn_1.json",
            f".guardkit/autobuild/{PCN_TASK_ID}/player_turn_2.json",
            f".guardkit/autobuild/{PCN_TASK_ID}/turn_state_turn_1.json",
            f".guardkit/autobuild/{PCN_TASK_ID}/state_transitions.json",
            f".guardkit/autobuild/{PCN_TASK_ID}/task_work_results.json",
            # AC-2 bullet 2 — .guardkit/bootstrap_state.json
            ".guardkit/bootstrap_state.json",
            # AC-2 bullet 3 — .guardkit/autobuild/<FEAT-ID>/*.{jsonl,md,json}
            f".guardkit/autobuild/{PCN_FEAT_ID}/turn_state.jsonl",
            f".guardkit/autobuild/{PCN_FEAT_ID}/feature_summary.md",
            f".guardkit/autobuild/{PCN_FEAT_ID}/feature.json",
            # AC-2 bullet 4 — tasks/<state>/<TASK-ID>-*.md
            f"tasks/backlog/{PCN_TASK_ID}-noisy-claim.md",
            f"tasks/design_approved/{PCN_TASK_ID}-noisy-claim.md",
            f"tasks/in_progress/{PCN_TASK_ID}-noisy-claim.md",
            f"tasks/in_review/{PCN_TASK_ID}-noisy-claim.md",
            f"tasks/completed/{PCN_TASK_ID}-noisy-claim.md",
            # AC-2 bullet 5 — feature subfolder variants
            f"tasks/backlog/run-5-feat/{PCN_TASK_ID}-noisy-claim.md",
            f"tasks/design_approved/auth-feature/{PCN_TASK_ID}-x.md",
            # ./ prefix and backslashes (Windows) are normalised
            f"./.guardkit/autobuild/{PCN_TASK_ID}/coach_turn_1.json",
            f".guardkit\\autobuild\\{PCN_TASK_ID}\\coach_turn_1.json",
        ],
    )
    def test_orchestrator_managed_path_matches(self, path: str):
        assert _is_orchestrator_managed_path(path), (
            f"Expected {path!r} to be classified as orchestrator-managed."
        )

    @pytest.mark.parametrize(
        "path",
        [
            # AC-4 — Player work product MUST pass through unchanged
            "src/study_tutor/adapters/nats_adapter.py",
            "tests/test_nats_adapter.py",
            "tests/integration/test_orchestrator.py",
            "guardkit/orchestrator/agent_invoker.py",
            "installer/core/agents/python-api-specialist.md",
            "docs/guides/autobuild-instrumentation-guide.md",
            "README.md",
            ".github/workflows/test.yml",
            # User-scripted .guardkit artefacts that are NOT autobuild-owned
            ".guardkit/graphiti.yaml",
            ".guardkit/some-user-script.py",
            # Task-related but not under a state directory
            "tasks/some-non-state-folder/notes.md",
            # Empty / non-string inputs are safely False
            "",
        ],
    )
    def test_player_authored_path_passes_through(self, path: str):
        assert not _is_orchestrator_managed_path(path), (
            f"Expected {path!r} to be treated as Player work, not "
            f"orchestrator-managed."
        )

    @pytest.mark.parametrize("non_str", [None, 123, ["list"], {"k": "v"}])
    def test_non_string_input_is_safely_false(self, non_str: Any):
        assert _is_orchestrator_managed_path(non_str) is False


# ---------------------------------------------------------------------------
# AC-3 #2 — synthetic Player report: every AC-2 path class is stripped
# ---------------------------------------------------------------------------


class TestStripOrchestratorManagedPathsRemovesAllAC2Classes:
    """AC-3: every AC-2 path class is stripped from the Player report."""

    def test_orchestrator_induced_path_filter(self, caplog):
        """Synthetic Player report seeded with one path from every AC-2
        bullet → all stripped, log line surfaces every stripped path
        (AC-5)."""
        report: Dict[str, Any] = {
            "files_modified": [
                f".guardkit/autobuild/{PCN_TASK_ID}/coach_turn_1.json",
                f".guardkit/autobuild/{PCN_TASK_ID}/player_turn_2.json",
                ".guardkit/bootstrap_state.json",
                f"tasks/backlog/{PCN_TASK_ID}-noisy.md",
                # Genuine player work — must NOT be stripped (AC-4)
                "src/study_tutor/adapters/nats_adapter.py",
            ],
            "files_created": [
                f".guardkit/autobuild/{PCN_FEAT_ID}/feature.json",
                f"tasks/design_approved/{PCN_TASK_ID}-noisy.md",
                "tests/test_nats_adapter.py",
            ],
            "tests_written": [
                f".guardkit/autobuild/{PCN_TASK_ID}/turn_state_turn_1.json",
                "tests/test_nats_adapter.py",
            ],
            "completion_promises": [
                {
                    "criterion_id": "AC-1",
                    "status": "complete",
                    "implementation_files": [
                        f".guardkit/autobuild/{PCN_TASK_ID}/state_transitions.json",
                        "src/study_tutor/adapters/nats_adapter.py",
                    ],
                    "test_file": f"tasks/in_progress/{PCN_TASK_ID}-x.md",
                },
            ],
        }

        with caplog.at_level(
            logging.INFO, logger="guardkit.orchestrator.agent_invoker"
        ):
            stripped = _strip_orchestrator_managed_paths(report, PCN_TASK_ID)

        # Every orchestrator-managed path was stripped from each list.
        assert report["files_modified"] == [
            "src/study_tutor/adapters/nats_adapter.py",
        ]
        assert report["files_created"] == ["tests/test_nats_adapter.py"]
        assert report["tests_written"] == ["tests/test_nats_adapter.py"]
        assert report["completion_promises"][0]["implementation_files"] == [
            "src/study_tutor/adapters/nats_adapter.py",
        ]
        # test_file is cleared (set to None) when it matches.
        assert report["completion_promises"][0]["test_file"] is None

        # The returned set is the union across every list.
        assert stripped == {
            f".guardkit/autobuild/{PCN_TASK_ID}/coach_turn_1.json",
            f".guardkit/autobuild/{PCN_TASK_ID}/player_turn_2.json",
            ".guardkit/bootstrap_state.json",
            f"tasks/backlog/{PCN_TASK_ID}-noisy.md",
            f".guardkit/autobuild/{PCN_FEAT_ID}/feature.json",
            f"tasks/design_approved/{PCN_TASK_ID}-noisy.md",
            f".guardkit/autobuild/{PCN_TASK_ID}/turn_state_turn_1.json",
            f".guardkit/autobuild/{PCN_TASK_ID}/state_transitions.json",
            f"tasks/in_progress/{PCN_TASK_ID}-x.md",
        }

        # AC-5: a single log line surfaces every stripped path.
        log_records = [
            r for r in caplog.records
            if "orchestrator-induced ghost path" in r.message
        ]
        assert len(log_records) == 1
        msg = log_records[0].message
        assert PCN_TASK_ID in msg
        assert f"{len(stripped)}" in msg
        # Every path must appear in the log, not just one (AC-5 emphasis).
        for path in stripped:
            assert path in msg, (
                f"Expected stripped path {path!r} to appear in the "
                f"'Filtered N orchestrator-induced ghost path(s)' log line."
            )


# ---------------------------------------------------------------------------
# AC-4 — Player-authored paths pass through unchanged
# ---------------------------------------------------------------------------


class TestPlayerAuthoredPathsPassThrough:
    """AC-4: a report with only genuine Player work is untouched."""

    def test_player_authored_paths_pass_through(self, caplog):
        """A report containing only ``src/`` and ``tests/`` paths — the
        run-5 PH1-005 NATSAdapter shape that was hand-salvaged when the
        Coach falsely failed it — must pass through with NO paths stripped
        and NO log line emitted."""
        report: Dict[str, Any] = {
            "files_modified": [
                "src/study_tutor/adapters/nats_adapter.py",
                "src/study_tutor/adapters/__init__.py",
            ],
            "files_created": [
                "src/study_tutor/adapters/nats_adapter.py",
                "tests/adapters/test_nats_adapter.py",
            ],
            "tests_written": [
                "tests/adapters/test_nats_adapter.py",
            ],
            "completion_promises": [
                {
                    "criterion_id": "AC-1",
                    "status": "complete",
                    "implementation_files": [
                        "src/study_tutor/adapters/nats_adapter.py",
                    ],
                    "test_file": "tests/adapters/test_nats_adapter.py",
                },
            ],
        }
        snapshot = json.dumps(report, sort_keys=True)

        with caplog.at_level(
            logging.INFO, logger="guardkit.orchestrator.agent_invoker"
        ):
            stripped = _strip_orchestrator_managed_paths(report, PCN_TASK_ID)

        # Nothing stripped — every path is genuine Player work.
        assert stripped == set()
        # The report is byte-identical to the input.
        assert json.dumps(report, sort_keys=True) == snapshot
        # No spurious log line.
        assert not [
            r for r in caplog.records
            if "orchestrator-induced ghost path" in r.message
        ]


# ---------------------------------------------------------------------------
# AC-3 / AC-5 — Empty / missing fields are no-ops
# ---------------------------------------------------------------------------


class TestStripOrchestratorManagedPathsEmptyReport:
    """An empty / sparse report does not raise and does not log."""

    def test_empty_report_is_noop(self, caplog):
        report: Dict[str, Any] = {}
        with caplog.at_level(
            logging.INFO, logger="guardkit.orchestrator.agent_invoker"
        ):
            stripped = _strip_orchestrator_managed_paths(report, PCN_TASK_ID)
        assert stripped == set()
        assert report == {}
        assert not [
            r for r in caplog.records
            if "orchestrator-induced ghost path" in r.message
        ]

    def test_lists_with_no_orchestrator_paths_are_unmodified(self):
        """When every list contains only Player work, the lists must be
        returned untouched (not even re-sorted)."""
        report: Dict[str, Any] = {
            "files_modified": [
                "src/b.py",  # intentionally unsorted to confirm no resort
                "src/a.py",
            ],
            "files_created": ["tests/test_a.py"],
            "tests_written": [],
            "completion_promises": [],
        }
        stripped = _strip_orchestrator_managed_paths(report, PCN_TASK_ID)
        assert stripped == set()
        # Order preserved when nothing was stripped — confirms the filter
        # only touches the list when it actually removes something.
        assert report["files_modified"] == ["src/b.py", "src/a.py"]
        assert report["files_created"] == ["tests/test_a.py"]
        assert report["tests_written"] == []
        assert report["completion_promises"] == []
