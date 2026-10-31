"""A CHECK THAT COULD NOT RUN IS AN ESTATE FAULT.

"The check ran and the result is bad" and "the check could not run" are
different outcomes. A check that could not run is never a pass, never sends a
turn back, and the operator's log says so in plain words (since 31 October
2026 it stops the task instead; see test_changed_parts_check.py). The isolated
copy these tests also pinned was removed on 31 October 2026: every task now
runs alone, so the copy was never made.

No pytest, no interpreter, no package manager anywhere in the fixtures.
"""

from __future__ import annotations

import asyncio
import json
import stat
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.harness import (
    AssistantMessageEvent,
    ResultMessageEvent,
)
from guardkit.orchestrator.quality_gates.coach_evidence import (
    CoachEvidenceBundle,
)
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    IndependentTestResult,
)
from guardkit.orchestrator.toolchain_declaration import snapshot_task_toolchain

_TASK_ID = "TASK-ISO-001"
_DECLARED_COMMAND = "qa/run-suite.sh"


# ---------------------------------------------------------------------------
# A repository that declares a shell test command needing a sibling file
# ---------------------------------------------------------------------------


def _executable(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)


def _make_repo(tmp_path: Path) -> tuple[Path, Path]:
    """Repo root plus the worktree beneath it, with the command declared."""
    root = tmp_path / "product"
    worktree = root / ".guardkit" / "worktrees" / _TASK_ID
    worktree.mkdir(parents=True)
    (root / ".guardkit").mkdir(parents=True, exist_ok=True)
    (root / ".guardkit" / "config.yaml").write_text(
        yaml.safe_dump({"toolchain": {"test": _DECLARED_COMMAND}}),
        encoding="utf-8",
    )
    snapshot_task_toolchain(_TASK_ID, worktree, root)
    return root, worktree


def _suite_needing(relative_tool: str) -> str:
    """A test command that needs a sibling file to exist where it runs."""
    return (
        "#!/bin/sh\n"
        'here=$(cd "$(dirname "$0")/.." && pwd)\n'
        f'tool="$here/{relative_tool}"\n'
        'if [ ! -x "$tool" ]; then\n'
        '  echo "run-suite: no runner at $tool" >&2\n'
        "  exit 127\n"
        "fi\n"
        'exec "$tool"\n'
    )


_RUNNER = "#!/bin/sh\necho '3 checks passed'\n"


def _validator(worktree: Path, wave_size: int) -> CoachValidator:
    validator = CoachValidator(
        str(worktree), task_id=_TASK_ID, wave_size=wave_size
    )
    return validator


# ---------------------------------------------------------------------------
# 1. THE MECHANISM — the copy reaches what the declared command needs
# ---------------------------------------------------------------------------


def _task_work_results(all_passed: bool = True) -> Dict[str, Any]:
    return {
        "quality_gates": {
            "tests_run": 12,
            "tests_failed": 0,
            "coverage_met": True,
            "all_passed": all_passed,
        },
        "code_review": {"score": 90},
        "plan_audit": {"violations": 0, "status": "passed"},
        "requirements_met": ["The endpoint answers"],
    }


def _write_task_work_results(worktree: Path) -> None:
    results_dir = worktree / ".guardkit" / "autobuild" / _TASK_ID
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "task_work_results.json").write_text(
        json.dumps(_task_work_results()), encoding="utf-8"
    )


def _could_not_run() -> IndependentTestResult:
    return IndependentTestResult.could_not_run(
        test_command=_DECLARED_COMMAND,
        detail=(
            f"The check could not run. Command: {_DECLARED_COMMAND}. "
            "Directory: an isolated copy of the worktree. What was missing: "
            "the runner the command needs."
        ),
        duration_seconds=0.1,
    )


def _task() -> Dict[str, Any]:
    return {
        "task_type": "feature",
        "acceptance_criteria": ["The endpoint answers"],
    }


class TestTheRule:
    def test_the_evidence_the_coach_reads_carries_the_same_two_facts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """The evidence bundle carries the run that could not happen, never
        as a pass, and the operator's log says so in plain words."""
        _root, worktree = _make_repo(tmp_path)
        _write_task_work_results(worktree)
        validator = _validator(worktree, wave_size=2)
        monkeypatch.setattr(
            validator, "run_independent_tests", lambda **kwargs: _could_not_run()
        )
        # The task changed a file in the root part, so the root's run counts.
        monkeypatch.setattr(
            validator, "_changed_files", lambda _results: (["app.py"], "a test")
        )

        with caplog.at_level("WARNING"):
            bundle = validator.gather_evidence(_TASK_ID, 1, _task())

        assert bundle.gathering_status == "complete"
        assert bundle.independent_tests is not None
        assert bundle.independent_tests.tests_passed is False
        assert bundle.independent_tests.check_could_not_run is True
        # An absent signal is never classified as a code failure.
        assert bundle.independent_test_classification is None
        serialised = bundle.to_dict()["independent_tests"]
        assert serialised["check_could_not_run"] is True
        assert _DECLARED_COMMAND in serialised["check_could_not_run_detail"]
        messages = [record.getMessage() for record in caplog.records]
        assert any("could not be run" in message for message in messages)

    def test_a_check_that_ran_and_failed_is_still_the_builders_to_fix(
        self, tmp_path: Path
    ) -> None:
        """The other half of the rule: a real red is untouched by any of this."""
        _root, worktree = _make_repo(tmp_path)
        _executable(
            worktree / "qa" / "run-suite.sh",
            "#!/bin/sh\necho '1 of 3 checks failed' >&2\nexit 1\n",
        )

        result = _validator(worktree, wave_size=2).run_independent_tests()

        assert result.tests_passed is False
        assert result.signal_absent is False
        assert result.check_could_not_run is False


# ---------------------------------------------------------------------------
# 5. A COMMAND THAT IS NOT PYTEST KEEPS ITS OWN MEANING
# ---------------------------------------------------------------------------
# Rich's binding constraint for this work: nothing here may assume Python.
# Exit code 5 means "collected no tests" to pytest and nothing whatever to
# anybody else — to a shell wrapper or to ``go test`` it is an ordinary
# non-zero exit, which usually means the checks FAILED. Reading it as "the
# check could not run" would hide a genuine red behind an estate fault and
# tell the operator something untrue about a command that has no opinion
# about Python.


_ESTATE_DETAIL = (
    f"The check could not run. Command: {_DECLARED_COMMAND}. Directory: the "
    "worktree. What was missing: no runner at dist/toolbox/runner."
)


def _invoker(worktree: Path) -> AgentInvoker:
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    invoker.sdk_timeout_seconds = 600
    invoker._calculate_sdk_timeout = MagicMock(return_value=600)
    invoker._venv_python = None
    return invoker


def _bundle_whose_check_could_not_run() -> CoachEvidenceBundle:
    return CoachEvidenceBundle(
        gathering_status="complete",
        independent_tests=IndependentTestResult.could_not_run(
            test_command=_DECLARED_COMMAND,
            detail=_ESTATE_DETAIL,
            duration_seconds=0.1,
        ),
    )


def _the_reviewer_answers(task_id: str, turn: int, verdict: Dict[str, Any]) -> list:
    text = "```json\n" + json.dumps(verdict) + "\n```"
    return [AssistantMessageEvent(text=text), ResultMessageEvent(session_id=None)]


def _ask_the_coach(
    invoker: AgentInvoker, *, task_id: str, turn: int, verdict: Dict[str, Any],
    bundle: CoachEvidenceBundle,
):
    events = AsyncMock(
        return_value=(None, _the_reviewer_answers(task_id, turn, verdict))
    )
    with patch.object(invoker, "_invoke_with_role", events):
        return asyncio.run(
            invoker.invoke_coach(
                task_id=task_id,
                turn=turn,
                requirements="The endpoint answers",
                player_report={"files_modified": ["src/x.py"], "tests_passed": True},
                evidence_bundle=bundle,
            )
        )


def _the_reviewer_blames_the_builder(task_id: str, turn: int) -> Dict[str, Any]:
    """Exactly what happened on 2026-09-11: the model was told to quote the
    oracle's output, so it handed the estate fault to the builder."""
    return {
        "task_id": task_id,
        "turn": turn,
        "decision": "feedback",
        "rationale": "Independent test verification did not complete.",
        "criteria_verification": [],
        "issues": [
            {
                "severity": "must_fix",
                "category": "absence_of_failure",
                "description": (
                    "Independent test verification did not complete (signal "
                    f"absent). Independent-test oracle output: {_ESTATE_DETAIL}"
                ),
            }
        ],
    }


def _bundle_whose_run_timed_out() -> CoachEvidenceBundle:
    return CoachEvidenceBundle(
        gathering_status="complete",
        independent_tests=IndependentTestResult.absent(
            test_command=_DECLARED_COMMAND,
            test_output_summary="timed out after 300s",
            duration_seconds=300.0,
        ),
    )


def _bundle_whose_check_exited_zero_with_no_count() -> CoachEvidenceBundle:
    return CoachEvidenceBundle(
        gathering_status="complete",
        independent_tests=IndependentTestResult.from_run(
            tests_passed=False,
            test_command=_DECLARED_COMMAND,
            test_output_summary="no parts yet; later tasks add checks",
            duration_seconds=0.1,
            output="no parts yet; later tasks add checks\n",
            resolved_interpreter=None,
            signal_absent=True,
            exit_code=0,
        ),
    )


class TestTheRuleOnTheLivePath:
    @pytest.mark.parametrize(
        "bundle_for",
        [
            _bundle_whose_check_could_not_run,
            _bundle_whose_run_timed_out,
                _bundle_whose_check_exited_zero_with_no_count,
        ],
    )
    def test_a_check_that_did_not_run_and_fail_never_sends_the_turn_back(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bundle_for,
    ) -> None:
        """The reviewer blames the builder; its verdict is kept as advice and
        the turn is approved, because no project check ran and failed."""
        invoker = _invoker(tmp_path)

        result = _ask_the_coach(
            invoker,
            task_id=_TASK_ID,
            turn=1,
            verdict=_the_reviewer_blames_the_builder(_TASK_ID, 1),
            bundle=bundle_for(),
        )

        assert result.success is True
        assert result.report["decision"] == "approve"
        # The reviewer's findings stay in the record.
        assert [i["category"] for i in result.report["issues"]] == [
            "absence_of_failure"
        ]
        assert result.report.get("is_configuration_error", False) is not True

    def test_a_check_that_ran_and_failed_sends_the_turn_back(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Negative control: the reviewer approves, the project's own suite
        ran and failed, and the turn goes back with the failing lines."""
        invoker = _invoker(tmp_path)
        approve = dict(
            _the_reviewer_blames_the_builder(_TASK_ID, 1),
            decision="approve",
            issues=[],
        )
        bundle = CoachEvidenceBundle(
            gathering_status="complete",
            task_type="feature",
            independent_tests=IndependentTestResult.from_run(
                tests_passed=False,
                test_command=_DECLARED_COMMAND,
                test_output_summary="1 of 3 checks failed",
                duration_seconds=0.2,
                output="1 of 3 checks failed\n",
                resolved_interpreter=None,
                exit_code=1,
            ),
        )

        result = _ask_the_coach(
            invoker, task_id=_TASK_ID, turn=1, verdict=approve, bundle=bundle,
        )

        assert result.report["decision"] == "feedback"
        assert result.report["issues"] != []


# ---------------------------------------------------------------------------
# 5. A CHECK THAT EXITED 0 COULD RUN (23 October 2026)
# ---------------------------------------------------------------------------
# A project's declared check passed (exit 0) but printed no test count the
# declared classifier recognises — a starter check script that runs no tests
# yet. That is an absent signal: never a pass, and never an estate fault. In
# a wave of two it used to end the whole feature as a configuration error,
# because the worktree close-out read "no test count recognised" as "the
# check could not run anywhere". The command started and finished, so it
# could run; only the test count is missing, exactly as a wave of one says.

_RAN_MARKER = r"(?m)^[1-9]\d* checks? passed"
