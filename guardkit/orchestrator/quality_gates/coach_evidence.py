"""CoachEvidenceBundle — structured evidence supplied by CoachValidator.

TASK-HMIG-008R Part A (Revision 3, operator-approved 2026-05-20). Restores the
LLM Coach as the primary decision-maker per the Block adversarial-cooperation
paper, demoting CoachValidator from primary decision path to evidence supplier.

The bundle is produced by ``CoachValidator.gather_evidence(...)`` and consumed
by ``AgentInvoker.invoke_coach(...)`` which renders it into the Coach prompt
via ``_build_coach_prompt(...)``. Every field corresponds to an intermediate
value that the legacy ``CoachValidator.validate()`` method previously consumed
internally to reach approve/feedback decisions. Under the new architecture
those intermediates become read-only evidence the LLM Coach reasons about.

Design rules (see ``.claude/rules/patterns/dataclasses.md``):

* Internal value object — no external API boundary, no field-level validation
  constraints, serialised via ``dataclasses.asdict`` + ``json.dumps``.
* All evidence fields are ``Optional[...]`` so the bundle can be returned even
  when one of the gathering stages aborted early.
* ``gathering_status`` disambiguates "field is None because gathering aborted"
  from "field is None because no signal was reported". The absence-of-failure
  guards in the Coach prompt (TASK-HMIG-008R §4) instruct the Coach to treat
  any ``None`` field as ABSENT SIGNAL when ``gathering_status != "complete"``.

Cross-references:

* ``.claude/rules/absence-of-failure-is-not-success.md`` — the structural
  rule the LLM-layer guards mirror. Pair-with-attempted-count semantics map
  directly onto the bundle's ``bdd.scenarios_attempted`` / ``tests.tests_run``
  fields.
* ``.claude/rules/path-string-mismatch-is-not-dishonesty.md`` — Layer-1
  identity resolution lives in ``honesty.resolved_paths``; Layer-2 demotion
  hint surfaces in ``severity_recommendations``.
* TASK-REV-HMIG §14.9 (the architectural correction).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

if TYPE_CHECKING:  # pragma: no cover — annotation-only imports
    # Imported under TYPE_CHECKING to avoid the circular dependency
    # coach_validator.py -> coach_evidence.py -> coach_validator.py.
    # Runtime values are duck-typed; the annotations document intent.
    from guardkit.orchestrator.coach_verification import HonestyVerification
    from guardkit.orchestrator.quality_gates.coach_validator import (
        IndependentTestResult,
        QualityGateStatus,
    )


GatheringStatus = Literal[
    "complete",
    "partial_honesty_abort",
    "partial_gate_abort",
    "partial_exception",
]
"""Status of the evidence-gathering pipeline.

* ``complete`` — all gathering stages ran successfully and populated their fields.
* ``partial_honesty_abort`` — honesty verification produced ``must_fix``
  discrepancies; downstream gathering (gates, independent tests, requirements)
  was skipped because the legacy decision tree would have short-circuited here.
  Fields downstream of honesty are ``None``.
* ``partial_gate_abort`` — quality gates failed; downstream gathering
  (independent tests, requirements) was skipped. ``quality_gates`` is populated;
  ``independent_tests`` and ``requirements_*`` fields are ``None``.
* ``partial_exception`` — pre-evidence error (invalid task type, missing
  task_work_results, or unexpected exception in a gathering helper). Inspect
  ``gathering_error`` for the cause.
"""


@dataclass
class CoachEvidenceBundle:
    """Structured evidence gathered by CoachValidator for the LLM Coach.

    Each field maps to an intermediate value the legacy ``validate()`` method
    consumed internally. Under TASK-HMIG-008R the LLM Coach reads this bundle
    (rendered as JSON into the Coach prompt) plus the honesty result and makes
    the final approve/feedback decision.

    Attributes
    ----------
    honesty
        ``HonestyVerification`` from ``CoachVerifier``. Carries
        ``resolved_paths`` (Layer 1 / TASK-FIX-1B4A) and ``should_fix_count``
        (Layer 2 demotion / TASK-FIX-1B4B). Populated on every non-pre-evidence
        gather path. The Coach reads this field unconditionally.
    gathering_status
        Pipeline status; see :data:`GatheringStatus` for the meaning of each
        value. Used by the Coach to decide whether ``None`` evidence fields
        mean ABSENT SIGNAL (status != "complete") or NO SIGNAL REPORTED
        (status == "complete").
    gathering_error
        Optional human-readable description of what went wrong when
        ``gathering_status == "partial_exception"``. ``None`` on every other
        status. Surfaced verbatim in the synthetic feedback rationale when the
        primary ``_invoke_coach`` path catches an exception around evidence
        gathering.
    quality_gates
        ``QualityGateStatus`` aggregate (tests / coverage / arch_review /
        plan_audit). ``None`` when gathering aborted before the gates ran or
        when the task type opts out of all gates.
    coverage_details
        Raw coverage dict slice from ``task_work_results['test_results']``
        (line_coverage, branch_coverage, files_below_threshold). ``None`` when
        coverage was not reported.
    plan_audit
        Plan-audit findings dict from ``task_work_results['plan_audit']``.
        ``None`` when the producer wrote no plan_audit block (e.g.
        ``--implement-only`` without a saved plan).
    bdd
        Raw ``task_work_results['bdd_results']`` dict (scenarios_attempted,
        scenarios_failed, scenarios_passed, scenarios_pending, failures,
        pending, feature_files). ``None`` when no BDD oracle ran. The Coach
        applies the Pattern-2 absence-of-failure guard against
        ``bdd['scenarios_attempted']``.
    arch_review
        Architectural review dict slice (``{"score": int, ...}``). ``None``
        when no Phase 2.5B output was produced.
    tests
        Aggregate test result dict (tests_passed / tests_run /
        line_coverage_met / branch_coverage_met / requires_infrastructure).
        ``None`` when no test_results block was produced. The Coach applies
        the absence-of-failure guard against ``tests['tests_run']``.
    independent_tests
        ``IndependentTestResult`` from Coach's own pytest pass. ``None`` when
        gathering aborted before independent tests or when the task type's
        profile opts out of independent verification.
    requirements
        ``RequirementsValidation`` from ``validate_requirements``. ``None``
        when gathering aborted before requirements validation.
    severity_recommendations
        Structured hints derived from ``_honesty_issues_from`` demotion logic
        (Layer 2). Each hint is ``{"recommendation": str, "rule": str}``. The
        Coach reads these to know when to demote ``file_existence``
        discrepancies from ``must_fix`` to ``should_fix``.
    task_type
        Resolved task type string (e.g. ``"feature"``, ``"refactor"``,
        ``"scaffolding"``). ``None`` when task type could not be resolved
        (``partial_exception`` with invalid_task_type cause).
    profile_name
        Quality-gate profile name string. ``None`` on the same paths as
        ``task_type``.
    advisory_issues
        Non-blocking issues that ride along with the final decision regardless
        of approve/feedback outcome. Currently sourced from:

        * Agent-invocations advisory (TASK-REV-F6E1 F3c) — process observation,
          ``severity == "warning"``.
        * Layer-2-demoted honesty ``should_fix`` issues — content observation,
          ``severity == "should_fix"``.

        Pre-populated so the LLM Coach can read them without re-computing the
        Layer-2 demotion.
    wiring
        UNWIRED_PATH analysis result (dict) from ``guardkitfactory.wiring``.
        Contains ``status``, ``dialect``, ``language``, ``targets_scanned``,
        ``symbols_examined``, ``findings``, ``degraded_files``. ``None`` when
        the task type gates out (SCAFFOLDING/DOCUMENTATION), there are no
        authored source targets, or the factory is unavailable.
    mocked_seam
        MOCKED_SEAM analysis result (dict). Contains ``status``, ``ran``,
        ``dialect``, ``findings``, ``external_mocks_ignored``. ``None`` when
        the task type gates out, there are no authored acceptance files, or
        the factory is unavailable.
    spec_gap
        SPEC_GAP analysis result (dict). Contains ``status``,
        ``ground_truth_count``, ``executed_count``, ``findings``,
        ``whole_file_deselection``. ``None`` when the task type gates out,
        the factory BDD plugin is unavailable, or Wave-3 wiring is not yet
        implemented.
    """

    honesty: "HonestyVerification"
    gathering_status: GatheringStatus = "complete"
    gathering_error: Optional[str] = None

    quality_gates: Optional["QualityGateStatus"] = None
    coverage_details: Optional[Dict[str, Any]] = None
    plan_audit: Optional[Dict[str, Any]] = None
    bdd: Optional[Dict[str, Any]] = None
    arch_review: Optional[Dict[str, Any]] = None
    tests: Optional[Dict[str, Any]] = None

    # Wave-1 wiring evidence fields (TASK-QAWE-002).
    # Populated by CoachValidator.gather_evidence at the complete-path return.
    # Left None for SCAFFOLDING/DOCUMENTATION tasks, zero-target turns,
    # or when guardkitfactory.wiring is unavailable (ImportError).
    wiring: Optional[Dict[str, Any]] = None         # UNWIRED_PATH analysis
    mocked_seam: Optional[Dict[str, Any]] = None    # MOCKED_SEAM analysis
    spec_gap: Optional[Dict[str, Any]] = None       # SPEC_GAP (Wave-3)

    independent_tests: Optional["IndependentTestResult"] = None
    requirements: Optional[Any] = None  # RequirementsValidation; avoid circular import

    severity_recommendations: List[Dict[str, str]] = field(default_factory=list)
    advisory_issues: List[Dict[str, Any]] = field(default_factory=list)

    task_type: Optional[str] = None
    profile_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the bundle to a JSON-compatible dict.

        Nested ``HonestyVerification`` / ``QualityGateStatus`` /
        ``IndependentTestResult`` / ``RequirementsValidation`` instances are
        also dataclasses, so ``dataclasses.asdict`` walks the entire tree.
        ``ResolvedPath`` / ``Discrepancy`` inside ``HonestyVerification`` are
        also dataclasses — the whole bundle is safe for ``json.dumps``.
        """
        from dataclasses import asdict

        return asdict(self)
