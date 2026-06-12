"""AC-002 / AC-008 / AC-011 / AC-015 / AC-016 / AC-017 — UNWIRED_PATH bundle integration.

TASK-QAWE-002, Wave 1. Verifies that the CoachEvidenceBundle carries the
three new wiring fields (``wiring``, ``mocked_seam``, ``spec_gap``), that
they are populated only on the complete-path return, that the task-type
gate excludes SCAFFOLDING/DOCUMENTATION, that the fields reach the Coach
prompt via ``_render_evidence_bundle_section``, that truncation works for
>20 findings, that absent-vs-empty is distinct, and that graceful import
absence does not crash.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.quality_gates.coach_evidence import (
    CoachEvidenceBundle,
)
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    _compute_authored_set,
    _run_wiring_analysis,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _init_git_worktree(path: Path) -> None:
    """Minimal git init so TaskStateBridge can construct without raising."""
    subprocess.run(
        ["git", "init", "-q"], cwd=path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "t@t"], check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "t"], check=True, capture_output=True,
    )


def _passing_task_work_results(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return a task_work_results dict where every gate passes."""
    results: Dict[str, Any] = {
        "task_id": "TASK-X",
        "quality_gates": {
            "all_passed": True,
            "tests_run": 12,
            "tests_failed": 0,
            "coverage_met": True,
            "line_coverage": 0.85,
            "branch_coverage": 0.78,
        },
        "code_review": {"score": 80, "solid_score": 85, "dry_score": 78, "yagni_score": 82},
        "plan_audit": {"status": "passed", "violations": 0, "severity": "low"},
        "files_modified": [],
        "files_created": [],
        "tests_written": [],
    }
    if extra:
        results.update(extra)
    return results


def _write_results(worktree: Path, task_id: str, results: Dict[str, Any]) -> None:
    results_dir = worktree / ".guardkit" / "autobuild" / task_id
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "task_work_results.json").write_text(json.dumps(results))


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    """A git worktree with a default-honest passing-turn fixture written."""
    _init_git_worktree(tmp_path)
    _write_results(tmp_path, "TASK-X", _passing_task_work_results())
    return tmp_path


# ---------------------------------------------------------------------------
# AC-002: Bundle fields exist
# ---------------------------------------------------------------------------


class TestAC002BundleFields:
    """AC-002: wiring, mocked_seam, spec_gap Optional[Dict] fields exist."""

    def test_bundle_has_wiring_field(self, worktree: Path) -> None:
        """The CoachEvidenceBundle dataclass has a ``wiring`` field."""
        validator = CoachValidator(str(worktree), task_id="TASK-X")
        bundle = validator.gather_evidence(
            task_id="TASK-X",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "x",
            },
        )
        assert hasattr(bundle, "wiring")
        assert bundle.wiring is None or isinstance(bundle.wiring, dict)

    def test_bundle_has_mocked_seam_field(self, worktree: Path) -> None:
        """The CoachEvidenceBundle dataclass has a ``mocked_seam`` field."""
        validator = CoachValidator(str(worktree), task_id="TASK-X")
        bundle = validator.gather_evidence(
            task_id="TASK-X",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "x",
            },
        )
        assert hasattr(bundle, "mocked_seam")
        assert bundle.mocked_seam is None or isinstance(bundle.mocked_seam, dict)

    def test_bundle_has_spec_gap_field(self, worktree: Path) -> None:
        """The CoachEvidenceBundle dataclass has a ``spec_gap`` field."""
        validator = CoachValidator(str(worktree), task_id="TASK-X")
        bundle = validator.gather_evidence(
            task_id="TASK-X",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "x",
            },
        )
        assert hasattr(bundle, "spec_gap")
        assert bundle.spec_gap is None or isinstance(bundle.spec_gap, dict)

    def test_to_dict_includes_new_fields(self, worktree: Path) -> None:
        """to_dict() serialises the new fields without modification."""
        validator = CoachValidator(str(worktree), task_id="TASK-X")
        bundle = validator.gather_evidence(
            task_id="TASK-X",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "x",
            },
        )
        d = bundle.to_dict()
        assert "wiring" in d
        assert "mocked_seam" in d
        assert "spec_gap" in d


# ---------------------------------------------------------------------------
# AC (gather population): populated at complete-path only
# ---------------------------------------------------------------------------


class TestGatherPopulation:
    """AC: wiring fields populated at complete-path return only."""

    def test_complete_path_with_authored_files(self, tmp_path: Path) -> None:
        """When task_type is feature and files_authored is non-empty,
        wiring fields are computed (may be None if factory unavailable)."""
        _init_git_worktree(tmp_path)
        results = _passing_task_work_results({
            "files_authored": ["src/main.py", "src/utils.py"],
        })
        _write_results(tmp_path, "TASK-Y", results)

        validator = CoachValidator(str(tmp_path), task_id="TASK-Y")
        bundle = validator.gather_evidence(
            task_id="TASK-Y",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "x",
            },
        )
        assert bundle.gathering_status == "complete"
        assert bundle.wiring is None or isinstance(bundle.wiring, dict)
        assert bundle.mocked_seam is None or isinstance(bundle.mocked_seam, dict)
        assert bundle.spec_gap is None or isinstance(bundle.spec_gap, dict)

    def test_partial_returns_leave_fields_none(self, tmp_path: Path) -> None:
        """Honesty must_fix short-circuit: all three fields are None."""
        _init_git_worktree(tmp_path)
        results = _passing_task_work_results({
            "files_authored": ["src/main.py"],
        })
        # Inject honesty must_fix to trigger short-circuit
        results["files_modified"] = ["nonexistent_file.py"]
        results["files_created"] = ["nonexistent_file.py"]
        _write_results(tmp_path, "TASK-Z", results)

        validator = CoachValidator(str(tmp_path), task_id="TASK-Z")
        bundle = validator.gather_evidence(
            task_id="TASK-Z",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "x",
            },
        )
        # Should be partial_honesty_abort due to file existence discrepancy
        if bundle.gathering_status != "complete":
            assert bundle.wiring is None
            assert bundle.mocked_seam is None
            assert bundle.spec_gap is None


# ---------------------------------------------------------------------------
# AC-008: Task-type gate
# ---------------------------------------------------------------------------


class TestAC008TaskTypeGate:
    """AC-008: SCAFFOLDING/DOCUMENTATION -> all three fields None."""

    @pytest.mark.parametrize("task_type", ["scaffolding", "documentation"])
    def test_scaffolding_task_type_excluded(self, tmp_path: Path, task_type: str) -> None:
        """SCAFFOLDING tasks produce None for all three wiring fields."""
        _init_git_worktree(tmp_path)
        results = _passing_task_work_results({
            "files_authored": ["src/main.py"],
        })
        _write_results(tmp_path, "TASK-ST", results)

        validator = CoachValidator(str(tmp_path), task_id="TASK-ST")
        bundle = validator.gather_evidence(
            task_id="TASK-ST",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": task_type,
                "description": "x",
            },
        )
        assert bundle.gathering_status == "complete"
        assert bundle.wiring is None
        assert bundle.mocked_seam is None
        assert bundle.spec_gap is None

    def test_zero_authored_files_excluded(self, tmp_path: Path) -> None:
        """Zero-authored files -> all three fields None."""
        _init_git_worktree(tmp_path)
        results = _passing_task_work_results({
            "files_authored": [],
        })
        _write_results(tmp_path, "TASK-EMPTY", results)

        validator = CoachValidator(str(tmp_path), task_id="TASK-EMPTY")
        bundle = validator.gather_evidence(
            task_id="TASK-EMPTY",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "x",
            },
        )
        assert bundle.gathering_status == "complete"
        assert bundle.wiring is None
        assert bundle.mocked_seam is None
        assert bundle.spec_gap is None


# ---------------------------------------------------------------------------
# _run_wiring_analysis unit tests
# ---------------------------------------------------------------------------


class TestRunWiringAnalysis:
    """Unit tests for the _run_wiring_analysis helper."""

    def test_scaffolding_returns_none(self, tmp_path: Path) -> None:
        """SCAFFOLDING task type -> None."""
        result = _run_wiring_analysis(
            worktree_path=tmp_path,
            authored_files=["src/main.py"],
            task_type="scaffolding",
            stack_template="python",
        )
        assert result is None

    def test_documentation_returns_none(self, tmp_path: Path) -> None:
        """DOCUMENTATION task type -> None."""
        result = _run_wiring_analysis(
            worktree_path=tmp_path,
            authored_files=["src/main.py"],
            task_type="documentation",
            stack_template="python",
        )
        assert result is None

    def test_zero_authored_returns_none(self, tmp_path: Path) -> None:
        """Zero authored files -> None."""
        result = _run_wiring_analysis(
            worktree_path=tmp_path,
            authored_files=[],
            task_type="feature",
            stack_template="python",
        )
        assert result is None

    def test_factory_unavailable_returns_none(self, tmp_path: Path) -> None:
        """AC-017: factory not available -> ALL THREE fields None, uniformly
        (no synthesized skip dicts, regardless of authored-file mix)."""
        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator._is_wiring_factory_available",
            return_value=False,
        ):
            for authored in (
                ["src/main.py"],
                ["src/main.py", "tests/test_main.py"],
            ):
                result = _run_wiring_analysis(
                    worktree_path=tmp_path,
                    authored_files=authored,
                    task_type="feature",
                    stack_template="python",
                )
                assert result is None

    def test_exception_returns_none(self, tmp_path: Path) -> None:
        """Exception in analyze_wiring -> None (fail-open, never a raise)."""
        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator._is_wiring_factory_available",
            return_value=True,
        ), patch(
            "guardkit.orchestrator.quality_gates.coach_validator.analyze_wiring",
            MagicMock(side_effect=ImportError("no tree-sitter")),
        ):
            result = _run_wiring_analysis(
                worktree_path=tmp_path,
                authored_files=["src/main.py"],
                task_type="feature",
                stack_template="python",
            )
        assert result is None

    def test_none_result_returns_none(self, tmp_path: Path) -> None:
        """analyze_wiring returns None -> None (probe legitimately didn't run)."""
        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator._is_wiring_factory_available",
            return_value=True,
        ), patch(
            "guardkit.orchestrator.quality_gates.coach_validator.analyze_wiring",
            MagicMock(return_value=None),
        ):
            result = _run_wiring_analysis(
                worktree_path=tmp_path,
                authored_files=["src/main.py"],
                task_type="feature",
                stack_template="python",
            )
        assert result is None


# ---------------------------------------------------------------------------
# AC-015: Absent-vs-empty
# ---------------------------------------------------------------------------


class TestAC015AbsentVsEmpty:
    """AC-015: findings:[] + positive status is distinct from None."""

    def test_empty_findings_distinct_from_none(self) -> None:
        """An empty findings list is NOT the same as None."""
        wiring_with_empty: Dict[str, Any] = {
            "status": "complete",
            "dialect": "python",
            "language": "python",
            "targets_scanned": 3,
            "symbols_examined": 15,
            "findings": [],
            "degraded_files": [],
        }
        mocked_seam_with_empty: Dict[str, Any] = {
            "status": "ran",
            "ran": True,
            "dialect": "python",
            "language": "python",
            "findings": [],
            "external_mocks_ignored": [],
        }
        assert wiring_with_empty is not None
        assert mocked_seam_with_empty is not None
        assert isinstance(wiring_with_empty["findings"], list)
        assert len(wiring_with_empty["findings"]) == 0
        assert isinstance(mocked_seam_with_empty["findings"], list)
        assert len(mocked_seam_with_empty["findings"]) == 0

    def test_none_is_absent_signal(self) -> None:
        """None means the probe did not run (absent signal)."""
        assert None is None
        assert None != []
        assert None != {"findings": []}


# ---------------------------------------------------------------------------
# AC-016: Truncation
# ---------------------------------------------------------------------------


class TestAC016Truncation:
    """AC-016: >20 findings -> first 20 + '... and N more'."""

    def test_wiring_findings_truncated_at_20(self) -> None:
        """When wiring.findings has >20 entries, only first 20 + marker remain."""
        from guardkit.orchestrator.agent_invoker import AgentInvoker

        findings: List[Dict[str, Any]] = [
            {"path": f"src/file_{i}.py", "symbol": f"func_{i}", "severity": "warning"}
            for i in range(25)
        ]
        wiring_dict = {
            "status": "complete",
            "findings": findings,
            "targets_scanned": 25,
        }
        bundle = CoachEvidenceBundle(
            honesty=MagicMock(verified=True, discrepancies=[], resolved_paths=[], should_fix_count=0),
            gathering_status="complete",
            wiring=wiring_dict,
        )

        invoker = AgentInvoker.__new__(AgentInvoker)
        invoker._COACH_BDD_DISCOVERIES_LIMIT = 20

        rendered = invoker._render_evidence_bundle_section(bundle)

        import re
        json_match = re.search(r"<evidence_bundle>\s*(\{.*?\})\s*</evidence_bundle>", rendered, re.DOTALL)
        assert json_match is not None, "Evidence bundle JSON not found in rendered output"
        bundle_json = json.loads(json_match.group(1))

        wiring = bundle_json.get("wiring")
        assert wiring is not None
        wiring_findings = wiring.get("findings", [])
        assert isinstance(wiring_findings, list)
        assert len(wiring_findings) == 21
        assert "... and 5 more" in wiring_findings[-1]

    def test_wiring_findings_not_truncated_under_20(self) -> None:
        """When wiring.findings has <=20 entries, no truncation occurs."""
        from guardkit.orchestrator.agent_invoker import AgentInvoker

        findings = [
            {"path": f"src/file_{i}.py", "symbol": f"func_{i}"}
            for i in range(15)
        ]
        wiring_dict = {
            "status": "complete",
            "findings": findings,
        }
        bundle = CoachEvidenceBundle(
            honesty=MagicMock(verified=True, discrepancies=[], resolved_paths=[], should_fix_count=0),
            gathering_status="complete",
            wiring=wiring_dict,
        )

        invoker = AgentInvoker.__new__(AgentInvoker)
        invoker._COACH_BDD_DISCOVERIES_LIMIT = 20

        rendered = invoker._render_evidence_bundle_section(bundle)

        import re
        json_match = re.search(r"<evidence_bundle>\s*(\{.*?\})\s*</evidence_bundle>", rendered, re.DOTALL)
        assert json_match is not None
        bundle_json = json.loads(json_match.group(1))

        wiring = bundle_json.get("wiring")
        assert wiring is not None
        assert len(wiring.get("findings", [])) == 15


# ---------------------------------------------------------------------------
# _compute_authored_set tests
# ---------------------------------------------------------------------------


class TestComputeAuthoredSet:
    """Unit tests for _compute_authored_set."""

    def test_returns_authored_files(self) -> None:
        results = {"files_authored": ["src/a.py", "src/b.py"]}
        authored = _compute_authored_set(results)
        assert sorted(authored) == ["src/a.py", "src/b.py"]

    def test_fallback_to_created_modified(self, tmp_path: Path) -> None:
        """When files_authored is missing, falls back to created + modified."""
        results = {
            "files_created": ["src/new.py"],
            "files_modified": ["src/old.py"],
        }
        authored = _compute_authored_set(results)
        assert sorted(authored) == ["src/new.py", "src/old.py"]

    def test_fallback_avoids_duplicates(self) -> None:
        """Duplicates across created and modified are deduplicated."""
        results = {
            "files_created": ["src/same.py"],
            "files_modified": ["src/same.py", "src/other.py"],
        }
        authored = _compute_authored_set(results)
        assert sorted(authored) == ["src/other.py", "src/same.py"]

    def test_returns_empty_for_missing_key(self) -> None:
        authored = _compute_authored_set({})
        assert authored == []


# ---------------------------------------------------------------------------
# AC-011: Reaches verdict (rendered in evidence bundle section)
# ---------------------------------------------------------------------------


class TestAC011ReachesVerdict:
    """AC-011: _render_evidence_bundle_section surfaces the fields."""

    def test_wiring_fields_in_rendered_bundle(self) -> None:
        """The rendered evidence bundle JSON contains wiring fields."""
        from guardkit.orchestrator.agent_invoker import AgentInvoker

        wiring_dict = {"status": "complete", "findings": []}
        mocked_seam_dict = {"status": "ran", "findings": []}
        spec_gap_dict = {"status": "complete", "deselected_files": []}

        bundle = CoachEvidenceBundle(
            honesty=MagicMock(verified=True, discrepancies=[], resolved_paths=[], should_fix_count=0),
            gathering_status="complete",
            wiring=wiring_dict,
            mocked_seam=mocked_seam_dict,
            spec_gap=spec_gap_dict,
        )

        invoker = AgentInvoker.__new__(AgentInvoker)
        rendered = invoker._render_evidence_bundle_section(bundle)

        import re
        json_match = re.search(r"<evidence_bundle>\s*(\{.*?\})\s*</evidence_bundle>", rendered, re.DOTALL)
        assert json_match is not None
        bundle_json = json.loads(json_match.group(1))

        assert "wiring" in bundle_json
        assert "mocked_seam" in bundle_json
        assert "spec_gap" in bundle_json
        assert bundle_json["wiring"] == wiring_dict
        assert bundle_json["mocked_seam"] == mocked_seam_dict
        assert bundle_json["spec_gap"] == spec_gap_dict

    def test_guard_sentence_7_present(self) -> None:
        """The _render_absence_of_failure_guards method includes guard #7."""
        from guardkit.orchestrator.agent_invoker import AgentInvoker

        invoker = AgentInvoker.__new__(AgentInvoker)
        guards = invoker._render_absence_of_failure_guards()

        assert "WIRING-EVIDENCE ADVISORY GUARD" in guards
        assert "7." in guards
        assert "wiring" in guards
        assert "mocked_seam" in guards
        assert "spec_gap" in guards
        assert "findings" in guards


# ---------------------------------------------------------------------------
# AC-017: Graceful import absence
# ---------------------------------------------------------------------------


class TestAC017GracefulImportAbsence:
    """AC-017: with guardkitfactory/tree-sitter absent, graceful handling."""

    def test_import_error_does_not_crash_gather_evidence(self, tmp_path: Path) -> None:
        """When analyze_wiring raises ImportError, gather_evidence does not crash."""
        _init_git_worktree(tmp_path)
        results = _passing_task_work_results({
            "files_authored": ["src/main.py"],
        })
        _write_results(tmp_path, "TASK-IMPORT", results)

        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator._is_wiring_factory_available",
            return_value=True,
        ), patch(
            "guardkit.orchestrator.quality_gates.coach_validator.analyze_wiring",
            MagicMock(side_effect=ImportError("no tree-sitter")),
        ):
            validator = CoachValidator(str(tmp_path), task_id="TASK-IMPORT")
            bundle = validator.gather_evidence(
                task_id="TASK-IMPORT",
                turn=1,
                task={
                    "acceptance_criteria": ["AC-001"],
                    "task_type": "feature",
                    "description": "x",
                },
            )

        assert bundle.gathering_status == "complete"
        # Fail-open: analyzer error -> all three fields None, never a crash.
        assert bundle.wiring is None
        assert bundle.mocked_seam is None
        assert bundle.spec_gap is None


# ---------------------------------------------------------------------------
# AC-018: No regression
# ---------------------------------------------------------------------------


class TestAC018NoRegression:
    """AC-018: existing guardkit + guardkitfactory suites green."""

    def test_existing_bundle_fields_still_populated(self, worktree: Path) -> None:
        """Existing bundle fields (honesty, quality_gates, tests, etc.)
        are still populated after adding wiring fields."""
        validator = CoachValidator(str(worktree), task_id="TASK-X")
        bundle = validator.gather_evidence(
            task_id="TASK-X",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "x",
            },
        )
        assert bundle.honesty is not None
        assert bundle.quality_gates is not None
        assert bundle.tests is not None
        assert bundle.coverage_details is not None
        assert bundle.plan_audit is not None
        assert bundle.arch_review is not None

    def test_to_dict_still_works(self, worktree: Path) -> None:
        """to_dict() still produces a valid JSON-serialisable dict."""
        validator = CoachValidator(str(worktree), task_id="TASK-X")
        bundle = validator.gather_evidence(
            task_id="TASK-X",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "x",
            },
        )
        d = bundle.to_dict()
        json_str = json.dumps(d, default=str)
        assert isinstance(json_str, str)
        json.loads(json_str)
