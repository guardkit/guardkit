"""One acceptance rule for every Coach path: a required suite that ran red blocks.

Factory reliability repairs, 12 October 2026 (repair 1). B463's first task, a
declarative task built in direct mode, was approved with 1 failed / 871 passed
in the Coach's own independent run. The deterministic backstop acted only for
``testing`` tasks, direct-mode tasks have no deterministic Phase 4, a turn
whose Phase 4 is skipped for budget has none either, and the legacy
``validate()`` path approved a code failure in a parallel wave. Each path had
its own slightly different rule, and the gaps between them let a red suite
through.

The rule, the same on every path:

    A task cannot be approved when the tests of a part it changed actually
    ran and failed, whatever its task type (after-task check redesign, 31
    October 2026: the tests that run are the changed parts', so there is no
    task-type exemption and no known-failure baseline). Evidence that is
    unavailable stays unavailable; it is never turned into a pass or a fail.

* **Actually ran and failed** is ``tests_passed is False`` with
  ``signal_absent`` False. ``signal_absent`` and ``check_could_not_run`` (which
  always sets ``signal_absent`` too) are unavailable evidence: a check that
  could not run stops the task instead (``AutoBuildOrchestrator``).
* **The classification exempts nothing.** ``code``, ``infrastructure``,
  ``parallel_contention`` and no classification at all are treated alike: in
  the four-worker trial the classifier labelled missing containers and DNS
  failures ``code``, so its labels cannot be trusted to excuse a failure. It
  only shapes the words the builder is sent.

Both decision paths call this module and persist the overridden decision, not
only the value they return: ``AgentInvoker._apply_independent_test_code_failure_guard``
on the primary path, and ``AutoBuildOrchestrator._invoke_coach_legacy`` on the
legacy path. No retry is added; the existing feedback, stall and timeout limits
bound the turns.
"""

from __future__ import annotations

import logging
from typing import (
    Any,
    Dict,
    Optional,
)

logger = logging.getLogger(__name__)

# The issue category the primary path has always used for this override. Kept
# so nothing that reads coach_turn_N.json sees a new name; the failure class
# itself is in ``details.failure_class``.
REQUIRED_SUITE_FAILURE_CATEGORY = "independent_test_code_failure"

_ENVIRONMENTAL_CLASSES = frozenset({"infrastructure", "sdk_api_error"})


def ran_and_failed(independent_tests: Any) -> bool:
    """``tests_passed is False`` with the signal present: a real red run."""
    if independent_tests is None:
        return False
    if getattr(independent_tests, "tests_passed", True) is not False:
        return False
    # Unavailable evidence (timeout, transport error, a check that could not
    # start) is never read as a failure here; its own guards own it.
    if getattr(independent_tests, "signal_absent", False) is not False:
        return False
    if getattr(independent_tests, "check_could_not_run", False):
        return False
    return True


def _guidance(failure_class: Optional[str]) -> str:
    if failure_class == "code":
        return (
            "The failure is classified as a code defect: fix the code or the "
            "tests that fail."
        )
    if failure_class == "parallel_contention":
        return (
            "The failure looks caused by a concurrent task in this parallel "
            "wave; do not change code for it unless the output below shows a "
            "defect in this task's own work."
        )
    if failure_class == "collection_error":
        # Neutral: a suite that cannot import or collect is as often this
        # task's own change as the environment.
        return (
            "The suite could not import or collect its tests; check whether "
            "this task's changes cause it before treating it as environmental."
        )
    if failure_class in _ENVIRONMENTAL_CLASSES:
        return (
            f"The failure looks environmental (classified '{failure_class}'); "
            "do not change code for it unless the output below shows a defect "
            "in this task's own work."
        )
    return (
        "No failure classification was recorded; read the output below to "
        "see what failed."
    )


def required_suite_override(
    *,
    task_type: Optional[str],
    independent_tests: Any,
    failure_class: Optional[str],
    confidence: Optional[str] = None,
    raw_output_excerpt: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Whether an ``approve`` may stand, and if not, the feedback that replaces it.

    Returns ``None`` when the approval may stand: there is no independent
    run, it passed, or its evidence is unavailable. Otherwise returns
    ``{"rationale": str, "issue": dict}``. ``task_type`` is recorded only.
    """
    if not ran_and_failed(independent_tests):
        return None

    excerpt = (raw_output_excerpt or "").strip()
    if not excerpt:
        excerpt = (getattr(independent_tests, "raw_output", None) or "")[-500:].strip()
    if not excerpt:
        excerpt = (getattr(independent_tests, "test_output_summary", "") or "").strip()
    command = getattr(independent_tests, "test_command", "") or "<unknown>"

    rationale = (
        "Independent test verification FAILED: the Coach's own run of the "
        f"tests of the parts this task changed ({command}) ran and reported "
        "failures. A task cannot be approved while the tests of a part it "
        f"changed fail. {_guidance(failure_class)} Independent-test output "
        "(tail): "
        f"{excerpt or '<empty>'}"
    )
    issue = {
        "severity": "must_fix",
        "category": REQUIRED_SUITE_FAILURE_CATEGORY,
        "description": rationale,
        "details": {
            "failure_class": failure_class,
            "confidence": confidence,
            "task_type": task_type,
            "test_command": command,
            "raw_output_excerpt": excerpt,
            "overridden_decision": "approve",
        },
    }
    return {"rationale": rationale, "issue": issue}


