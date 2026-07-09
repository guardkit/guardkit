"""Baseline-green probe + Coach test-gate baseline diff (red-baseline retro, L12).

The 2026-07-08 study-tutor FEAT-VOICE-003 incident burned ~2.5h across two
autobuild runs on a task made un-passable by ONE stale pre-existing baseline
test: the worktree's suite was already red on ``main`` before wave 1, and
autobuild never checked, so the pre-existing failure was silently attributed
to whichever task's Coach first ran the full suite.

This module implements the incident's cure — a *session-scoped OBSERVATION*,
never a substitute for the human-curated F2 ledger (WS3 §3 composition rule,
pre-decided with B2):

* **Item 1 — baseline-green probe.** Run the feature's smoke/test command once
  at worktree setup (after bootstrap, before wave 1). Record the result to
  ``.guardkit/autobuild/<feature>/baseline.json``. Emit a wave-0 WARNING when
  red. Report-only — it NEVER blocks the run.
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

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "expected_exit": self.expected_exit,
            "passed": self.passed,
            "exit_code": self.exit_code,
            "failing_node_ids": list(self.failing_node_ids),
            "failing_count": self.failing_count,
            "timestamp": self.timestamp,
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


def read_baseline_from_worktree(worktree_path: Path) -> Optional[BaselineResult]:
    """Find and load the feature ``baseline.json`` under a worktree, if any.

    Globs ``.guardkit/autobuild/*/baseline.json`` (only the feature dir carries
    a ``baseline.json``; task dirs carry ``task_work_results.json``). Returns
    ``None`` when absent / unreadable (fail open — the diff is simply inert).
    """
    root = Path(worktree_path) / ".guardkit" / "autobuild"
    if not root.is_dir():
        return None
    try:
        matches = sorted(root.glob(f"*/{_BASELINE_FILENAME}"))
    except OSError:
        return None
    for candidate in matches:
        try:
            return BaselineResult.from_dict(
                json.loads(candidate.read_text(encoding="utf-8"))
            )
        except (OSError, ValueError):
            continue
    return None


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
) -> BaselineResult:
    """Assemble a :class:`BaselineResult` from an executed smoke/test run.

    ``output`` is the combined stdout/stderr of the run; failing node IDs are
    pytest-parsed from it (empty for non-pytest stacks — the pass/fail signal
    still drives the wave-0 warning).
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
