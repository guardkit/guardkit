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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attempt": self.attempt,
            "command": self.command,
            "candidate_sha": self.candidate_sha,
            "passed": self.passed,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "duration_seconds": round(self.duration_seconds, 3),
            "stdout_tail": self.stdout_tail,
            "stderr_tail": self.stderr_tail,
            "failure_reason": self.failure_reason,
            "twin_coverage": self.twin_coverage,
            "missing_twins": list(self.missing_twins),
            "scenarios_covered": list(self.scenarios_covered),
            "ran_at": self.ran_at,
        }


@dataclass
class FeatureCheckOutcome:
    """Everything the receipt says, and what the finaliser reads back."""

    feature_id: str
    status: str  # "passed" | "failed" | "not_declared" | "skipped"
    declared: bool
    command: Optional[str] = None
    timeout: Optional[int] = None
    attempts: List[FeatureCheckAttempt] = field(default_factory=list)
    reason: Optional[str] = None
    claimed_machine_criteria: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    @property
    def scenarios_covered(self) -> List[str]:
        for attempt in reversed(self.attempts):
            if attempt.passed:
                return list(attempt.scenarios_covered)
        return []

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
            "criteria_still_claimed": list(self.claimed_machine_criteria),
            "attempts": [a.to_dict() for a in self.attempts],
        }


def write_feature_check_receipt(outcome: FeatureCheckOutcome, root: Path) -> Path:
    """Write the receipt into the built tree; return its path."""
    receipt_path = Path(root) / RECEIPT_RELATIVE_PATH
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(outcome.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    return receipt_path


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
    """Whether the finaliser may record this feature as completed."""

    blocks: bool
    reason: Optional[str] = None


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
    if receipt.get("status") != "passed":
        return CompletionVerdict(
            blocks=True,
            reason=(
                "the declared whole-feature check did not pass "
                f"(receipt status: {receipt.get('status')!r})"
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
        return CompletionVerdict(
            blocks=True,
            reason=(
                "these promises were only claimed, never independently "
                "proved, and the whole-feature check did not name them as "
                "covered: " + "; ".join(uncovered)
            ),
        )
    return CompletionVerdict(blocks=False)


__all__ = [
    "MAX_RETRIES_ENV",
    "DEFAULT_MAX_RETRIES",
    "RECEIPT_RELATIVE_PATH",
    "STDOUT_JSON_KEY",
    "OUTPUT_TAIL_LINES",
    "REQUEST_WORDS_HEADING",
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
