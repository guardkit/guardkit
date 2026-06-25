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
class RuntimeParityResult:
    """Outcome of the per-task Coach runtime-parity check (TASK-AB-COACHRUNPARITY01, arm b).

    The per-task Coach runs the feature's declared smoke command — the
    deliverable's REAL runtime entry point — before approving, so a "passes
    pytest but does not run" deliverable is caught pre-approval rather than
    only by the post-wave smoke gate. Honours
    ``absence-of-failure-is-not-success.md``: a ran-and-FAILED result blocks
    approval; an ABSENT result (``ran=False`` — no command, parallel wave, or
    runner error) never blocks and never counts as a pass.

    Attributes
    ----------
    ran : bool
        ``True`` only when the smoke command actually executed and produced an
        exit code. ``False`` for every skip/absent case (``skipped_reason`` set).
    passed : bool
        ``True`` when ``ran`` and the observed exit code equals ``expected_exit``.
        Always ``False`` when ``ran`` is ``False`` (absent != pass).
    command : str
        The smoke command that was (or would have been) run.
    exit_code : Optional[int]
        Observed exit code; ``None`` when the command did not run (or timed out).
    expected_exit : int
        The exit code that counts as success (the feature's configured value).
    timed_out : bool
        ``True`` when the command exceeded its timeout before completing.
    stderr_tail : str
        Last lines of captured stderr (for Player-facing feedback). Empty when
        ``ran`` is ``False``.
    skipped_reason : Optional[str]
        Why the check did not run (``"no_smoke_command"``, ``"parallel_wave"``,
        ``"runner_error: ..."``). ``None`` when the check ran.
    """

    ran: bool
    passed: bool
    command: str
    exit_code: Optional[int] = None
    expected_exit: int = 0
    timed_out: bool = False
    stderr_tail: str = ""
    skipped_reason: Optional[str] = None


@dataclass
class IndependentTestClassification:
    """Substrate-vs-code classification of a ran-and-failed independent test run.

    TASK-ABFIX-012. Computed by ``CoachValidator.gather_evidence`` ONLY when the
    Coach's own independent test run RAN and FAILED (``tests_passed is False`` AND
    ``signal_absent is False``) — never for a passing run and never for an ABSENT
    signal (an absent signal must never manufacture a code verdict;
    ``absence-of-failure-is-not-success.md``). ``None`` on the bundle otherwise.

    A ``failure_class == "code"`` result for a TESTING task deterministically
    blocks the turn via
    ``AgentInvoker._apply_independent_test_code_failure_guard`` — the deterministic
    backstop the LLM Coach lacked when it false-approved FEAT-FMDR-004 (a 5/9-red
    TESTING task whose real code bugs were reasoned away as "substrate, absent").

    Attributes
    ----------
    failure_class : str
        One of ``"code"`` / ``"infrastructure"`` / ``"parallel_contention"`` /
        ``"collection_error"`` / ``"sdk_api_error"`` (see
        ``CoachValidator._classify_test_failure``). Only ``"code"`` blocks; a
        substrate gap classifies ``"infrastructure"`` and genuine cross-task
        contention classifies ``"parallel_contention"`` — neither reaches the
        blocking guard, preserving the parallel-contention amnesty for non-code
        failures.
    confidence : str
        ``"high"`` / ``"ambiguous"`` / ``"n/a"``. The guard blocks on any
        confidence (a single-wave failure with no recognised exception token is
        still ``("code", "n/a")`` and IS a real failure for a TESTING task).
    raw_output_excerpt : str
        Last 500 chars of the independent-test raw output, for the Player-facing
        feedback. Bounded so ``coach_turn_N.json`` stays small.
    """

    failure_class: str
    confidence: str
    raw_output_excerpt: str = ""


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
    independent_test_classification
        ``IndependentTestClassification`` (TASK-ABFIX-012) — substrate-vs-code
        verdict for a RAN-AND-FAILED independent test run. Populated only when
        ``independent_tests`` ran and failed (``tests_passed`` False AND
        ``signal_absent`` False); ``None`` for passing / absent / skipped runs.
        A ``("code", ...)`` result for a TESTING task deterministically blocks
        the turn via ``AgentInvoker._apply_independent_test_code_failure_guard``.
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
    # TASK-ABFIX-012: substrate-vs-code classification of a ran-and-failed
    # independent test run. Populated by gather_evidence ONLY when independent
    # tests RAN and FAILED (tests_passed False AND signal_absent False). A
    # ("code", ...) result for a TESTING task deterministically blocks via
    # AgentInvoker._apply_independent_test_code_failure_guard. ``None`` for
    # passing / absent / skipped runs — an absent signal never manufactures a
    # code verdict (absence-of-failure-is-not-success). Serialised automatically
    # by ``to_dict``/``asdict`` (it is a dataclass), so the verdict reaches
    # coach_turn_N.json with no to_dict change (the ABFIX-010 serialization
    # invariant).
    independent_test_classification: Optional["IndependentTestClassification"] = None
    requirements: Optional[Any] = None  # RequirementsValidation; avoid circular import

    # TASK-AB-COACHRUNPARITY01 (arm b): per-task runtime-parity check. The
    # Coach runs the deliverable's declared runtime entry point (the feature
    # smoke command) before approving, on single-task waves only. ``None`` when
    # no check was attempted (no smoke command threaded / older callers).
    # ``ran=False`` records an attempted-but-skipped check (parallel wave /
    # runner error). A ``ran=True, passed=False`` result deterministically
    # blocks the turn via ``AgentInvoker._apply_runtime_parity_guard``.
    runtime_parity: Optional["RuntimeParityResult"] = None

    # TASK-AB-XREPOEV01 (AC-002): Coach's independent test runs in declared
    # sibling repos (``evidence_repos``). Each entry is an
    # ``EvidenceTestResult.to_dict()``. Empty when no sibling repos are
    # declared. These results reach ``coach_turn_N.json`` (this bundle is
    # serialised verbatim) and the Coach prompt, and a ran-and-failed suite
    # deterministically blocks the turn in the orchestrator.
    evidence_repo_tests: List[Dict[str, Any]] = field(default_factory=list)

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
