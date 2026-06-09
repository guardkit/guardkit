"""AC-016 + AC-017 — Coach prompt absence-of-failure guards (TASK-HMIG-008R Part E).

This test asserts the absence-of-failure guard sentences are correctly
*wired into the prompt*. It does NOT assert that a real LLM Coach
follows them. The behavioural assertion (that an LLM would actually
return ``feedback`` on a zero-cardinality bundle) is the falsifier for
Wave 3 canary observability (TASK-HMIG-009), not this unit test.
Per Phase 2.5 review should-address #5.

Falsifier shapes:

* **AC-016 / Pattern 2 zero-cardinality**:
  When the BDD plugin returned ``scenarios_attempted == 0,
  scenarios_failed == 0``, the rendered Coach prompt must contain
  Guard #1 ("ZERO-CARDINALITY BDD GUARD") referencing
  ``scenarios_attempted == 0``. The structural rule is the LLM-layer
  equivalent of the deterministic guard in
  ``.claude/rules/absence-of-failure-is-not-success.md``.
* **AC-017 / Pattern 3 state-bridge move**:
  A state-bridge-style fixture (Player report contains a pre-move
  path, canonical path exists on disk) must:
  - Under the primary path: produce a bundle whose
    ``honesty.resolved_paths`` is non-empty AND a prompt containing
    Guard #4 ("LAYER-1 PATH DEMOTION GUARD") plus the resolved
    canonical path verbatim.
  - Under ``GUARDKIT_COACH_LEGACY=1``: validate() runs unchanged and
    the existing TASK-FIX-1B4A wiring continues to suppress the
    discrepancy without regression.

Wave-3 canary (TASK-HMIG-009) covers the *behavioural* claim that an
LLM Coach following these guards returns feedback on zero-cardinality
bundles and approve on Layer-1-suppressed bundles. This file's
contract is narrower: the guards must reach the prompt.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.coach_verification import (
    CoachVerifier,
    HonestyVerification,
)
from guardkit.orchestrator.quality_gates.coach_evidence import (
    CoachEvidenceBundle,
)
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _init_git_worktree(path: Path) -> None:
    subprocess.run(
        ["git", "init", "-q"], cwd=path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "t@t"],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "t"],
        check=True, capture_output=True,
    )


def _write_results(worktree: Path, task_id: str, results: dict) -> None:
    results_dir = worktree / ".guardkit" / "autobuild" / task_id
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "task_work_results.json").write_text(json.dumps(results))


def _passing_results_with_bdd(*, scenarios_attempted: int, scenarios_failed: int = 0) -> dict:
    return {
        "task_id": "TASK-ZCG-001",
        "quality_gates": {
            "all_passed": True,
            "tests_run": 5,
            "tests_failed": 0,
            "coverage_met": True,
            "line_coverage": 0.85,
            "branch_coverage": 0.78,
        },
        "code_review": {"score": 80},
        "plan_audit": {"status": "passed", "violations": 0, "severity": "low"},
        "bdd_results": {
            "scenarios_attempted": scenarios_attempted,
            "scenarios_failed": scenarios_failed,
            "scenarios_passed": max(0, scenarios_attempted - scenarios_failed),
            "scenarios_pending": 0,
            "failures": [],
            "pending": [],
            "feature_files": ["features/example.feature"],
        },
        "files_modified": [],
        "files_created": [],
        "tests_written": [],
    }


def _build_invoker(worktree: Path) -> AgentInvoker:
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    return invoker


# ---------------------------------------------------------------------------
# AC-016: Pattern 2 zero-cardinality BDD bundle
# ---------------------------------------------------------------------------


class TestZeroCardinalityBDDGuard:
    """When ``evidence.bdd.scenarios_attempted == 0`` the Coach prompt
    MUST carry Guard #1 verbatim so the LLM can apply the
    absence-of-failure rule from
    ``.claude/rules/absence-of-failure-is-not-success.md`` at the
    LLM layer.
    """

    @pytest.fixture
    def worktree(self, tmp_path: Path) -> Path:
        _init_git_worktree(tmp_path)
        return tmp_path

    def test_zero_cardinality_bundle_renders_guard_in_prompt(
        self, worktree: Path,
    ) -> None:
        _write_results(
            worktree, "TASK-ZCG-001",
            _passing_results_with_bdd(scenarios_attempted=0, scenarios_failed=0),
        )
        validator = CoachValidator(str(worktree), task_id="TASK-ZCG-001")
        bundle = validator.gather_evidence(
            task_id="TASK-ZCG-001",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "zero-cardinality BDD",
            },
        )

        assert bundle.bdd is not None
        assert bundle.bdd["scenarios_attempted"] == 0
        assert bundle.bdd["scenarios_failed"] == 0

        prompt = _build_invoker(worktree)._build_coach_prompt(
            task_id="TASK-ZCG-001",
            turn=1,
            requirements="zero-cardinality test",
            player_report={"files_modified": []},
            evidence_bundle=bundle,
        )

        # Guard #1 is the load-bearing absence-of-failure rule at the LLM layer.
        assert "ZERO-CARDINALITY BDD GUARD" in prompt
        assert "scenarios_attempted == 0" in prompt
        assert "ABSENT SIGNAL" in prompt

        # Cross-reference to the seeded rule must be present so the Coach can
        # cite it in its rationale.
        assert "absence-of-failure-is-not-success.md" in prompt

    def test_zero_cardinality_bundle_serialised_in_evidence_section(
        self, worktree: Path,
    ) -> None:
        """The Coach can ONLY apply Guard #1 if the JSON-serialised bundle
        actually contains ``scenarios_attempted: 0`` for it to read."""
        _write_results(
            worktree, "TASK-ZCG-001",
            _passing_results_with_bdd(scenarios_attempted=0),
        )
        validator = CoachValidator(str(worktree), task_id="TASK-ZCG-001")
        bundle = validator.gather_evidence(
            task_id="TASK-ZCG-001",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "x",
            },
        )

        prompt = _build_invoker(worktree)._build_coach_prompt(
            task_id="TASK-ZCG-001",
            turn=1,
            requirements="x",
            player_report={"files_modified": []},
            evidence_bundle=bundle,
        )

        evidence_start = prompt.index("<evidence_bundle>")
        evidence_end = prompt.index("</evidence_bundle>")
        evidence_block = prompt[evidence_start:evidence_end]
        assert '"scenarios_attempted": 0' in evidence_block

    def test_non_zero_cardinality_still_renders_guard(
        self, worktree: Path,
    ) -> None:
        """The guard SENTENCE is always present in the prompt regardless of
        cardinality — the Coach applies it conditionally. Confirms drift
        protection: the guard isn't accidentally hidden when scenarios > 0.
        """
        _write_results(
            worktree, "TASK-ZCG-001",
            _passing_results_with_bdd(scenarios_attempted=3, scenarios_failed=0),
        )
        validator = CoachValidator(str(worktree), task_id="TASK-ZCG-001")
        bundle = validator.gather_evidence(
            task_id="TASK-ZCG-001",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "x",
            },
        )

        prompt = _build_invoker(worktree)._build_coach_prompt(
            task_id="TASK-ZCG-001",
            turn=1,
            requirements="x",
            player_report={"files_modified": []},
            evidence_bundle=bundle,
        )

        # Guard sentences are unconditional in the prompt — Coach applies them
        # only when the structural condition holds.
        assert "ZERO-CARDINALITY BDD GUARD" in prompt

    def test_all_five_guards_present_in_prompt(
        self, worktree: Path,
    ) -> None:
        """AC-009 + Phase 2.5 finding #2 + TASK-FIX-COACHTESTTO: six guards
        must always render."""
        _write_results(
            worktree, "TASK-ZCG-001",
            _passing_results_with_bdd(scenarios_attempted=0),
        )
        validator = CoachValidator(str(worktree), task_id="TASK-ZCG-001")
        bundle = validator.gather_evidence(
            task_id="TASK-ZCG-001",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "x",
            },
        )

        prompt = _build_invoker(worktree)._build_coach_prompt(
            task_id="TASK-ZCG-001",
            turn=1,
            requirements="x",
            player_report={"files_modified": []},
            evidence_bundle=bundle,
        )

        for guard_name in (
            "ZERO-CARDINALITY BDD GUARD",
            "ZERO-CARDINALITY TEST GUARD",
            "SOPHISTICATED-LIE GUARD",
            "LAYER-1 PATH DEMOTION GUARD",
            "GATHERING-STATUS GUARD",
            "INDEPENDENT-TEST ABSENT GUARD",
        ):
            assert guard_name in prompt, f"Missing guard: {guard_name}"

    def test_guards_emitted_inside_xml_tag(
        self, worktree: Path,
    ) -> None:
        """The XML-like tag is the load-bearing structural marker that lets
        the Coach LLM locate guards deterministically without prompt-engineering
        fragility. Drift in the tag breaks Wave-3 canary observability."""
        _write_results(
            worktree, "TASK-ZCG-001",
            _passing_results_with_bdd(scenarios_attempted=0),
        )
        validator = CoachValidator(str(worktree), task_id="TASK-ZCG-001")
        bundle = validator.gather_evidence(
            task_id="TASK-ZCG-001",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "x",
            },
        )

        prompt = _build_invoker(worktree)._build_coach_prompt(
            task_id="TASK-ZCG-001",
            turn=1,
            requirements="x",
            player_report={"files_modified": []},
            evidence_bundle=bundle,
        )

        assert "<absence_of_failure_guards>" in prompt
        assert "</absence_of_failure_guards>" in prompt
        guards_start = prompt.index("<absence_of_failure_guards>")
        guards_end = prompt.index("</absence_of_failure_guards>")
        guards_block = prompt[guards_start:guards_end]
        assert "ZERO-CARDINALITY BDD GUARD" in guards_block

    def test_zero_tests_run_guard_renders(self, worktree: Path) -> None:
        """Guard #2 (ZERO-CARDINALITY TEST GUARD) must also appear."""
        # Construct a bundle directly so we can force tests_run=0
        bundle = CoachEvidenceBundle(
            honesty=HonestyVerification(verified=True),
            gathering_status="complete",
            tests={"tests_run": 0, "tests_passed": True, "tests_failed": 0},
            task_type="feature",
            profile_name="feature",
        )

        prompt = _build_invoker(worktree)._build_coach_prompt(
            task_id="TASK-ZCG-001",
            turn=1,
            requirements="zero-cardinality tests scenario",
            player_report={"files_modified": []},
            evidence_bundle=bundle,
        )

        assert "ZERO-CARDINALITY TEST GUARD" in prompt
        assert "tests_run == 0" in prompt


# ---------------------------------------------------------------------------
# AC-017: Pattern 3 state-bridge move regression
# ---------------------------------------------------------------------------


class TestStateBridgeMoveRegression:
    """The TASK-FIX-1B4A Layer-1 / TASK-FIX-1B4C Layer-3' protections must
    remain operative under the new primary path. Pattern 3 reproducer:
    Player report carries a pre-move task path, the file exists on disk
    only at the canonical (post-move) location, ``CoachVerifier``
    consults ``state_bridge.canonical_path_for`` and suppresses the
    discrepancy. Bundle.honesty.resolved_paths records the suppression
    and the prompt's Guard #4 instructs the LLM Coach on how to
    interpret it.
    """

    @pytest.fixture
    def worktree_with_state_bridge_move(self, tmp_path: Path) -> Path:
        _init_git_worktree(tmp_path)
        (tmp_path / "tasks" / "design_approved").mkdir(
            parents=True, exist_ok=True
        )
        canonical = (
            tmp_path / "tasks" / "design_approved" / "TASK-PATTERN3-foo.md"
        )
        canonical.write_text(
            "---\nid: TASK-PATTERN3\nstatus: design_approved\n---\n"
        )
        _write_results(tmp_path, "TASK-PATTERN3", {
            "task_id": "TASK-PATTERN3",
            "quality_gates": {
                "all_passed": True,
                "tests_run": 5,
                "tests_failed": 0,
                "coverage_met": True,
            },
            "code_review": {"score": 80},
            "plan_audit": {
                "status": "passed", "violations": 0, "severity": "low",
            },
            # Ghost path: Player report claims the PRE-MOVE location
            "files_modified": ["tasks/backlog/TASK-PATTERN3-foo.md"],
            "files_created": [],
            "tests_written": [],
        })
        return tmp_path

    def test_primary_path_suppresses_discrepancy_via_layer1(
        self, worktree_with_state_bridge_move: Path,
    ) -> None:
        """Under the primary path the bundle's honesty must show the ghost
        path was Layer-1-suppressed (zero discrepancies, non-empty
        resolved_paths)."""
        # Patch _verify_claims_were_staged so the unrelated claim_audit
        # gate doesn't fire on the unstaged ghost path (FEAT-39E1 sibling)
        # — orthogonal to AC-017 which is about Layer-1 resolution.
        with patch.object(CoachVerifier, "_verify_claims_were_staged", return_value=[]):
            validator = CoachValidator(
                str(worktree_with_state_bridge_move),
                task_id="TASK-PATTERN3",
            )
            bundle = validator.gather_evidence(
                task_id="TASK-PATTERN3",
                turn=1,
                task={
                    "acceptance_criteria": ["AC-001"],
                    "task_type": "feature",
                    "description": "state-bridge move pattern",
                },
            )

        assert bundle.honesty.verified is True, (
            "Pattern 3 regression: Layer-1 resolution must suppress the "
            "ghost-path discrepancy entirely on the primary path."
        )
        assert bundle.honesty.discrepancies == []
        assert bundle.honesty.resolved_paths, (
            "resolved_paths must record the audit trail of the suppression."
        )
        resolved = bundle.honesty.resolved_paths[0]
        assert resolved.claimed == "tasks/backlog/TASK-PATTERN3-foo.md"
        assert resolved.resolved_to.endswith(
            "tasks/design_approved/TASK-PATTERN3-foo.md"
        )

    def test_primary_path_prompt_carries_layer1_guard(
        self, worktree_with_state_bridge_move: Path,
    ) -> None:
        """Guard #4 must be in the prompt so the LLM knows how to interpret
        resolved_paths when it sees them."""
        with patch.object(CoachVerifier, "_verify_claims_were_staged", return_value=[]):
            validator = CoachValidator(
                str(worktree_with_state_bridge_move),
                task_id="TASK-PATTERN3",
            )
            bundle = validator.gather_evidence(
                task_id="TASK-PATTERN3",
                turn=1,
                task={
                    "acceptance_criteria": ["AC-001"],
                    "task_type": "feature",
                    "description": "state-bridge move pattern",
                },
            )

        prompt = _build_invoker(worktree_with_state_bridge_move)._build_coach_prompt(
            task_id="TASK-PATTERN3",
            turn=1,
            requirements="state-bridge move pattern",
            player_report={
                "files_modified": ["tasks/backlog/TASK-PATTERN3-foo.md"]
            },
            evidence_bundle=bundle,
        )

        assert "LAYER-1 PATH DEMOTION GUARD" in prompt
        assert "path-string-mismatch-is-not-dishonesty" in prompt
        # The resolved canonical path appears in the JSON honesty section.
        assert "tasks/design_approved/TASK-PATTERN3-foo.md" in prompt

    def test_legacy_path_preserves_layer1_suppression(
        self, worktree_with_state_bridge_move: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC-017: under ``GUARDKIT_COACH_LEGACY=1``, the existing
        TASK-FIX-1B4A wiring in ``validate()`` must continue to suppress
        the ghost path. This proves the legacy revert does NOT regress
        Layer-1.
        """
        monkeypatch.setenv("GUARDKIT_COACH_LEGACY", "1")

        with patch.object(CoachVerifier, "_verify_claims_were_staged", return_value=[]):
            validator = CoachValidator(
                str(worktree_with_state_bridge_move),
                task_id="TASK-PATTERN3",
            )
            # Calling validate() directly exercises the legacy decision path.
            # The honesty short-circuit must NOT fire because the ghost was
            # Layer-1-resolved.
            result = validator.validate(
                task_id="TASK-PATTERN3",
                turn=1,
                task={
                    "acceptance_criteria": ["AC-001 trivial"],
                    "task_type": "feature",
                    "description": "state-bridge move pattern",
                },
            )

        # The honesty_verification on the legacy result must show the
        # suppression — resolved_paths populated, no critical discrepancy.
        assert result.honesty_verification is not None
        assert result.honesty_verification.resolved_paths
        assert all(
            d.claim_type != "file_existence"
            for d in result.honesty_verification.discrepancies
        ), (
            "AC-017 regression under legacy path: the Layer-1 resolution "
            "must continue to suppress file_existence discrepancies "
            "produced by state-bridge moves."
        )


# ---------------------------------------------------------------------------
# Drift protection — guard sentences are tied to .claude/rules citations
# ---------------------------------------------------------------------------


class TestGuardCitationDrift:
    """The five guard sentences cite specific .claude/rules files. Drift in
    the citations breaks the operator's ability to trace the prompt back to
    the seeded rules — flag any rename or removal."""

    @pytest.fixture
    def populated_bundle(self) -> CoachEvidenceBundle:
        return CoachEvidenceBundle(
            honesty=HonestyVerification(verified=True),
            gathering_status="complete",
            tests={"tests_run": 5, "tests_passed": True},
            bdd={"scenarios_attempted": 3, "scenarios_failed": 0},
            task_type="feature",
            profile_name="feature",
        )

    def test_absence_of_failure_rule_cited(
        self, populated_bundle: CoachEvidenceBundle, tmp_path: Path,
    ) -> None:
        prompt = _build_invoker(tmp_path)._build_coach_prompt(
            task_id="TASK-DRIFT",
            turn=1,
            requirements="x",
            player_report={"files_modified": []},
            evidence_bundle=populated_bundle,
        )
        assert "absence-of-failure-is-not-success.md" in prompt

    def test_path_string_rule_cited(
        self, populated_bundle: CoachEvidenceBundle, tmp_path: Path,
    ) -> None:
        prompt = _build_invoker(tmp_path)._build_coach_prompt(
            task_id="TASK-DRIFT",
            turn=1,
            requirements="x",
            player_report={"files_modified": []},
            evidence_bundle=populated_bundle,
        )
        assert "path-string-mismatch-is-not-dishonesty" in prompt
