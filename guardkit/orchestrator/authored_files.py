"""One rule for reading a task's authored-file list.

Background (2026-09-21). A task's ``task_work_results.json`` carries
``files_authored``: the files the builder wrote with its own file tools. Three
readers use it — the per-task review
(``quality_gates.coach_validator._compute_authored_set``), the after-each-group
gate (``feature_orchestrator._wave_authored_files``) and the stale-test
attribution map (``stale_test_attribution._authored_files``). Until today all
three treated an empty list as "this task wrote nothing", so every detector that
reads the list reported nothing to look at and the build looked clean.

The list was empty for a different reason: only one of the two builders ever
reached the code that filled it, so on the other builder the list was never
recorded at all. The repair is at the source (``agent_invoker``); this module
holds the reading rule, so the three readers cannot drift apart:

* **tracked** — the list is what the builder's file tools wrote. An empty
  tracked list really does mean "this task changed no file with its file
  tools". Detectors may act on it.
* **unknown** — the list is empty and nothing says it was recorded. That is a
  failure of the tracking, not a statement about the task. Detectors must
  report :data:`NOT_CHECKED_REASON`, never "clean", and must never fall back to
  ``files_modified`` / ``files_created`` (those are union-merged with a
  whole-folder ``git diff`` before they reach a reader, so in a wave they carry
  a neighbour's edits; using them once produced false alarms that blocked
  approvals — see ``coach_validator`` at the contention-detection comment).
* **no_key** — the record has no ``files_authored`` key at all. That is how
  records written before the key existed read, and every caller keeps whatever
  it did with them before. This module does not change that branch.

Every record written before 2026-09-21 has no marker, so an empty list in one
reads as **unknown** — which is the truth about it.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

#: The key the writer puts beside the list. Values: ``"tracked"`` when at least
#: one tool event was seen for the task, ``"not_tracked"`` when none was.
TRACKING_KEY = "files_authored_tracking"

#: The key the writer puts beside the list for shell-command tool uses. A file
#: written by a shell command is not in the list, so a reader that wants to say
#: "the list is empty and N shell commands ran" can.
SHELL_COMMAND_COUNT_KEY = "shell_command_tool_uses"

TRACKED = "tracked"
NOT_TRACKED = "not_tracked"

#: Statuses returned by :func:`read_authored_files`.
STATUS_TRACKED = "tracked"
STATUS_UNKNOWN = "unknown"
STATUS_NO_KEY = "no_key"

#: What a detector says when the list is unknown. Plain words on purpose: it
#: goes in front of a reader, and "clean" would be a lie.
NOT_CHECKED_REASON = "not checked: the builder's file list was not recorded"


def read_authored_files(data: Any) -> Tuple[List[str], str]:
    """Read one task record's authored-file list under the one rule.

    Parameters
    ----------
    data
        A parsed ``task_work_results.json`` mapping. Anything else reads as
        ``no_key`` with an empty list (fail open; this never raises).

    Returns
    -------
    (files, status)
        ``status`` is one of :data:`STATUS_TRACKED`, :data:`STATUS_UNKNOWN` or
        :data:`STATUS_NO_KEY`. ``files`` is empty for the last two.
    """
    if not isinstance(data, dict):
        return [], STATUS_NO_KEY

    raw = data.get("files_authored")
    if not isinstance(raw, list):
        return [], STATUS_NO_KEY

    files = [str(f) for f in raw]
    if files:
        # A non-empty list can only have come from real tool calls, whatever
        # the marker says (records written before the marker existed included).
        return files, STATUS_TRACKED

    if data.get(TRACKING_KEY) == TRACKED:
        return [], STATUS_TRACKED

    return [], STATUS_UNKNOWN


def shell_command_count(data: Any) -> Any:
    """The record's shell-command tool-use count, or ``None`` when absent."""
    if not isinstance(data, dict):
        return None
    value = data.get(SHELL_COMMAND_COUNT_KEY)
    if type(value) is int and value >= 0:
        return value
    return None


def not_checked_block(extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """The block a detector returns when the authored list is unknown.

    ``findings`` is ``None``, not ``[]``: an empty list of findings is what a
    detector that really ran and found nothing returns, and this detector did
    not run.
    """
    block: Dict[str, Any] = {
        "status": "not_checked",
        "ran": False,
        "findings": None,
        "reason": NOT_CHECKED_REASON,
    }
    if extra:
        block.update(extra)
    return block
