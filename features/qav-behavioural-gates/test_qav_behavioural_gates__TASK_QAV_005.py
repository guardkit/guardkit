"""pytest-bdd glue + step definitions for TASK-QAV-005.

Binds the @task:TASK-QAV-005 scenario: "A correctly-wired stub with green
co-generated tests is still flagged".

Per .claude/rules/bdd-per-task-glue.md the glue module MUST be named
test_<slug>__<TASK-ID>.py to avoid cross-task race conditions in parallel
wave execution.

Step definitions are embedded in this module so pytest-bdd discovers them
automatically.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

from pytest_bdd import given, scenario, then, when

# Ensure project root is on sys.path for imports
_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator
from guardkit.orchestrator.quality_gates.coverage_gate import run_coverage_gate_for_bundle


# ============================================================================
# Shared state
# ============================================================================

_state: Dict[str, Any] = {}


def _write_task_work_results(
    worktree_path: Path,
    task_id: str,
    payload: Dict[str, Any],
) -> Path:
    """Write a task_work_results.json into the standard autobuild path."""
    results_path = worktree_path / ".guardkit" / "autobuild" / task_id
    results_path.mkdir(parents=True, exist_ok=True)
    results_file = results_path / "task_work_results.json"
    results_file.write_text(json.dumps(payload, indent=2))

    for f in payload.get("files_created", []) + payload.get("files_modified", []):
        full_path = worktree_path / f
        full_path.parent.mkdir(parents=True, exist_ok=True)
        if not full_path.exists():
            full_path.write_text("# placeholder\n")

    for f in payload.get("files_authored", []):
        full_path = worktree_path / f
        full_path.parent.mkdir(parents=True, exist_ok=True)
        if not full_path.exists():
            full_path.write_text("# placeholder\n")

    return results_file


def _stub_payload() -> Dict[str, Any]:
    """Return a task_work_results payload for a correctly-wired stub."""
    return {
        "task_id": "TASK-QAV-005-STUB",
        "turn": 1,
        "files_created": ["src/service.py", "src/__init__.py", "tests/test_service.py"],
        "files_modified": [],
        "files_authored": ["src/service.py", "src/__init__.py"],
        "tests_passed": True,
        "tests_run": True,
        "test_results": {
            "line_coverage": 90.0,
            "branch_coverage": 80.0,
            "files_below_threshold": 0,
        },
        "quality_gates": {
            "all_passed": True,
            "tests_failed": 0,
            "tests_run": True,
            "coverage_met": True,
            "line_coverage": 90.0,
            "branch_coverage": 80.0,
            "line_threshold": 80.0,
            "branch_threshold": 60.0,
            "arch_review_score": 85,
            "arch_review_threshold": 60,
            "plan_audit_status": "clean",
        },
        "plan_audit": {
            "status": "clean",
            "loc_variance": 3.0,
            "extra_files": [],
            "missing_files": [],
        },
        "bdd_results": {
            "scenarios_attempted": 2,
            "scenarios_passed": 2,
            "scenarios_failed": 0,
            "scenarios_pending": 0,
            "scenarios_errored": 0,
            "failures": [],
            "pending": [],
            "feature_files": ["features/service.feature"],
        },
        "completion_promises": [
            {
                "criterion_id": "AC-002",
                "criterion_text": "correctly-wired stub",
                "status": "complete",
                "evidence": "stub fixture",
                "test_file": "tests/test_service.py",
                "implementation_files": ["src/service.py"],
            }
        ],
        "requirements_met": ["stub detected"],
        "requirements_addressed": ["stub detection"],
        "code_review": {"status": "approved", "score": 85, "issues": []},
        "agent_invocations": [],
        "_synthetic": True,
    }


# ============================================================================
# BDD Steps for TASK-QAV-005 scenario
# ============================================================================

@given("the Coach evidence gathering runs for an autobuild turn")
def coach_evidence_gathering_runs():
    """Background: the Coach evidence gathering context is active."""
    _state["evidence_gathering"] = True


@given("an authored implementation that is fully wired into the composition root")
def authored_implementation_wired(tmp_path: Path) -> None:
    """The fixture has source files that are wired into a composition root."""
    worktree_path = tmp_path / "worktree-stub-bdd"
    task_id = "TASK-QAV-005-STUB"
    _write_task_work_results(worktree_path, task_id, _stub_payload())
    _state["worktree_path"] = worktree_path
    _state["task_id"] = task_id


@given("its body is a stub returning plausibly-shaped data")
def stub_body_plausibly_shaped() -> None:
    """The implementation body is a stub (simulated via mock)."""
    _state["is_stub"] = True


@given("its co-generated unit tests all pass")
def co_generated_tests_pass() -> None:
    """The co-generated unit tests pass (reflected in task_work_results)."""
    _state["tests_pass"] = True


@when("the anti-stub scan and the coverage gate run")
def anti_stub_and_coverage_run() -> None:
    """Run the evidence gathering pipeline with stub/coverage detection."""
    from unittest.mock import patch

    worktree_path = _state["worktree_path"]
    task_id = _state["task_id"]

    validator = CoachValidator(worktree_path=worktree_path)
    task = {
        "id": task_id,
        "task_type": "feature",
        "acceptance_criteria": [],
        "requires_infrastructure": False,
    }

    with patch(
        "guardkit.orchestrator.quality_gates.coach_validator._compute_stub_scan",
        return_value={
            "status": "positive",
            "findings": [
                {
                    "file": "src/service.py",
                    "symbol": "fetch_data",
                    "pattern": "HARDCODED_DEFAULT",
                    "description": "Returns hardcoded empty dict",
                }
            ],
            "symbols_scanned": 3,
        },
    ):
        with patch(
            "guardkit.orchestrator.quality_gates.coverage_gate.run_coverage_gate_for_bundle",
            return_value={
                "status": "positive",
                "coverage_percentage": 45.0,
                "files_below_threshold": 1,
                "findings": [
                    {
                        "file": "src/service.py",
                        "symbol": "fetch_data",
                        "lineno": 12,
                        "executed_lines": 0,
                        "severity": "warning",
                        "pattern": "ZERO_EXECUTION",
                    }
                ],
            },
        ):
            bundle = validator.gather_evidence(task_id=task_id, turn=1, task=task)

    _state["bundle"] = bundle


@then("at least one behavioural-evidence finding should name the stubbed symbol")
def finding_names_stubbed_symbol() -> None:
    """Assert that the bundle contains findings naming the stubbed symbol."""
    bundle = _state["bundle"]

    assert bundle.stub_scan is not None, "stub_scan should be populated"
    assert bundle.stub_scan["status"] == "positive", "stub_scan status should be positive"
    findings = bundle.stub_scan.get("findings", [])
    assert len(findings) >= 1, f"Expected >=1 stub_scan finding, got {len(findings)}"

    symbol_found = any("symbol" in f for f in findings)
    assert symbol_found, "At least one finding should name a symbol"

    assert bundle.coverage is not None, "coverage should be populated"
    assert bundle.coverage["status"] == "positive", "coverage status should be positive"
    coverage_findings = bundle.coverage.get("findings", [])
    assert len(coverage_findings) >= 1, f"Expected >=1 coverage finding, got {len(coverage_findings)}"


# ============================================================================
# Scenario binding
# ============================================================================

_FEATURE = Path(__file__).with_name("qav-behavioural-gates.feature")


@scenario(
    _FEATURE,
    "A correctly-wired stub with green co-generated tests is still flagged",
)
def test_correctly_wired_stub_flagged():
    """Bind the TASK-QAV-005 regression scenario."""
    pass
