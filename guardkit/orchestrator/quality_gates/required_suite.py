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

    A task whose profile requires tests cannot be approved when its
    independent required suite actually ran and failed, unless a verified
    baseline exception covers every failure. Evidence that is unavailable
    stays unavailable; it is never turned into a pass or a fail.

* **Requires tests** is the task type's existing ``tests_required`` profile
  setting (``guardkit/models/task_types.py``), whatever the type.
* **Actually ran and failed** is ``tests_passed is False`` with
  ``signal_absent`` False. ``signal_absent`` and ``check_could_not_run`` (which
  always sets ``signal_absent`` too) are unavailable evidence, owned by their
  own guards, and are left exactly as they are handled today.
* **The baseline exception** is the existing ``CoachValidator._apply_baseline_diff``.
  When it verifies every failure as pre-existing it reports the run as passed,
  so a run still reading ``tests_passed is False`` here is one it did not cover.
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

from guardkit.models.task_types import TaskType, get_profile, normalise_task_type

logger = logging.getLogger(__name__)

# The issue category the primary path has always used for this override. Kept
# so nothing that reads coach_turn_N.json sees a new name; the failure class
# itself is in ``details.failure_class``.
REQUIRED_SUITE_FAILURE_CATEGORY = "independent_test_code_failure"

_ENVIRONMENTAL_CLASSES = frozenset({"infrastructure", "sdk_api_error"})


def tests_required_for(task_type: Optional[str]) -> bool:
    """The task type's ``tests_required`` profile setting.

    ``None`` means the FEATURE profile, as ``CoachValidator._resolve_task_type``
    and ``get_profile`` already treat it; an unknown name falls back to FEATURE
    through ``normalise_task_type``, which logs it.
    """
    if not task_type:
        return get_profile(None).tests_required
    canonical = normalise_task_type(str(task_type).strip().lower())
    return get_profile(TaskType(canonical)).tests_required


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

    Returns ``None`` when the approval may stand: tests are not required for
    this task type, there is no independent run, it passed (or the baseline
    exception verified every failure as pre-existing), or its evidence is
    unavailable. Otherwise returns ``{"rationale": str, "issue": dict}``.
    """
    if not tests_required_for(task_type):
        return None
    if not ran_and_failed(independent_tests):
        return None

    excerpt = (raw_output_excerpt or "").strip()
    if not excerpt:
        excerpt = (getattr(independent_tests, "raw_output", None) or "")[-500:].strip()
    if not excerpt:
        excerpt = (getattr(independent_tests, "test_output_summary", "") or "").strip()
    command = getattr(independent_tests, "test_command", "") or "<unknown>"

    rationale = (
        "Independent test verification FAILED: the Coach's own run of this "
        f"task's required test suite ({command}) ran and reported failures, "
        "and no measured baseline showed every failure to be pre-existing. A "
        "task whose tests are required cannot be approved while that suite is "
        f"red. {_guidance(failure_class)} Independent-test output (tail): "
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


