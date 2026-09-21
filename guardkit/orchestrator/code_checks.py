"""One summary of what the code checks did, written once at the end of a build.

WHY THIS EXISTS (21 September 2026)
-----------------------------------
Each task's review already saves what the code checks said, in
``coach_evidence_turn_N.json`` under the task's own folder. The check after
each group of tasks saved nothing at all: its result was printed and dropped.
So by the time anyone is offered a merge, the one thing nobody can find out is
whether the code was checked — and "nothing was reported" read exactly like
"nothing was wrong".

This module reads what was kept and writes one summary, ``code_checks.json``,
beside the whole-feature record in ``.guardkit/autobuild-private/`` — a folder
the runner already exports. It holds, per task and per group of tasks, each
check's state in one of five words, whether the builder's file list was
recorded, and how many shell commands ran (a file a shell command wrote is in
no list, so a reader can say so).

WHAT IT IS NOT
--------------
* It is not a gate. Nothing here refuses, blocks or fails anything, and every
  function in this module swallows its own errors. A build is never failed by
  a summary of itself.
* It knows nothing about any language, test runner, protocol or product. It
  carries the checks' own words as TEXT and never reads, compares or judges
  them. "This kind of project is not supported" is a state a check reports
  about itself; this module repeats it and does not work out what kind.

AN ABSENCE IS NOT A DECISION (corrected 21 September 2026)
---------------------------------------------------------
A kept review holds nothing at all for a check in several different cases: the
checks do not look at that kind of task, the task wrote no file with its file
tools, the check's analyser was not installed, or the analyser stopped on the
way. The first two are honest declines; the last two mean the check DID NOT
RUN. Reading every absence as "it had nothing to do" counted a check that
never ran as one that was done, so the count of what nothing looked at came
out as nought on a build nothing had looked at. Now the record decides — see
:func:`absence_reading` — and where it cannot decide, the answer is "not
checked".
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from guardkit.orchestrator.authored_files import (
    NOT_CHECKED_REASON,
    STATUS_NO_KEY,
    STATUS_TRACKED,
    STATUS_UNKNOWN,
    kind_is_analysed,
    read_authored_files,
    shell_command_count,
)

logger = logging.getLogger(__name__)

#: Where the summary lands, relative to the built tree — beside the
#: whole-feature record, in the folder the runner already exports.
SUMMARY_RELATIVE_PATH = (
    Path(".guardkit") / "autobuild-private" / "code_checks.json"
)

#: The checks a task's kept review record carries, by the names it uses. Each
#: one is a key in ``coach_evidence_turn_N.json``. A name this list does not
#: know is not invented here, and a name missing from a record is reported as
#: absent rather than assumed fine.
CHECK_NAMES = ("wiring", "mocked_seam", "stub_scan", "coverage")

#: The five states a check can be in. Nothing else is ever recorded, and
#: "not checked" is never one of the passing two.
STATE_RAN_FOUND_NOTHING = "ran_and_found_nothing"
STATE_FOUND_SOMETHING = "found_something"
STATE_NOT_CHECKED = "not_checked"
STATE_DOES_NOT_APPLY = "does_not_apply"
STATE_KIND_NOT_SUPPORTED = "kind_of_project_not_supported"

#: How many findings one check may name in the summary before the rest are
#: counted rather than listed. The true count is always kept.
MAX_LISTED_FINDINGS = 10

_TURN_FILE = re.compile(r"coach_evidence_turn_(\d+)\.json$")

#: Statuses a check reports about itself, and what each one means here. These
#: are the analyser's own words, not a judgement made in this module.
_KIND_NOT_SUPPORTED_STATUSES = {"unsupported_stack"}
_DOES_NOT_APPLY_STATUSES = {
    "skipped_no_targets",
    "skipped_no_acceptance_files",
}
_ERROR_STATUSES = {"error"}
#: The words a check uses for "I ran, and my list of findings is the whole
#: answer". Only these mean an empty findings list may be read as a result.
_RAN_STATUSES = {"complete", "ran"}
#: The word a check uses when it read only PART of what it was given. It ran,
#: and its findings stand for the part it could read — the rest was covered by
#: nothing, so how much it could not read travels beside the state as a number
#: (21 September 2026; the group half below has carried it from the start).
_PARTLY_READ_STATUSES = {"parse_degraded"}
#: Where a check lists the things it could not read.
_UNREAD_KEYS = ("degraded_files",)

#: What an entry that is ``None`` — or missing altogether — means when the
#: kept record cannot say. The review writes that same absence for several
#: different reasons: the check declined (a kind of task it does not look at,
#: or a task that wrote no file with its file tools), or the check never ran
#: (its analyser was not installed, or it stopped on the way). Only the record
#: can tell those apart, and where it cannot, the answer is "not checked".
#: An absence is never reported as a state that reads like a clean run, and
#: never as a decision the record does not support.
ABSENCE_CANNOT_TELL: Dict[str, str] = {
    "state": STATE_NOT_CHECKED,
    "reason": (
        "the kept record holds nothing for this check, and nothing in it "
        "shows the check ran"
    ),
}


def _finding_summary(finding: Any) -> Dict[str, Optional[str]]:
    """One finding, as the file and the name it is about."""
    if not isinstance(finding, dict):
        return {"file": None, "name": None, "kind": None}
    name = finding.get("symbol")
    if not isinstance(name, str) or not name.strip():
        for key in ("name", "function", "title", "id"):
            value = finding.get(key)
            if isinstance(value, str) and value.strip():
                name = value
                break
    kind = finding.get("pattern")
    return {
        "file": finding.get("file") if isinstance(finding.get("file"), str) else None,
        "name": name if isinstance(name, str) and name.strip() else None,
        "kind": kind if isinstance(kind, str) and kind.strip() else None,
    }


def absence_reading(review_record: Any, task_results: Any = None) -> Dict[str, str]:
    """What an absent entry means on THIS task. Never raises.

    Two absences are honest, and the kept record says both in its own words:

    * a kind of task the checks do not look at at all — they declined;
    * a task whose file list WAS recorded and is empty — it wrote no file with
      its file tools, so there was nothing for a check to look at.

    Anything else is "not checked": the same absence is what a task gets when
    the check's analyser was not there or stopped, and nothing in the record
    tells those apart. See :data:`ABSENCE_CANNOT_TELL`.
    """
    try:
        kind = (
            review_record.get("task_type")
            if isinstance(review_record, dict)
            else None
        )
        if isinstance(kind, str) and kind.strip() and not kind_is_analysed(kind):
            return {
                "state": STATE_DOES_NOT_APPLY,
                "reason": (
                    "the code checks do not look at a "
                    f"{kind.strip().lower()} task"
                ),
            }
        files, status = read_authored_files(task_results)
        if status == STATUS_TRACKED and not files:
            return {
                "state": STATE_DOES_NOT_APPLY,
                "reason": "this task wrote no file with its file tools",
            }
    except Exception as exc:  # noqa: BLE001 — a summary never fails a build
        logger.debug("code checks: an absence could not be read: %s", exc)
    return dict(ABSENCE_CANNOT_TELL)


def _entry(
    state: str,
    reason: str,
    findings: Optional[Sequence[Any]] = None,
    inputs_not_read: Optional[int] = None,
) -> Dict[str, Any]:
    """One check's entry, always the same shape.

    ``inputs_not_read`` is how many of the things the check was given it
    could not read, or ``None`` when the record does not say. It is the same
    field, with the same name and the same meaning, that :func:`group_record`
    has carried since this module was written; the per-task half gained it on
    21 September 2026, because it was throwing the number away and calling a
    partly-read check clean.
    """
    listed = list(findings or [])
    return {
        "state": state,
        "reason": reason,
        "findings": [_finding_summary(f) for f in listed[:MAX_LISTED_FINDINGS]],
        "finding_count": len(listed),
        "inputs_not_read": inputs_not_read,
    }


def _unread_count(block: Any) -> Optional[int]:
    """How many things this check says it could not read, or ``None``."""
    if not isinstance(block, dict):
        return None
    for key in _UNREAD_KEYS:
        value = block.get(key)
        if isinstance(value, (list, tuple)):
            return len(value)
    return None


def summarise_check(
    block: Any, *, absence: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """What one check did, in one of the five states. Never raises.

    ``block`` is whatever the kept record holds under the check's name.
    ``None`` is the shape a check leaves behind whether it declined or never
    ran, so what that absence means comes from ``absence`` — the reading
    :func:`absence_reading` takes off the record. With no reading given, an
    absence is "not checked", never a state that reads like a clean run.

    TWO CORRECTIONS, 21 September 2026 (the Stage C re-check):

    * a check that could read only PART of what it was given still ran, and
      its empty findings list still means "nothing in the part I read" — but
      the part it could not read was covered by nothing, so the count travels
      beside the state exactly as the group half has always carried it;
    * a status word this mapping does not know is "not checked", with the
      word itself as the reason. It used to fall through to the findings
      list, so an unknown skip word with no findings came out as "ran and
      found nothing" — a clean answer made out of a word nobody understood.
    """
    try:
        if block is None:
            reading = absence if isinstance(absence, dict) else ABSENCE_CANNOT_TELL
            state = str(reading.get("state") or "") or STATE_NOT_CHECKED
            return _entry(
                state,
                str(reading.get("reason") or "") or ABSENCE_CANNOT_TELL["reason"],
            )
        if not isinstance(block, dict):
            return _entry(
                STATE_NOT_CHECKED,
                "the kept record's entry for this check could not be read",
            )

        status = block.get("status")
        status = status.strip().lower() if isinstance(status, str) else ""
        reason = block.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            skip = block.get("skip_reason")
            reason = skip if isinstance(skip, str) else ""

        if status in _KIND_NOT_SUPPORTED_STATUSES:
            return _entry(
                STATE_KIND_NOT_SUPPORTED,
                reason or "this check does not cover this kind of project",
            )
        if status == STATE_NOT_CHECKED:
            return _entry(STATE_NOT_CHECKED, reason or NOT_CHECKED_REASON)
        if status in _DOES_NOT_APPLY_STATUSES:
            return _entry(
                STATE_DOES_NOT_APPLY, reason or "this check had nothing to look at"
            )
        if status in _ERROR_STATUSES:
            return _entry(
                STATE_NOT_CHECKED,
                reason or "this check stopped on an error of its own",
            )

        partly_read = status in _PARTLY_READ_STATUSES
        if not partly_read and status not in _RAN_STATUSES:
            # A word nobody here knows, or no word at all, says nothing about
            # whether the check looked at anything, so it cannot be read as
            # either answer (the no-word case: coordinator's review,
            # 21 September 2026).
            return _entry(
                STATE_NOT_CHECKED,
                reason
                or (
                    f"this check reported '{status}', which is not a word "
                    "this summary knows"
                    if status
                    else "this check recorded no word saying whether it ran"
                ),
                block.get("findings")
                if isinstance(block.get("findings"), (list, tuple))
                else None,
            )

        findings = block.get("findings")
        if not isinstance(findings, (list, tuple)):
            # ``findings: None`` is the shape a check that did not run uses.
            return _entry(
                STATE_NOT_CHECKED,
                reason or "this check recorded no list of findings",
            )

        not_read = _unread_count(block) if partly_read else None
        if partly_read and not reason:
            reason = (
                f"some of what it was given could not be read ({not_read} of them)"
                if not_read
                else "some of what it was given could not be read"
            )
        if findings:
            return _entry(
                STATE_FOUND_SOMETHING, reason or "", findings, not_read
            )
        return _entry(STATE_RAN_FOUND_NOTHING, reason or "", None, not_read)
    except Exception as exc:  # noqa: BLE001 — a summary never fails a build
        logger.debug("code checks: a check entry could not be summarised: %s", exc)
        return _entry(
            STATE_NOT_CHECKED,
            "the kept record's entry for this check could not be read",
        )


def latest_review_record(task_private_dir: Path) -> Optional[Path]:
    """The LAST review record of a task, or ``None``. Never raises.

    The last one is the one that describes the code as it was left. Turn
    numbers are compared as numbers, so turn 10 comes after turn 9.
    """
    try:
        best: Optional[Path] = None
        best_turn = -1
        for path in Path(task_private_dir).glob("coach_evidence_turn_*.json"):
            match = _TURN_FILE.search(path.name)
            if match is None:
                continue
            turn = int(match.group(1))
            if turn > best_turn:
                best_turn, best = turn, path
        return best
    except Exception as exc:  # noqa: BLE001
        logger.debug("code checks: no review record found in %s: %s", task_private_dir, exc)
        return None


def summarise_task(
    task_id: str,
    *,
    review_record: Any = None,
    task_results: Any = None,
    review_record_path: Optional[str] = None,
) -> Dict[str, Any]:
    """What every code check did on one task. Never raises.

    ``review_record`` is the task's LAST kept review record, already parsed;
    ``task_results`` is its ``task_work_results.json``. Either may be ``None``,
    and a task with no kept review is reported as not checked — never as
    clean.
    """
    checks: Dict[str, Any] = {}
    if isinstance(review_record, dict):
        absence = absence_reading(review_record, task_results)
        for name in CHECK_NAMES:
            checks[name] = summarise_check(
                review_record.get(name) if name in review_record else None,
                absence=absence,
            )
        reviewed = True
    else:
        for name in CHECK_NAMES:
            checks[name] = _entry(
                STATE_NOT_CHECKED, "no review record of this task was kept"
            )
        reviewed = False

    files_recorded: Optional[bool]
    _files, status = read_authored_files(task_results)
    if status == STATUS_TRACKED:
        files_recorded = True
    elif status == STATUS_UNKNOWN:
        files_recorded = False
    else:  # STATUS_NO_KEY — a record from before the list existed
        files_recorded = None

    return {
        "task": str(task_id),
        "review_record_kept": reviewed,
        "review_record": review_record_path,
        "file_list_recorded": files_recorded,
        "file_list_note": (
            "this record predates the builder's file list"
            if status == STATUS_NO_KEY
            else ("" if files_recorded else NOT_CHECKED_REASON)
        ),
        "shell_command_count": shell_command_count(task_results),
        "checks": checks,
    }


def group_record(
    group: Any,
    *,
    state: str,
    reason: str = "",
    findings: Optional[Sequence[Any]] = None,
    tasks_without_a_file_list: Optional[Sequence[str]] = None,
    inputs_not_read: Optional[int] = None,
) -> Dict[str, Any]:
    """One entry for the check that runs after a group of tasks.

    ``inputs_not_read`` is how many of the things the check was given it could
    not read. A check that read only part of what it was given and found
    nothing in the rest has not covered the part it could not read, so the
    count travels beside the state instead of being lost in a sentence.
    """
    listed = list(findings or [])
    count: Optional[int]
    try:
        count = int(inputs_not_read) if inputs_not_read is not None else None
    except (TypeError, ValueError):
        count = None
    return {
        "group": group,
        "check": "wiring",
        "state": state,
        "reason": reason,
        "findings": [_finding_summary(f) for f in listed[:MAX_LISTED_FINDINGS]],
        "finding_count": len(listed),
        "tasks_without_a_file_list": [str(t) for t in (tasks_without_a_file_list or [])],
        "inputs_not_read": count,
    }


def build_code_checks_summary(
    *,
    feature_id: str,
    tasks: Sequence[Dict[str, Any]],
    groups: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """The whole summary, with the counts a reader needs first. Never raises."""
    task_rows = list(tasks)
    group_rows = list(groups)
    not_checked_tasks = [
        row["task"]
        for row in task_rows
        if isinstance(row, dict)
        and any(
            check.get("state") == STATE_NOT_CHECKED
            for check in (row.get("checks") or {}).values()
        )
    ]
    finding_count = sum(
        int(check.get("finding_count") or 0)
        for row in task_rows
        if isinstance(row, dict)
        for check in (row.get("checks") or {}).values()
    ) + sum(int(row.get("finding_count") or 0) for row in group_rows if isinstance(row, dict))
    shell_commands = sum(
        int(row.get("shell_command_count") or 0)
        for row in task_rows
        if isinstance(row, dict) and isinstance(row.get("shell_command_count"), int)
    )
    return {
        "feature": str(feature_id),
        "what": (
            "What the code checks did during this build: for each task, the "
            "last review's result for each check; for each group of tasks, "
            "the check that runs after it. Five states, and 'not checked' is "
            "never one of the passing ones. Nothing here refuses anything."
        ),
        "finding_count": finding_count,
        "tasks_total": len(task_rows),
        "tasks_with_something_not_checked": len(not_checked_tasks),
        "tasks_not_checked": not_checked_tasks,
        "shell_command_count": shell_commands,
        "shell_command_note": (
            "a file a shell command wrote is in no builder's file list, so no "
            "check covered it"
        ),
        "tasks": task_rows,
        "groups": group_rows,
    }


def write_code_checks_summary(summary: Dict[str, Any], root: Path) -> Optional[Path]:
    """Write the summary into the built tree. Never raises."""
    try:
        path = Path(root) / SUMMARY_RELATIVE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
        return path
    except Exception as exc:  # noqa: BLE001 — a summary never fails a build
        logger.warning("code checks: the summary could not be written: %s", exc)
        return None


def read_code_checks_summary(root: Path) -> Optional[Dict[str, Any]]:
    """Read the summary back, or ``None``. Never raises."""
    try:
        path = Path(root) / SUMMARY_RELATIVE_PATH
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("code checks: the summary could not be read: %s", exc)
        return None
    return data if isinstance(data, dict) else None


__all__ = [
    "ABSENCE_CANNOT_TELL",
    "CHECK_NAMES",
    "MAX_LISTED_FINDINGS",
    "STATE_DOES_NOT_APPLY",
    "STATE_FOUND_SOMETHING",
    "STATE_KIND_NOT_SUPPORTED",
    "STATE_NOT_CHECKED",
    "STATE_RAN_FOUND_NOTHING",
    "SUMMARY_RELATIVE_PATH",
    "absence_reading",
    "build_code_checks_summary",
    "group_record",
    "latest_review_record",
    "read_code_checks_summary",
    "summarise_check",
    "summarise_task",
    "write_code_checks_summary",
]
