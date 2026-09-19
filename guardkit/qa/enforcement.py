"""Tier-1 QA enforcement (session B2, 2026-07-08) — flag-gated, default OFF.

Design source (binding): ai-transition/docs/ws2-qa-verifier-and-last-mile-
build-plan-2026-07-07.md §B2. This module wires the tier-1 QA formats (F1
pass-bar, F2 known-failure ledger, F4 gate registry — built schema-only in B1)
into three refusals. All three key on ``qa.enforce_tier1`` (``.guardkit/
config.yaml``, default ``False``; env override ``GUARDKIT_QA_ENFORCE_TIER1``):

1. **Ledger post-merge sweep** — the completion suite result is diffed against
   ``qa/known-failures.yaml`` (F2). An un-ledgered failure fails the gate; an
   unexpectedly-passing *unconditional* ledger entry fails the gate (stale
   ledger is a finding). ``completion_verification.py`` is the enforcement
   home (WS2 build-plan §B2 ownership note = WS3-S4; built once, here);
   :func:`diff_failures_against_ledger` + :func:`parse_pytest_outcome` are the
   pure helpers it consumes.

2. **Coach task-start precondition** — a task cannot start without a pinned F1
   pass bar at ``qa/pass-bar-<TASK-ID>.yaml`` whose ``registered_at.sha``
   predates implementation commits (mechanically: is an ancestor of HEAD).
   :func:`check_pass_bar_precondition`.

3. **feature-complete runtime-surface refusal** — a feature whose pass bar
   declares a runtime surface (auth-surface-bearing, walk-bearing, or any
   live-evidence criterion) cannot reach feature-complete without at least one
   registered, green gate in the F4 registry. :func:`check_runtime_surface_gate`.

4. **plan-time ledger-authorship reject-lint** — a headless ``/feature-spec`` /
   ``/feature-plan`` session whose diff adds or modifies ``qa/known-failures.yaml``
   is refused. The F2 ledger is authored by human/Coach *at triage* only (K15 /
   LPA-09); the other three refusals check *when* ledger entries are honoured
   (the sweep) but never *who authored them at plan time*. A planner writing the
   ledger would have its invented entries silently treated as expected failures
   by refusal 1's sweep (the ABL-001 false-green class, planner channel).
   :func:`check_plan_does_not_author_ledger` (pure; consumes a diff / changed-path
   set) + :func:`git_changed_paths` (the working-tree + staged + untracked reader
   the wiring feeds it). Wired at ``guardkit feature validate`` — the plan-output
   oracle ``/feature-plan`` runs (feature-plan.md step 8.5) and the SPL
   FEAT-SPL-007/008 named oracle — so the lint fires on a planning session's
   outputs at the same deterministic Python surface the other refusals prefer,
   never the LLM skill markdown (DIM5-F3, DF-012 §2.5).

Guardrails honoured (WS2 build-plan §B2):

- The F2 ledger is written by human/Coach at triage ONLY. **No function in this
  module writes the ledger** — it is read-only here (LPA-09; a mid-build Player
  append would neuter the whole point of the ledger). Refusal 4 extends that
  writer restriction explicitly to headless planners (K15): the ledger stays
  writable by nothing automated.
- No F1–F5 semantic changes: this module *consumes* ``guardkit.qa.formats``
  (including PB-14's ``auth_surface_bearing`` + the exported
  ``AUTH_/UNIVERSAL_/REQUIRED_NEGATIVE_PATHS`` sets), it does not reopen them.
- Absence-of-failure-safe (``.claude/rules/absence-of-failure-is-not-success``):
  a suite that could not run, a not-collected test, or a missing/absent signal
  is never read as a pass and never fabricated into a fail. Only positive
  evidence (a test ran and failed; the suite ran green) drives a verdict.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Sequence, Tuple

import yaml

from guardkit.qa.formats import (
    GateRegistry,
    KnownFailureLedger,
    PassBar,
    QAFormatError,
    validate_instance,
)

logger = logging.getLogger(__name__)

__all__ = [
    "ENFORCE_ENV",
    "is_tier1_enforced",
    "PytestOutcome",
    "parse_pytest_outcome",
    "LedgerSweepResult",
    "diff_failures_against_ledger",
    "PassBarPreconditionResult",
    "check_pass_bar_precondition",
    "RuntimeSurfaceGateResult",
    "check_runtime_surface_gate",
    "pass_bar_path_for",
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

# The two F1 evidence kinds that only a *live* / operator surface produces — a
# pass bar carrying either declares a runtime surface (see
# ``_pass_bar_is_runtime_surface``).
_LIVE_EVIDENCE_KINDS = frozenset({"screenshot", "operator_signoff"})


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


def pass_bar_path_for(repo_root: Path, task_id: str) -> Path:
    """Canonical F1 instance path for a task (``qa/pass-bar-<TASK-ID>.yaml``)."""
    return repo_root / "qa" / f"pass-bar-{task_id}.yaml"


# ---------------------------------------------------------------------------
# 1. Ledger post-merge sweep (F2)
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
      - ``"pass"``       — every failure is ledgered; no stale entry.
      - ``"fail"``       — un-ledgered failure(s) and/or stale ledger entry.
      - ``"unverified"`` — the suite produced no positive run signal (absent);
                            never a fail (absence-of-failure-is-not-success).
      - ``"error"``      — the ledger file exists but is malformed (loud config
                            error; fails closed).
    """

    status: str
    unledgered_failures: Tuple[str, ...]
    stale_ledger_entries: Tuple[str, ...]
    detail: str

    @property
    def passed(self) -> bool:
        return self.status == "pass"


def diff_failures_against_ledger(
    outcome: PytestOutcome,
    ledger_path: Path,
) -> LedgerSweepResult:
    """Diff a parsed pytest outcome against the F2 ledger at ``ledger_path``.

    Semantics (WS2 build-plan §B2):

    - **un-ledgered failure** → FAIL: any failing test id not present in the
      ledger. If the summary reports failed/errored counts but no ids could be
      attributed, that unattributable failure also fails (a failure we cannot
      excuse is never waved through).
    - **unexpectedly-passing entry** → FAIL: an *unconditional* ledger entry
      (no ``env_condition``) that did not fail this run, when the suite ran with
      positive evidence. Entries with an ``env_condition`` are exempt — they are
      environment-specific and legitimately pass elsewhere, so flagging them
      everywhere would be a false-red.

    A missing ledger file is treated as an empty ledger (zero known failures):
    a green suite passes, any failure is un-ledgered. A present-but-malformed
    ledger is a loud config error (``status="error"``).
    """
    if not outcome.ran:
        return LedgerSweepResult(
            status="unverified",
            unledgered_failures=(),
            stale_ledger_entries=(),
            detail=(
                "ledger sweep skipped: no positive evidence the suite ran "
                "(absent signal is never a pass and never a fail)"
            ),
        )

    ledger: Optional[KnownFailureLedger] = None
    if ledger_path.is_file():
        try:
            ledger = validate_instance("known-failures", ledger_path)  # type: ignore[assignment]
        except QAFormatError as exc:
            return LedgerSweepResult(
                status="error",
                unledgered_failures=(),
                stale_ledger_entries=(),
                detail=f"ledger is malformed and cannot be diffed against: {exc}",
            )

    ledgered_ids = {e.test_id for e in ledger.known_failures} if ledger else set()
    unconditional_ids = (
        {e.test_id for e in ledger.known_failures if not e.env_condition}
        if ledger
        else set()
    )

    failing = set(outcome.failing_ids)
    unledgered = tuple(sorted(failing - ledgered_ids))

    # Unattributable failure: the summary says something failed/errored but no
    # node id surfaced (truncated tail, an import/collection error before ids
    # are printed). We cannot excuse what we cannot name — fail closed.
    fail_count = (outcome.failed or 0) + (outcome.errored or 0)
    unattributable = fail_count > len(failing)

    # Stale: an unconditional known-failure that did not fail this run.
    stale = tuple(sorted(unconditional_ids - failing))

    problems: List[str] = []
    if unledgered:
        problems.append(
            f"{len(unledgered)} un-ledgered failure(s): {', '.join(unledgered)}"
        )
    if unattributable:
        problems.append(
            f"{fail_count} failure(s)/error(s) reported but only "
            f"{len(failing)} attributable to a node id — an unattributable "
            f"failure cannot be excused by the ledger"
        )
    if stale:
        problems.append(
            f"{len(stale)} stale ledger entry/entries (unconditional, "
            f"expected to fail but passed this run): {', '.join(stale)}"
        )

    if problems:
        return LedgerSweepResult(
            status="fail",
            unledgered_failures=unledgered,
            stale_ledger_entries=stale,
            detail="known-failure ledger sweep FAILED — " + "; ".join(problems),
        )

    return LedgerSweepResult(
        status="pass",
        unledgered_failures=(),
        stale_ledger_entries=(),
        detail=(
            f"ledger sweep clean: {len(failing)} failure(s), all ledgered; "
            f"no stale entries"
        ),
    )


# ---------------------------------------------------------------------------
# 2. Coach task-start precondition (F1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PassBarPreconditionResult:
    """Outcome of the task-start pinned-pass-bar precondition."""

    status: str  # "pass" | "fail"
    detail: str
    pass_bar_path: Optional[str] = None

    @property
    def passed(self) -> bool:
        return self.status == "pass"


def _default_git(repo_root: Path) -> Callable[[Sequence[str]], subprocess.CompletedProcess]:
    def _run(args: Sequence[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            timeout=30,
        )

    return _run


def check_pass_bar_precondition(
    repo_root: Path,
    task_id: str,
    *,
    git_run: Optional[Callable[[Sequence[str]], subprocess.CompletedProcess]] = None,
) -> PassBarPreconditionResult:
    """Refuse task start without a pinned F1 pass bar that predates the work.

    A ``pass`` requires, in order:

    1. ``qa/pass-bar-<TASK-ID>.yaml`` exists;
    2. it validates as an F1 pass bar;
    3. its ``task_id`` matches ``task_id`` (guards a copy-pasted bar);
    4. its ``registered_at.sha`` is a real commit that is an ancestor of HEAD
       (the pass bar was pinned BEFORE implementation begins — the ordering the
       F1 docstring calls "mechanically checkable").

    Fails CLOSED: if git cannot verify the ordering (not a repo, sha unknown),
    the precondition refuses — the whole point of the gate is proving the bar
    predates the work, and enforcement is opt-in.
    """
    path = pass_bar_path_for(repo_root, task_id)
    if not path.is_file():
        return PassBarPreconditionResult(
            status="fail",
            detail=(
                f"no pinned F1 pass bar for {task_id}: expected {path} "
                f"(the pass bar must be committed BEFORE implementation — "
                f"qa.enforce_tier1 is on)"
            ),
            pass_bar_path=str(path),
        )

    try:
        bar: PassBar = validate_instance("pass-bar", path)  # type: ignore[assignment]
    except QAFormatError as exc:
        return PassBarPreconditionResult(
            status="fail",
            detail=f"pinned pass bar {path} is invalid: {exc}",
            pass_bar_path=str(path),
        )

    if bar.task_id != task_id:
        return PassBarPreconditionResult(
            status="fail",
            detail=(
                f"pass bar {path} declares task_id {bar.task_id!r} but is being "
                f"used to start {task_id!r} — a mismatched bar is not a pinned bar"
            ),
            pass_bar_path=str(path),
        )

    sha = bar.registered_at.sha
    run = git_run or _default_git(repo_root)
    try:
        exists = run(["cat-file", "-e", f"{sha}^{{commit}}"])
    except (OSError, subprocess.SubprocessError) as exc:
        return PassBarPreconditionResult(
            status="fail",
            detail=(
                f"cannot verify registered_at.sha {sha} for {task_id}: git "
                f"unavailable ({exc}). Refusing — the pass bar's predates-impl "
                f"ordering must be checkable."
            ),
            pass_bar_path=str(path),
        )
    if exists.returncode != 0:
        return PassBarPreconditionResult(
            status="fail",
            detail=(
                f"registered_at.sha {sha} in {path} is not a commit in this "
                f"repository — the pass bar cannot be shown to predate "
                f"implementation"
            ),
            pass_bar_path=str(path),
        )

    ancestor = run(["merge-base", "--is-ancestor", sha, "HEAD"])
    if ancestor.returncode != 0:
        return PassBarPreconditionResult(
            status="fail",
            detail=(
                f"registered_at.sha {sha} is NOT an ancestor of HEAD — the pass "
                f"bar for {task_id} was not pinned before implementation began "
                f"(a bar registered after the work does not predate it)"
            ),
            pass_bar_path=str(path),
        )

    return PassBarPreconditionResult(
        status="pass",
        detail=(
            f"pinned pass bar {path.name} predates implementation "
            f"(registered_at.sha {sha} is an ancestor of HEAD)"
        ),
        pass_bar_path=str(path),
    )


# ---------------------------------------------------------------------------
# 3. feature-complete runtime-surface refusal (F1 + F4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RuntimeSurfaceGateResult:
    """Outcome of the feature-complete runtime-surface / green-gate refusal."""

    status: str  # "pass" | "fail" | "not_applicable"
    runtime_surface: bool
    detail: str
    feature_pass_bars: Tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        # not_applicable is a pass (an authless feature needs no live gate).
        return self.status in {"pass", "not_applicable"}


def _pass_bar_is_runtime_surface(bar: PassBar) -> bool:
    """A pass bar declares a runtime surface when it is auth-surface-bearing,
    walk-bearing, or carries a live/operator-evidenced criterion."""
    if bar.auth_surface_bearing:
        return True
    if bar.checkpoint_list_ref:
        return True
    return any(c.evidence_kind in _LIVE_EVIDENCE_KINDS for c in bar.criteria)


def _latest_results_envelope(repo_root: Path) -> Optional[Path]:
    """The most recent F4 results envelope under ``qa/gates/history/``.

    Newest by modification time, then by name so a fixture writing several
    files in the same tick is still deterministic. ``None`` when the directory
    is absent or holds no ``.json`` file.
    """
    history = repo_root / "qa" / "gates" / "history"
    if not history.is_dir():
        return None
    envelopes = sorted(
        (p for p in history.glob("*.json") if p.is_file()),
        key=lambda p: (p.stat().st_mtime, p.name),
    )
    return envelopes[-1] if envelopes else None


def _gate_envelope_has_real_assertion(envelope: Path, gate_id: str) -> bool:
    """True when *envelope* carries a gate result for *gate_id* with at least
    one assertion whose ``expected`` is non-empty.

    A gate that asserted nothing proves nothing: an envelope with an empty
    assertion list (or assertions with no stated expectation) is a green light
    with no bulb behind it. Read defensively — a malformed envelope is simply
    no corroboration.
    """
    try:
        data = json.loads(envelope.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("results envelope %s is unreadable (%s)", envelope, exc)
        return False
    if not isinstance(data, dict):
        return False
    for gate in data.get("gates") or []:
        if not isinstance(gate, dict) or gate.get("gate_id") != gate_id:
            continue
        for assertion in gate.get("assertions") or []:
            if not isinstance(assertion, dict):
                continue
            expected = assertion.get("expected")
            if isinstance(expected, str) and expected.strip():
                return True
            if expected is not None and not isinstance(expected, str):
                return True
    return False


def check_runtime_surface_gate(
    repo_root: Path,
    feature_task_ids: Sequence[str],
    candidate_sha: Optional[str] = None,
) -> RuntimeSurfaceGateResult:
    """Refuse feature-complete for a runtime-surface feature with no green gate.

    The feature's committed F1 pass bars are the pass bars named
    ``qa/pass-bar-<task_id>.yaml`` for its tasks. The feature is
    *runtime-surface-bearing* when any of them declares a runtime surface
    (:func:`_pass_bar_is_runtime_surface`). Such a feature cannot reach
    feature-complete unless the F4 registry (``qa/gates/registry.yaml``)
    carries at least one registered, GREEN gate (a gate with ``last_green``
    set).

    A feature with no runtime-surface pass bar is ``not_applicable`` (an
    authless CLI / library / pipeline needs no live gate — PB-14's whole
    point). A malformed pass bar or registry is a loud config error → fail.
    """
    pass_bars: List[Tuple[str, PassBar]] = []
    for task_id in feature_task_ids:
        path = pass_bar_path_for(repo_root, task_id)
        if not path.is_file():
            continue
        try:
            bar: PassBar = validate_instance("pass-bar", path)  # type: ignore[assignment]
        except QAFormatError as exc:
            return RuntimeSurfaceGateResult(
                status="fail",
                runtime_surface=False,
                detail=(
                    f"pass bar {path} is invalid and cannot be assessed for a "
                    f"runtime surface: {exc}"
                ),
            )
        pass_bars.append((str(path), bar))

    runtime_bars = [p for p in pass_bars if _pass_bar_is_runtime_surface(p[1])]
    if not runtime_bars:
        return RuntimeSurfaceGateResult(
            status="not_applicable",
            runtime_surface=False,
            detail=(
                "no runtime-surface pass bar among the feature's tasks — "
                "no live gate required (authless feature)"
            ),
            feature_pass_bars=tuple(p[0] for p in pass_bars),
        )

    runtime_bar_names = tuple(Path(p[0]).name for p in runtime_bars)
    registry_path = repo_root / "qa" / "gates" / "registry.yaml"
    if not registry_path.is_file():
        return RuntimeSurfaceGateResult(
            status="fail",
            runtime_surface=True,
            detail=(
                f"feature declares a runtime surface ({', '.join(runtime_bar_names)}) "
                f"but has no F4 gate registry at {registry_path} — a "
                f"runtime-surface feature needs at least one registered, green "
                f"gate before feature-complete"
            ),
            feature_pass_bars=runtime_bar_names,
        )

    try:
        registry: GateRegistry = validate_instance("gate-registry", registry_path)  # type: ignore[assignment]
    except QAFormatError as exc:
        return RuntimeSurfaceGateResult(
            status="fail",
            runtime_surface=True,
            detail=f"F4 gate registry {registry_path} is invalid: {exc}",
            feature_pass_bars=runtime_bar_names,
        )

    green_gates = [g for g in registry.gates if g.last_green is not None]
    if not green_gates:
        return RuntimeSurfaceGateResult(
            status="fail",
            runtime_surface=True,
            detail=(
                f"feature declares a runtime surface ({', '.join(runtime_bar_names)}) "
                f"but the F4 registry has no green gate (no gate with a "
                f"last_green sha) — register a live gate and take it green "
                f"before feature-complete"
            ),
            feature_pass_bars=runtime_bar_names,
        )

    # B9 (2026-09-19): A GREEN GATE MUST BE *THIS* FEATURE'S GREEN GATE.
    # Before this, any registered gate with any last_green sha satisfied the
    # check — an unrelated gate, green months ago against different code, with
    # an envelope that asserted nothing, let a feature through. Three bindings
    # now have to hold together:
    #   1. the gate's pass_bar_ref is one of THIS feature's task pass bars;
    #   2. its last_green.sha is the candidate sha under check;
    #   3. its latest results envelope enumerates at least one assertion with
    #      a non-empty `expected` (a gate that asserted nothing proves nothing).
    if candidate_sha is None:
        # FAILS CLOSED, and says why. A caller that cannot name the candidate
        # cannot be told the gate covers it. The fix is to pass the sha.
        return RuntimeSurfaceGateResult(
            status="fail",
            runtime_surface=True,
            detail=(
                f"feature declares a runtime surface ({', '.join(runtime_bar_names)}) "
                f"and the F4 registry has green gate(s) "
                f"({', '.join(g.id for g in green_gates)}), but no candidate sha "
                f"was given to bind them to — a green gate cannot be shown to "
                f"cover code it was never matched against. Pass "
                f"candidate_sha=<the sha under check> to this check."
            ),
            feature_pass_bars=runtime_bar_names,
        )

    feature_bar_refs = {
        _normalise_pass_bar_ref(p[0], repo_root) for p in pass_bars
    }
    bound = [
        g
        for g in green_gates
        if _normalise_pass_bar_ref(g.pass_bar_ref, repo_root) in feature_bar_refs
    ]
    if not bound:
        return RuntimeSurfaceGateResult(
            status="fail",
            runtime_surface=True,
            detail=(
                f"no registered green gate is bound to this feature: the green "
                f"gate(s) {', '.join(g.id for g in green_gates)} name pass bars "
                f"{', '.join(sorted({g.pass_bar_ref for g in green_gates}))}, "
                f"none of which is one of this feature's "
                f"({', '.join(runtime_bar_names)}). An unrelated green gate is "
                f"not evidence about this feature."
            ),
            feature_pass_bars=runtime_bar_names,
        )

    at_sha = [g for g in bound if g.last_green.sha == candidate_sha]
    if not at_sha:
        return RuntimeSurfaceGateResult(
            status="fail",
            runtime_surface=True,
            detail=(
                f"the gate(s) bound to this feature "
                f"({', '.join(g.id for g in bound)}) last went green at "
                f"{', '.join(sorted({g.last_green.sha for g in bound}))}, not at "
                f"the candidate sha {candidate_sha} — a stale green says nothing "
                f"about the code being completed"
            ),
            feature_pass_bars=runtime_bar_names,
        )

    envelope = _latest_results_envelope(repo_root)
    if envelope is None:
        return RuntimeSurfaceGateResult(
            status="fail",
            runtime_surface=True,
            detail=(
                f"gate(s) {', '.join(g.id for g in at_sha)} are green at "
                f"{candidate_sha} but there is no results envelope under "
                f"qa/gates/history/ — nothing records what the gate actually "
                f"asserted"
            ),
            feature_pass_bars=runtime_bar_names,
        )

    asserted = [
        g for g in at_sha if _gate_envelope_has_real_assertion(envelope, g.id)
    ]
    if not asserted:
        return RuntimeSurfaceGateResult(
            status="fail",
            runtime_surface=True,
            detail=(
                f"the latest results envelope {envelope.name} carries no "
                f"assertion with a stated expectation for gate(s) "
                f"{', '.join(g.id for g in at_sha)} — a gate that asserted "
                f"nothing proves nothing"
            ),
            feature_pass_bars=runtime_bar_names,
        )

    green_ids = ", ".join(g.id for g in asserted)
    return RuntimeSurfaceGateResult(
        status="pass",
        runtime_surface=True,
        detail=(
            f"runtime-surface feature backed by {len(asserted)} registered "
            f"green gate(s) bound to it: {green_ids} (green at {candidate_sha}, "
            f"assertions recorded in {envelope.name})"
        ),
        feature_pass_bars=runtime_bar_names,
    )


def _normalise_pass_bar_ref(ref: str, repo_root: Path) -> str:
    """Compare pass-bar references by their repo-relative posix path.

    A registry may name ``qa/pass-bar-TASK-X.yaml`` while the feature's bars
    are absolute paths; both mean the same file.
    """
    candidate = Path(ref)
    try:
        if candidate.is_absolute():
            candidate = candidate.relative_to(repo_root)
    except ValueError:
        pass
    return candidate.as_posix().lstrip("./")


# ---------------------------------------------------------------------------
# 4. Plan-time ledger-authorship reject-lint (F2 · K15 / LPA-09)
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
    B2's other three refusals check *when* ledger entries are honoured; none
    checks *who authored them at plan time*. A headless planner writing the
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
