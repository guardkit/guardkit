"""COACH control for Lane D — written by the independent checker, not the builder.

Drives the real FeatureOrchestrator wave phase and finaliser against a
NON-PYTHON fixture project (a Makefile whose declared feature check is a
shell script using a counter file), with only ``_execute_wave`` stubbed.

Proves, end to end and without a model:
  1. a check that fails once and passes on the retry re-enters the LAST wave
     exactly once, with the script's own output tail and the request's words
     in the Player's feedback, and the feature then COMPLETES with a receipt
     listing two attempts of different outcomes, both on the real HEAD sha;
  2. with GUARDKIT_FEATURE_CHECK_MAX_RETRIES=0 and a check that always fails,
     the feature is FAILED, the wave is un-marked, and the orchestration
     result is not a success (the signal guardkit's CLI turns into exit 2);
  3. the declaration is read from the MAIN checkout: editing the worktree's
     own .guardkit/config.yaml has no effect at all.
"""

from __future__ import annotations

import json
import os
import subprocess
from contextlib import ExitStack
from pathlib import Path
from typing import List, Optional
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.feature_check import RECEIPT_RELATIVE_PATH
from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    TaskExecutionResult,
    WaveExecutionResult,
)
from guardkit.worktrees import Worktree


REQUEST = "Show me how many users were created per day"
TITLE = "Seeing the daily count of new users"
STDERR_MARKER = "COACH-CONTROL-404: /users/created-per-day answered 404"

COUNTING_SCRIPT = f"""#!/bin/sh
C="$GUARDKIT_WORKTREE/.coach-check-count"
N=0
if [ -f "$C" ]; then N=$(cat "$C"); fi
N=$((N+1))
echo "$N" > "$C"
echo "coach control run number $N on sha $GUARDKIT_CANDIDATE_SHA"
echo "feature=$GUARDKIT_FEATURE_ID record=$GUARDKIT_FEATURE_RECORD"
if [ "$N" -ge 2 ]; then
  echo '{{"guardkit_feature_check": {{"scenarios_covered": ["{TITLE}"]}}}}'
  exit 0
fi
echo "{STDERR_MARKER}" >&2
exit 1
"""

ALWAYS_FAILS = f"""#!/bin/sh
echo "{STDERR_MARKER}" >&2
exit 1
"""

MAKEFILE = "check:\n\tsh qa/feature-check.sh\n"

TASK_DOC = f"""# TASK-001

## The words of the request this task serves

{REQUEST}

## Acceptance criteria

- one row per day
"""


def _write(root: Path, rel: str, text: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=str(root), check=True, capture_output=True, text=True
    )
    return (proc.stdout or "").strip()


def _project(tmp_path: Path, script: str, main_command: str) -> tuple[Path, Path, str]:
    main = tmp_path / "main"
    wt = tmp_path / "worktree"
    for root in (main, wt):
        _write(root, "Makefile", MAKEFILE)
        _write(root, "qa/feature-check.sh", script)
    _write(
        main,
        ".guardkit/config.yaml",
        'toolchain:\n  test: "make test"\n  feature_check: "%s"\n' % main_command,
    )
    _write(wt, "tasks/TASK-001.md", TASK_DOC)
    _git(wt, "init", "-b", "main")
    _git(wt, "config", "user.email", "coach@example.com")
    _git(wt, "config", "user.name", "Coach")
    _git(wt, "add", "-A")
    _git(wt, "commit", "-m", "candidate")
    head = _git(wt, "rev-parse", "HEAD")
    return main, wt, head


def _feature(wt: Path):
    feature = MagicMock()
    feature.id = "FEAT-COACH"
    feature.name = "daily count"
    feature.description = REQUEST
    feature.status = "in_progress"
    feature.smoke_gates = None
    feature.estimated_minutes = None
    feature.file_path = str(wt / ".guardkit/features/FEAT-COACH.yaml")
    feature.scenarios = {}
    task = MagicMock()
    task.id = "TASK-001"
    task.dependencies = []
    task.status = "pending"
    task.file_path = str(wt / "tasks/TASK-001.md")
    feature.tasks = [task]
    feature.orchestration.parallel_groups = [["TASK-001"]]
    feature.execution.current_wave = 0
    feature.execution.completed_waves = []
    return feature


class _Waves:
    def __init__(self) -> None:
        self.feedback: List[Optional[str]] = []

    def __call__(
        self, wave_number, task_ids, feature, worktree, seed_feedback=None, attempt=0
    ):
        self.feedback.append(seed_feedback)
        return WaveExecutionResult(
            wave_number=wave_number,
            task_ids=list(task_ids),
            results=[
                TaskExecutionResult(
                    task_id=t, success=True, total_turns=1, final_decision="approved"
                )
                for t in task_ids
            ],
            all_succeeded=True,
        )


def _drive(main: Path, wt: Path, feature, waves: _Waves):
    orch = FeatureOrchestrator(
        repo_root=main, max_turns=1, worktree_manager=MagicMock(), quiet=True
    )
    worktree = Worktree(
        task_id=feature.id,
        branch_name=f"autobuild/{feature.id}",
        path=wt,
        base_branch="main",
    )
    with ExitStack() as stack:
        for cm in (
            patch.object(orch, "_preflight_check"),
            patch.object(orch, "_bootstrap_environment"),
            patch.object(
                orch,
                "_run_post_wave_wiring_gate",
                autospec=True,
                side_effect=lambda wn, ti, f, w, wr: MagicMock(
                    final_wave_result=wr, terminate=False
                ),
            ),
            patch(
                "guardkit.orchestrator.feature_orchestrator.FeatureLoader.find_task",
                side_effect=lambda f, tid: f,
            ),
            patch(
                "guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature"
            ),
            patch.object(orch, "_run_final_wave_boot_smoke", return_value=None),
            patch.object(orch, "_execute_wave", side_effect=waves),
            patch.object(orch, "_display_summary"),
        ):
            stack.enter_context(cm)
        wave_results = orch._wave_phase(feature, worktree)
        result = orch._finalize_phase(feature, wave_results, worktree)
    return orch, wave_results, result


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GUARDKIT_FEATURE_CHECK_MAX_RETRIES", raising=False)
    monkeypatch.delenv("GUARDKIT_QA_ENFORCE_TWIN_COVERAGE", raising=False)


def _receipt(wt: Path) -> dict:
    return json.loads((wt / RECEIPT_RELATIVE_PATH).read_text(encoding="utf-8"))


# =====================================================================
# Control 1 — fail once, repair, pass: one re-entry and a completed feature
# =====================================================================


def test_one_reentry_repairs_the_feature_and_it_completes(tmp_path: Path):
    main, wt, head = _project(tmp_path, COUNTING_SCRIPT, "sh qa/feature-check.sh")
    feature = _feature(wt)
    waves = _Waves()

    _orch, _wave_results, result = _drive(main, wt, feature, waves)

    # exactly one re-entry of the LAST wave
    assert len(waves.feedback) == 2, waves.feedback
    assert waves.feedback[0] is None
    feedback = waves.feedback[1]
    assert feedback is not None
    # the script's own output tail
    assert STDERR_MARKER in feedback
    # the request's words
    assert REQUEST in feedback
    # and the words of the request, named as such
    assert "exit=1, expected=0" in feedback

    # the second run passed and the feature completed
    assert feature.status == "completed"
    assert result.success is True

    receipt = _receipt(wt)
    assert receipt["status"] == "passed"
    assert [a["attempt"] for a in receipt["attempts"]] == [1, 2]
    assert [a["passed"] for a in receipt["attempts"]] == [False, True]
    assert [a["exit_code"] for a in receipt["attempts"]] == [1, 0]
    assert {a["candidate_sha"] for a in receipt["attempts"]} == {head}
    assert receipt["scenarios_covered"] == [TITLE]
    # the script really ran twice
    assert (wt / ".coach-check-count").read_text().strip() == "2"


# =====================================================================
# Control 2 — budget 0 and a check that never passes: failed, wave un-marked
# =====================================================================


def test_zero_retry_budget_fails_the_feature_and_unmarks_the_wave(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("GUARDKIT_FEATURE_CHECK_MAX_RETRIES", "0")
    main, wt, head = _project(tmp_path, ALWAYS_FAILS, "sh qa/feature-check.sh")
    feature = _feature(wt)
    waves = _Waves()

    _orch, wave_results, result = _drive(main, wt, feature, waves)

    # no re-entry at all
    assert waves.feedback == [None]

    receipt = _receipt(wt)
    assert receipt["status"] == "failed"
    assert len(receipt["attempts"]) == 1
    assert receipt["attempts"][0]["candidate_sha"] == head

    # the failure rides the start-up checks' rail
    gate = wave_results[-1].smoke_gate_result
    assert gate is not None and gate.passed is False
    assert str(gate.command).startswith("whole-feature check (")

    # the wave is un-marked so a resume re-runs it
    assert wave_results[-1].wave_number not in (
        feature.execution.completed_waves or []
    )

    # the finaliser's answer: this is a failed feature, and that is the signal
    # guardkit's CLI turns into a non-zero exit (autobuild.py: exit 0 if
    # result.success else 2), which is what forge's runner reads.
    assert feature.status == "failed"
    assert result.success is False
    assert STDERR_MARKER in (result.error or "") or "whole-feature check" in (
        result.error or ""
    )


# =====================================================================
# Control 3 — the declaration is the MAIN checkout's, never the build's copy
# =====================================================================


def test_the_build_cannot_rewrite_its_own_check(tmp_path: Path):
    main, wt, _head = _project(tmp_path, ALWAYS_FAILS, "sh qa/feature-check.sh")
    # The build edits its OWN copy of the declaration to a check that passes,
    # and replaces its own copy of the script with one that exits 0.
    _write(
        wt,
        ".guardkit/config.yaml",
        'toolchain:\n  test: "make test"\n  feature_check: "true"\n',
    )
    feature = _feature(wt)
    waves = _Waves()

    _orch, wave_results, result = _drive(main, wt, feature, waves)

    receipt = _receipt(wt)
    # the MAIN checkout's failing command is the one that ran
    assert receipt["command"] == "sh qa/feature-check.sh"
    assert receipt["status"] == "failed"
    assert feature.status == "failed"
    assert result.success is False
