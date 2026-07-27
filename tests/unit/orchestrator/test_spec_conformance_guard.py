"""Unit tests for the FEAT-SCG (SCG-002) spec-conformance evidence leg + guard.

Modelled on ``tests/unit/orchestrator/test_runtime_parity.py``. Covers:

1. ``AutoBuildOrchestrator._produce_spec_conformance_leg`` — the leg produced
   beside ``gather_evidence``: absent (``None``) when no snapshot exists (no
   executor activity), a ``{status, failures}`` dict when a snapshot does.
2. ``AgentInvoker._apply_spec_conformance_guard`` — the deterministic backstop:
   flips ``approve`` -> ``feedback`` on a failed leg with one ``must_fix`` issue
   per failed rule (rule id + detail verbatim); no-op on absent / passed legs;
   never touches a ``feedback`` verdict; runs the opt-in ``ac_paths`` presence
   check over the threaded structured ACs.
3. The BYTE-EQUIVALENCE proof — with NO ``conformance`` block, no leg activity
   and no decision mutation (existing builds are unchanged).

Coverage Target: >=85%
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle
from guardkit.orchestrator.quality_gates.spec_conformance import (
    ConformanceBlock,
    TokenCoverageRule,
    snapshot_paths,
)


TASK_ID = "TASK-SCG-001"


# ============================================================================
# Helpers
# ============================================================================


def _bundle(spec_conformance):
    return (
        CoachEvidenceBundle(honesty=None, spec_conformance=spec_conformance)
        if spec_conformance is not None
        else CoachEvidenceBundle(honesty=None)
    )


def _guard(
    decision: dict,
    spec_conformance,
    tmp_path,
    *,
    acceptance_criteria=None,
    worktree=None,
) -> dict:
    """Invoke the guard against a fresh, un-__init__'d AgentInvoker."""
    inv = AgentInvoker.__new__(AgentInvoker)
    if worktree is not None:
        inv.worktree_path = worktree
    bundle = _bundle(spec_conformance)
    coach_path = tmp_path / "coach_turn_1.json"
    coach_path.write_text(json.dumps(decision))
    inv._apply_spec_conformance_guard(
        decision=decision,
        evidence_bundle=bundle,
        task_id=TASK_ID,
        turn=1,
        coach_output_path=coach_path,
        acceptance_criteria=acceptance_criteria,
    )
    return decision


def _write_snapshot(tmp_path: Path, block: ConformanceBlock) -> None:
    """Write a conformance snapshot (block only; byte_parity authorities N/A)."""
    paths = snapshot_paths(TASK_ID, tmp_path)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    paths["block"].write_text(
        json.dumps(block.model_dump(mode="json"), indent=2), encoding="utf-8"
    )


_FAILED_LEG = {
    "status": "failed",
    "failures": [
        {
            "rule_id": "R-1",
            "kind": "byte_parity",
            "detail": "src/foo.py does not byte-match the captured authority.",
        }
    ],
}


# ============================================================================
# 1. AutoBuildOrchestrator._produce_spec_conformance_leg
# ============================================================================


def _orch():
    return AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)


def test_leg_absent_when_no_snapshot_no_executor_activity(tmp_path):
    """No snapshot ⇒ None (leg absent), and the executor is never invoked."""
    with patch(
        "guardkit.orchestrator.quality_gates.spec_conformance."
        "evaluate_from_snapshot"
    ) as ev:
        result = _orch()._produce_spec_conformance_leg(
            TASK_ID, 1, SimpleNamespace(path=tmp_path)
        )
    assert result is None
    ev.assert_not_called()


def test_leg_reports_failed_rule_from_snapshot(tmp_path):
    """A token_coverage rule whose required token is absent yields a failed leg."""
    block = ConformanceBlock(
        ac_paths=False,
        rules=[
            TokenCoverageRule(
                id="R-2",
                type="token_coverage",
                paths=["src/*.py"],
                require_tokens=["REQUIRED_MARKER"],
            )
        ],
    )
    _write_snapshot(tmp_path, block)
    # No src file exists ⇒ the required token is absent ⇒ failed.
    result = _orch()._produce_spec_conformance_leg(
        TASK_ID, 1, SimpleNamespace(path=tmp_path)
    )
    assert result is not None
    assert result["status"] == "failed"
    assert result["failures"][0]["rule_id"] == "R-2"
    assert result["failures"][0]["kind"] == "token_coverage"


def test_leg_reports_passed_when_rule_satisfied(tmp_path):
    """The same rule passes once the required token is present in the worktree."""
    block = ConformanceBlock(
        ac_paths=False,
        rules=[
            TokenCoverageRule(
                id="R-2",
                type="token_coverage",
                paths=["src/*.py"],
                require_tokens=["REQUIRED_MARKER"],
            )
        ],
    )
    _write_snapshot(tmp_path, block)
    src = tmp_path / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "foo.py").write_text("REQUIRED_MARKER = 1\n")
    result = _orch()._produce_spec_conformance_leg(
        TASK_ID, 1, SimpleNamespace(path=tmp_path)
    )
    assert result["status"] == "passed"
    assert result["failures"] == []


def test_leg_never_raises_on_error(tmp_path):
    """Any executor error degrades to None (the leg must never block a turn)."""
    _write_snapshot(tmp_path, ConformanceBlock(ac_paths=False, rules=[]))
    with patch(
        "guardkit.orchestrator.quality_gates.spec_conformance."
        "evaluate_from_snapshot",
        side_effect=RuntimeError("boom"),
    ):
        result = _orch()._produce_spec_conformance_leg(
            TASK_ID, 1, SimpleNamespace(path=tmp_path)
        )
    assert result is None


# ============================================================================
# 2. AgentInvoker._apply_spec_conformance_guard — leg-driven overrides
# ============================================================================


def test_guard_overrides_approve_when_leg_failed(tmp_path):
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    out = _guard(decision, _FAILED_LEG, tmp_path)
    assert out["decision"] == "feedback"
    assert out["issues"][0]["category"] == "spec_conformance_failure"
    assert out["issues"][0]["severity"] == "must_fix"
    # Re-persisted to disk (deterministic-verdict-override-must-persist).
    persisted = json.loads((tmp_path / "coach_turn_1.json").read_text())
    assert persisted["decision"] == "feedback"


def test_guard_issue_carries_rule_id_and_detail_verbatim(tmp_path):
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    out = _guard(decision, _FAILED_LEG, tmp_path)
    issue = out["issues"][0]
    assert "R-1" in issue["description"]
    assert (
        "src/foo.py does not byte-match the captured authority."
        in issue["description"]
    )
    # Structured details preserve the raw fields for downstream consumers.
    assert issue["details"]["rule_id"] == "R-1"
    assert issue["details"]["kind"] == "byte_parity"
    assert (
        issue["details"]["detail"]
        == "src/foo.py does not byte-match the captured authority."
    )
    assert issue["details"]["overridden_decision"] == "approve"


def test_guard_prepends_one_issue_per_failed_rule(tmp_path):
    leg = {
        "status": "failed",
        "failures": [
            {"rule_id": "R-1", "kind": "byte_parity", "detail": "d1"},
            {"rule_id": "R-2", "kind": "token_coverage", "detail": "d2"},
            {"rule_id": "R-3", "kind": "assert_command", "detail": "d3"},
        ],
    }
    decision = {
        "decision": "approve",
        "issues": [{"pre": "existing"}],
        "rationale": "lgtm",
    }
    out = _guard(decision, leg, tmp_path)
    assert out["decision"] == "feedback"
    # Three prepended issues, one per failed rule, ahead of the pre-existing one.
    assert len(out["issues"]) == 4
    ids = [i["details"]["rule_id"] for i in out["issues"][:3]]
    assert ids == ["R-1", "R-2", "R-3"]
    assert out["issues"][3] == {"pre": "existing"}
    for i in out["issues"][:3]:
        assert i["category"] == "spec_conformance_failure"
        assert i["severity"] == "must_fix"
    assert "R-1, R-2, R-3" in out["rationale"]


def test_guard_noop_when_leg_passed(tmp_path):
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    out = _guard(decision, {"status": "passed", "failures": []}, tmp_path)
    assert out["decision"] == "approve"
    assert out["rationale"] == "lgtm"


def test_guard_noop_when_leg_absent(tmp_path):
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    out = _guard(decision, {"status": "absent", "failures": []}, tmp_path)
    assert out["decision"] == "approve"


def test_guard_noop_when_spec_conformance_none(tmp_path):
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    out = _guard(decision, None, tmp_path)
    assert out["decision"] == "approve"


def test_guard_leaves_feedback_verdict_untouched(tmp_path):
    """A pre-existing feedback verdict is not modified (only approve is flipped)."""
    decision = {
        "decision": "feedback",
        "issues": [{"x": 1}],
        "rationale": "already feedback",
    }
    out = _guard(decision, _FAILED_LEG, tmp_path)
    assert out["decision"] == "feedback"
    assert out["rationale"] == "already feedback"
    assert out["issues"] == [{"x": 1}]
    # A feedback verdict is never re-persisted by this guard.
    persisted = json.loads((tmp_path / "coach_turn_1.json").read_text())
    assert persisted["rationale"] == "already feedback"


def test_guard_extract_feedback_delivers_detail_to_player(tmp_path):
    """The must_fix detail reaches the Player via _extract_feedback (prepended,
    so it survives the issues[:3] truncation)."""
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    out = _guard(decision, _FAILED_LEG, tmp_path)
    orch = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
    feedback = orch._extract_feedback(out)
    assert "R-1" in feedback
    assert "does not byte-match the captured authority" in feedback


# ============================================================================
# 3. The opt-in ac_paths check (threaded structured ACs)
# ============================================================================


def test_ac_paths_fires_when_block_opts_in_and_path_missing(tmp_path):
    _write_snapshot(tmp_path, ConformanceBlock(ac_paths=True, rules=[]))
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    acs = [{"id": "AC-1", "text": "must create src/missing_module.py"}]
    out = _guard(
        decision, None, tmp_path, acceptance_criteria=acs, worktree=tmp_path
    )
    assert out["decision"] == "feedback"
    issue = out["issues"][0]
    assert issue["category"] == "spec_conformance_failure"
    assert issue["details"]["kind"] == "ac_paths"
    assert "src/missing_module.py" in issue["description"]


def test_ac_paths_noop_when_cited_path_present(tmp_path):
    _write_snapshot(tmp_path, ConformanceBlock(ac_paths=True, rules=[]))
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "present.py").write_text("x = 1\n")
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    acs = [{"id": "AC-1", "text": "wire up src/present.py"}]
    out = _guard(
        decision, None, tmp_path, acceptance_criteria=acs, worktree=tmp_path
    )
    assert out["decision"] == "approve"


def test_ac_paths_noop_when_block_opts_out(tmp_path):
    """A block with ac_paths=false never runs the AC presence check."""
    _write_snapshot(tmp_path, ConformanceBlock(ac_paths=False, rules=[]))
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    acs = [{"id": "AC-1", "text": "must create src/missing_module.py"}]
    out = _guard(
        decision, None, tmp_path, acceptance_criteria=acs, worktree=tmp_path
    )
    assert out["decision"] == "approve"


def test_ac_paths_is_stack_agnostic_non_python(tmp_path):
    """The extraction accepts any extension — a missing .kt path fires too."""
    _write_snapshot(tmp_path, ConformanceBlock(ac_paths=True, rules=[]))
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    acs = [{"id": "AC-1", "text": "add app/src/Main.kt with the entry point"}]
    out = _guard(
        decision, None, tmp_path, acceptance_criteria=acs, worktree=tmp_path
    )
    assert out["decision"] == "feedback"
    assert "app/src/Main.kt" in out["issues"][0]["description"]


def test_ac_paths_helper_noop_without_worktree(tmp_path):
    """No worktree_path set on the invoker ⇒ ac_paths degrades to None."""
    inv = AgentInvoker.__new__(AgentInvoker)
    assert (
        inv._spec_conformance_ac_paths_failure(
            TASK_ID, [{"id": "AC-1", "text": "src/x.py"}]
        )
        is None
    )


def test_ac_paths_combines_with_failed_leg(tmp_path):
    """A failed rule leg AND an ac_paths miss both surface as must_fix issues."""
    _write_snapshot(tmp_path, ConformanceBlock(ac_paths=True, rules=[]))
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    acs = [{"id": "AC-1", "text": "create src/missing_module.py"}]
    out = _guard(
        decision, _FAILED_LEG, tmp_path, acceptance_criteria=acs, worktree=tmp_path
    )
    assert out["decision"] == "feedback"
    kinds = {i["details"]["kind"] for i in out["issues"]}
    assert "byte_parity" in kinds
    assert "ac_paths" in kinds


# ============================================================================
# 4. Byte-equivalence: NO conformance block ⇒ no leg activity, no mutation
# ============================================================================


def test_bundle_spec_conformance_defaults_none():
    assert CoachEvidenceBundle(honesty=None).spec_conformance is None


def test_byte_equivalence_no_block_leaves_decision_and_bundle_unchanged(tmp_path):
    """With NO conformance block: the leg is None (no executor call) and the
    guard chain does not mutate the decision — existing builds are unchanged."""
    # (a) Leg production: no snapshot ⇒ None, executor never invoked.
    with patch(
        "guardkit.orchestrator.quality_gates.spec_conformance."
        "evaluate_from_snapshot"
    ) as ev_leg:
        leg = _orch()._produce_spec_conformance_leg(
            TASK_ID, 1, SimpleNamespace(path=tmp_path)
        )
    assert leg is None
    ev_leg.assert_not_called()

    # (b) Guard: a bundle with spec_conformance=None and real ACs present but
    #     no snapshot ⇒ ac_paths executor is never invoked, decision unchanged.
    decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
    original = json.loads(json.dumps(decision))
    with patch(
        "guardkit.orchestrator.quality_gates.spec_conformance.evaluate_ac_paths"
    ) as ev_ac:
        out = _guard(
            decision,
            None,
            tmp_path,
            acceptance_criteria=[{"id": "AC-1", "text": "src/x.py present"}],
            worktree=tmp_path,
        )
    ev_ac.assert_not_called()
    assert out == original
