"""Stage 3 · AUTO-MERGE behind the DF-021 trust ledger.

H-A RETIRE-THE-COORDINATOR, Stage 3 (see
``docs/ways-of-working/retire-the-coordinator-build-handoff-2026-07-17.md`` §3).

The merge primitive ``worktrees/manager.py:merge()`` has always existed but was
left UNCALLED after ``auto_merge`` was removed as YAGNI (``cli/autobuild.py``:
"Preserve worktree for human review (never auto-merges)"). Stage 3 rebuilds the
auto-merge act **behind the trust ledger** — never unconditionally. The gate the
spec pins is::

    if ledger.graduated(lane) and not constitutional(target) and clean_signal:
        manager.merge(worktree, target)

:func:`should_auto_merge` is that gate as a pure predicate (every input explicit,
so it is hermetic); :func:`auto_merge_if_graduated` performs the merge behind it,
preserving the worktree on conflict (``WorktreeMergeError``) exactly as the
failure path always has.

**Default posture (binding).** A lane NEVER auto-merges until it has both
graduated (streak≥N of clean MG-3 records) AND the master auto-merge switch is
ON. In-window the switch is OFF (``GUARDKIT_AUTO_MERGE`` unset), so nothing
auto-merges even once a lane graduates — the mechanism is live, the automation
has not yet earned itself in (spec §5 honest bar; on Monday the streak is 0/5).
The per-lane graduation flip is Rich's, evidence-cited, post-window.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

from guardkit.orchestrator.machine_verify import SIGNAL_CLEAN, MachineVerifyReport
from guardkit.qa.trust_ledger import TrustLedger

logger = logging.getLogger(__name__)

#: Env kill-switch — auto-merge is OFF unless this is explicitly truthy. Default
#: OFF is the binding in-window posture (nothing auto-merges even when a lane has
#: graduated) so the streak matures through real use before automation acts.
_AUTO_MERGE_ENV = "GUARDKIT_AUTO_MERGE"
_TRUTHY = {"1", "true", "on", "yes"}


def auto_merge_enabled() -> bool:
    """Master switch for the auto-merge act (default OFF, spec §4 / §5)."""
    raw = os.environ.get(_AUTO_MERGE_ENV)
    return raw is not None and raw.strip().lower() in _TRUTHY


def clean_signal(report: Optional[MachineVerifyReport]) -> bool:
    """Whether Stage 1's report is a clean, no-disposition-needed signal.

    Auto-merge requires an unambiguous clean: the branch introduced no regression
    (``signal == clean``) AND nothing forces a human disposition (a CATCH, or the
    suite's reds being unavailable, both set ``disposition_required``). Absence of
    a report is treated as NOT clean (fail toward attention).
    """
    if report is None:
        return False
    return report.signal == SIGNAL_CLEAN and not report.disposition_required


@dataclass(frozen=True)
class AutoMergeDecision:
    """Why auto-merge did or did not fire — an auditable, receipt-bearing record."""

    fired: bool
    reason: str
    lane: str
    target: str


def should_auto_merge(
    ledger: TrustLedger,
    lane: str,
    target: str,
    report: Optional[MachineVerifyReport],
) -> AutoMergeDecision:
    """The pinned Stage 3 gate as a pure predicate.

    Fires iff ALL hold (spec §3, Stage 3 seams):

    * the lane has **graduated** (streak≥N of clean MG-3 records) — and the lane
      is not itself a constitutional class (``ledger.graduated`` enforces that);
    * the **target** is not a constitutional class (checked independently — a
      target can be constitutional even when the lane is not; constitutional
      classes NEVER auto, regardless of streak);
    * Stage 1's report is a **clean signal** (no regression, no disposition
      required).

    The master ``GUARDKIT_AUTO_MERGE`` switch is enforced by the caller
    (:func:`auto_merge_if_graduated`), NOT here — this predicate is the pure
    ledger gate so tests can exercise it without touching the environment.
    """
    if ledger.constitutional(target):
        return AutoMergeDecision(False, "target is a constitutional class", lane, target)
    if not ledger.graduated(lane):
        return AutoMergeDecision(False, "lane has not graduated (streak < N)", lane, target)
    if not clean_signal(report):
        return AutoMergeDecision(False, "machine-verify signal not clean", lane, target)
    return AutoMergeDecision(True, "graduated lane, clean signal, non-constitutional", lane, target)


def auto_merge_if_graduated(
    manager,
    worktree,
    ledger: TrustLedger,
    lane: str,
    report: Optional[MachineVerifyReport],
    *,
    target_branch: Optional[str] = None,
    cleanup: bool = True,
    respect_env_switch: bool = True,
) -> AutoMergeDecision:
    """Auto-merge ``worktree`` iff the ledger gate opens — else a no-op.

    Behind BOTH the master env switch (default OFF in-window) and the pure
    :func:`should_auto_merge` ledger gate. On a fired decision it runs the
    previously-UNCALLED ``manager.merge()`` primitive (``git checkout <target>`` +
    ``git merge --no-ff``); a merge conflict raises ``WorktreeMergeError`` and the
    worktree is preserved for manual resolution (the failure path's invariant).

    Returns the :class:`AutoMergeDecision` so the caller can log a receipt whether
    or not the merge fired.
    """
    target = target_branch or getattr(worktree, "base_branch", "main")

    if respect_env_switch and not auto_merge_enabled():
        return AutoMergeDecision(
            False, "auto-merge master switch OFF (GUARDKIT_AUTO_MERGE unset)", lane, target
        )

    decision = should_auto_merge(ledger, lane, target, report)
    if not decision.fired:
        return decision

    from guardkit.worktrees.manager import WorktreeMergeError

    try:
        manager.merge(worktree, target_branch=target)
    except WorktreeMergeError:
        # A conflict is a human-resolution event, never a silent drop — preserve
        # and re-raise exactly as the manual failure path always has.
        try:
            manager.preserve_on_failure(worktree)
        except Exception:  # noqa: BLE001 — preserve is best-effort; re-raise the merge error
            logger.warning("auto-merge: preserve_on_failure failed after a merge conflict")
        raise

    if cleanup:
        try:
            manager.cleanup(worktree)
        except Exception as exc:  # noqa: BLE001 — cleanup failure must not undo a done merge
            logger.warning("auto-merge: cleanup after merge failed for %s: %s", lane, exc)

    return decision


__all__ = [
    "auto_merge_enabled",
    "clean_signal",
    "AutoMergeDecision",
    "should_auto_merge",
    "auto_merge_if_graduated",
]
