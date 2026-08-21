"""Notices — and records — when an automated build wrote no test files.

PLAIN-LANGUAGE SUMMARY
----------------------
GuardKit builds software in a loop with two halves. A **Player** writes the
code. A **Coach** then reviews what the Player did and decides one of three
things: approve, send feedback, or reject.

There are two Coach implementations in this repository:

* The **legacy** Coach is a set of hard-coded rules
  (``CoachValidator.validate``). One of those rules,
  ``CoachValidator._check_zero_test_anomaly``, refuses to approve a turn in
  which the Player claimed its quality gates passed but wrote no test file.
* The **live** Coach — the default since 2026-05-21 — is a language model.
  The rule-based validator was demoted to gathering evidence for it
  (``CoachValidator.gather_evidence``). On that path the zero-test rule was
  never run, and the model's written instructions never mentioned the case,
  so nothing put the fact in front of it.

This module closes that gap on the live path. It runs **the same rule** —
``_check_zero_test_anomaly``, not a second copy of it — over the same evidence,
puts the answer in front of the language model in plain words, and writes a
durable record every time it fires.

ADVISORY FIRST — deliberate, and the whole point
------------------------------------------------
By default this **reports and blocks nothing**. A turn in which the Player
wrote no tests is still approved if the Coach approves it. Only the record is
written.

That is not timidity, it is the estate's own lesson. Whether a test file was
written is a **fact**, so detecting it deterministically is right. But a hard
rule would also stop changes that legitimately need no test — a documentation
edit, a rename, deleting dead code, a configuration change — and **nobody
knows yet how often that happens**. That number is the whole promotion
decision, and it does not exist. A previous check in this estate was promoted
without being measured first and turned out to raise a false alarm 97% of the
time; it would have stopped real builds roughly thirty times for nothing.

To make a fired check actually stop a turn, set the environment variable::

    GUARDKIT_ZERO_TEST_BLOCKING=1

Accepted values are ``1``, ``true``, ``yes`` and ``on`` (case-insensitive);
anything else, including the variable being absent, means advisory. This
mirrors ``guardkit.orchestrator.boot_smoke_gate.GUARDKIT_BOOT_SMOKE_BLOCKING``
exactly, on purpose — one shape for every advisory-first instrument here.

WHAT "NO TESTS WERE WRITTEN" MEANS — matched to the legacy rule, not reinvented
------------------------------------------------------------------------------
The detection is delegated wholesale to
``CoachValidator._check_zero_test_anomaly``. Everything that rule already
decides, this module inherits without restating:

* A task type whose profile does not require tests never fires.
* A Coach-run independent test suite that genuinely PASSED suppresses the
  anomaly — the zero count was then a bookkeeping error in the Player's
  report, not missing tests.
* A test file named in ``files_created`` that really is on disk is found by
  independent verification, which then does not report ``"skipped"`` — so a
  real test file legitimately suppresses the anomaly, even when the Player
  forgot to list it under ``tests_written``.
* A test file the Player *claims* but never wrote is a different finding
  entirely — a dishonest report. The honesty verifier catches it first and
  evidence gathering stops there, so this check is never reached. That is
  the same order the legacy rule ran in.

WHAT DIFFERS BETWEEN THE TWO PATHS — stated plainly, because it matters
----------------------------------------------------------------------
The *detection* is identical: the same method, the same arguments. What
differs is **how often it is reached**.

The legacy ``validate()`` runs the check as step 5, after the acceptance
criteria have been confirmed met; a turn that fails its acceptance criteria
returns feedback earlier and the zero-test rule never runs. ``gather_evidence``
has no such early return — the language model is given every piece of
evidence at once and decides — so this check is computed at the
complete-gathering path whether or not the acceptance criteria were met. The
receipt therefore records ``requirements_met`` so a person adjudicating the
measurement can filter the turns the legacy path would never have reached.

Both paths still share the two earlier exits: a dishonest report and a failed
quality gate both stop gathering before this check, on both paths.

THE RECEIPT — durable, and where it lives
-----------------------------------------
Every fired check writes two things:

* a per-turn receipt beside the Coach's own verdict, at
  ``<worktree>/.guardkit/autobuild/<task_id>/zero_test_turn_<turn>.json``;
* one appended line in the repository's ledger,
  ``<repo root>/.guardkit/zero-test/queue.jsonl``.

This is the estate's existing shadow-lane convention (see
``guardkit.qa.qav_shadow``, which writes ``.guardkit/qav-shadow/queue.jsonl``)
with one deliberate difference: the ledger is written to the **main repository
root**, not to the build's disposable worktree. A worktree is deleted when the
feature is archived; a measurement that has to accumulate over months cannot
live somewhere that gets thrown away. The per-turn receipt stays in the
worktree, beside the verdict it describes, because that is where a person
debugging one build looks.

Read the ledger with::

    guardkit autobuild zero-test-report

Neither write can ever break a build: every failure swallows to a warning.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

logger = logging.getLogger(__name__)

__all__ = [
    "BLOCKING_ENV_VAR",
    "ZERO_TEST_QUEUE",
    "ZERO_TEST_RECEIPT",
    "ANOMALY_CATEGORY",
    "blocking_requested",
    "evaluate_zero_test",
    "build_receipt",
    "write_receipt",
    "coach_advisory_text",
    "read_receipts",
]

#: Environment variable that promotes this check from advisory to blocking.
#: Named and shaped after ``boot_smoke_gate.BLOCKING_ENV_VAR``.
BLOCKING_ENV_VAR = "GUARDKIT_ZERO_TEST_BLOCKING"

_TRUTHY = {"1", "true", "yes", "on"}

#: The repository-level ledger every fired check appends to. One JSON object
#: per line. Lives at the MAIN repository root (see module docstring).
ZERO_TEST_QUEUE = ".guardkit/zero-test/queue.jsonl"

#: The per-turn receipt, written beside ``coach_turn_{turn}.json`` inside the
#: build's own worktree.
ZERO_TEST_RECEIPT = ".guardkit/autobuild/{task_id}/zero_test_turn_{turn}.json"

#: The issue category the legacy rule already uses. Kept identical so the two
#: paths are greppable as one thing.
ANOMALY_CATEGORY = "zero_test_anomaly"


def blocking_requested(env: Optional[Mapping[str, str]] = None) -> bool:
    """Has the operator asked a fired zero-test check to stop the turn?

    Reads :data:`BLOCKING_ENV_VAR`. Absent or unrecognised means no — the
    check stays advisory. Same contract as
    ``boot_smoke_gate.blocking_requested``.
    """
    source = os.environ if env is None else env
    return str(source.get(BLOCKING_ENV_VAR, "")).strip().lower() in _TRUTHY


def _string_list(value: Any) -> List[str]:
    """Coerce a Player-reported file list to a list of strings; never raise."""
    if not isinstance(value, (list, tuple)):
        return []
    return [str(item) for item in value if isinstance(item, (str, Path))]


def evaluate_zero_test(
    validator: Any,
    *,
    task_work_results: Dict[str, Any],
    profile: Any,
    independent_tests: Any = None,
    task_id: Optional[str] = None,
    requirements: Any = None,
) -> Dict[str, Any]:
    """Run the legacy zero-test rule and package what it found as evidence.

    The detection itself is **not** implemented here. It is delegated to
    ``validator._check_zero_test_anomaly(...)`` — the same method the legacy
    Coach calls, with the same arguments — so the two paths cannot drift.

    Everything else in the returned dict is context for the person who will
    later adjudicate the measurement: what the Player said it created and
    modified, which of those look like test files, and which of THOSE are
    actually present on disk.

    Never raises. If the rule itself blows up, the result records that fact
    with ``fired`` false — an instrument that cannot report must not
    manufacture a verdict.

    Returns
    -------
    dict
        Always a dict, never ``None``. ``fired`` is the only key a caller
        must branch on.
    """
    files_created = _string_list(task_work_results.get("files_created"))
    files_modified = _string_list(task_work_results.get("files_modified"))
    tests_written = _string_list(task_work_results.get("tests_written"))

    is_test_path = getattr(validator, "_is_test_file_path", None)
    worktree_path = getattr(validator, "worktree_path", None)

    claimed_test_files: List[str] = []
    for candidate in [*tests_written, *files_created, *files_modified]:
        if candidate in claimed_test_files:
            continue
        try:
            looks_like_a_test = bool(is_test_path and is_test_path(candidate))
        except Exception:  # noqa: BLE001 — a heuristic must never break gathering
            looks_like_a_test = False
        if looks_like_a_test:
            claimed_test_files.append(candidate)

    test_files_on_disk: List[str] = []
    if worktree_path is not None:
        for candidate in claimed_test_files:
            try:
                if (Path(worktree_path) / candidate).exists():
                    test_files_on_disk.append(candidate)
            except Exception:  # noqa: BLE001 — an odd path must not break gathering
                continue

    independent_command = getattr(independent_tests, "test_command", None)

    evidence: Dict[str, Any] = {
        "fired": False,
        "severity": None,
        "category": ANOMALY_CATEGORY,
        "description": None,
        "detector": "CoachValidator._check_zero_test_anomaly",
        "tests_required": bool(getattr(profile, "tests_required", False)),
        "profile_blocks_on_zero_tests": bool(
            getattr(profile, "zero_test_blocking", False)
        ),
        "files_created": files_created,
        "files_modified": files_modified,
        "tests_written": tests_written,
        "claimed_test_files": claimed_test_files,
        "test_files_on_disk": test_files_on_disk,
        "any_test_file_on_disk": bool(test_files_on_disk),
        "independent_test_command": independent_command,
        "requirements_met": _requirements_met(requirements),
        "evaluation_error": None,
    }

    try:
        issues = validator._check_zero_test_anomaly(
            task_work_results,
            profile,
            independent_tests=independent_tests,
            task_id=task_id,
        )
    except Exception as exc:  # noqa: BLE001 — the instrument must never break a build
        logger.warning(
            "zero_test_gate: the zero-test rule raised %s for %s — recorded "
            "as not fired (an instrument that cannot report must not "
            "manufacture a verdict).",
            exc.__class__.__name__,
            task_id,
        )
        evidence["evaluation_error"] = f"{exc.__class__.__name__}: {exc}"
        return evidence

    if not issues:
        return evidence

    first = issues[0] if isinstance(issues[0], dict) else {}
    evidence["fired"] = True
    evidence["severity"] = first.get("severity")
    evidence["description"] = first.get("description")
    return evidence


def _requirements_met(requirements: Any) -> Optional[bool]:
    """``True``/``False`` when the acceptance criteria verdict is known, else None."""
    if requirements is None:
        return None
    value = getattr(requirements, "all_criteria_met", None)
    return bool(value) if isinstance(value, bool) else None


def coach_advisory_text(evidence: Optional[Dict[str, Any]]) -> str:
    """The plain sentence the language-model Coach is shown. Empty when clean.

    This is the behaviour change that costs nothing and helps immediately:
    before this, the Coach was never told, in words, that the Player wrote no
    test file. The numbers were buried among dozens of sibling keys in the
    evidence JSON and nothing named them.

    The wording deliberately states that the check does not block, so the
    Coach neither treats it as a rule it must obey nor as a fact it may
    ignore — it is one more piece of evidence to weigh, and it says so.
    """
    if not isinstance(evidence, dict) or not evidence.get("fired"):
        return ""

    created = evidence.get("files_created") or []
    modified = evidence.get("files_modified") or []
    return (
        "\nADVISORY — NO TEST FILE WAS WRITTEN: the Player's report for this "
        f"turn lists {len(created)} file(s) created and {len(modified)} "
        "file(s) modified, and none of them is a test file that exists on "
        "disk. The Coach's own independent test run found no task-specific "
        "tests to execute.\n"
        "Some changes legitimately need no test — a documentation edit, a "
        "rename, deleting dead code, a configuration change. Others do not: a "
        "new behaviour with no test is unverified work.\n"
        "Weigh this. It is ADVISORY and does NOT block the turn on its own, "
        "and you must not reject solely because this line is present — say in "
        "your rationale which of the two cases you judge this to be.\n"
    )


def build_receipt(
    *,
    evidence: Dict[str, Any],
    task_id: str,
    turn: int,
    feature_id: Optional[str],
    repo: Optional[str],
    repo_path: Optional[str],
    coach_decision: Optional[str],
    blocking: bool,
    overridden: bool,
    now: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble the durable record for one fired check.

    Carries everything a person needs, months later, to answer "was this build
    legitimately test-free?" without re-running anything: which feature and
    task, when, what the Player created and modified, whether any test file
    exists, what the Coach decided anyway, and which repository it happened in.
    """
    return {
        "schema": "zero_test_receipt/1",
        "recorded_at": now or datetime.now(timezone.utc).isoformat(),
        "repo": repo,
        "repo_path": repo_path,
        "feature_id": feature_id,
        "task_id": task_id,
        "turn": turn,
        "coach_decision": coach_decision,
        "severity": evidence.get("severity"),
        "blocking_requested": blocking,
        "decision_overridden": overridden,
        "files_created": evidence.get("files_created") or [],
        "files_modified": evidence.get("files_modified") or [],
        "tests_written": evidence.get("tests_written") or [],
        "claimed_test_files": evidence.get("claimed_test_files") or [],
        "test_files_on_disk": evidence.get("test_files_on_disk") or [],
        "any_test_file_on_disk": bool(evidence.get("any_test_file_on_disk")),
        "independent_test_command": evidence.get("independent_test_command"),
        "requirements_met": evidence.get("requirements_met"),
        "tests_required": bool(evidence.get("tests_required")),
        "profile_blocks_on_zero_tests": bool(
            evidence.get("profile_blocks_on_zero_tests")
        ),
        "description": evidence.get("description"),
        # Left for a person to fill in later, by hand or by a follow-up tool.
        # This is the half of the promotion question a machine cannot answer.
        "legitimately_test_free": None,
    }


def write_receipt(
    record: Dict[str, Any],
    *,
    worktree_path: Path,
    repo_root: Optional[Path] = None,
    task_id: str,
    turn: int,
) -> Optional[Path]:
    """Write the per-turn receipt and append the repository ledger line.

    Mirrors ``qav_shadow._write_receipt``: the two writes are independent, and
    **neither can ever break a build** — a failure swallows to a warning.

    ``repo_root`` is where the accumulating ledger goes. When it is ``None``
    (the build is running directly in the repository rather than in a
    worktree) the worktree path is used, which is then the same directory.

    Returns the per-turn receipt path, or ``None`` when that write failed.
    """
    receipt_path: Optional[Path] = Path(worktree_path) / ZERO_TEST_RECEIPT.format(
        task_id=task_id, turn=turn
    )
    try:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        logger.warning(
            "zero_test_gate: unwritable receipt %s (%r) — record dropped",
            receipt_path,
            exc,
        )
        receipt_path = None

    ledger_root = Path(repo_root) if repo_root is not None else Path(worktree_path)
    ledger_path = ledger_root / ZERO_TEST_QUEUE
    try:
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    except OSError as exc:
        logger.warning(
            "zero_test_gate: unwritable ledger %s (%r) — row dropped",
            ledger_path,
            exc,
        )
    return receipt_path


def read_receipts(repo_root: Path) -> List[Dict[str, Any]]:
    """Read the repository's ledger, oldest first. Missing file means no rows.

    A malformed line is skipped with a warning rather than aborting the read —
    a measurement instrument that refuses to report because one row is corrupt
    is worse than one that reports the rest.
    """
    ledger_path = Path(repo_root) / ZERO_TEST_QUEUE
    if not ledger_path.is_file():
        return []

    rows: List[Dict[str, Any]] = []
    try:
        raw_lines: Sequence[str] = ledger_path.read_text(
            encoding="utf-8"
        ).splitlines()
    except OSError as exc:
        logger.warning(
            "zero_test_gate: unreadable ledger %s (%r) — reporting nothing",
            ledger_path,
            exc,
        )
        return []

    for number, line in enumerate(raw_lines, start=1):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except ValueError:
            logger.warning(
                "zero_test_gate: ledger %s line %d is not valid JSON — skipped",
                ledger_path,
                number,
            )
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows
