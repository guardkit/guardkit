"""What a gate-driven repair round tells the plan audit and the Coach.

WHY THIS EXISTS (20 October 2026)
---------------------------------
A gate that runs after a wave (the whole-feature check, the smoke gate, the
wiring gate) can fail after every task in the wave was approved. The feature
orchestrator then re-opens those tasks with the gate's output as the Player's
feedback (``FeatureOrchestrator._execute_wave_parallel``). To make the gate
pass the Player may have to change files the task document never named: the
failing end-to-end test, the scripts and helpers beside it. The plan audit
knew nothing about the round, compared the whole task with the task document,
and refused every repair turn as high, so the task stalled although the
Player was doing what the round asked.

WHAT IT DOES
------------
At the re-open the feature orchestrator makes a :class:`RepairRound` - the
round's number, the commit the round starts from (HEAD at the re-open), the
gate's output, and the files earlier approved repair rounds of the task
changed - and hands it, in memory, down the call chain it controls:
``_execute_task`` -> ``AutoBuildOrchestrator`` -> its ``AgentInvoker``. Nothing
is written to disk for it and nothing on disk is read back, so there is
nothing a Player could write to make a turn look like a repair round.

In a repair round the plan audit does not refuse a turn for the number of
extra files the round made. The Coach's prompt for the turn lists every file
the round changed that the task document does not name - read from git since
the round's start, whatever the ordinary audit reports - marks the ones the
gate's output names (:func:`implicated_paths`), says it is a repair round for
the failing check and asks the reviewer to refuse the turn if any of them is
not needed to make that check pass. If that section cannot reach the model
whole, the Coach is not run. A protected file the round made (migration,
Dockerfile, lockfile, .env ...) is still refused by the audit itself. Ordinary turns have no repair round and are
audited exactly as before. A resumed build starts without one, so its turns
are audited as ordinary turns.

Nothing here knows a programming language: a path is a run of characters
with a slash in it, or a bare file name, that matches a file git tracks.
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import FrozenSet, Iterable, List, Optional, Set

from guardkit.lib.project_git import run_git

logger = logging.getLogger(__name__)

#: How much of the gate's output the Coach's prompt carries (its end).
GATE_OUTPUT_PROMPT_LIMIT = 6000


@dataclass(frozen=True)
class RepairRound:
    """A round a gate opened again after the task was approved. In memory only.

    ``round_number`` is this round's number: 2 for the first repair round,
    whose approved predecessor's turn files went into ``round-1/`` (see
    ``turn_rounds``); it is for the record and the prompt only. ``start_commit`` is HEAD at the
    re-open: the candidate the gate failed. ``gate_output`` is the feedback the
    Player was given, the gate's own words. ``approved_by_earlier_repairs`` is
    every file an earlier, approved repair round of this task changed (worked
    out from git between that round's start and this re-open, never read from
    disk): a later gate's re-entry does not count them again.
    """

    round_number: int
    start_commit: str
    gate_output: str
    approved_by_earlier_repairs: FrozenSet[str] = frozenset()


#: The most implicated paths kept. A gate's output is cut to its last lines
#: already; this is only a bound on a pathological output.
MAX_IMPLICATED_PATHS = 200

# Characters that separate one path from the next in tool output: white
# space, quotes, brackets, commas, and the arrows and bars test runners print.
_SEPARATORS = re.compile(r"[\s\"'`()\[\]{}<>,;|›→»]+")
# A trailing ``:line`` or ``:line:column`` (``spec.ts:124:26``).
_LINE_SUFFIX = re.compile(r"(?::\d+)+$")


def _candidates(text: str) -> Iterable[str]:
    for token in _SEPARATORS.split(text or ""):
        token = token.strip().rstrip(".:")
        token = _LINE_SUFFIX.sub("", token).rstrip(".:")
        if token:
            yield token


def implicated_paths(text: str, tracked: Iterable[str]) -> List[str]:
    """The tracked files ``text`` names, sorted.

    A token with a slash names the tracked file that is its longest trailing
    run of path parts, so an absolute path printed from inside any checkout
    (``/somewhere/checkout/tests/e2e/login.spec.ts:12:3``) names
    ``tests/e2e/login.spec.ts``. A bare file name with an extension
    (``login.spec.ts``) names a file only when exactly one tracked file has
    that name. Anything else names nothing. Pure.
    """
    tracked_set: Set[str] = {str(path) for path in tracked if path}
    by_name: dict = {}
    for path in tracked_set:
        by_name.setdefault(path.rsplit("/", 1)[-1], []).append(path)

    found: Set[str] = set()
    for token in _candidates(text):
        if "/" in token:
            parts = [part for part in token.split("/") if part not in ("", ".")]
            for start in range(len(parts)):
                suffix = "/".join(parts[start:])
                if suffix in tracked_set:
                    found.add(suffix)
                    break
        elif "." in token.strip("."):
            matches = by_name.get(token, [])
            if len(matches) == 1:
                found.add(matches[0])
        if len(found) >= MAX_IMPLICATED_PATHS:
            break
    return sorted(found)


def begin_repair_round(
    worktree_path: Path,
    round_number: Optional[int],
    gate_output: str,
    previous: Optional[RepairRound] = None,
) -> Optional[RepairRound]:
    """The repair round a re-open starts, or ``None``. Never raises.

    Reads HEAD of the worktree, the round's start. ``previous`` is this
    task's last repair round, when a gate re-opened it before: the task was
    approved again after it (only an approved task is re-opened), so every
    file that changed between that round's start and this HEAD was approved
    by a repair round, and is carried forward with the ones before it.
    ``None`` when git cannot say where the round starts: the round then goes
    ahead and its turns are audited as ordinary ones.
    """
    head = _git_out(worktree_path, ["rev-parse", "HEAD"]).strip()
    if not head:
        logger.warning(
            "The repair round's start could not be read from git; its turns "
            "are audited as ordinary turns."
        )
        return None
    approved: Set[str] = set()
    if previous is not None:
        approved |= set(previous.approved_by_earlier_repairs)
        listed = _git_out(
            worktree_path, ["diff", "--name-only", previous.start_commit, head]
        )
        approved |= {line.strip() for line in listed.splitlines() if line.strip()}
    number = round_number if isinstance(round_number, int) and round_number > 1 else 2
    return RepairRound(
        round_number=number,
        start_commit=head,
        gate_output=str(gate_output or ""),
        approved_by_earlier_repairs=frozenset(approved),
    )


def _git_out(worktree_path: Path, args: List[str]) -> str:
    """git's output, or "" when git cannot answer. Never raises."""
    try:
        done = run_git(args, cwd=Path(worktree_path), check=False, timeout=30)
    except (subprocess.SubprocessError, FileNotFoundError, OSError, TypeError):
        return ""
    return done.stdout if done.returncode == 0 else ""
