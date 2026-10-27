"""CoachEvidenceBundle — the project's own check results for one Coach turn.

Produced by ``CoachValidator.gather_evidence(...)`` and consumed by
``AgentInvoker.invoke_coach(...)``, which renders it into the reviewer's prompt
and reads it for the only things that send a turn back (27 October 2026): the
project's required tests ran and failed, the declared smoke command ran and
failed, the declared behavioural check ran and failed, the secrets check found a
secret. The reviewer's own verdict is advice.

Internal value object, serialised via ``dataclasses.asdict`` + ``json.dumps``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

if TYPE_CHECKING:  # pragma: no cover — annotation-only imports
    # Imported under TYPE_CHECKING to avoid the circular dependency
    # coach_validator.py -> coach_evidence.py -> coach_validator.py.
    from guardkit.orchestrator.quality_gates.coach_validator import (
        IndependentTestResult,
    )


GatheringStatus = Literal["complete", "partial_exception"]
"""``complete``, or ``partial_exception`` when running the project's tests
raised; ``gathering_error`` then names the cause."""


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
    output_tail : Optional[str]
        Combined stdout+stderr tail (stdout first, each stream bounded to its
        last 2000 chars). Additive field (2026-07-04 code review): pytest
        writes its ``FAILED <nodeid>`` short-summary lines to STDOUT, so a
        stderr-only tail hides the failing-test names from
        ``AgentInvoker._apply_runtime_parity_guard``'s evidence extraction —
        the same stdout+stderr join ``feature_orchestrator._build_smoke_feedback``
        already performs post-wave. ``None`` on older records / when the run
        produced no output; consumers fall back to ``stderr_tail``.
    """

    ran: bool
    passed: bool
    command: str
    exit_code: Optional[int] = None
    expected_exit: int = 0
    timed_out: bool = False
    stderr_tail: str = ""
    skipped_reason: Optional[str] = None
    output_tail: Optional[str] = None


@dataclass
class IndependentTestClassification:
    """Substrate-vs-code classification of a ran-and-failed independent test run.

    TASK-ABFIX-012. Computed by ``CoachValidator.gather_evidence`` ONLY when the
    Coach's own independent test run RAN and FAILED (``tests_passed is False`` AND
    ``signal_absent is False``) — never for a passing run and never for an ABSENT
    signal (an absent signal must never manufacture a code verdict;
    ``absence-of-failure-is-not-success.md``). ``None`` on the bundle otherwise.

    Since reliability repair 1 (12 October 2026) the classification exempts
    nothing: ``AgentInvoker._apply_independent_test_code_failure_guard`` blocks
    every ran-and-failed required suite, whatever its class, and the class only
    shapes the feedback words (``quality_gates/required_suite.py``).

    Attributes
    ----------
    failure_class : str
        One of ``"code"`` / ``"infrastructure"`` / ``"parallel_contention"`` /
        ``"collection_error"`` / ``"sdk_api_error"`` (see
        ``CoachValidator._classify_test_failure``). Used for the feedback
        words only; no class exempts a red required suite.
    confidence : str
        ``"high"`` / ``"ambiguous"`` / ``"n/a"``. Recorded, never a reason to
        approve.
    raw_output_excerpt : str
        Last 500 chars of the independent-test raw output, for the Player-facing
        feedback. Bounded so ``coach_turn_N.json`` stays small.
    """

    failure_class: str
    confidence: str
    raw_output_excerpt: str = ""


@dataclass
class CoachEvidenceBundle:
    """The project's own check results for one Coach turn.

    Attributes
    ----------
    gathering_status, gathering_error
        See :data:`GatheringStatus`.
    independent_tests
        ``IndependentTestResult`` from the run of the project's tests. ``None``
        when running them raised.
    independent_test_classification
        What kind of failure a red run looks like; it only shapes the words the
        Player is sent. ``None`` unless the run ran and failed.
    behavioural_oracle
        The declared behavioural check's result (dict), or ``None``.
    runtime_parity
        The feature's declared smoke command's result, or ``None``.
    security_check
        The secrets check's result (dict: ``ran``, ``passed``, ``command``,
        ``exit_code``, ``output_tail``), or ``None`` when the check is not on.
    whole_feature_check
        In a whole-feature repair round only, the project's whole-feature check
        record (``feature_check.whole_feature_check_record``); left out of
        ``to_dict`` otherwise.
    evidence_repo_tests
        Results of the declared sibling repositories' test runs.
    task_type, profile_name
        The resolved task type and its profile name.
    """

    gathering_status: GatheringStatus = "complete"
    gathering_error: Optional[str] = None
    independent_tests: Optional["IndependentTestResult"] = None
    independent_test_classification: Optional["IndependentTestClassification"] = None
    behavioural_oracle: Optional[Dict[str, Any]] = None
    runtime_parity: Optional["RuntimeParityResult"] = None
    security_check: Optional[Dict[str, Any]] = None
    whole_feature_check: Optional[Dict[str, Any]] = None
    evidence_repo_tests: List[Dict[str, Any]] = field(default_factory=list)
    task_type: Optional[str] = None
    profile_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the bundle to a JSON-compatible dict."""
        from dataclasses import asdict

        data = asdict(self)
        # Present only in a whole-feature repair round (see the field).
        if data.get("whole_feature_check") is None:
            data.pop("whole_feature_check", None)
        if data.get("security_check") is None:
            data.pop("security_check", None)
        return data
