"""Measurement provenance survives the real Coach evidence/prompt path.

These tests stop at the model boundary. They exercise the real evidence
producer, bundle serializer and served synthesis prompt; they do not claim a
model will follow the resulting attribution instructions.
"""

from __future__ import annotations

import asyncio
import json
import stat
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    IndependentTestResult,
)
from guardkit.orchestrator.toolchain_declaration import parse_toolchain_block


TASK_ID = "TASK-ATTRIBUTION"
CRITERION = "AC-001: Preserve the reported compatibility evidence"


def _init_worktree(path: Path) -> None:
    subprocess.run(
        ["git", "init", "-q"], cwd=path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "tests@example.invalid"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "GuardKit Tests"],
        cwd=path,
        check=True,
        capture_output=True,
    )


def _reported_results(*, task_type: str = "testing") -> dict:
    return {
        "task_id": TASK_ID,
        "task_type": task_type,
        "quality_gates": {
            "all_passed": True,
            "tests_passed": 125,
            "tests_failed": 0,
            "tests_run": None,
            "coverage": 96.5,
            "coverage_met": None,
        },
        "code_review": {"score": 80},
        "plan_audit": {"status": "passed", "violations": 0},
        "files_modified": [],
        "files_created": [],
        "tests_written": [],
        "completion_promises": [
            {
                "criterion_id": "AC-001",
                "criterion_text": CRITERION,
                "status": "complete",
                "evidence": "Player reports 125 passing tests and 96.5% coverage.",
            }
        ],
    }


def _write_results(worktree: Path, results: dict) -> None:
    target = worktree / ".guardkit" / "autobuild" / TASK_ID
    target.mkdir(parents=True)
    (target / "task_work_results.json").write_text(
        json.dumps(results), encoding="utf-8"
    )


def _root_only_receipt() -> IndependentTestResult:
    return IndependentTestResult(
        tests_passed=True,
        test_command=(
            "bash reference/check.sh reference/fence.txt && bash scripts/check.sh"
        ),
        test_output_summary="reference check passed; root check has no parts yet",
        raw_output="reference check passed\nroot check: no parts yet\n",
        duration_seconds=0.1,
        signal_absent=False,
        tests_skipped=0,
        exit_code=0,
    )


def _task(task_type: str) -> dict:
    return {
        "task_id": TASK_ID,
        "task_type": task_type,
        "description": "Generic cross-language attribution fixture",
        "acceptance_criteria": [CRITERION],
    }


def _gather(worktree: Path, *, task_type: str = "testing", toolchain=None):
    validator = CoachValidator(
        str(worktree), task_id=TASK_ID, toolchain=toolchain
    )
    with patch.object(
        validator, "run_independent_tests", return_value=_root_only_receipt()
    ):
        return validator.gather_evidence(
            task_id=TASK_ID,
            turn=1,
            task=_task(task_type),
        )


def _served_synthesis_prompt(
    worktree: Path,
    bundle,
    player_report: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> str:
    monkeypatch.setenv("GUARDKIT_COACH_SYNTHESIS", "1")
    monkeypatch.setenv("GUARDKIT_COACH_GATHER", "0")
    monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "coachsplit")
    invoker = AgentInvoker(worktree_path=worktree)
    call = AsyncMock(side_effect=RuntimeError("stop after prompt capture"))
    with patch.object(invoker, "_invoke_with_role", call):
        result = asyncio.run(
            invoker.invoke_coach(
                task_id=TASK_ID,
                turn=1,
                requirements=CRITERION,
                player_report=player_report,
                evidence_bundle=bundle,
                acceptance_criteria=[{"id": "AC-001", "text": CRITERION}],
            )
        )
    assert result.success is False
    call.assert_awaited_once()
    kwargs = call.await_args.kwargs
    assert kwargs["synthesis"] is True
    assert kwargs["allowed_tools"] == []
    return kwargs["prompt"]


@pytest.mark.parametrize("consumer", ["ordinary", "direct"])
def test_mixed_measurements_keep_their_sources_in_served_synthesis_prompt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    consumer: str,
) -> None:
    _init_worktree(tmp_path)
    player_report = _reported_results()
    _write_results(tmp_path, player_report)

    bundle = _gather(tmp_path)
    serialized = bundle.to_dict()
    assert bundle.gathering_status == "complete"
    assert serialized["tests"]["tests_run"] is None
    assert serialized["coverage_details"]["line_coverage"] == 96.5
    assert serialized["coverage_details"]["provenance"] == (
        "player_task_work_results"
    )
    assert serialized["quality_gates"]["coverage_required"] is False
    assert serialized["quality_gates"]["coverage_met"] is True
    assert serialized["quality_gates"]["coverage_receipt"] is None
    assert serialized["independent_tests"]["test_command"].startswith(
        "bash reference/check.sh"
    )
    assert "125" not in serialized["independent_tests"]["test_output_summary"]
    assert "96.5" not in serialized["independent_tests"]["test_output_summary"]

    player_report["implementation_mode"] = consumer
    prompt = _served_synthesis_prompt(
        tmp_path, bundle, player_report, monkeypatch
    )
    flat_prompt = " ".join(prompt.split())

    assert '"tests_passed": 125' in prompt
    assert '"line_coverage": 96.5' in prompt
    assert '"provenance": "player_task_work_results"' in prompt
    assert "root check has no parts yet" in prompt
    assert "Player-reported test counts and coverage remain Player-reported" in prompt
    assert "independent_tests proves only its recorded command" in prompt
    assert "A non-required or relaxed gate is not a measurement" in flat_prompt
    assert "exit-zero generic check does not certify" in flat_prompt
    assert "has ALREADY run the tests, coverage" not in prompt
    assert "the orchestrator ran them, not the Player" not in prompt


def test_real_coverage_receipt_only_supports_measurements_in_its_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _init_worktree(tmp_path)
    results = _reported_results(task_type="feature")
    _write_results(tmp_path, results)
    config = tmp_path / ".guardkit" / "config.yaml"
    config.parent.mkdir(exist_ok=True)
    config.write_text(
        "toolchain:\n  coverage: ./measure-coverage.sh\n",
        encoding="utf-8",
    )
    coverage_script = tmp_path / "measure-coverage.sh"
    coverage_script.write_text(
        "#!/bin/sh\necho 'independently measured line coverage: 88.0%'\n",
        encoding="utf-8",
    )
    coverage_script.chmod(coverage_script.stat().st_mode | stat.S_IEXEC)

    toolchain = parse_toolchain_block(
        {"coverage": "./measure-coverage.sh"}
    )
    bundle = _gather(
        tmp_path, task_type="feature", toolchain=toolchain
    )
    serialized = bundle.to_dict()
    details = serialized["coverage_details"]
    receipt = details["coverage_receipt"]
    assert bundle.gathering_status == "complete"
    assert serialized["quality_gates"]["coverage_required"] is True
    assert serialized["quality_gates"]["coverage_met"] is True
    assert details["line_coverage"] == 96.5
    assert receipt["command"] == "./measure-coverage.sh"
    assert receipt["exit_code"] == 0
    assert "independently measured line coverage: 88.0%" in receipt["output_tail"]
    assert "96.5" not in receipt["output_tail"]

    prompt = _served_synthesis_prompt(
        tmp_path, bundle, results, monkeypatch
    )
    flat_prompt = " ".join(prompt.split())
    assert "independently measured line coverage: 88.0%" in prompt
    assert '"line_coverage": 96.5' in prompt
    assert "only the command, output, and measurements it records" in flat_prompt
    assert (
        "tests and coverage_details may contain Player-reported facts"
        in flat_prompt
    )
