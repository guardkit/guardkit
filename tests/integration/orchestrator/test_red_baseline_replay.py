"""End-to-end replay of the FEAT-VOICE-003 red-baseline incident (L12 GATE).

Retro: guardkit/docs/retros/2026-07-08-autobuild-red-baseline-burned-two-runs.md.
A stale pre-existing baseline test (``happy_path`` asserting the old default
subject) made TASK-VC-005 un-passable across two runs, while the Coach's
``claim_audit_gitignored`` negation false-positive flooded every turn.

This test reproduces the incident's SHAPE over a real red-baseline repo and
asserts the fixes converge it:

1. Item 1 — the wave-0 baseline probe records the red baseline and warns
   ("N pre-existing failures — not attributable to any task").
2. Item 2 — an UNRELATED task whose independent test run surfaces ONLY the
   pre-existing failure is APPROVED (baseline diff): the deterministic gate
   defers and ``_apply_baseline_diff`` flips the ran-and-failed verdict.
3. Item 6 — the ``claim_audit_gitignored`` negation false-positive stays
   silent on the tracked, ``!app/lib/**``-re-included file.

It exercises the deterministic orchestrator/Coach seams directly (no SDK
loop), which is where the incident actually played out.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from guardkit.orchestrator.baseline import read_baseline_from_worktree
from guardkit.orchestrator.coach_verification import CoachVerifier
from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureExecution,
    FeatureOrchestration,
    FeatureTask,
    SmokeGates,
)
from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    IndependentTestResult,
)
from guardkit.worktrees import Worktree


def _git(*args, cwd):
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True)


@pytest.fixture
def red_baseline_worktree(tmp_path) -> Path:
    """A real git repo whose suite is ALREADY red on the base commit, with the
    retro's exact ``lib/`` + ``!app/lib/**`` re-include gitignore."""
    wt = tmp_path / "wt"
    wt.mkdir()
    _git("init", "--initial-branch=main", cwd=wt)
    _git("config", "user.email", "t@e.com", cwd=wt)
    _git("config", "user.name", "T", cwd=wt)

    # The retro's gitignore: lib/ ignored, app/lib re-included.
    (wt / ".gitignore").write_text("lib/\n!app/lib/\n!app/lib/**\n")

    # The re-included, tracked production file (the negation false-positive victim).
    src = wt / "app" / "lib" / "ui"
    src.mkdir(parents=True)
    (src / "session_screen.dart").write_text("class SessionScreen {}\n")

    # The STALE baseline test — red on the base commit, unrelated to any task.
    tests = wt / "app" / "test" / "slice"
    tests.mkdir(parents=True)
    (tests / "happy_path_test.py").write_text(
        "def test_home_lists_under_default_subject():\n"
        "    # stale: asserts the OLD default subject (retro ASSUM-001)\n"
        "    assert 'english' == 'maths'\n"
    )
    _git("add", "-A", cwd=wt)
    _git("commit", "-m", "base (already red)", cwd=wt)
    return wt


def _feature(command="python -m pytest -q app/test/slice/happy_path_test.py"):
    return Feature(
        id="FEAT-VOICE-003", name="voice", description="d",
        created="2026-07-09T00:00:00Z", status="in_progress",
        complexity=6, estimated_tasks=1,
        tasks=[FeatureTask(
            id="TASK-VC-005", name="unrelated ui task",
            file_path=Path("tasks/backlog/TASK-VC-005.md"),
            complexity=6, dependencies=[], status="pending",
            implementation_mode="task-work", estimated_minutes=113,
        )],
        orchestration=FeatureOrchestration(
            parallel_groups=[["TASK-VC-005"]],
            estimated_duration_minutes=113, recommended_parallel=1,
        ),
        execution=FeatureExecution(),
        smoke_gates=SmokeGates(after_wave="all", command=command, expected_exit=0),
    )


def test_incident_replays_green(red_baseline_worktree, caplog):
    wt = red_baseline_worktree
    orch = FeatureOrchestrator(
        repo_root=wt.parent, worktree_manager=MagicMock(),
        task_timeout=3000, timeout_multiplier=1.0, max_turns=5,
    )
    worktree = Worktree(
        task_id="FEAT-VOICE-003", branch_name="autobuild/FEAT-VOICE-003",
        path=wt, base_branch="main",
    )

    # --- Item 1: wave-0 baseline probe surfaces the pre-existing red. -------
    with caplog.at_level(logging.WARNING):
        orch._run_baseline_probe(_feature(), worktree)

    baseline = orch._measured_baseline
    assert baseline is not None and baseline.passed is False
    failing_node = "app/test/slice/happy_path_test.py::test_home_lists_under_default_subject"
    assert failing_node in baseline.failing_node_ids
    assert read_baseline_from_worktree(wt) is not None
    assert any(
        "not attributable to any task" in r.getMessage() for r in caplog.records
    )

    # --- Item 2: the UNRELATED task's Coach approves despite the red. -------
    cv = CoachValidator(str(wt))
    # (a) deterministic count gate defers to the independent run.
    gates = cv.verify_quality_gates(
        {"quality_gates": {"tests_failed": 1, "all_passed": False}}
    )
    assert gates.tests_passed is True

    # (b) the independent run surfaces ONLY the pre-existing failure → flipped.
    failed = IndependentTestResult.from_run(
        tests_passed=False, test_command="pytest -q",
        test_output_summary="1 failed",
        duration_seconds=0.1,
        output=f"FAILED {failing_node} - stale assertion\n",
        resolved_interpreter=None,
    )
    # The unrelated task touched session_screen.dart, NOT the stale slice test.
    approved = cv._apply_baseline_diff(
        failed, {"files_modified": ["app/lib/ui/session_screen.dart"]}
    )
    assert approved.tests_passed is True
    assert "attributed to the measured baseline" in approved.test_output_summary

    # (b') a genuine regression is still charged (guardrail).
    regressed = IndependentTestResult.from_run(
        tests_passed=False, test_command="pytest -q",
        test_output_summary="2 failed", duration_seconds=0.1,
        output=(
            f"FAILED {failing_node} - stale assertion\n"
            "FAILED app/test/new_test.py::test_real_regression - boom\n"
        ),
        resolved_interpreter=None,
    )
    still_failed = cv._apply_baseline_diff(regressed, {"files_modified": []})
    assert still_failed.tests_passed is False

    # --- Item 6: the negation claim-audit stays SILENT on the tracked file. -
    verifier = CoachVerifier(wt)
    assert (
        verifier._classify_dropped_path("app/lib/ui/session_screen.dart")
        == "tracked_unmodified"
    )
    discrepancies = verifier._verify_claims_were_staged(
        {"files_modified": ["app/lib/ui/session_screen.dart"]}
    )
    assert not any(
        d.claim_type == "claim_audit_gitignored" for d in discrepancies
    )
