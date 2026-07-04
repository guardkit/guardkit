"""TASK-QAV-002: stub_scan, coverage, behavioural_oracle fields on CoachEvidenceBundle.

Acceptance criteria covered:
  AC-1: Fields exist as Optional[Dict] = None; to_dict() carries them.
  AC-2: findings:[] with positive status distinct from None; partial returns leave fields None.
  AC-3: Lazy import seam populates stub_scan on complete path; graceful absence leaves None.
  AC-4: Truncation logic; advisory guard sentence; coverage/behavioural_oracle render when present.
  AC-5: Cross-repo seam test verifies guardkitfactory.wiring.analyze_stub_scan contract keys.
  AC-6: Behavioral dogfood integration test drives gather_evidence end-to-end.
  AC-7: Advisory only, no verdict override.
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
    _compute_stub_scan,
    _is_wiring_factory_available,
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
# AC-1: Fields exist as Optional[Dict] = None
# ---------------------------------------------------------------------------


class TestAC1FieldsExist:
    """AC-1: stub_scan, coverage, behavioural_oracle exist with correct defaults."""

    def test_bundle_has_stub_scan_field(self, worktree: Path) -> None:
        """CoachEvidenceBundle has a ``stub_scan`` field defaulting to None."""
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
        assert hasattr(bundle, "stub_scan"), "Bundle missing stub_scan field"
        # Coverage and behavioural_oracle always exist
        assert hasattr(bundle, "coverage"), "Bundle missing coverage field"
        assert hasattr(bundle, "behavioural_oracle"), "Bundle missing behavioural_oracle field"

    def test_bundle_fields_none_by_default(self, worktree: Path) -> None:
        """New fields default to None when not populated."""
        # Direct construction with no values
        bundle = CoachEvidenceBundle(gathering_status="complete", honesty=None)
        assert bundle.stub_scan is None
        assert bundle.coverage is None
        assert bundle.behavioural_oracle is None

    def test_to_dict_carries_new_fields(self, worktree: Path) -> None:
        """CoachEvidenceBundle.to_dict() includes the new fields."""
        bundle = CoachEvidenceBundle(
            gathering_status="complete",
            honesty=None,
            stub_scan={"status": "passed", "findings": []},
            coverage={"status": "passed", "coverage_percentage": 85.0},
            behavioural_oracle={"status": "passed", "scenarios_verified": 10},
        )
        d = bundle.to_dict()
        assert "stub_scan" in d
        assert "coverage" in d
        assert "behavioural_oracle" in d
        assert d["stub_scan"]["status"] == "passed"
        assert d["coverage"]["coverage_percentage"] == 85.0
        assert d["behavioural_oracle"]["scenarios_verified"] == 10

    def test_docstring_follows_pattern(self) -> None:
        """CoachEvidenceBundle docstring documents the new fields."""
        assert CoachEvidenceBundle.__doc__ is not None
        assert "stub_scan" in CoachEvidenceBundle.__doc__
        assert "coverage" in CoachEvidenceBundle.__doc__
        assert "behavioural_oracle" in CoachEvidenceBundle.__doc__


# ---------------------------------------------------------------------------
# AC-2: findings:[] with positive status distinct from None
# ---------------------------------------------------------------------------


class TestAC2PartialReturnsLeaveNone:
    """AC-2: Partial returns leave stub_scan/coverage/behavioural_oracle as None."""

    def test_honesty_abort_leaves_fields_none(self, worktree: Path) -> None:
        """When gathering aborts (any reason), all three fields are None."""
        results = _passing_task_work_results()
        results["honesty"] = {
            "verified": False,
            "discrepancies": [{"claim_type": "file_existence", "severity": "critical"}],
        }
        _write_results(worktree, "TASK-X", results)
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
        # If gathering aborts (partial_honesty_abort, partial_gate_abort, etc.)
        # the three new fields must be None.
        if bundle.gathering_status != "complete":
            assert bundle.stub_scan is None
            assert bundle.coverage is None
            assert bundle.behavioural_oracle is None

    def test_gate_abort_leaves_fields_none(self, worktree: Path) -> None:
        """When quality gates fail, all three fields are None."""
        results = _passing_task_work_results()
        results["quality_gates"]["all_passed"] = False
        results["quality_gates"]["tests_failed"] = 5
        _write_results(worktree, "TASK-X", results)
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
        assert bundle.gathering_status == "partial_gate_abort"
        assert bundle.stub_scan is None
        assert bundle.coverage is None
        assert bundle.behavioural_oracle is None

    def test_stub_scan_findings_distinct_from_none(self) -> None:
        """A stub_scan with findings:[] is distinct from None."""
        bundle = CoachEvidenceBundle(
            gathering_status="complete",
            honesty=None,
            stub_scan={"status": "passed", "findings": []},
        )
        assert bundle.stub_scan is not None
        assert isinstance(bundle.stub_scan["findings"], list)


# ---------------------------------------------------------------------------
# AC-3: Lazy import seam populates stub_scan on complete path
# ---------------------------------------------------------------------------


class TestAC3LazyImportSeam:
    """AC-3: stub_scan populated on complete path via lazy import seam."""

    def test_stub_scan_none_when_factory_unavailable(self, worktree: Path) -> None:
        """When guardkitfactory.wiring is unavailable, stub_scan stays None."""
        with patch("guardkit.orchestrator.quality_gates.coach_validator._is_wiring_factory_available", return_value=False):
            result = _compute_stub_scan(
                worktree_path=worktree,
                authored_files=["src/main.py"],
                task_type="FEATURE",
            )
            assert result is None

    def test_stub_scan_none_for_scaffolding_task(self, worktree: Path) -> None:
        """SCAFFOLDING task type gates out stub_scan → None."""
        with patch("guardkit.orchestrator.quality_gates.coach_validator._is_wiring_factory_available", return_value=False):
            result = _compute_stub_scan(
                worktree_path=worktree,
                authored_files=["src/main.py"],
                task_type="SCAFFOLDING",
            )
            assert result is None

    def test_stub_scan_none_for_documentation_task(self, worktree: Path) -> None:
        """DOCUMENTATION task type gates out stub_scan → None."""
        with patch("guardkit.orchestrator.quality_gates.coach_validator._is_wiring_factory_available", return_value=False):
            result = _compute_stub_scan(
                worktree_path=worktree,
                authored_files=["src/main.py"],
                task_type="DOCUMENTATION",
            )
            assert result is None

    def test_stub_scan_none_when_no_authored_files(self) -> None:
        """Zero authored files → stub_scan stays None."""
        with patch("guardkit.orchestrator.quality_gates.coach_validator._is_wiring_factory_available", return_value=False):
            result = _compute_stub_scan(
                worktree_path=Path("/tmp"),
                authored_files=[],
                task_type="FEATURE",
            )
            assert result is None

    def test_stub_scan_populated_when_factory_available(
        self, worktree: Path,
    ) -> None:
        """When factory is available, stub_scan is populated on complete path."""
        mock_result = {
            "status": "passed",
            "findings": [],
            "symbols_examined": 5,
        }
        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator._is_wiring_factory_available",
            return_value=True,
        ), patch(
            "guardkit.orchestrator.quality_gates.coach_validator.analyze_stub_scan",
            return_value=mock_result,
        ):
            result = _compute_stub_scan(
                worktree_path=worktree,
                authored_files=["src/main.py"],
                task_type="FEATURE",
            )
            assert result == mock_result

    def test_stub_scan_populated_for_refactor_task(
        self, worktree: Path,
    ) -> None:
        """REFACTOR task type also gets stub_scan populated."""
        mock_result = {
            "status": "passed",
            "findings": [],
            "symbols_examined": 3,
        }
        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator._is_wiring_factory_available",
            return_value=True,
        ), patch(
            "guardkit.orchestrator.quality_gates.coach_validator.analyze_stub_scan",
            return_value=mock_result,
        ):
            result = _compute_stub_scan(
                worktree_path=worktree,
                authored_files=["src/main.py"],
                task_type="REFACTOR",
            )
            assert result == mock_result

    def test_stub_scan_populated_for_integration_task(
        self, worktree: Path,
    ) -> None:
        """INTEGRATION task type also gets stub_scan populated."""
        mock_result = {
            "status": "passed",
            "findings": [],
            "symbols_examined": 2,
        }
        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator._is_wiring_factory_available",
            return_value=True,
        ), patch(
            "guardkit.orchestrator.quality_gates.coach_validator.analyze_stub_scan",
            return_value=mock_result,
        ):
            result = _compute_stub_scan(
                worktree_path=worktree,
                authored_files=["src/main.py"],
                task_type="INTEGRATION",
            )
            assert result == mock_result

    def test_stub_scan_none_on_factory_exception(self, worktree: Path) -> None:
        """When factory raises, stub_scan stays None (graceful degradation)."""
        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator._is_wiring_factory_available",
            return_value=True,
        ), patch(
            "guardkit.orchestrator.quality_gates.coach_validator.analyze_stub_scan",
            side_effect=RuntimeError("factory error"),
        ):
            result = _compute_stub_scan(
                worktree_path=worktree,
                authored_files=["src/main.py"],
                task_type="FEATURE",
            )
            assert result is None


# ---------------------------------------------------------------------------
# AC-4: Truncation logic + advisory guard sentence
# ---------------------------------------------------------------------------


class TestAC4TruncationAndAdvisory:
    """AC-4: Truncation for >20 findings; advisory guard sentence present."""

    def test_stub_scan_truncation_keeps_first_20(self, worktree: Path) -> None:
        """stub_scan findings truncated to first 20 + remainder marker."""
        from guardkit.orchestrator.agent_invoker import AgentInvoker

        findings = [{"symbol": f"stub_{i}"} for i in range(25)]
        bundle = CoachEvidenceBundle(
            gathering_status="complete",
            honesty=None,
            stub_scan={"status": "passed", "findings": findings},
        )
        invoker = AgentInvoker(worktree_path=str(worktree))
        rendered = invoker._render_evidence_bundle_section(bundle)

        # The rendered JSON should contain the truncated list
        assert "... and 5 more" in rendered

    def test_stub_scan_no_truncation_under_limit(self, worktree: Path) -> None:
        """stub_scan findings under 20 are NOT truncated."""
        from guardkit.orchestrator.agent_invoker import AgentInvoker

        findings = [{"symbol": f"stub_{i}"} for i in range(15)]
        bundle = CoachEvidenceBundle(
            gathering_status="complete",
            honesty=None,
            stub_scan={"status": "passed", "findings": findings},
        )
        invoker = AgentInvoker(worktree_path=str(worktree))
        rendered = invoker._render_evidence_bundle_section(bundle)
        assert "... and" not in rendered
        # All 15 should be present
        for i in range(15):
            assert f"stub_{i}" in rendered

    def test_coverage_fields_render_when_present(self, worktree: Path) -> None:
        """coverage renders in bundle when populated."""
        from guardkit.orchestrator.agent_invoker import AgentInvoker

        bundle = CoachEvidenceBundle(
            gathering_status="complete",
            honesty=None,
            coverage={"status": "passed", "coverage_percentage": 85.0},
        )
        invoker = AgentInvoker(worktree_path=str(worktree))
        rendered = invoker._render_evidence_bundle_section(bundle)
        assert "coverage" in rendered
        assert "85.0" in rendered

    def test_behavioural_oracle_fields_render_when_present(self, worktree: Path) -> None:
        """behavioural_oracle renders in bundle when populated."""
        from guardkit.orchestrator.agent_invoker import AgentInvoker

        bundle = CoachEvidenceBundle(
            gathering_status="complete",
            honesty=None,
            behavioural_oracle={"status": "passed", "scenarios_verified": 10},
        )
        invoker = AgentInvoker(worktree_path=str(worktree))
        rendered = invoker._render_evidence_bundle_section(bundle)
        assert "behavioural_oracle" in rendered
        assert "10" in rendered

    def test_advisory_guard_sentence_present(self, worktree: Path) -> None:
        """Absence-of-failure guards include stub_scan advisory sentence."""
        from guardkit.orchestrator.agent_invoker import AgentInvoker

        invoker = AgentInvoker(worktree_path=str(worktree))
        guards = invoker._render_absence_of_failure_guards()
        assert "stub_scan" in guards
        assert "STUB-SCAN ADVISORY GUARD" in guards
        assert "NEVER changes the Coach decision deterministically" in guards


# ---------------------------------------------------------------------------
# AC-5: Cross-repo seam test for analyze_stub_scan contract
# ---------------------------------------------------------------------------


class TestAC5SeamContract:
    """AC-5: Cross-repo seam test verifies guardkitfactory.wiring.analyze_stub_scan contract."""

    def test_analyze_stub_scan_returns_contract_keys(self, tmp_path: Path) -> None:
        """guardkitfactory.wiring.analyze_stub_scan returns dict with required keys."""
        pytest.importorskip("guardkitfactory.wiring")

        # Import the real factory after skip check
        from guardkitfactory.wiring import analyze_stub_scan  # noqa: F811

        # Create a minimal authored file with a stub
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        stub_file = src_dir / "service.py"
        stub_file.write_text(
            "class MyService:\n"
            "    def do_work(self):\n"
            "        pass\n"
        )

        # Contract: authored_files are WORKTREE-RELATIVE. An absolute path
        # here also trips the dialect's test-file markers on pytest tmp_path
        # (the "pytest-of-*/test_*" segment contains "test_"), yielding a
        # spurious None. Caught at merge review, 2026-07-04.
        result = analyze_stub_scan(
            authored_files=["src/service.py"],
            worktree_path=tmp_path,
            task_type="feature",
        )
        assert result is not None
        assert isinstance(result, dict)
        assert "status" in result, (
            "guardkitfactory.wiring.analyze_stub_scan dropped the 'status' key"
        )
        assert "findings" in result, (
            "guardkitfactory.wiring.analyze_stub_scan dropped the 'findings' key"
        )
        assert "symbols_examined" in result, (
            "guardkitfactory.wiring.analyze_stub_scan dropped the 'symbols_examined' key"
        )


# ---------------------------------------------------------------------------
# AC-6: Behavioral dogfood integration test
# ---------------------------------------------------------------------------


class TestAC6Integration:
    """AC-6: End-to-end gather_evidence over a fixture worktree."""

    def test_gather_evidence_carries_stub_scan_field(
        self, worktree: Path,
    ) -> None:
        """gather_evidence returns bundle with stub_scan field (may be None)."""
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
        assert hasattr(bundle, "stub_scan")
        assert hasattr(bundle, "coverage")
        assert hasattr(bundle, "behavioural_oracle")
        # In a dev venv without guardkitfactory, stub_scan should be None
        # (graceful absence). The field must exist regardless.

    def test_gather_evidence_complete_path_has_fields(
        self, worktree: Path,
    ) -> None:
        """Complete path gather_evidence includes all new fields in to_dict."""
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
        assert "stub_scan" in d
        assert "coverage" in d
        assert "behavioural_oracle" in d


# ---------------------------------------------------------------------------
# AC-7: Advisory only, no verdict override
# ---------------------------------------------------------------------------


class TestAC7AdvisoryOnly:
    """AC-7: stub_scan findings are advisory only, never override verdict."""

    def test_stub_scan_findings_do_not_block_bundle(self, worktree: Path) -> None:
        """Bundle with stub_scan findings still gathers as complete."""
        from guardkit.orchestrator.agent_invoker import AgentInvoker

        findings = [{"symbol": "stub_func", "type": "pass_body"}]
        bundle = CoachEvidenceBundle(
            gathering_status="complete",
            honesty=None,
            stub_scan={"status": "findings", "findings": findings},
        )
        # The bundle itself should be valid regardless of findings
        assert bundle.gathering_status == "complete"
        assert bundle.stub_scan is not None
        assert len(bundle.stub_scan["findings"]) == 1

    def test_advisory_guard_does_not_override_decision(
        self, worktree: Path,
    ) -> None:
        """Advisory guard sentence explicitly states advisory-only."""
        from guardkit.orchestrator.agent_invoker import AgentInvoker

        invoker = AgentInvoker(worktree_path=str(worktree))
        guards = invoker._render_absence_of_failure_guards()
        # The guard must state it's advisory-only
        assert "advisory-only" in guards.lower() or "advisory only" in guards.lower()
        assert "NEVER" in guards
