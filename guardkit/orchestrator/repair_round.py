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
gate's output, and the non-protected files the reviewer approved in this
task's earlier repair rounds - and hands it, in memory, down the call chain it controls:
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

import hashlib
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, FrozenSet, Iterable, List, Optional, Set, Tuple

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
    Player was given, the gate's own words. ``approved_by_earlier_repairs`` are
    the non-protected files this task's earlier repair rounds showed the
    reviewer on the turns it approved, carried in memory: a later gate's
    re-entry does not count them again. Never a protected file.
    """

    round_number: int
    start_commit: str
    gate_output: str
    approved_by_earlier_repairs: FrozenSet[str] = frozenset()
    #: Every protected file git ignores, as it stood at the re-open: path and
    #: sha256 of its bytes, nothing else (``ignored_protected_files``). Never
    #: the contents.
    ignored_protected: Tuple[Tuple[str, str], ...] = ()
    #: Why the round's facts could not be established at the re-open, or
    #: ``None`` when they were. A round that is unavailable is still a repair
    #: round: every one of its turns is refused (the unreadable-record
    #: refusal), never audited as an ordinary turn.
    unavailable: Optional[str] = None


class RepairFactsUnavailable(Exception):
    """A repair round's facts could not be established. Every helper that
    establishes them raises this on any error, and the caller refuses the
    turn; no helper returns a stand-in value."""


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
    approved_by_earlier_repairs: Iterable[str] = (),
) -> RepairRound:
    """The repair round a re-open starts. Always a round; never raises.

    Reads HEAD of the worktree, the round's start, and the protected files git
    ignores. ``approved_by_earlier_repairs`` are the non-protected files this
    task's earlier repair rounds showed the reviewer on the turns it approved
    (``FeatureOrchestrator._remember_repair_approvals``); never another
    task's files, and never a protected file. If anything cannot be
    established the round is returned with ``unavailable`` set to the reason,
    and every one of its turns is refused.
    """
    number = round_number if isinstance(round_number, int) and round_number > 1 else 2
    approved = frozenset(str(path) for path in approved_by_earlier_repairs if path)
    try:
        head = git_head(worktree_path)
        ignored = ignored_protected_files(worktree_path)
    except Exception as exc:  # noqa: BLE001 — becomes an explicit unavailable round
        reason = str(exc) if isinstance(exc, RepairFactsUnavailable) else type(exc).__name__
        logger.warning(
            "The repair round's facts could not be established at the re-open "
            "(%s); every turn of the round will be refused.", reason,
        )
        return RepairRound(
            round_number=number,
            start_commit="",
            gate_output=str(gate_output or ""),
            approved_by_earlier_repairs=approved,
            unavailable=reason,
        )
    return RepairRound(
        round_number=number,
        start_commit=head,
        gate_output=str(gate_output or ""),
        approved_by_earlier_repairs=approved,
        ignored_protected=tuple(sorted(ignored.items())),
    )


def git_head(worktree_path: Path) -> str:
    """HEAD of the worktree. Raises ``RepairFactsUnavailable`` on any error."""
    try:
        done = run_git(["rev-parse", "HEAD"], cwd=Path(worktree_path), check=False, timeout=30)
    except Exception as exc:  # noqa: BLE001
        raise RepairFactsUnavailable(f"HEAD could not be read ({type(exc).__name__})") from exc
    head = (done.stdout or "").strip() if done.returncode == 0 else ""
    if not head:
        raise RepairFactsUnavailable("HEAD could not be read")
    return head


def ignored_protected_files(worktree_path: Path) -> Dict[str, str]:
    """Every protected file git ignores, as ``{path: sha256 of its bytes}``.

    git's own view of changes says nothing about an ignored file, so an
    ignored ``.env`` a repair round makes, edits or deletes would never be
    seen. This lists the ignored files (``git ls-files --others --ignored
    --exclude-standard``), keeps the protected ones (the plan audit's
    ``_is_protected``), leaves out what the audit never counts (installed
    packages, caches, the factory's own records) and hashes each one. The
    contents are read only to hash them: they are never kept, logged or
    shown. Raises ``RepairFactsUnavailable`` if the listing or any one hash
    cannot be taken.
    """
    try:
        from installer.core.commands.lib.plan_audit import PlanAuditor, _is_protected

        done = run_git(
            ["ls-files", "--others", "--ignored", "--exclude-standard", "-z"],
            cwd=Path(worktree_path),
            check=False,
            timeout=60,
        )
    except Exception as exc:  # noqa: BLE001
        raise RepairFactsUnavailable(
            f"the ignored files could not be listed ({type(exc).__name__})"
        ) from exc
    if done.returncode != 0:
        raise RepairFactsUnavailable("the ignored files could not be listed")
    auditor = PlanAuditor()
    found: Dict[str, str] = {}
    for path in done.stdout.split("\0"):
        if not path or not _is_protected(path) or auditor._is_excluded(Path(path)):
            continue
        found[path] = _sha256_of(Path(worktree_path) / path)
    return found


def _sha256_of(path: Path) -> str:
    """The sha256 of a file's bytes (of a symlink's target text, for a link).
    Raises ``RepairFactsUnavailable`` naming the path when it cannot be read;
    there is no stand-in value that could compare equal."""
    digest = hashlib.sha256()
    try:
        if path.is_symlink():
            digest.update(b"symlink:" + os.fsencode(os.readlink(path)))
            return digest.hexdigest()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
    except OSError as exc:
        raise RepairFactsUnavailable(
            f"{path.name} could not be read to hash it ({type(exc).__name__})"
        ) from exc
    return digest.hexdigest()


def ignored_protected_changes(
    before: Iterable[Tuple[str, str]], now: Dict[str, str]
) -> Set[str]:
    """The ignored protected files made, changed or deleted between two
    complete listings. Pure."""
    then = dict(before)
    return {path for path in set(then) | set(now) if then.get(path) != now.get(path)}
