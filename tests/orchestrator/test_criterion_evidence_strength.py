"""Criterion evidence strength stays honest through the served Coach prompt.

These regressions exercise the real requirement matcher, corroborator, bundle
serializer and prompt builder.  They intentionally stop at the model boundary:
prompt assertions prove what the Coach receives, not what a model will decide.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.coach_verification import HonestyVerification
from guardkit.orchestrator.feature_check import (
    FeatureCheckAttempt,
    FeatureCheckOutcome,
    write_feature_check_receipt,
)
from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle
from guardkit.orchestrator.quality_gates.coach_validator import (
    CLAIMED,
    VERIFIED,
    CoachValidator,
    IndependentTestResult,
)


TASK_ID = "TASK-EVIDENCE"


def _validator(worktree: Path) -> CoachValidator:
    return CoachValidator(str(worktree), task_id=TASK_ID)


def _passing_run() -> IndependentTestResult:
    return IndependentTestResult(
        tests_passed=True,
        test_command="project-check",
        test_output_summary="all project checks passed",
        duration_seconds=0.1,
    )


def _honesty() -> HonestyVerification:
    return HonestyVerification(verified=True)


def _task(*criteria: str) -> Dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "task_type": "feature",
        "acceptance_criteria": list(criteria),
    }


def _invoker(worktree: Path) -> AgentInvoker:
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    return invoker


def _rendered_bundle(prompt: str) -> Dict[str, Any]:
    match = re.search(
        r"<evidence_bundle>\s*(.*?)\s*</evidence_bundle>",
        prompt,
        re.DOTALL,
    )
    assert match is not None
    return json.loads(match.group(1))


def _requirements_in_prompt(
    worktree: Path,
    validation: Any,
    *,
    synthesis: bool,
) -> Dict[str, Any]:
    bundle = CoachEvidenceBundle(
        honesty=_honesty(),
        requirements=validation,
        independent_tests=_passing_run(),
    )
    prompt = _invoker(worktree)._build_coach_prompt(
        task_id=TASK_ID,
        turn=1,
        requirements="Satisfy every acceptance criterion.",
        player_report={"task_id": TASK_ID},
        acceptance_criteria=[
            {"id": row.criterion_id, "text": row.criterion_text}
            for row in validation.criteria_results
        ],
        evidence_bundle=bundle,
        synthesis=synthesis,
    )
    return _rendered_bundle(prompt)["requirements"]


@pytest.mark.parametrize("status", ["complete", "partial"])
@pytest.mark.parametrize("consumer", ["ordinary", "direct"])
@pytest.mark.parametrize(
    "synthesis", [False, True], ids=["tool_using", "toolless"]
)
def test_cross_language_exact_value_departure_remains_a_claim_in_served_prompt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: str,
    consumer: str,
    synthesis: bool,
) -> None:
    """A green generic suite cannot prove a contradictory Rust setting."""
    monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "coachsplit")
    criterion = "AC-PORT: The Rust service binds exactly to port 7401"
    task = _task(criterion)
    player_report = {
        "task_id": TASK_ID,
        "tests_run": True,
        "tests_passed": True,
        "completion_promises": [
            {
                "criterion_id": "AC-PORT",
                "criterion_text": criterion,
                "status": status,
                "evidence": (
                    "The service binds to port 7402; this documented departure "
                    "avoids a conflict."
                ),
            }
        ],
    }
    if consumer == "direct":
        results = json.loads(
            _invoker(tmp_path)._write_direct_mode_results(
                TASK_ID, player_report
            ).read_text(encoding="utf-8")
        )
        assert results["implementation_mode"] == "direct"
    else:
        results = player_report
    validator = _validator(tmp_path)

    validation = validator.validate_requirements(task, results, turn=1)
    corroborated = validator.corroborate_claims(
        validation,
        independent_tests=_passing_run(),
        honesty_verification=_honesty(),
    )

    covered = status == "complete"
    expected_result = CLAIMED if covered else "rejected"
    assert corroborated.criteria_results[0].result == expected_result
    assert corroborated.criteria_met == int(covered)
    assert corroborated.all_criteria_met is covered

    bundle = CoachEvidenceBundle(
        honesty=_honesty(),
        requirements=corroborated,
        independent_tests=_passing_run(),
    )
    serialized = bundle.to_dict()["requirements"]
    assert serialized["criteria_with_claim_coverage"] == int(covered)
    assert serialized["all_criteria_have_claim_coverage"] is covered
    assert "criteria_met" not in serialized
    assert "all_criteria_met" not in serialized

    prompt = _invoker(tmp_path)._build_coach_prompt(
        task_id=TASK_ID,
        turn=1,
        requirements="Build the service described by the criterion.",
        player_report=player_report,
        acceptance_criteria=[{"id": "AC-PORT", "text": criterion}],
        evidence_bundle=bundle,
        synthesis=synthesis,
    )
    prompt_requirements = _rendered_bundle(prompt)["requirements"]
    assert prompt_requirements["criteria_results"][0]["result"] == expected_result
    assert prompt_requirements["all_criteria_have_claim_coverage"] is covered
    assert "Claim coverage only" in prompt_requirements["aggregate_meaning"]
    assert "documented conflict or departure is not fulfilment" in prompt
    assert "authoritative amended criterion" in prompt

    gather_prompt = _invoker(tmp_path)._build_coach_gather_prompt(
        task_id=TASK_ID,
        turn=1,
        requirements="Build the service described by the criterion.",
        player_report=player_report,
        honesty_verification=_honesty(),
        acceptance_criteria=[{"id": "AC-PORT", "text": criterion}],
        evidence_bundle=bundle,
    )
    assert "documented conflict or departure as unmet" in gather_prompt
    assert "authoritative\n  amended criterion" in gather_prompt


@pytest.mark.parametrize("classification", ["absent", "malformed", "operator"])
def test_pass_bar_classification_never_lets_generic_facts_promote_claims(
    tmp_path: Path,
    classification: str,
) -> None:
    qa = tmp_path / "qa"
    if classification != "absent":
        qa.mkdir()
        pass_bar = qa / f"pass-bar-{TASK_ID}.yaml"
        if classification == "malformed":
            pass_bar.write_text("criteria: [", encoding="utf-8")
        else:
            pass_bar.write_text(
                f'''format_version: "2.0"
task_id: {TASK_ID}
registered_at: {{sha: abcd, date: "2026-10-23"}}
auth_surface_bearing: false
preconditions: [suite_green_vs_ledger]
criteria:
  - id: AC-PORT
    text: operator confirms the service port
    class: operator
    evidence_kind: operator_signoff
    runbook_ref: docs/runbook.md
negative_paths: [dependency_down_degradation]
''',
                encoding="utf-8",
            )

    criterion = "AC-PORT: The service listens on port 7401"
    validation = _validator(tmp_path).validate_requirements(
        _task(criterion),
        {
            "task_id": TASK_ID,
            "completion_promises": [
                {
                    "criterion_id": "AC-PORT",
                    "status": "complete",
                    "evidence": "Player says the port is configured",
                }
            ],
        },
        turn=1,
    )
    corroborated = _validator(tmp_path).corroborate_claims(
        validation,
        independent_tests=_passing_run(),
        honesty_verification=_honesty(),
    )
    assert corroborated.criteria_results[0].result == CLAIMED
    assert _requirements_in_prompt(
        tmp_path, corroborated, synthesis=False
    )["criteria_results"][0]["result"] == CLAIMED


@pytest.mark.parametrize(
    ("synthetic", "reported", "match_kind"),
    [
        (False, "The worker records an immutable audit entry", "Matched in"),
        (
            True,
            "The worker records an immutable audit entry and timestamp",
            "Substring match",
        ),
        (
            False,
            "immutable audit entry worker records",
            "Keyword overlap match",
        ),
    ],
)
def test_no_promise_text_matches_are_claims_for_normal_and_synthetic_reports(
    tmp_path: Path,
    synthetic: bool,
    reported: str,
    match_kind: str,
) -> None:
    criterion = "The worker records an immutable audit entry"
    results = {
        "task_id": TASK_ID,
        "_synthetic": synthetic,
        "requirements_addressed": [reported],
    }
    validation = _validator(tmp_path).validate_requirements(
        _task(criterion), results, turn=1
    )
    assert validation.criteria_results[0].result == CLAIMED
    assert match_kind in validation.criteria_results[0].evidence
    assert validation.criteria_met == 1
    assert validation.all_criteria_met is True
    corroborated = _validator(tmp_path).corroborate_claims(
        validation,
        independent_tests=_passing_run(),
        honesty_verification=_honesty(),
    )
    for synthesis in (False, True):
        requirements = _requirements_in_prompt(
            tmp_path, corroborated, synthesis=synthesis
        )
        assert requirements["criteria_results"][0]["result"] == CLAIMED
        assert requirements["all_criteria_have_claim_coverage"] is True


def test_hybrid_fallback_keeps_claim_coverage_and_refusals(tmp_path: Path) -> None:
    criteria = [
        "AC-ONE: The CLI prints a stable identifier",
        "AC-TWO: The CLI stores an audit record",
    ]
    validator = _validator(tmp_path)
    validation = validator.validate_requirements(
        _task(*criteria),
        {
            "task_id": TASK_ID,
            "completion_promises": [
                {
                    "criterion_id": "AC-ONE",
                    "status": "complete",
                    "evidence": "Implemented stable output",
                }
            ],
            "requirements_addressed": [criteria[1]],
        },
        turn=1,
    )
    assert [row.result for row in validation.criteria_results] == [CLAIMED, CLAIMED]
    assert validation.criteria_met == 2
    assert validation.all_criteria_met is True
    corroborated = validator.corroborate_claims(
        validation,
        independent_tests=_passing_run(),
        honesty_verification=_honesty(),
    )
    for synthesis in (False, True):
        requirements = _requirements_in_prompt(
            tmp_path, corroborated, synthesis=synthesis
        )
        assert [
            row["result"] for row in requirements["criteria_results"]
        ] == [CLAIMED, CLAIMED]
        assert requirements["criteria_with_claim_coverage"] == 2

    incomplete = validator.validate_requirements(
        _task(criteria[1]),
        {
            "task_id": TASK_ID,
            "completion_promises": [
                {"criterion_id": "AC-TWO", "status": "incomplete"}
            ],
            "requirements_addressed": [criteria[1]],
        },
        turn=1,
    )
    assert incomplete.criteria_results[0].result == "rejected"

    path_criterion = "AC-FILE: Create config/runtime.toml with safe defaults"
    missing_path = validator.validate_requirements(
        _task(path_criterion),
        {
            "task_id": TASK_ID,
            "completion_promises": [
                {"criterion_id": "AC-OTHER", "status": "complete"}
            ],
            "requirements_addressed": [path_criterion],
        },
        turn=1,
    )
    assert missing_path.criteria_results[0].result == "rejected"
    assert missing_path.all_criteria_met is False


def test_criterion_bound_gate_can_still_verify_a_claim(tmp_path: Path) -> None:
    criterion = "AC-PORT: The service listens on port 7401"
    validator = _validator(tmp_path)
    validation = validator.validate_requirements(
        _task(criterion),
        {
            "task_id": TASK_ID,
            "completion_promises": [
                {"criterion_id": "AC-PORT", "status": "complete"}
            ],
        },
        turn=1,
    )
    corroborated = validator.corroborate_claims(
        validation,
        independent_tests=_passing_run(),
        honesty_verification=_honesty(),
        gate_verified_ids={"AC-PORT"},
    )
    assert corroborated.criteria_results[0].result == VERIFIED
    assert "criterion-bound" not in corroborated.criteria_results[0].evidence
    assert "bound gate result" in corroborated.criteria_results[0].evidence
    assert _requirements_in_prompt(
        tmp_path, corroborated, synthesis=True
    )["criteria_results"][0]["result"] == VERIFIED


@pytest.mark.parametrize(
    "receipt",
    [
        pytest.param({"criteria_covered": ["AC-PORT"]}, id="absent"),
        pytest.param(
            {"status": "", "criteria_covered": ["AC-PORT"]},
            id="empty",
        ),
        pytest.param(
            {"status": {"unexpected": True}, "criteria_covered": ["AC-PORT"]},
            id="malformed",
        ),
    ],
)
def test_receipt_without_valid_passing_status_cannot_verify_through_prompt(
    tmp_path: Path,
    receipt: Dict[str, Any],
) -> None:
    criterion = "AC-PORT: The service listens on port 7401"
    receipt_path = (
        tmp_path / ".guardkit" / "autobuild-private" / "feature_check.json"
    )
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    validator = _validator(tmp_path)
    validation = validator.validate_requirements(
        _task(criterion),
        {
            "task_id": TASK_ID,
            "completion_promises": [
                {"criterion_id": "AC-PORT", "status": "complete"}
            ],
        },
        turn=1,
    )

    corroborated = validator.corroborate_claims(validation)

    assert corroborated.criteria_results[0].result == CLAIMED
    bundle = CoachEvidenceBundle(
        honesty=_honesty(),
        requirements=corroborated,
    )
    serialized = bundle.to_dict()["requirements"]
    assert serialized["criteria_results"][0]["result"] == CLAIMED
    for synthesis in (False, True):
        prompt_requirements = _requirements_in_prompt(
            tmp_path, corroborated, synthesis=synthesis
        )
        assert prompt_requirements["criteria_results"][0]["result"] == CLAIMED


def test_explicit_passing_receipt_can_verify_through_prompt(tmp_path: Path) -> None:
    criterion = "AC-PORT: The service listens on port 7401"
    write_feature_check_receipt(
        FeatureCheckOutcome(
            feature_id="FEATURE-EVIDENCE",
            status="passed",
            declared=True,
            attempts=[
                FeatureCheckAttempt(
                    attempt=1,
                    command="project-feature-check",
                    candidate_sha="abc123",
                    passed=True,
                    outcome="passed",
                    scenarios_covered=["AC-PORT"],
                )
            ],
        ),
        tmp_path,
    )
    validator = _validator(tmp_path)
    validation = validator.validate_requirements(
        _task(criterion),
        {
            "task_id": TASK_ID,
            "completion_promises": [
                {"criterion_id": "AC-PORT", "status": "complete"}
            ],
        },
        turn=1,
    )

    corroborated = validator.corroborate_claims(validation)

    assert corroborated.criteria_results[0].result == VERIFIED
    assert (
        CoachEvidenceBundle(honesty=_honesty(), requirements=corroborated)
        .to_dict()["requirements"]["criteria_results"][0]["result"]
        == VERIFIED
    )
    for synthesis in (False, True):
        prompt_requirements = _requirements_in_prompt(
            tmp_path, corroborated, synthesis=synthesis
        )
        assert prompt_requirements["criteria_results"][0]["result"] == VERIFIED


def test_served_player_prompt_and_agent_files_forbid_self_waiver(
    tmp_path: Path,
) -> None:
    player_prompt = _invoker(tmp_path)._build_player_prompt(
        task_id=TASK_ID,
        turn=1,
        requirements="Use the exact configured value.",
        feedback=None,
        acceptance_criteria=[
            {"id": "AC-001", "text": "Use the exact configured value"}
        ],
    )
    assert "Only an authoritative amended criterion changes the target" in player_prompt
    assert "do not restore unsafe behaviour" in player_prompt

    for multiplier in (1.0, 2.0):
        ordinary_prompt = AgentInvoker(
            worktree_path=tmp_path,
            timeout_multiplier=multiplier,
        )._build_autobuild_implementation_prompt(
            task_id=TASK_ID,
            requirements="Use the exact configured value.",
        )
        assert "implementation departure does not satisfy" in ordinary_prompt
        assert "authoritative amendment changes the target" in ordinary_prompt
        assert "do not restore unsafe behaviour" in ordinary_prompt

    repo_root = Path(__file__).resolve().parents[2]
    player_definition = (
        repo_root / "installer/core/agents/autobuild-player.md"
    ).read_text(encoding="utf-8")
    coach_definition = (
        repo_root / "installer/core/agents/autobuild-coach.md"
    ).read_text(encoding="utf-8")
    assert "Only an authoritative\namendment" in player_definition
    assert "deliberate departure does not satisfy" in player_definition
    assert "authoritative amendment" in coach_definition
    assert "implementation departure is not" in coach_definition
