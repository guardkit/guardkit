"""Tier-1 QA enforcement (session B2, 2026-07-08) — flag-gated, default OFF.

Design source (binding): ai-transition/docs/ws2-qa-verifier-and-last-mile-
build-plan-2026-07-07.md §B2. This module keeps two refusals, both keyed on ``qa.enforce_tier1``
(``.guardkit/config.yaml``, default ``False``; env override
``GUARDKIT_QA_ENFORCE_TIER1``):

1. **Ledger sweep at completion** — the completion suite result is diffed
   against ``qa/known-failures.yaml`` (F2). A test that ran and failed and is
   not in the ledger refuses completion. :func:`diff_failures_against_ledger` +
   :func:`parse_pytest_outcome`. (The cull of 27 October 2026 removed the
   refusals that read only the record's form: a missing, unreadable or
   mismatched pass-bar file, a ledger entry that unexpectedly passed, and a
   malformed ledger file, which is now read as an empty ledger.)

2. **Plan-time ledger-authorship reject-lint** — a headless ``/feature-spec`` /
   ``/feature-plan`` session whose diff adds or modifies ``qa/known-failures.yaml``
   is refused, because the ledger excuses real failures in refusal 1.
   :func:`check_plan_does_not_author_ledger` (pure; consumes a changed-path
   set) + :func:`git_changed_paths`. Wired at ``guardkit feature validate``.

Guardrails honoured (WS2 build-plan §B2):

- The F2 ledger is written by human/Coach at triage ONLY. **No function in this
  module writes the ledger** — it is read-only here (LPA-09; a mid-build Player
  append would neuter the whole point of the ledger). Refusal 2 extends that
  writer restriction explicitly to headless planners (K15): the ledger stays
  writable by nothing automated.
- No F1–F5 semantic changes: this module *consumes* ``guardkit.qa.formats``
  (including PB-14's ``auth_surface_bearing`` + the exported
  ``AUTH_/UNIVERSAL_/REQUIRED_NEGATIVE_PATHS`` sets), it does not reopen them.
- Only a test that ran and failed drives a refusal; a suite that produced no
  run signal is never fabricated into a fail.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Sequence, Tuple

import yaml

from guardkit.qa.formats import (
    KnownFailureLedger,
    QAFormatError,
    validate_instance,
)
from guardkit.lib.project_git import run_git

logger = logging.getLogger(__name__)

__all__ = [
    "ENFORCE_ENV",
    "is_tier1_enforced",
    "PytestOutcome",
    "parse_pytest_outcome",
    "LedgerSweepResult",
    "diff_failures_against_ledger",
    "LEDGER_RELPATH",
    "LedgerAuthorshipResult",
    "check_plan_does_not_author_ledger",
    "git_changed_paths",
]

#: Env override for the tier-1 enforcement flag. When set to a truthy value it
#: wins over ``.guardkit/config.yaml``; when set to a falsy value it forces OFF.
ENFORCE_ENV = "GUARDKIT_QA_ENFORCE_TIER1"

_TRUTHY = frozenset({"1", "true", "yes", "on"})
_FALSY = frozenset({"0", "false", "no", "off", ""})



def _load_config(repo_root: Path) -> dict:
    """Read ``<repo_root>/.guardkit/config.yaml``; empty dict if absent/unreadable."""
    path = repo_root / ".guardkit" / "config.yaml"
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError) as exc:
        logger.warning("qa.enforce_tier1: could not read %s (%s) — treating as OFF", path, exc)
        return {}
    return data if isinstance(data, dict) else {}


def is_tier1_enforced(repo_root: Path) -> bool:
    """Return whether tier-1 QA enforcement is on for ``repo_root``.

    Precedence: ``GUARDKIT_QA_ENFORCE_TIER1`` env var (truthy/falsy) >
    ``.guardkit/config.yaml`` ``qa.enforce_tier1`` > ``False``.

    Default OFF everywhere (WS2 build-plan §B2): a repo flips the flag as an
    explicit V1/V2 step; nothing is enforced fleet-wide by default.
    """
    env = os.environ.get(ENFORCE_ENV)
    if env is not None:
        token = env.strip().lower()
        if token in _TRUTHY:
            return True
        if token in _FALSY:
            return False
        logger.warning(
            "%s=%r is not a recognised boolean — treating as OFF", ENFORCE_ENV, env
        )
        return False
    qa = _load_config(repo_root).get("qa")
    if not isinstance(qa, dict):
        return False
    return bool(qa.get("enforce_tier1", False))


# ---------------------------------------------------------------------------
# 1. Ledger sweep at completion (F2)
# ---------------------------------------------------------------------------

# pytest's "short test summary info" lines — the tail of a run enumerates every
# non-pass outcome as ``FAILED <nodeid> - ...`` / ``ERROR <nodeid> - ...``.
_PYTEST_FAILED_RE = re.compile(r"^(?:FAILED|ERROR)\s+(\S+)", re.MULTILINE)
_PYTEST_PASSED_COUNT_RE = re.compile(r"\b(\d+)\s+passed\b")
_PYTEST_FAILED_COUNT_RE = re.compile(r"\b(\d+)\s+failed\b")
_PYTEST_ERROR_COUNT_RE = re.compile(r"\b(\d+)\s+errors?\b")


@dataclass(frozen=True)
class PytestOutcome:
    """Parsed pytest text-output signal used by the ledger diff.

    ``ran`` is the positive-evidence flag: a run with a passed/failed/error
    count is evidence the suite executed. A text blob with no summary at all is
    ``ran=False`` (absent signal — never diffed into a fail).
    """

    failing_ids: Tuple[str, ...]
    passed: Optional[int]
    failed: Optional[int]
    errored: Optional[int]
    ran: bool


def parse_pytest_outcome(output: str) -> PytestOutcome:
    """Parse failing node ids + summary counts from pytest text output.

    Robust to being handed only the tail of a run: pytest prints its
    ``FAILED``/``ERROR`` summary and its ``N passed, M failed`` line at the very
    end, so the tail is exactly where the diff-relevant signal lives.
    """
    output = output or ""
    failing = tuple(dict.fromkeys(_PYTEST_FAILED_RE.findall(output)))

    def _count(pattern: re.Pattern) -> Optional[int]:
        m = pattern.search(output)
        return int(m.group(1)) if m else None

    passed = _count(_PYTEST_PASSED_COUNT_RE)
    failed = _count(_PYTEST_FAILED_COUNT_RE)
    errored = _count(_PYTEST_ERROR_COUNT_RE)
    ran = any(c is not None for c in (passed, failed, errored)) or bool(failing)
    return PytestOutcome(
        failing_ids=failing,
        passed=passed,
        failed=failed,
        errored=errored,
        ran=ran,
    )


@dataclass(frozen=True)
class LedgerSweepResult:
    """Outcome of diffing a completion run against the F2 ledger.

    ``status``:
      - ``"pass"``       — every failure that ran is in the ledger.
      - ``"fail"``       — a test ran and failed and is not in the ledger.
      - ``"unverified"`` — the suite produced no run signal; never a fail.
    """

    status: str
    unledgered_failures: Tuple[str, ...]
    detail: str

    @property
    def passed(self) -> bool:
        return self.status == "pass"


def diff_failures_against_ledger(
    outcome: PytestOutcome,
    ledger_path: Path,
) -> LedgerSweepResult:
    """Diff a parsed pytest outcome against the F2 ledger at ``ledger_path``.

    A failing test id not present in the ledger fails the sweep. If the summary
    reports failed/errored counts but fewer ids could be named, the unnamed
    failures are not in the ledger either, so they fail the sweep too.

    A missing or unreadable ledger file is read as an empty ledger (zero known
    failures): a green suite passes, any failure is un-ledgered.
    """
    if not outcome.ran:
        return LedgerSweepResult(
            status="unverified",
            unledgered_failures=(),
            detail="ledger sweep skipped: no evidence the suite ran",
        )

    ledger: Optional[KnownFailureLedger] = None
    if ledger_path.is_file():
        try:
            ledger = validate_instance("known-failures", ledger_path)  # type: ignore[assignment]
        except QAFormatError as exc:
            logger.warning(
                "known-failure ledger %s is unreadable (%s); reading it as empty",
                ledger_path,
                exc,
            )

    ledgered_ids = {e.test_id for e in ledger.known_failures} if ledger else set()

    failing = set(outcome.failing_ids)
    unledgered = tuple(sorted(failing - ledgered_ids))

    fail_count = (outcome.failed or 0) + (outcome.errored or 0)
    unnamed = max(fail_count - len(failing), 0)

    problems: List[str] = []
    if unledgered:
        problems.append(
            f"{len(unledgered)} un-ledgered failure(s): {', '.join(unledgered)}"
        )
    if unnamed:
        problems.append(
            f"{fail_count} failure(s)/error(s) reported but only "
            f"{len(failing)} named by a test id; the unnamed ones are not in "
            f"the ledger"
        )

    if problems:
        return LedgerSweepResult(
            status="fail",
            unledgered_failures=unledgered,
            detail="known-failure ledger sweep FAILED — " + "; ".join(problems),
        )

    return LedgerSweepResult(
        status="pass",
        unledgered_failures=(),
        detail=f"ledger sweep clean: {len(failing)} failure(s), all ledgered",
    )


# ---------------------------------------------------------------------------
# Shared git runner
# ---------------------------------------------------------------------------


def _default_git(repo_root: Path) -> Callable[[Sequence[str]], subprocess.CompletedProcess]:
    def _run(args: Sequence[str]) -> subprocess.CompletedProcess:
        return run_git(
            ["-C", str(repo_root), *args],
            timeout=30,
        )

    return _run


# ---------------------------------------------------------------------------
# 2. Plan-time ledger-authorship reject-lint (F2 · K15 / LPA-09)
# ---------------------------------------------------------------------------

#: The canonical repo-relative F2 known-failure ledger path. A planning session
#: (``/feature-spec`` / ``/feature-plan``) must never author it — that is
#: human/Coach-at-triage work only (K15). Matched repo-relatively so a
#: sibling-repo instance (``../other/qa/known-failures.yaml``) or a
#: repo-qualified evidence path (``repo:qa/known-failures.yaml``) is still caught.
LEDGER_RELPATH = "qa/known-failures.yaml"


@dataclass(frozen=True)
class LedgerAuthorshipResult:
    """Outcome of the plan-time known-failure-ledger authorship reject-lint.

    ``status``:
      - ``"pass"`` — the planning diff does not touch the F2 ledger.
      - ``"fail"`` — the diff adds or modifies ``qa/known-failures.yaml``; the
        offending path(s) are in ``offending_paths``.
    """

    status: str  # "pass" | "fail"
    offending_paths: Tuple[str, ...]
    detail: str

    @property
    def passed(self) -> bool:
        return self.status == "pass"


def _normalise_changed_path(raw: str) -> str:
    """Normalise a changed-path token to a posix repo-relative comparison form.

    Strips a leading evidence-repo qualifier (``<repo>:<path>``, per the
    evidence-boundary scheme), backslashes → forward slashes, and a leading
    ``./``. Windows drive letters (``C:\\...``) are left intact — the qualifier
    strip only fires for a non-path ``<token>:`` with no slash before the colon.
    """
    token = (raw or "").strip().strip('"')
    # Evidence-repo qualifier: ``<repo>:<path>`` where <repo> has no separator.
    if ":" in token:
        head, sep, tail = token.partition(":")
        if sep and "/" not in head and "\\" not in head and len(head) != 1:
            token = tail
    token = token.replace("\\", "/")
    if token.startswith("./"):
        token = token[2:]
    return token


def _is_ledger_path(normalised: str) -> bool:
    return normalised == LEDGER_RELPATH or normalised.endswith("/" + LEDGER_RELPATH)


def check_plan_does_not_author_ledger(
    changed_paths: Iterable[str],
) -> LedgerAuthorshipResult:
    """Refuse a planning-session diff that authors ``qa/known-failures.yaml``.

    Pure: ``changed_paths`` is the set of repo-relative paths a planning
    (``/feature-spec`` / ``/feature-plan``) session added or modified — e.g.
    from :func:`git_changed_paths`, a ``git diff --name-only`` list, or an
    explicit file set. FAILS if any of them is the F2 known-failure ledger.

    The F2 ledger is authored by human/Coach *at triage* only (K15 / LPA-09).
    The completion sweep checks *when* ledger entries are honoured; it does
    not check *who authored them at plan time*. A headless planner writing the
    ledger would have its invented entries silently treated as expected
    failures by the post-merge sweep (:func:`diff_failures_against_ledger`) —
    the ABL-001 false-green class through the planner channel. This lint closes
    that channel by refusing the write at the plan/spec boundary.
    """
    offenders = tuple(
        sorted(
            {
                _normalise_changed_path(cp)
                for cp in changed_paths
                if _is_ledger_path(_normalise_changed_path(cp))
            }
        )
    )
    if offenders:
        return LedgerAuthorshipResult(
            status="fail",
            offending_paths=offenders,
            detail=(
                f"planning session must not author the F2 known-failure ledger: "
                f"diff touches {', '.join(offenders)}. "
                f"qa/known-failures.yaml is written by human/Coach at triage only "
                f"(K15 / LPA-09) — a headless /feature-spec|/feature-plan session "
                f"authoring it would have its entries silently excused as expected "
                f"failures. Remove the ledger edit from this plan; triage the "
                f"failure separately. (qa.enforce_tier1 is on.)"
            ),
        )
    return LedgerAuthorshipResult(
        status="pass",
        offending_paths=(),
        detail="planning diff does not touch the F2 known-failure ledger",
    )


def git_changed_paths(
    repo_root: Path,
    *,
    git_run: Optional[Callable[[Sequence[str]], subprocess.CompletedProcess]] = None,
) -> Tuple[str, ...]:
    """Return the working-tree + staged + untracked changed paths in ``repo_root``.

    Reads ``git status --porcelain --untracked-files=all`` — which enumerates
    staged, unstaged, AND untracked changes (``--untracked-files=all`` expands a
    wholly-untracked directory to its individual files, so a planner creating
    ``qa/known-failures.yaml`` in a fresh ``qa/`` dir surfaces as the file, not a
    collapsed ``qa/`` entry) — exactly the set a planning session has produced
    before it commits. Rename entries (``R  old -> new``) contribute the
    destination path. Returns an empty tuple if git is unavailable or the command
    fails (the reject-lint then has nothing to refuse — the wiring surface is the
    loud one; a git failure here must not fabricate an offender).
    """
    run = git_run or _default_git(repo_root)
    try:
        proc = run(["status", "--porcelain", "--untracked-files=all"])
    except (OSError, subprocess.SubprocessError):
        return ()
    if proc.returncode != 0:
        return ()

    paths: List[str] = []
    for line in (proc.stdout or "").splitlines():
        if not line.strip():
            continue
        # Porcelain v1: two status chars, a space, then the path (or "old -> new").
        entry = line[3:] if len(line) > 3 else line.strip()
        if " -> " in entry:
            entry = entry.split(" -> ", 1)[1]
        entry = entry.strip().strip('"')
        if entry:
            paths.append(entry)
    return tuple(paths)
