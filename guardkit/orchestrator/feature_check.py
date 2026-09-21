"""The whole-feature check: does the feature do what the person asked for?

WHY THIS EXISTS (the B9 hole, 2026-09-18)
-----------------------------------------
Five tasks each passed their own checks and the endpoint the person asked for
was still wrong. Every check in the build was a check of a PART: a task's own
tests, a task's own Coach, a wave's smoke command. Nothing ran once, at the
end, over the assembled feature, and asked the question the request asked.
The only feature-level runtime check in the estate ran AFTER the merge word,
in Forge's sandbox — which is far too late to repair anything.

So: the project declares one command that proves its own feature at the
surface the person uses, and the orchestrator runs it after the last wave,
before the merge card can ever be offered.

WHAT THIS MODULE IS AND IS NOT
------------------------------
* It is a declaration reader, a subprocess runner, a feedback composer and a
  receipt writer. The retry loop lives in ``FeatureOrchestrator`` beside the
  smoke gate's, because re-entering a wave is the orchestrator's business.
* It is NOT language-aware. The command is a string the project wrote; the
  verdict is its exit code (the toolchain declaration's standing law). A shell
  script under a ``Makefile`` project is as first-class as pytest.
* It parses NOTHING for a verdict. The one thing it reads out of the command's
  stdout is an OPTIONAL line of JSON naming the scenarios the command covered
  — and that line can only ever make the completion rule stricter to satisfy,
  never turn a non-zero exit into a pass.

THE DECLARATION IS READ FROM THE MAIN CHECKOUT
----------------------------------------------
``toolchain.feature_check`` is read from ``self.repo_root`` — the canonical
tree the build never edits — exactly as twin coverage reads its enforcement
flag. A build that could rewrite its own final check would not be checked.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from guardkit.orchestrator.toolchain_declaration import load_toolchain_declaration

logger = logging.getLogger(__name__)


#: Bounded retry budget for the whole-feature check, mirroring
#: ``GUARDKIT_SMOKE_GATE_MAX_RETRIES``. Default 1: one repair round.
MAX_RETRIES_ENV = "GUARDKIT_FEATURE_CHECK_MAX_RETRIES"
DEFAULT_MAX_RETRIES = 1

#: Where the receipt lands, relative to the built tree — beside the twin
#: coverage receipt, in the orchestrator's own private directory.
RECEIPT_RELATIVE_PATH = (
    Path(".guardkit") / "autobuild-private" / "feature_check.json"
)

#: The optional stdout line the command may print to name what it covered:
#: ``{"guardkit_feature_check": {"scenarios_covered": ["...", "..."]}}``
STDOUT_JSON_KEY = "guardkit_feature_check"

#: The three outcomes of one attempt, by name (2026-09-21). "Not checked" is
#: never one of them: it is a LIST carried beside the outcome, and nothing that
#: was not checked is ever recorded as passed.
OUTCOME_PASSED = "passed"
OUTCOME_FAILED = "failed"
OUTCOME_COULD_NOT_RUN = "could_not_run"

#: Caps on the text the project hands back. Central code carries this text and
#: never reads, compares or judges it, so the only thing it owes the reader is
#: a bound: a project cannot flood a card or a record.
MAX_OBSERVATIONS = 6
OBSERVATION_SIDE_LIMIT = 400
MAX_NOT_CHECKED_CARRIED = 50
NOT_CHECKED_NAME_LIMIT = 300
NOT_CHECKED_REASON_LIMIT = 300
CUT_MARK = " …[cut]"

#: Said on the record when the project declared "could not run" without saying
#: why. A reason is expected; its absence is stated rather than invented.
COULD_NOT_RUN_WITHOUT_REASON = "the project's check said it could not run and gave no reason"

#: How much of the command's output the Player is shown on a failure.
OUTPUT_TAIL_LINES = 40

#: The heading a task document uses to carry the request's own words. Written
#: by the planning leg; absent in older task documents, which is not an error.
REQUEST_WORDS_HEADING = "The words of the request this task serves"


# =========================================================================
# Declaration
# =========================================================================


@dataclass(frozen=True)
class FeatureCheckDeclaration:
    """What the project declared: one command and its time bound."""

    command: str
    timeout: int


def load_feature_check_declaration(
    repo_root: Path,
) -> Optional[FeatureCheckDeclaration]:
    """Read ``toolchain.feature_check`` from the MAIN checkout.

    Returns ``None`` when the project declared nothing — every repo that has
    not opted in behaves exactly as it did before this module existed. Never
    raises: a malformed declaration is already logged loudly by
    :func:`load_toolchain_declaration` and degrades to "undeclared".
    """
    try:
        declaration = load_toolchain_declaration(Path(repo_root))
    except Exception as exc:  # noqa: BLE001 — a broken config never crashes a build
        logger.warning("feature check: could not read the declaration: %s", exc)
        return None
    if declaration is None:
        return None
    command = (declaration.feature_check or "").strip()
    if not command:
        return None
    return FeatureCheckDeclaration(
        command=command, timeout=int(declaration.feature_check_timeout)
    )


def resolve_max_retries(environ: Optional[Dict[str, str]] = None) -> int:
    """How many times the last wave may be re-entered. Never raises."""
    source = os.environ if environ is None else environ
    try:
        return max(0, int(source.get(MAX_RETRIES_ENV, str(DEFAULT_MAX_RETRIES))))
    except (TypeError, ValueError):
        return DEFAULT_MAX_RETRIES


def candidate_sha(worktree_root: Path) -> str:
    """The worktree's HEAD at check time, or ``"unknown"``.

    Unknown is a word, not a crash: a tree that is not a git checkout can
    still run its own check, and the receipt says plainly what it could not
    pin.
    """
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(worktree_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception as exc:  # noqa: BLE001 — a missing git is not a build failure
        logger.warning("feature check: could not read the candidate sha: %s", exc)
        return "unknown"
    if proc.returncode != 0:
        return "unknown"
    return (proc.stdout or "").strip() or "unknown"


# =========================================================================
# Attempts and the receipt
# =========================================================================


@dataclass
class FeatureCheckAttempt:
    """One run of the declared check (or one twin-coverage refusal)."""

    attempt: int
    command: str
    candidate_sha: str
    passed: bool
    exit_code: Optional[int] = None
    timed_out: bool = False
    duration_seconds: float = 0.0
    stdout_tail: str = ""
    stderr_tail: str = ""
    failure_reason: Optional[str] = None
    twin_coverage: Dict[str, Any] = field(default_factory=dict)
    missing_twins: List[str] = field(default_factory=list)
    scenarios_covered: List[str] = field(default_factory=list)
    ran_at: str = ""
    #: One of :data:`OUTCOME_PASSED`, :data:`OUTCOME_FAILED`,
    #: :data:`OUTCOME_COULD_NOT_RUN`. Empty means "read it off ``passed``",
    #: which is how every attempt written before 2026-09-21 reads.
    outcome: str = ""
    could_not_run_reason: Optional[str] = None
    not_checked: List[Dict[str, str]] = field(default_factory=list)
    not_checked_total: int = 0
    observations: List[Dict[str, str]] = field(default_factory=list)
    observations_total: int = 0
    notes: List[str] = field(default_factory=list)

    @property
    def resolved_outcome(self) -> str:
        if self.outcome:
            return self.outcome
        return OUTCOME_PASSED if self.passed else OUTCOME_FAILED

    @property
    def could_not_run(self) -> bool:
        return self.resolved_outcome == OUTCOME_COULD_NOT_RUN

    def covered_minus_not_checked(
        self, also_not_checked: Sequence[Dict[str, str]] = ()
    ) -> List[str]:
        """What this attempt covered, minus anything named as not checked.

        The rule the record's top-level covered list already follows, applied
        to the copy inside the attempt — the shape every reader written before
        today picks up. A name can never be on both lists, whichever list a
        reader happens to read.
        """
        blocked = {
            str(e.get("name", "")).strip().lower()
            for e in list(self.not_checked) + list(also_not_checked or [])
            if isinstance(e, dict)
        }
        blocked.discard("")
        return [
            name
            for name in self.scenarios_covered
            if str(name).strip().lower() not in blocked
        ]

    def to_dict(
        self, also_not_checked: Sequence[Dict[str, str]] = ()
    ) -> Dict[str, Any]:
        return {
            "attempt": self.attempt,
            "command": self.command,
            "candidate_sha": self.candidate_sha,
            "passed": self.passed,
            "outcome": self.resolved_outcome,
            "could_not_run_reason": self.could_not_run_reason,
            "not_checked": [dict(e) for e in self.not_checked],
            "not_checked_total": self.not_checked_total,
            "observations": [dict(o) for o in self.observations],
            "observations_total": self.observations_total,
            "notes": list(self.notes),
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "duration_seconds": round(self.duration_seconds, 3),
            "stdout_tail": self.stdout_tail,
            "stderr_tail": self.stderr_tail,
            "failure_reason": self.failure_reason,
            "twin_coverage": self.twin_coverage,
            "missing_twins": list(self.missing_twins),
            "scenarios_covered": self.covered_minus_not_checked(also_not_checked),
            "ran_at": self.ran_at,
        }


@dataclass
class FeatureCheckOutcome:
    """Everything the receipt says, and what the finaliser reads back."""

    feature_id: str
    #: "passed" | "failed" | "could_not_run" | "not_declared" | "skipped"
    status: str
    declared: bool
    command: Optional[str] = None
    timeout: Optional[int] = None
    attempts: List[FeatureCheckAttempt] = field(default_factory=list)
    reason: Optional[str] = None
    claimed_machine_criteria: List[str] = field(default_factory=list)
    #: Everything nothing looked at, by name and reason. Fed from the central
    #: guard, from the project's own line and from the completion rule. A name
    #: on this list is NEVER on :attr:`scenarios_covered`.
    not_checked: List[Dict[str, str]] = field(default_factory=list)
    not_checked_total: int = 0
    observations: List[Dict[str, str]] = field(default_factory=list)
    observations_total: int = 0
    could_not_run_reason: Optional[str] = None
    notes: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == OUTCOME_PASSED

    @property
    def could_not_run(self) -> bool:
        return self.status == OUTCOME_COULD_NOT_RUN

    @property
    def scenarios_covered(self) -> List[str]:
        """What a PASSING attempt said it covered, minus anything not checked.

        The second half is the rule that matters: a name the record also
        carries as not checked can never be read back as covered, whatever the
        project printed.
        """
        covered: List[str] = []
        for attempt in reversed(self.attempts):
            if attempt.passed:
                covered = list(attempt.scenarios_covered)
                break
        if not covered or not self.not_checked:
            return covered
        blocked = {
            str(e.get("name", "")).strip().lower()
            for e in self.not_checked
            if isinstance(e, dict)
        }
        return [name for name in covered if name.strip().lower() not in blocked]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature": self.feature_id,
            "what": (
                "The whole-feature check: the one command this project "
                "declared (toolchain.feature_check in .guardkit/config.yaml, "
                "read from the main checkout) that proves the feature does "
                "what was asked at the surface the person uses. Exit 0 is the "
                "only pass. Every attempt is listed, including the wave "
                "re-entries the failures paid for."
            ),
            "status": self.status,
            "declared": self.declared,
            "command": self.command,
            "timeout": self.timeout,
            "generated_at": datetime.now().isoformat(),
            "reason": self.reason,
            "scenarios_covered": self.scenarios_covered,
            "not_checked": [dict(e) for e in self.not_checked],
            "not_checked_total": max(
                int(self.not_checked_total or 0), len(self.not_checked)
            ),
            "observations": [dict(o) for o in self.observations],
            "observations_total": max(
                int(self.observations_total or 0), len(self.observations)
            ),
            "could_not_run_reason": self.could_not_run_reason,
            "record_notes": list(self.notes),
            "criteria_still_claimed": list(self.claimed_machine_criteria),
            # Every attempt's covered list is filtered by the record's
            # not-checked list as well as its own, so the two lists never
            # both claim the same example anywhere in the record.
            "attempts": [a.to_dict(self.not_checked) for a in self.attempts],
        }


def write_feature_check_receipt(outcome: FeatureCheckOutcome, root: Path) -> Path:
    """Write the receipt into the built tree; return its path."""
    receipt_path = Path(root) / RECEIPT_RELATIVE_PATH
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(outcome.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    return receipt_path


def update_feature_check_receipt(
    root: Path,
    *,
    not_checked: Optional[Sequence[Dict[str, str]]] = None,
    notes: Optional[Sequence[str]] = None,
) -> Optional[Path]:
    """Finish the record on disk, after the last thing that learns anything.

    The record is written inside the build, before the completion rule and the
    end-of-build guard have run. Those two are the last sources of "nothing
    looked at this", so the record on disk would be incomplete without this
    call — and the runner exports it straight afterwards. Adding a name here
    also REMOVES it from ``scenarios_covered``: the two lists can never both
    claim the same example.

    Never raises: a record that cannot be read or written is logged and the
    build is unaffected. Returns the path when it wrote, ``None`` otherwise.
    """
    path = Path(root) / RECEIPT_RELATIVE_PATH
    additions = list(not_checked or [])
    extra_notes = [str(n) for n in (notes or []) if str(n).strip()]
    if not additions and not extra_notes:
        return None
    try:
        if not path.is_file():
            logger.warning(
                "feature check: no record at %s to finish, so the "
                "not-checked list could not be recorded", path,
            )
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        merged = merge_not_checked(data.get("not_checked"), additions)
        data["not_checked"] = merged
        data["not_checked_total"] = max(
            int(data.get("not_checked_total") or 0), len(merged)
        )
        blocked = {e["name"].strip().lower() for e in merged}

        def _minus_blocked(names: Any) -> Any:
            if not isinstance(names, list):
                return names
            return [
                name
                for name in names
                if not (isinstance(name, str) and name.strip().lower() in blocked)
            ]

        data["scenarios_covered"] = _minus_blocked(data.get("scenarios_covered"))
        # The copy inside each attempt follows the same rule: a reader that
        # picks up the attempt rather than the top of the record must not be
        # told an example was covered that this list says nothing looked at.
        attempts = data.get("attempts")
        if isinstance(attempts, list):
            for entry in attempts:
                if isinstance(entry, dict):
                    entry["scenarios_covered"] = _minus_blocked(
                        entry.get("scenarios_covered")
                    )
        if extra_notes:
            existing_notes = data.get("record_notes")
            existing_notes = existing_notes if isinstance(existing_notes, list) else []
            data["record_notes"] = existing_notes + extra_notes
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return path
    except Exception as exc:  # noqa: BLE001 — finishing a record never fails a build
        logger.warning("feature check: could not finish %s: %s", path, exc)
        return None


def read_feature_check_receipt(root: Path) -> Optional[Dict[str, Any]]:
    """Read the receipt back, or ``None`` when there is none. Never raises."""
    path = Path(root) / RECEIPT_RELATIVE_PATH
    try:
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — an unreadable receipt is absence
        logger.warning("feature check: could not read %s: %s", path, exc)
        return None
    return data if isinstance(data, dict) else None


# =========================================================================
# Running the declared command
# =========================================================================


def tail_lines(text: str, count: int = OUTPUT_TAIL_LINES) -> str:
    """The last ``count`` lines of some output, trailing blank lines dropped."""
    return "\n".join((text or "").rstrip().splitlines()[-count:])


def parse_scenarios_covered(stdout: str) -> List[str]:
    """Read the command's optional coverage line out of its stdout.

    The line is ``{"guardkit_feature_check": {"scenarios_covered": [...]}}``.
    Anything else on stdout is ignored. This never decides pass or fail — it
    only lets a passing command say which scenarios it actually exercised, so
    the completion rule can tell a covered promise from an unproven one.
    """
    covered: List[str] = []
    for line in (stdout or "").splitlines():
        stripped = line.strip()
        if not stripped.startswith("{") or STDOUT_JSON_KEY not in stripped:
            continue
        try:
            payload = json.loads(stripped)
        except (ValueError, TypeError):
            continue
        if not isinstance(payload, dict):
            continue
        block = payload.get(STDOUT_JSON_KEY)
        if not isinstance(block, dict):
            continue
        raw = block.get("scenarios_covered")
        if not isinstance(raw, list):
            continue
        for item in raw:
            if isinstance(item, str) and item.strip() and item not in covered:
                covered.append(item)
    return covered


# -------------------------------------------------------------------------
# The rest of the project's one line (2026-09-21)
# -------------------------------------------------------------------------


def cut(text: Any, limit: int) -> str:
    """One piece of the project's text, bounded, with a visible mark when cut."""
    value = "" if text is None else str(text)
    if len(value) <= limit:
        return value
    return value[:limit] + CUT_MARK


@dataclass
class ProjectCheckLine:
    """Everything the project's one line of JSON said, read defensively.

    The project writes this line; central code carries it and never reads,
    compares or judges what is in it. Anything malformed is ignored and the
    fact that it was ignored is recorded in :attr:`notes`, because silently
    dropping what a project said is how "not checked" turns into "fine".
    """

    scenarios_covered: List[str] = field(default_factory=list)
    not_checked: List[Dict[str, str]] = field(default_factory=list)
    not_checked_total: int = 0
    observations: List[Dict[str, str]] = field(default_factory=list)
    observations_total: int = 0
    could_not_run: bool = False
    could_not_run_reason: Optional[str] = None
    notes: List[str] = field(default_factory=list)


def _read_not_checked(block: Dict[str, Any], line: ProjectCheckLine) -> None:
    raw = block.get("not_checked")
    if raw is None:
        return
    if not isinstance(raw, list):
        line.notes.append(
            "the project's not_checked was not a list, so it was ignored"
        )
        return
    entries: List[Dict[str, str]] = []
    malformed = 0
    for item in raw:
        if isinstance(item, str):
            name, reason = item, ""
        elif isinstance(item, dict):
            name = item.get("name")
            if not isinstance(name, str):
                name = item.get("scenario") if isinstance(item.get("scenario"), str) else None
            reason = item.get("reason")
            reason = reason if isinstance(reason, str) else ""
        else:
            malformed += 1
            continue
        if not isinstance(name, str) or not name.strip():
            malformed += 1
            continue
        entries.append(
            {
                "name": cut(name.strip(), NOT_CHECKED_NAME_LIMIT),
                "reason": cut(reason.strip(), NOT_CHECKED_REASON_LIMIT),
            }
        )
    if malformed:
        line.notes.append(
            f"{malformed} not_checked entr(y/ies) the project sent were "
            "malformed and were ignored"
        )
    line.not_checked_total = len(entries)
    line.not_checked = entries[:MAX_NOT_CHECKED_CARRIED]
    if line.not_checked_total > len(line.not_checked):
        line.notes.append(
            f"the project named {line.not_checked_total} not-checked "
            f"item(s); the first {len(line.not_checked)} are carried"
        )


def _read_observations(block: Dict[str, Any], line: ProjectCheckLine) -> None:
    raw = block.get("observations")
    if raw is None:
        return
    if not isinstance(raw, list):
        line.notes.append(
            "the project's observations were not a list, so they were ignored"
        )
        return
    entries: List[Dict[str, str]] = []
    malformed = 0
    for item in raw:
        if not isinstance(item, dict):
            malformed += 1
            continue
        asked = item.get("asked")
        answered = item.get("answered")
        if not isinstance(asked, str) and not isinstance(answered, str):
            malformed += 1
            continue
        entries.append(
            {
                "asked": cut(asked if isinstance(asked, str) else "", OBSERVATION_SIDE_LIMIT),
                "answered": cut(
                    answered if isinstance(answered, str) else "",
                    OBSERVATION_SIDE_LIMIT,
                ),
            }
        )
    if malformed:
        line.notes.append(
            f"{malformed} observation(s) the project sent were malformed and "
            "were ignored"
        )
    line.observations_total = len(entries)
    line.observations = entries[:MAX_OBSERVATIONS]
    if line.observations_total > len(line.observations):
        line.notes.append(
            f"the project sent {line.observations_total} observation(s); the "
            f"first {len(line.observations)} are carried"
        )


def _read_could_not_run(block: Dict[str, Any], line: ProjectCheckLine) -> None:
    raw = block.get("could_not_run")
    if raw is None:
        return
    reason: Optional[str] = None
    if isinstance(raw, bool):
        if not raw:
            return
        spare = block.get("could_not_run_reason")
        reason = spare if isinstance(spare, str) else None
    elif isinstance(raw, str):
        if not raw.strip():
            return
        reason = raw
    elif isinstance(raw, dict):
        value = raw.get("reason")
        reason = value if isinstance(value, str) else None
    else:
        line.notes.append(
            "the project's could_not_run was not a statement this could read, "
            "so it was ignored"
        )
        return
    line.could_not_run = True
    line.could_not_run_reason = (
        cut(reason.strip(), NOT_CHECKED_REASON_LIMIT)
        if isinstance(reason, str) and reason.strip()
        else COULD_NOT_RUN_WITHOUT_REASON
    )


def parse_project_check_line(stdout: str) -> ProjectCheckLine:
    """Read the whole of the project's optional line, not only what it covered.

    Never raises. A line that is not JSON, a block that is not a mapping and a
    field of the wrong shape are all ignored — and each one that is ignored
    leaves a note, so a reader can tell "the project said nothing" from "the
    project said something this could not read".
    """
    line = ProjectCheckLine()
    saw_block = False
    for raw_line in (stdout or "").splitlines():
        stripped = raw_line.strip()
        if not stripped.startswith("{") or STDOUT_JSON_KEY not in stripped:
            continue
        try:
            payload = json.loads(stripped)
        except (ValueError, TypeError):
            line.notes.append(
                "a line naming the check's key was not readable as JSON and "
                "was ignored"
            )
            continue
        if not isinstance(payload, dict):
            continue
        block = payload.get(STDOUT_JSON_KEY)
        if not isinstance(block, dict):
            line.notes.append(
                "the check's key carried something other than a block of "
                "fields, so it was ignored"
            )
            continue
        saw_block = True
        raw = block.get("scenarios_covered")
        if isinstance(raw, list):
            for item in raw:
                if (
                    isinstance(item, str)
                    and item.strip()
                    and item not in line.scenarios_covered
                ):
                    line.scenarios_covered.append(item)
        elif raw is not None:
            line.notes.append(
                "the project's scenarios_covered was not a list, so it was "
                "ignored"
            )
        _read_not_checked(block, line)
        _read_observations(block, line)
        _read_could_not_run(block, line)
    if not saw_block:
        line.notes = [n for n in line.notes if n]
    return line


def merge_not_checked(
    existing: Any,
    additions: Sequence[Dict[str, str]],
    *,
    later_reason_wins: bool = False,
) -> List[Dict[str, str]]:
    """One not-checked list out of several, first reason wins, bounded.

    Names are compared case-insensitively, exactly as the completion rule
    compares a covered name, so the same example named by two sources appears
    once, keeping the order it was first named in.

    ``later_reason_wins`` is for the one caller that knows better than the
    lists it is merging: when the whole check could not run, THAT is why every
    example was not checked, whatever an earlier source said about one of
    them. The name keeps its place in the list; only its reason is replaced.
    """
    merged: List[Dict[str, str]] = []
    at: Dict[str, int] = {}
    for position, source in enumerate((existing, additions)):
        if not isinstance(source, (list, tuple)):
            continue
        later = position == 1
        for item in source:
            if isinstance(item, str):
                item = {"name": item, "reason": ""}
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            key = name.strip().lower()
            reason = item.get("reason")
            reason = cut(
                reason.strip() if isinstance(reason, str) else "",
                NOT_CHECKED_REASON_LIMIT,
            )
            if key in at:
                if later and later_reason_wins and reason:
                    merged[at[key]]["reason"] = reason
                continue
            at[key] = len(merged)
            merged.append(
                {
                    "name": cut(name.strip(), NOT_CHECKED_NAME_LIMIT),
                    "reason": reason,
                }
            )
    return merged


def run_feature_check_command(
    command: str,
    *,
    cwd: Path,
    timeout: int,
    env_extra: Optional[Dict[str, str]] = None,
    venv_python: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the declared command in the feature worktree; report what happened.

    ``shell=True`` for the same reason the smoke gate uses it: the project
    wrote a command line, not an argv. The environment is the daemon's plus
    the four ``GUARDKIT_*`` names the check is promised, plus (when known) the
    bootstrap venv on PATH so a bare ``python`` means the project's python.
    """
    env = os.environ.copy()
    if venv_python:
        env["PATH"] = (
            str(Path(venv_python).parent) + os.pathsep + env.get("PATH", "")
        )
    env.update(env_extra or {})

    started = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "exit_code": None,
            "timed_out": True,
            "stdout": _decode(exc.stdout),
            "stderr": _decode(exc.stderr),
            "duration_seconds": time.monotonic() - started,
        }
    except OSError as exc:
        # A command that cannot even start (no such shell, unreadable cwd) is
        # a failure of the check, never a silent skip.
        return {
            "exit_code": None,
            "timed_out": False,
            "stdout": "",
            "stderr": f"the feature check command could not start: {exc}",
            "duration_seconds": time.monotonic() - started,
        }
    return {
        "exit_code": proc.returncode,
        "timed_out": False,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
        "duration_seconds": time.monotonic() - started,
    }


def _decode(stream: Any) -> str:
    if stream is None:
        return ""
    if isinstance(stream, bytes):
        return stream.decode("utf-8", errors="replace")
    return str(stream)


# =========================================================================
# The words the repair round is given
# =========================================================================


def scenario_titles(feature: Any) -> List[str]:
    """The feature's scenario titles, in the order the plan wrote them."""
    scenarios = getattr(feature, "scenarios", None) or {}
    if not isinstance(scenarios, dict):
        return []
    return [str(title) for title in scenarios]


def _request_words_from_document(text: str) -> str:
    """The block under "The words of the request this task serves", if any.

    Reads to the next Markdown heading. A task document without the heading
    contributes nothing — the heading is written by the planning leg and older
    documents simply do not have it.
    """
    lines = text.splitlines()
    collected: List[str] = []
    capturing = False
    for line in lines:
        if not capturing:
            if REQUEST_WORDS_HEADING.lower() in line.lower():
                capturing = True
            continue
        if line.lstrip().startswith("#"):
            break
        collected.append(line)
    return "\n".join(collected).strip()


def feature_request_words(feature: Any, worktree_root: Optional[Path] = None) -> str:
    """The person's own words, as the artifacts recorded them.

    The feature's description, then every task document's recorded request
    words. Never raises — an unreadable task document is simply not quoted.
    """
    parts: List[str] = []
    description = str(getattr(feature, "description", "") or "").strip()
    if description:
        parts.append(description)

    for task in getattr(feature, "tasks", None) or []:
        raw_path = getattr(task, "file_path", None)
        if not raw_path:
            continue
        candidates = [Path(raw_path)]
        if worktree_root is not None and not Path(raw_path).is_absolute():
            candidates.insert(0, Path(worktree_root) / raw_path)
        for candidate in candidates:
            try:
                if not candidate.is_file():
                    continue
                block = _request_words_from_document(
                    candidate.read_text(encoding="utf-8", errors="replace")
                )
            except Exception:  # noqa: BLE001 — quoting is best-effort
                continue
            if block and block not in parts:
                parts.append(block)
            break
    return "\n\n".join(parts).strip()


def build_feature_check_feedback(
    attempt: FeatureCheckAttempt,
    *,
    request_words: str,
    titles: Sequence[str],
) -> str:
    """Compose the Player-facing feedback for a failed whole-feature check.

    Frames it as what it is: every task passed its own checks, and the feature
    still does not do what was asked. So the words of the request and the
    scenario titles are in the feedback, not only the output tail — a Player
    told only "exit 1" will fix the command, not the feature.
    """
    if attempt.missing_twins:
        reason = (
            "the scenarios below are marked for a frozen twin and no twin "
            "file exists in the built tree"
        )
    elif attempt.timed_out:
        reason = "it timed out"
    elif attempt.exit_code is None:
        reason = "it could not run"
    else:
        reason = f"exit={attempt.exit_code}, expected=0"

    sections: List[str] = [
        "THE WHOLE-FEATURE CHECK FAILED.",
        "",
        "Every task in this feature passed its own checks, and the check this "
        "project declared for the finished feature still says no. That means "
        "the parts are right and the thing the person asked for is not "
        "working at the surface they use. Fix the feature, not the check: the "
        "check is the project's, and you must not edit it.",
        "",
        f"Check command:\n{attempt.command}",
        "",
        f"Result: {reason}",
    ]

    if attempt.missing_twins:
        sections += [
            "",
            "Scenarios with no twin file:\n"
            + "\n".join(f"  - {title}" for title in attempt.missing_twins),
        ]

    output = "\n\n".join(
        part
        for part in (
            f"stdout (last {OUTPUT_TAIL_LINES} lines):\n{attempt.stdout_tail}"
            if attempt.stdout_tail
            else "",
            f"stderr (last {OUTPUT_TAIL_LINES} lines):\n{attempt.stderr_tail}"
            if attempt.stderr_tail
            else "",
        )
        if part
    )
    sections += ["", output or "(the check produced no output)"]

    if request_words:
        sections += ["", f"The words of the request this feature serves:\n{request_words}"]
    if titles:
        sections += [
            "",
            "The scenarios this feature promised:\n"
            + "\n".join(f"  - {title}" for title in titles),
        ]
    return "\n".join(sections).strip()


# =========================================================================
# The completion rule (reads Lane C's word "claimed", defensively)
# =========================================================================

#: Keys a criterion record might carry its verdict under.
_STATUS_KEYS = ("status", "result", "verdict", "state")
#: Keys a criterion record might carry its pass-bar class under.
_CLASS_KEYS = ("pass_bar_class", "criterion_class", "bar_class", "class", "klass")
#: Keys a criterion record might carry its own name under.
_NAME_KEYS = ("criterion", "name", "title", "text", "description", "id")


def _criterion_name(record: Dict[str, Any]) -> Optional[str]:
    for key in _NAME_KEYS:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _walk_for_claimed(node: Any, found: List[str]) -> None:
    if isinstance(node, dict):
        status = next(
            (
                node.get(key)
                for key in _STATUS_KEYS
                if isinstance(node.get(key), str)
            ),
            None,
        )
        klass = next(
            (
                node.get(key)
                for key in _CLASS_KEYS
                if isinstance(node.get(key), str)
            ),
            None,
        )
        if (
            isinstance(status, str)
            and status.strip().lower() == "claimed"
            and isinstance(klass, str)
            and klass.strip().lower() == "machine"
        ):
            name = _criterion_name(node)
            if name and name not in found:
                found.append(name)
        for value in node.values():
            _walk_for_claimed(value, found)
    elif isinstance(node, list):
        for value in node:
            _walk_for_claimed(value, found)


def pass_bar_machine_criteria(
    worktree_root: Path, task_ids: Sequence[str]
) -> List[str]:
    """The machine-class promises the feature's own pass bars register.

    WHY THIS READER EXISTS (19 September 2026, found at integration). In the
    plans the factory actually writes, the promises at the delivered surface
    are not the task documents' acceptance criteria at all: they are the
    approved scenarios, registered per task in ``qa/pass-bar-<TASK-ID>.yaml``
    with ``class: machine`` and the scenario's title as ``text``. The task
    Coach never evaluates those rows, so no task receipt ever says "claimed"
    about them — and a completion rule that waited for such a receipt never
    fired. In the failed B9 build every one of these rows went unproved while
    five task Coaches approved.

    So the rule reads the pass bars themselves: every ``class: machine`` row
    of every task in the feature is a promise that only the whole-feature
    check can prove, and it counts as claimed until that check names it as
    covered. Read as plain YAML on purpose — no schema import, no raise: a
    missing, unreadable or oddly shaped pass bar registers nothing, because
    absent evidence is not evidence of a claim. ``class: operator`` rows are
    a person's to prove and are never consumed here.
    """
    names: List[str] = []
    try:
        import yaml
    except Exception:  # noqa: BLE001 — no parser, no claims
        return names
    for task_id in task_ids or []:
        try:
            path = Path(worktree_root) / "qa" / f"pass-bar-{task_id}.yaml"
            if not path.is_file():
                continue
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — unreadable is absence
            continue
        rows = data.get("criteria") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            klass = row.get("class", row.get("criterion_class"))
            if not isinstance(klass, str) or klass.strip().lower() != "machine":
                continue
            text = row.get("text")
            if isinstance(text, str) and text.strip() and text.strip() not in names:
                names.append(text.strip())
    return names


def claimed_machine_criteria(
    worktree_root: Path, task_ids: Sequence[str]
) -> List[str]:
    """Criteria a task's Coach recorded as ``claimed`` at machine class.

    DEFENSIVE BY DESIGN. The word ``claimed`` is written by the Coach's own
    evidence (the separate correction that stops a Player's promise counting
    as proof). This reader must survive a factory where that correction is not
    installed, where the receipt's shape differs, or where no receipts were
    written at all: in every one of those cases it answers "no claimed
    criteria", because absent evidence is not evidence of a claim. It never
    raises and never blocks a build on its own uncertainty.
    """
    found: List[str] = []
    # The feature's own pass bars come first: a criterion a pass bar marks
    # ``class: machine`` is a promise at a delivered surface, and no task turn
    # proves it on its own (see ``pass_bar_machine_criteria``).
    for name in pass_bar_machine_criteria(worktree_root, task_ids):
        if name not in found:
            found.append(name)
    root = Path(worktree_root) / ".guardkit" / "autobuild-private"
    for task_id in task_ids or []:
        directory = root / str(task_id)
        try:
            if not directory.is_dir():
                continue
            paths = sorted(directory.glob("*.json"))
        except Exception:  # noqa: BLE001 — absence, not a failure
            continue
        for path in paths:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001 — an unreadable receipt is absence
                continue
            try:
                _walk_for_claimed(data, found)
            except Exception:  # noqa: BLE001 — defensive to the last
                continue
    return found


def _covers(covered: Sequence[str], name: str) -> bool:
    target = name.strip().lower()
    return any(
        isinstance(item, str) and item.strip().lower() == target for item in covered
    )


@dataclass(frozen=True)
class CompletionVerdict:
    """Whether the finaliser may record this feature as completed.

    ``not_checked`` is what the rule learned and the record does not yet say:
    names nothing looked at, each with a reason. The caller adds them to the
    record before it leaves the build. They are never added to the covered
    list, and the record never calls them passed.
    """

    blocks: bool
    reason: Optional[str] = None
    not_checked: List[Dict[str, str]] = field(default_factory=list)


def completion_verdict(
    *,
    repo_root: Path,
    worktree_root: Path,
    feature: Any,
) -> CompletionVerdict:
    """May a feature with a declared whole-feature check be called completed?

    Three questions, in plain words:

    1. Did the declared check actually run and pass? No receipt, or a receipt
       that does not say passed, is not a pass.
    2. Was that pass about THIS candidate — the code in the worktree now?
    3. Are there criteria the Coach could only record as claimed (a promise at
       a delivered surface that nothing independent proved)? If so, the check
       must have named those scenarios as covered.

    A project that declared no check is unchanged: no receipt is required and
    this always answers "does not block".

    2026-09-21, two changes, and only two. A record that says the check COULD
    NOT RUN does not block: there was nothing for anyone to repair, so every
    example goes on the not-checked list with that reason instead. And a
    promise that was only claimed and never covered no longer blocks either —
    it comes back on the not-checked list, by name, so the reader is told what
    was not looked at rather than the build being refused over it. Everything
    else blocks exactly as before: no record, a record that did not pass, a
    pass about different code.
    """
    declaration = load_feature_check_declaration(repo_root)
    if declaration is None:
        return CompletionVerdict(blocks=False)

    receipt = read_feature_check_receipt(worktree_root)
    if receipt is None:
        return CompletionVerdict(
            blocks=True,
            reason=(
                "this project declares a whole-feature check "
                f"({declaration.command}) and no receipt of it was written, "
                "so nothing proved the finished feature"
            ),
        )
    status = receipt.get("status")
    if status == OUTCOME_COULD_NOT_RUN:
        reason = receipt.get("could_not_run_reason")
        reason = (
            reason.strip()
            if isinstance(reason, str) and reason.strip()
            else COULD_NOT_RUN_WITHOUT_REASON
        )
        every_example = list(scenario_titles(feature))
        for name in claimed_machine_criteria(
            worktree_root,
            [getattr(t, "id", "") for t in getattr(feature, "tasks", []) or []],
        ):
            if name not in every_example:
                every_example.append(name)
        return CompletionVerdict(
            blocks=False,
            reason=f"the project's check could not run: {reason}",
            not_checked=[
                {"name": name, "reason": reason} for name in every_example
            ],
        )
    if status != OUTCOME_PASSED:
        return CompletionVerdict(
            blocks=True,
            reason=(
                "the declared whole-feature check did not pass "
                f"(receipt status: {status!r})"
            ),
        )

    attempts = receipt.get("attempts")
    recorded_sha = None
    if isinstance(attempts, list):
        for entry in reversed(attempts):
            if isinstance(entry, dict) and entry.get("passed"):
                recorded_sha = entry.get("candidate_sha")
                break
    current_sha = candidate_sha(worktree_root)
    if (
        isinstance(recorded_sha, str)
        and recorded_sha not in ("", "unknown")
        and current_sha not in ("", "unknown")
        and recorded_sha != current_sha
    ):
        return CompletionVerdict(
            blocks=True,
            reason=(
                "the whole-feature check passed on "
                f"{recorded_sha[:12]} but the candidate is now "
                f"{current_sha[:12]}, so the pass is about different code"
            ),
        )

    claimed = claimed_machine_criteria(
        worktree_root, [getattr(t, "id", "") for t in getattr(feature, "tasks", []) or []]
    )
    if not claimed:
        return CompletionVerdict(blocks=False)

    covered = receipt.get("scenarios_covered")
    covered_list = covered if isinstance(covered, list) else []
    uncovered = [name for name in claimed if not _covers(covered_list, name)]
    if uncovered:
        # Not a block any more (21 September 2026): these names go back to the
        # caller and onto the record's not-checked list, by name. They are
        # never added to the covered list and the record never calls them
        # passed — "nothing looked at this" is said out loud instead.
        return CompletionVerdict(
            blocks=False,
            reason=(
                "these promises were only claimed, never independently "
                "proved, and the whole-feature check did not name them as "
                "covered: " + "; ".join(uncovered)
            ),
            not_checked=[
                {
                    "name": name,
                    "reason": (
                        "only claimed by the build; the project's check did "
                        "not name it as covered"
                    ),
                }
                for name in uncovered
            ],
        )
    return CompletionVerdict(blocks=False)


__all__ = [
    "MAX_RETRIES_ENV",
    "DEFAULT_MAX_RETRIES",
    "RECEIPT_RELATIVE_PATH",
    "STDOUT_JSON_KEY",
    "OUTPUT_TAIL_LINES",
    "REQUEST_WORDS_HEADING",
    "OUTCOME_PASSED",
    "OUTCOME_FAILED",
    "OUTCOME_COULD_NOT_RUN",
    "COULD_NOT_RUN_WITHOUT_REASON",
    "MAX_OBSERVATIONS",
    "OBSERVATION_SIDE_LIMIT",
    "MAX_NOT_CHECKED_CARRIED",
    "CUT_MARK",
    "ProjectCheckLine",
    "cut",
    "merge_not_checked",
    "parse_project_check_line",
    "update_feature_check_receipt",
    "CompletionVerdict",
    "FeatureCheckAttempt",
    "FeatureCheckDeclaration",
    "FeatureCheckOutcome",
    "build_feature_check_feedback",
    "candidate_sha",
    "claimed_machine_criteria",
    "pass_bar_machine_criteria",
    "completion_verdict",
    "feature_request_words",
    "load_feature_check_declaration",
    "parse_scenarios_covered",
    "read_feature_check_receipt",
    "resolve_max_retries",
    "run_feature_check_command",
    "scenario_titles",
    "tail_lines",
    "write_feature_check_receipt",
]
