"""Baseline-green probe + Coach test-gate baseline diff (red-baseline retro, L12).

The 2026-07-08 study-tutor FEAT-VOICE-003 incident burned ~2.5h across two
autobuild runs on a task made un-passable by ONE stale pre-existing baseline
test: the worktree's suite was already red on ``main`` before wave 1, and
autobuild never checked, so the pre-existing failure was silently attributed
to whichever task's Coach first ran the full suite.

This module implements the incident's cure — a *session-scoped OBSERVATION*,
never a substitute for the human-curated F2 ledger (WS3 §3 composition rule,
pre-decided with B2):

* **Item 1 — baseline-green probe.** Run the suite once at worktree setup
  (after bootstrap, before wave 1) — the feature's own smoke command when it
  declares one, otherwise the repository's declared test command (Rich's
  ruling, 2026-09-10, so a repair with no smoke command still gets a measured
  base). That declaration is read from the repository root, never from the
  copy inside the worktree, because the worktree copy is a file the model can
  rewrite. Record the result, and which command measured it, to
  ``.guardkit/autobuild/<feature>/baseline.json``. Emit a wave-0 WARNING when
  red. Report-only — it NEVER blocks the run.

  Two rules keep the record honest, because a record here is what the Coach
  subtracts and what finalize re-runs, so an invented one is worse than none.
  First, a run that measured nothing writes NO record at all: on the declared
  path a record is written only when the run named at least one failing test,
  or passed with pytest's own "N passed" as evidence tests really ran.
  Everything else — a timeout, a command the shell could not run, a suite that
  collected nothing, an interpreter with no pytest in it (which exits 1, not
  127, and reads exactly like a failing suite) — is one warning line and
  nothing on disk. Second, a worktree is measured ONCE, and the record it
  keeps is one THIS build measured: a record this run wrote in this worktree is
  kept untouched (the ``--resume`` case, where measuring again would file the
  build's own breakage as pre-existing), while a record that was already lying
  about in the tree — a ``baseline.json`` somebody committed — is never taken
  as this build's base. See "HOW WE TELL" below for how the two are told
  apart. Third, a record that cannot be read — missing, not JSON, or JSON that
  is not an object — is one warning line and "no record", never an error that
  ends a run.
* **Item 2 — Coach test-gate baseline diff.** When the Coach's ``tests_passed``
  gate would charge a failure, charge the Player ONLY for failures that are NOT
  in ``measured baseline ∪ qa/known-failures.yaml`` (the B2 F2 ledger). A test
  that was baseline-red AND lives in a file the task authored is still charged
  (a task cannot hide behind the baseline for a test it was meant to fix).

Hard constraints (WS3 §3 / prompt):

* The measured baseline is written to ``baseline.json`` only — NEVER to the F2
  ledger (LPA-09: no Player-append path to ``qa/known-failures.yaml`` exists,
  and none is created here — this module only READS the ledger).
* B2's feature-complete ledger sweep (``completion_verification.py``) is
  UNTOUCHED — un-ledgered failures still fail completion.
* The diff only ever REMOVES false charges (the honest direction). It never
  turns a genuine regression green. When failing test IDs cannot be parsed
  (non-pytest stack output), it fails CLOSED — the charge stands.

Stack scope: the failing-test-ID extractor is pytest node-id shaped (the F2
ledger's "adapter #1" convention — see ``guardkit/qa/formats/known_failures.py``).
Other stacks (flutter/dotnet/jest) still get the pass/fail baseline + the
wave-0 warning; the ID-level diff is a future per-stack adapter. This mirrors
``stack-plugin-architecture.md``.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence, Set

from guardkit.orchestrator.stale_test_attribution import (
    extract_failing_test_lines,
    failing_test_files,
)

logger = logging.getLogger(__name__)

_BASELINE_DIFF_ENV = "GUARDKIT_AUTOBUILD_BASELINE_DIFF"
_BASELINE_FILENAME = "baseline.json"

# WHERE THE PROBE'S COMMAND CAME FROM, in the words a person reads.
#
# Two, and only two, so anyone opening baseline.json months later knows what
# the numbers mean: the feature said how to smoke itself, or the repository
# said how its tests are run. The probe records one of these strings verbatim;
# nothing parses them, so they are free to stay plain English.
SOURCE_FEATURE_SMOKE = "the feature's smoke command"
SOURCE_REPOSITORY_TEST = "the repository's declared test command"


# HOW WE TELL "WE MEASURED THIS" FROM "THIS WAS LYING ABOUT IN THE TREE".
#
# A baseline.json can arrive in a worktree two ways. This build's probe can
# write it, and then it says what this repository's tests did minutes ago on
# this build's own base. Or it can arrive WITH THE CODE, because somebody
# committed one: forge's main tracks .guardkit/autobuild/FEAT-UBS1C/baseline.json
# from July, and study-tutor's main tracks two more. They keep arriving because
# guardkit's own checkpoint commit stages untracked files, so any repository
# that does not ignore .guardkit/autobuild commits the record of every build it
# runs, and the trap then plants itself in the next build. (Stopping them being
# committed at all is a repository's own business — a line in .gitignore — and
# not something this module can do from here. This is the guard that holds
# whether or not that ever happens.)
#
# Telling the two apart matters more than anything else in this module. The
# Coach subtracts this list before charging a task with a failure, and finalize
# re-runs the command it names. An empty baseline forgives nothing. A record
# from July, measured with a different command on different code, forgives
# everything — including the regression this build has just introduced.
#
# The file's PATH cannot tell them apart: a committed record sits under the
# feature's own id whenever the feature id matches, which is exactly what
# happens when a feature is built again. Its CONTENT cannot either: a commit
# copies every word of it faithfully, this marker included.
#
# So the probe stamps every record it writes with the identity of the DIRECTORY
# it measured — the device and inode number the filesystem gives that directory
# when it is created, which no commit can carry. A record is this build's own
# only when that stamp names the very directory we are about to measure:
#
#   * the same worktree on a resumed build MATCHES (``git worktree add`` made
#     that directory once and a resume hands the same one back) — which is the
#     case the measure-once rule was built for;
#   * a record that came in with the code CANNOT match, because it was written
#     in some other directory, on some other day; and
#   * neither can one left behind by an earlier build at the same path, because
#     removing and re-adding a worktree makes a brand new directory.
#
# The honest limit: an inode number can be reused after a directory is deleted,
# so a freak match is possible. It would need the same repository, the same
# feature, the same path and that reused number, and the worst it could do is
# what this file did for everyone before the stamp existed — trust the previous
# build's record.
_MEASURED_IN_DIRECTORY = "directory_id"


def worktree_identity(worktree_path: Path) -> dict:
    """Who this directory is, in facts a commit cannot carry.

    ``{"worktree": "<path>", "directory_id": "<device>:<inode>"}``. The path is
    there so a person opening baseline.json can see where it was measured;
    the device and inode are the filesystem's own name for that directory, and
    they are what the comparison actually uses — two directories never share
    them at the same time, and a fresh worktree always gets a new pair.

    Never raises. When the directory cannot be looked at, the identity comes
    back with no ``directory_id`` at all, and an identity with no
    ``directory_id`` matches nothing — the honest direction, because "we could
    not tell" is not evidence that a record is ours.
    """
    path = Path(worktree_path)
    identity = {"worktree": str(path)}
    try:
        stat = path.stat()
    except OSError:
        return identity
    identity[_MEASURED_IN_DIRECTORY] = f"{stat.st_dev}:{stat.st_ino}"
    return identity


def baseline_measured_here(
    result: "BaselineResult", worktree_path: Path
) -> bool:
    """Did a run in THIS worktree directory measure ``result``?

    True only when the record carries a directory stamp and it names the
    directory being asked about. Everything else is False: a record with no
    stamp (written before the stamp existed, or by hand), a record stamped in
    another directory (the committed one), or a directory we cannot look at.
    False is the safe answer — it means "measure the base yourself", never
    "trust this".
    """
    stamped = getattr(result, "measured_in", None)
    if not isinstance(stamped, dict):
        return False
    theirs = str(stamped.get(_MEASURED_IN_DIRECTORY) or "")
    ours = str(worktree_identity(worktree_path).get(_MEASURED_IN_DIRECTORY) or "")
    return bool(theirs) and theirs == ours


def baseline_diff_enabled() -> bool:
    """Whether the Coach test-gate baseline diff is active (default ON).

    Kill-switch: ``GUARDKIT_AUTOBUILD_BASELINE_DIFF=0`` (or ``false``/``off``/
    ``no``). Default ON because the diff only removes *false* charges — the
    honest direction. Documented in the WS3 §3 calibration note.
    """
    raw = os.environ.get(_BASELINE_DIFF_ENV)
    if raw is None:
        return True
    return raw.strip().lower() not in {"0", "false", "off", "no"}


def to_node_id(failing_line: str) -> str:
    """Normalise a ``"FAILED path::test - reason"`` line to a bare node id.

    ``extract_failing_test_lines`` already drops the `` - <reason>`` suffix and
    yields ``"FAILED <node>"`` / ``"ERROR <node>"``; this strips the leading
    verdict word so baseline / ledger / observed IDs compare apples-to-apples.
    """
    parts = failing_line.split(None, 1)
    if len(parts) == 2 and parts[0] in {"FAILED", "ERROR"}:
        return parts[1].strip()
    return failing_line.strip()


def failing_node_ids(output: Optional[str]) -> List[str]:
    """Pytest failing node IDs parsed from runner output (deduped, in order)."""
    seen: Set[str] = set()
    ids: List[str] = []
    for line in extract_failing_test_lines(output):
        node = to_node_id(line)
        if node and node not in seen:
            seen.add(node)
            ids.append(node)
    return ids


@dataclass
class BaselineResult:
    """The measured baseline suite outcome — a session-scoped observation."""

    command: str
    expected_exit: int
    passed: bool
    exit_code: Optional[int]
    failing_node_ids: List[str] = field(default_factory=list)
    failing_count: int = 0
    timestamp: str = ""
    # Where the command came from, in plain words (one of the SOURCE_*
    # constants above). Empty on a record written before this field existed,
    # or one built by hand in a test — never a reason to fail.
    source: str = ""
    # Which directory this record was measured in — the probe's stamp, and the
    # only thing that separates "we measured this" from "this was committed
    # into the repository months ago". See "HOW WE TELL" above. Empty on any
    # record this probe did not write, which is exactly how it should read.
    measured_in: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "expected_exit": self.expected_exit,
            "passed": self.passed,
            "exit_code": self.exit_code,
            "failing_node_ids": list(self.failing_node_ids),
            "failing_count": self.failing_count,
            "timestamp": self.timestamp,
            "source": self.source,
            "measured_in": dict(self.measured_in),
            # A loud marker that this is NOT the F2 ledger (LPA-09).
            "note": (
                "session-scoped observation; NOT the qa/known-failures.yaml "
                "ledger; used only to suppress mid-build mis-attribution"
            ),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BaselineResult":
        return cls(
            command=str(data.get("command", "")),
            expected_exit=int(data.get("expected_exit", 0)),
            passed=bool(data.get("passed", True)),
            exit_code=data.get("exit_code"),
            failing_node_ids=[str(x) for x in (data.get("failing_node_ids") or [])],
            failing_count=int(data.get("failing_count", 0)),
            timestamp=str(data.get("timestamp", "")),
            source=str(data.get("source", "")),
            measured_in=(
                dict(data.get("measured_in"))
                if isinstance(data.get("measured_in"), dict)
                else {}
            ),
        )


def feature_baseline_path(state_root: Path, feature_id: str) -> Path:
    """``<state_root>/.guardkit/autobuild/<feature_id>/baseline.json``."""
    return (
        Path(state_root)
        / ".guardkit"
        / "autobuild"
        / feature_id
        / _BASELINE_FILENAME
    )


def write_baseline(path: Path, result: BaselineResult) -> None:
    """Persist ``result`` to ``path`` (atomic tmp + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    tmp.replace(path)


def load_baseline_file(path: Path) -> Optional[BaselineResult]:
    """Read ONE ``baseline.json``, or ``None`` when it cannot be read.

    Anything at all wrong with the file reads as "there is no record": it is
    not there, it cannot be opened, it is not JSON, it is JSON but not an
    object (``[]``, ``"nope"``, ``3``, ``null``), or a field in it is the wrong
    shape. Every one of those is ONE warning line and ``None``. A file that is
    simply absent is not even that — the ordinary case says nothing.

    This function can never raise, and that is the whole point of it. The probe
    is report-only and must never end a run, but until this guard existed a
    baseline.json holding ``[]`` reached ``BaselineResult.from_dict``, which
    asked a list for ``.get`` and killed the build before wave 1. A record
    nobody can read must cost a warning, not a build.
    """
    candidate = Path(path)
    if not candidate.is_file():
        return None
    try:
        data = json.loads(candidate.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(
                "a baseline record must be a JSON object, and this one is "
                f"a {type(data).__name__}"
            )
        return BaselineResult.from_dict(data)
    except Exception as exc:  # noqa: BLE001 — a record nobody can read is "no record"
        logger.warning(
            "Baseline record at %s could not be read (%s). Carrying on as if "
            "there were no record at all — nothing is treated as this build's "
            "measured base.",
            candidate, exc,
        )
        return None


def read_baseline_from_worktree(worktree_path: Path) -> Optional[BaselineResult]:
    """Find and load the feature ``baseline.json`` under a worktree, if any.

    Globs ``.guardkit/autobuild/*/baseline.json`` (only the feature dir carries
    a ``baseline.json``; task dirs carry ``task_work_results.json``). Returns
    ``None`` when absent / unreadable (fail open — the diff is simply inert),
    and an unreadable one costs a warning, never an exception.

    When the worktree holds MORE THAN ONE record, a record stamped as measured
    in this very worktree beats one that is not (see ``baseline_measured_here``).
    That is not a nicety: a repository that tracks an old build's baseline.json
    — forge tracks FEAT-UBS1C's from July, study-tutor tracks two — hands every
    later build a stale record filed under some other feature's id, and this
    glob would otherwise hand whichever sorts first to the Coach and to
    finalize. This build's own measurement wins. With nothing stamped, the
    first readable record is returned exactly as it always was.
    """
    root = Path(worktree_path) / ".guardkit" / "autobuild"
    if not root.is_dir():
        return None
    try:
        matches = sorted(root.glob(f"*/{_BASELINE_FILENAME}"))
    except OSError:
        return None
    unstamped: Optional[BaselineResult] = None
    for candidate in matches:
        record = load_baseline_file(candidate)
        if record is None:
            continue
        if baseline_measured_here(record, worktree_path):
            return record
        if unstamped is None:
            unstamped = record
    return unstamped


def load_known_failure_ids(worktree_root: Path) -> Set[str]:
    """Read the F2 ledger's known-failure ``test_id``s (READ-ONLY, fail open).

    Parses ``<worktree_root>/qa/known-failures.yaml`` leniently — any error
    (missing file, bad YAML, no PyYAML) yields an empty set. This module NEVER
    writes the ledger (LPA-09); it only consults it to avoid charging a
    human-triaged known failure.
    """
    ledger_path = Path(worktree_root) / "qa" / "known-failures.yaml"
    if not ledger_path.exists():
        return set()
    try:
        import yaml  # lazy — optional dependency in some envs
    except ImportError:
        logger.debug("baseline diff: PyYAML unavailable; F2 ledger not consulted")
        return set()
    try:
        data = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):  # type: ignore[attr-defined]
        return set()
    if not isinstance(data, dict):
        return set()
    ids: Set[str] = set()
    for entry in data.get("known_failures") or []:
        if isinstance(entry, dict):
            tid = entry.get("test_id")
            if isinstance(tid, str) and tid.strip():
                ids.add(tid.strip())
    return ids


def compute_charged_failures(
    observed_node_ids: Sequence[str],
    baseline_node_ids: Sequence[str],
    ledger_ids: Set[str],
    authored_test_files: Sequence[str] = (),
) -> List[str]:
    """The failures the current task is actually charged for.

    ``observed - (baseline ∪ ledger)``, PLUS any excused (baseline/ledger)
    failure whose test *file* the current task authored — a task cannot hide
    behind the baseline for a test it was meant to fix (the retro's
    "fixed-then-still-red is charged" constraint).

    All comparisons are on bare pytest node IDs. Returns the charged node IDs
    in first-seen order.
    """
    excused = set(baseline_node_ids) | set(ledger_ids)
    authored = {str(f) for f in authored_test_files}
    charged: List[str] = []
    seen: Set[str] = set()
    for node in observed_node_ids:
        if node in seen:
            continue
        seen.add(node)
        if node not in excused:
            charged.append(node)
            continue
        # Excused by the baseline/ledger — but re-charge if the task authored
        # the failing test's file (it claimed responsibility for it).
        test_file = node.split("::", 1)[0]
        if test_file in authored:
            charged.append(node)
    return charged


def probe_baseline_result(
    command: str,
    expected_exit: int,
    passed: bool,
    exit_code: Optional[int],
    output: Optional[str],
    timestamp: str,
    source: str = "",
    measured_in: Optional[dict] = None,
) -> BaselineResult:
    """Assemble a :class:`BaselineResult` from an executed smoke/test run.

    ``output`` is the combined stdout/stderr of the run; failing node IDs are
    pytest-parsed from it (empty for non-pytest stacks — the pass/fail signal
    still drives the wave-0 warning).

    ``source`` says where the command came from, in the words a person reads
    (one of the ``SOURCE_*`` constants). It defaults to empty so a caller that
    does not know stays exactly as it was.

    ``measured_in`` is the stamp that says which directory this run measured —
    ``worktree_identity(<worktree>)``. It defaults to empty, and an empty stamp
    reads as "this is not a record anybody can claim to have measured", which
    is the right answer for a record built by hand.
    """
    ids = failing_node_ids(output)
    return BaselineResult(
        command=command,
        expected_exit=expected_exit,
        passed=passed,
        exit_code=exit_code,
        failing_node_ids=ids,
        failing_count=len(ids),
        timestamp=timestamp,
        source=source,
        measured_in=dict(measured_in or {}),
    )


def wave0_baseline_warning(result: BaselineResult) -> Optional[str]:
    """The wave-0 warning string for a red baseline, or ``None`` when green.

    "N pre-existing failures — not attributable to any task", listing the
    parsed failing IDs (or a count when the stack's IDs weren't parseable).
    """
    if result.passed:
        return None
    n = result.failing_count if result.failing_count else "one or more"
    header = (
        f"BASELINE RED: {n} pre-existing test failure(s) in the feature suite "
        f"BEFORE wave 1 — not attributable to any task in this feature "
        f"(command: {result.command}, exit={result.exit_code})."
    )
    if result.failing_node_ids:
        listing = "\n".join(f"    - {nid}" for nid in result.failing_node_ids)
        return f"{header}\n{listing}"
    return (
        f"{header} (individual test IDs not parseable for this stack; the "
        f"pass/fail baseline is still recorded)."
    )


def now_isoformat() -> str:
    """Timestamp helper (isolated so tests can monkeypatch it)."""
    return datetime.now().isoformat()
