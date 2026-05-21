"""AC-014 — CoachValidator.gather_evidence returns a populated CoachEvidenceBundle.

TASK-HMIG-008R Part E (Revision 3). Verifies the deterministic gathering
pipeline introduced in Part A: ``CoachValidator.gather_evidence`` runs the
same helpers ``validate()`` uses (``_verify_honesty``, ``verify_quality_gates``,
``validate_requirements``, ``run_independent_tests``) and packages the
intermediates into a :class:`CoachEvidenceBundle` instead of applying
decision logic.

Falsifier shape:

* A passing-turn fixture must yield ``gathering_status == "complete"`` and a
  bundle with populated ``quality_gates``, ``arch_review``, ``plan_audit``,
  and ``tests`` fields. ``honesty.verified`` is True. JSON-serialisation via
  ``bundle.to_dict()`` works for the entire bundle.
* A state-bridge-move fixture (Player report contains a path the
  orchestrator moved mid-turn, canonical path resolves) must populate
  ``bundle.honesty.resolved_paths`` so the LLM Coach receives the
  Layer-1 audit trail.
* A pre-evidence error (missing ``task_work_results.json``) must produce
  ``gathering_status == "partial_exception"`` with a populated
  ``gathering_error`` rather than raising to the caller. This is the
  Phase 2.5-review-finding-#1 contract: ``gather_evidence`` MUST NOT
  raise so the autobuild primary path never falls back to ``validate()``.

These tests do not assert decision logic; that is the
``_apply_legacy_decision_logic`` shim's responsibility (Part A.2 follow-up)
and the LLM Coach's responsibility under the primary path.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from guardkit.orchestrator.coach_verification import CoachVerifier
from guardkit.orchestrator.quality_gates.coach_evidence import (
    CoachEvidenceBundle,
    GatheringStatus,
)
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


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


def _passing_task_work_results() -> dict:
    """Return a task_work_results dict where every gate passes."""
    return {
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


def _write_results(worktree: Path, task_id: str, results: dict) -> None:
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
# Happy path
# ---------------------------------------------------------------------------


class TestGatherEvidenceHappyPath:
    """Passing-turn fixture: every field on the bundle is populated."""

    def test_returns_coach_evidence_bundle(self, worktree: Path) -> None:
        validator = CoachValidator(str(worktree), task_id="TASK-X")
        bundle = validator.gather_evidence(
            task_id="TASK-X",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001 trivial"],
                "task_type": "feature",
                "description": "happy path",
            },
        )
        assert isinstance(bundle, CoachEvidenceBundle)

    def test_gathering_status_complete_for_passing_turn(self, worktree: Path) -> None:
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
        assert bundle.gathering_status == "complete"
        assert bundle.gathering_error is None

    def test_quality_gates_populated(self, worktree: Path) -> None:
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
        assert bundle.quality_gates is not None
        assert bundle.quality_gates.all_gates_passed is True
        assert bundle.quality_gates.tests_passed is True

    def test_arch_review_populated_with_score(self, worktree: Path) -> None:
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
        assert bundle.arch_review is not None
        assert bundle.arch_review["score"] == 80

    def test_plan_audit_populated_with_status(self, worktree: Path) -> None:
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
        assert bundle.plan_audit is not None
        assert bundle.plan_audit["status"] == "passed"

    def test_bdd_is_none_when_absent_from_results(self, worktree: Path) -> None:
        """``bdd_results`` key absent → bundle.bdd is None (Pattern 2 guard
        in the prompt branches on this directly)."""
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
        assert bundle.bdd is None

    def test_tests_dict_carries_tests_run_count(self, worktree: Path) -> None:
        """The Pattern-2 zero-cardinality test guard inspects
        ``bundle.tests['tests_run']`` — must be populated even when all
        gates pass."""
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
        assert bundle.tests is not None
        assert bundle.tests["tests_run"] == 12

    def test_honesty_verified_for_clean_fixture(self, worktree: Path) -> None:
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
        assert bundle.honesty.verified is True
        assert bundle.honesty.discrepancies == []
        assert bundle.severity_recommendations == []

    def test_task_type_and_profile_populated(self, worktree: Path) -> None:
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
        assert bundle.task_type == "feature"
        assert bundle.profile_name is not None

    def test_bundle_is_json_serialisable(self, worktree: Path) -> None:
        """The bundle is rendered into the Coach prompt as JSON in Part C."""
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
        payload = json.dumps(bundle.to_dict(), default=str)
        # JSON contains the structural keys the prompt absence-of-failure
        # guards reference by name.
        assert '"gathering_status":' in payload
        assert '"honesty":' in payload
        assert '"tests":' in payload


# ---------------------------------------------------------------------------
# Layer-1 state_bridge resolution (mirrors the AC-013 wiring smoke)
# ---------------------------------------------------------------------------


class TestGatherEvidenceLayer1Resolution:
    """When the Player claims a pre-move task path, state_bridge identity
    resolution suppresses the discrepancy and appends a ResolvedPath
    audit record. Bundle.honesty.resolved_paths must carry that record so
    the LLM Coach prompt's LAYER-1 PATH DEMOTION GUARD has the data it
    needs to demote the would-be discrepancy.
    """

    def test_resolved_paths_populated_for_state_bridge_move(self, tmp_path: Path) -> None:
        _init_git_worktree(tmp_path)

        # Canonical task file lives at design_approved/...
        (tmp_path / "tasks" / "design_approved").mkdir(parents=True, exist_ok=True)
        canonical = tmp_path / "tasks" / "design_approved" / "TASK-X-foo.md"
        canonical.write_text("---\nid: TASK-X\nstatus: design_approved\n---\n")

        # task_work_results claims the pre-move backlog/... path (ghost).
        _write_results(tmp_path, "TASK-X", {
            "task_id": "TASK-X",
            "quality_gates": {"all_passed": True, "tests_run": 1, "tests_failed": 0, "coverage_met": True},
            "code_review": {"score": 80},
            "plan_audit": {"status": "passed", "violations": 0, "severity": "low"},
            "files_modified": ["tasks/backlog/TASK-X-foo.md"],
            "files_created": [],
            "tests_written": [],
        })

        # Patch out _verify_claims_were_staged so the unrelated claim_audit
        # gate doesn't fire on an unstaged ghost path (FEAT-39E1 sibling).
        # The wiring under test is _verify_files_exist + state_bridge, not
        # the gitignore/staged probes.
        with patch.object(CoachVerifier, "_verify_claims_were_staged", return_value=[]):
            validator = CoachValidator(str(tmp_path), task_id="TASK-X")
            bundle = validator.gather_evidence(
                task_id="TASK-X",
                turn=1,
                task={
                    "acceptance_criteria": ["AC-001"],
                    "task_type": "feature",
                    "description": "state-bridge move scenario",
                },
            )

        # The ghost path must NOT surface as a critical discrepancy.
        assert bundle.honesty.verified is True
        assert bundle.honesty.discrepancies == []
        # The resolution must be audited in resolved_paths.
        assert bundle.honesty.resolved_paths, (
            "Layer-1 suppression must populate resolved_paths so the "
            "Coach prompt audit trail records the resolution."
        )
        assert any(
            rp.claimed == "tasks/backlog/TASK-X-foo.md"
            and rp.resolved_to.endswith("tasks/design_approved/TASK-X-foo.md")
            for rp in bundle.honesty.resolved_paths
        )


# ---------------------------------------------------------------------------
# Pre-evidence exception paths — gather_evidence MUST NOT raise
# ---------------------------------------------------------------------------


class TestGatherEvidenceNeverRaises:
    """Per Phase 2.5 review finding #1 and plan §3: gather_evidence MUST NOT
    raise to its caller — the primary autobuild path would otherwise fall back
    to validate(), which is exactly the path falsifier #1 requires to be gone.
    """

    def test_missing_results_returns_partial_exception(self, tmp_path: Path) -> None:
        _init_git_worktree(tmp_path)
        # No task_work_results.json written.
        validator = CoachValidator(str(tmp_path), task_id="TASK-MISSING")
        bundle = validator.gather_evidence(
            task_id="TASK-MISSING",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "missing results",
            },
        )
        assert bundle.gathering_status == "partial_exception"
        assert bundle.gathering_error is not None
        assert "missing_results" in bundle.gathering_error

    def test_invalid_task_type_returns_partial_exception(self, tmp_path: Path) -> None:
        _init_git_worktree(tmp_path)
        validator = CoachValidator(str(tmp_path), task_id="TASK-Y")
        bundle = validator.gather_evidence(
            task_id="TASK-Y",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "not_a_real_task_type",
                "description": "invalid type",
            },
        )
        assert bundle.gathering_status == "partial_exception"
        assert bundle.gathering_error is not None
        assert "invalid_task_type" in bundle.gathering_error

    def test_operator_handoff_returns_complete_with_marker(self, tmp_path: Path) -> None:
        """Operator-handoff tasks intentionally produce an empty bundle —
        the autobuild layer is responsible for short-circuiting Coach
        invocation, not the bundle gatherer."""
        _init_git_worktree(tmp_path)
        validator = CoachValidator(str(tmp_path), task_id="TASK-OPS")
        bundle = validator.gather_evidence(
            task_id="TASK-OPS",
            turn=1,
            task={
                "acceptance_criteria": ["operator runs X"],
                "task_type": "operator_handoff",
                "description": "operator-driven verification",
            },
        )
        assert bundle.gathering_status == "complete"
        assert bundle.task_type == "operator_handoff"
        # Downstream evidence fields stay None — no evidence applies.
        assert bundle.quality_gates is None
        assert bundle.independent_tests is None


# ---------------------------------------------------------------------------
# Type / API surface checks
# ---------------------------------------------------------------------------


class TestBundleTypeSurface:
    """Structural assertions that protect against silent schema drift."""

    def test_required_fields_present(self) -> None:
        """AC-001 enumerated the required fields. Drift here breaks the
        Coach prompt renderer (Part C ``_render_evidence_bundle_section``)."""
        from dataclasses import fields

        names = {f.name for f in fields(CoachEvidenceBundle)}
        required = {
            "honesty",
            "quality_gates",
            "coverage_details",
            "plan_audit",
            "bdd",
            "arch_review",
            "tests",
            "severity_recommendations",
            "gathering_status",
        }
        missing = required - names
        assert not missing, f"AC-001 fields missing from bundle: {missing}"

    def test_gathering_status_literal_values(self) -> None:
        """The four literal values are referenced by name in the absence-of-
        failure guards in the Coach prompt — drift would silently break Guard #5."""
        # Literal-type contents — extract via __args__ on the alias.
        assert GatheringStatus.__args__ == (
            "complete",
            "partial_honesty_abort",
            "partial_gate_abort",
            "partial_exception",
        )
