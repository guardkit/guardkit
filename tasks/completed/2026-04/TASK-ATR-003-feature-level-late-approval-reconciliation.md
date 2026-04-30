---
id: TASK-ATR-003
title: Feature-level late-approval reconciliation
task_type: feature
parent_review: TASK-REV-E73C
parent_review_repo: jarvis
feature_id: FEAT-ATR
wave: 2
implementation_mode: task-work
complexity: 6
dependencies: []
priority: medium
status: completed
previous_state: in_review
state_transition_reason: "All acceptance criteria met, quality gates passed"
completed: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
tags: [autobuild, race-condition, reconciliation, FEAT-ATR]
---

# TASK-ATR-003 — Feature-level late-approval reconciliation

## Description

The per-task `_loop_phase` already honours late Coach approvals via the
TASK-ABFIX-004 mechanism at
[`autobuild.py:2192–2202`](../../../guardkit/orchestrator/autobuild.py#L2192-L2202)
("approval-wins-over-timeout"). When the per-task layer detects the timeout
*after* Coach has approved, it correctly returns `(turn_history, "approve")`
rather than `"timeout"`.

The **feature** layer has no symmetric mechanism. When
`asyncio.wait_for(asyncio.to_thread(_execute_task), timeout=task_timeout)`
fires `TimeoutError` while the worker thread is mid-`subprocess.run(pytest)`,
the thread continues executing in the background and writes
`coach_turn_<N>.json` with `decision=approve`, but the feature orchestrator
has already collected `TimeoutError` from `gather()` and recorded TIMEOUT in
the feature YAML. The two layers disagree on the same task.

Observed in production (FEAT-J005-946D run-1, 2026-04-29): per-task wrote
`approve` 68 ms after `wait_for` raised. See
`jarvis/.claude/reviews/TASK-REV-E73C-review-report.md` for full timeline
and code-validated mechanics.

## Root Cause Addressed

`asyncio.to_thread` cannot be hard-cancelled; the worker thread runs to
natural completion regardless of `wait_for`'s `TimeoutError`. The thread's
durable disk artifacts (`coach_turn_<N>.json`, frontmatter, git commit) are
authoritative for the *implementation* outcome, but the feature orchestrator
discards the thread's return value because the gather slot already holds
`TimeoutError`.

## Files to Modify

1. `guardkit/orchestrator/feature_orchestrator.py` — add
   `_check_late_approval(task_id, timer_fire_time)` helper. Modify the
   `isinstance(result, asyncio.TimeoutError)` branch at lines 2137–2178 to
   call the helper before recording TIMEOUT.
2. `guardkit/orchestrator/feature_orchestrator.py` — add
   `LATE_APPROVAL_GRACE_S` constant (default 60s, env-var overridable via
   `GUARDKIT_LATE_APPROVAL_GRACE`).
3. `tests/unit/test_feature_orchestrator.py` — `TestLateApprovalReconciliation`
   class with cases listed in Acceptance Criteria below.

## Acceptance Criteria

- [ ] New `_check_late_approval(task_id, timer_fire_time)` returns the
      Coach `decision` from the latest `coach_turn_*.json` if and only if
      the file's mtime is within `LATE_APPROVAL_GRACE_S` seconds of
      `timer_fire_time`.
- [ ] Helper is read-only and never raises (returns `None` on any error).
- [ ] When `result isinstance asyncio.TimeoutError` AND helper returns
      `"approve"`, the feature YAML records the task as
      `final_decision: approved_late` with `success: True` instead of
      `final_decision: timeout`.
- [ ] When the late-approve path fires, log at INFO with task_id, mtime
      delta, and `coach_turn_<N>.json` path for auditability.
- [ ] The `decision_subtype` field captures `late_approval_window=Ns`
      so review-summary renderers can distinguish APPROVED from APPROVED_LATE.
- [ ] `LATE_APPROVAL_GRACE_S` reads from env var
      `GUARDKIT_LATE_APPROVAL_GRACE` at module load time
      (mirrors `MIN_TURN_BUDGET_SECONDS` pattern at autobuild.py:184).
- [ ] Unit tests:
  - approve file mtime now-30s, grace 60s → returns "approve"
  - approve file mtime now-90s, grace 60s → returns None
  - feedback file mtime now-30s → returns "feedback" (not approved, so
    no reclassification — feature still records TIMEOUT)
  - missing autobuild dir → returns None
  - missing/malformed coach_turn_*.json → returns None
  - integration: simulated `TimeoutError` slot in gather + pre-written
    Coach-approved file → feature YAML records `approved_late`.
- [ ] `wave_display` shows the task as ✓ APPROVED_LATE not ⏱ TIMEOUT.
- [ ] No regression in existing TimeoutError handling for tasks WITHOUT
      a late approval (file absent or stale).

## Test Requirements

- pytest unit tests in `tests/unit/test_feature_orchestrator.py`
- pytest integration test under `tests/integration/`
- Re-run existing `tests/unit/test_feature_orchestrator.py` suite

## Implementation Notes

Sketch (~40 LoC across two methods):

```python
# At module top, near MIN_TURN_BUDGET_SECONDS:
LATE_APPROVAL_GRACE_S: int = int(
    os.environ.get("GUARDKIT_LATE_APPROVAL_GRACE", "60")
)

class FeatureOrchestrator:
    def _check_late_approval(
        self, task_id: str, timer_fire_time: float
    ) -> Optional[str]:
        """Read-only check: did Coach approve within the grace window
        after the feature timer fired?

        Returns the decision string from the latest coach_turn_*.json
        if its mtime is within LATE_APPROVAL_GRACE_S of timer_fire_time.
        Never raises; returns None on any error or absence.
        """
        try:
            autobuild_dir = (
                self.repo_root / ".guardkit" / "autobuild" / task_id
            )
            if not autobuild_dir.exists():
                return None
            coach_files = sorted(
                autobuild_dir.glob("coach_turn_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if not coach_files:
                return None
            latest = coach_files[0]
            mtime_delta = abs(latest.stat().st_mtime - timer_fire_time)
            if mtime_delta > LATE_APPROVAL_GRACE_S:
                return None
            return json.loads(latest.read_text()).get("decision")
        except Exception as exc:
            logger.debug(
                f"[{task_id}] _check_late_approval skipped: {exc}"
            )
            return None
```

Modified TimeoutError branch (around line 2137):

```python
if isinstance(result, asyncio.TimeoutError):
    timer_fire_time = time.time()  # close enough to gather's actual fire
    late_decision = self._check_late_approval(task_id, timer_fire_time)
    if late_decision == "approve":
        logger.info(
            f"[{task_id}] APPROVED_LATE: Coach decision arrived within "
            f"{LATE_APPROVAL_GRACE_S}s of timer fire; reclassifying."
        )
        # Read turn_state to recover total_turns
        total_turns = self._read_total_turns(task_id) or 0
        late_result = TaskExecutionResult(
            task_id=task_id,
            success=True,
            total_turns=total_turns,
            final_decision="approved_late",
            error=None,
            decision_subtype=f"late_approval_window={LATE_APPROVAL_GRACE_S}s",
        )
        results.append(late_result)
        if self._wave_display:
            self._wave_display.update_task_status(
                task_id, "success", "Coach approved late",
                turns=total_turns, decision="approved_late"
            )
        self._update_feature(feature, task_id, late_result, wave_number)
        continue  # skip the original TIMEOUT handling

    # else: existing TIMEOUT handling (unchanged)
    sdk_timeout = self.sdk_timeout or 1200
    timeout_msg = ...
```

Risk profile: read-only check; the worst regression is "still records
TIMEOUT" (current behaviour). The `continue` skip on the new branch is
the only flow-control change; covered by the integration test.

## Out-of-scope

- Cancellation of the still-running thread after late approval. The
  thread's writes are durable; future reads will be consistent. Hard
  thread cancellation is a separate, much riskier change.
- Reclassifying TIMEOUT → REJECTED_LATE if Coach `decision == "reject"`
  arrives within the window. Rare edge case; current behaviour (record
  TIMEOUT) is conservative-correct and we should not weaken it.

## Implementation Summary

Added `LATE_APPROVAL_GRACE_S` (env-overridable via
`GUARDKIT_LATE_APPROVAL_GRACE`, default 60s) and two read-only helpers
on `FeatureOrchestrator`:

- `_check_late_approval(task_id, timer_fire_time)` — peeks at the latest
  `coach_turn_*.json` under `.guardkit/autobuild/<task_id>/` and returns
  the `decision` string when the file's mtime is within
  `LATE_APPROVAL_GRACE_S` of the timer-fire time. Never raises; returns
  `None` on any error or absence.
- `_read_total_turns(task_id)` — recovers `turn_number` from the latest
  `turn_state_turn_*.json` so the synthesised `TaskExecutionResult`
  carries an accurate `total_turns` even though the gather slot held
  `TimeoutError` and the worker thread's return value was discarded.

Modified the `isinstance(result, asyncio.TimeoutError)` branch in the
per-wave gather loop: when the helper returns `"approve"`, build a
`TaskExecutionResult(success=True, final_decision="approved_late",
decision_subtype="late_approval_window={N}s", total_turns=...)`,
update the wave display with `success` status / `approved_late`
decision text, persist via `_update_feature`, then `continue` to skip
the original TIMEOUT handling. Audit log line includes task_id,
mtime delta, and source coach_turn path.

## Approach

Read-only file-peek pattern. The worst regression is "still records
TIMEOUT" (the prior behaviour). The single new flow-control branch
(`continue` after the late-approval block) is covered by the
integration test that pre-writes a `coach_turn_2.json` with
`decision=approve` and asserts the feature YAML records
`approved_late`.

## Notes

Lessons / non-obvious findings:

- `asyncio.to_thread` cannot be hard-cancelled; the worker thread
  always runs to natural completion. The thread's *durable disk
  writes* (`coach_turn_<N>.json`, `turn_state_turn_<N>.json`,
  frontmatter, git commit) are the authoritative implementation
  outcome, but the feature orchestrator was discarding them when
  `wait_for` raised. The fix is purely a peek-at-disk reconciliation —
  no asyncio surgery needed.
- The integration tests required `GUARDKIT_AUTOBUILD_TASK_TIMEOUT_FLOOR=0`
  via monkeypatch to prevent TASK-ABSR-FLOR's 3000s floor from lifting
  the test's `task_timeout=1` to 3000s. Six pre-existing tests in
  `test_feature_orchestrator.py` (and four in
  `test_parallel_wave_execution.py`) fail at HEAD for the same reason
  — they predate the floor and should be updated in a follow-up.
- The helper's signature (`Optional[str]` decision string) keeps it a
  pure file-peek with no allocation cost; the audit-logging
  side-channel re-stats the latest coach file at the call site (one
  extra `stat()` only fires on the late-approval path, which is rare
  by definition).

## Related ADRs

- TASK-REV-E73C (parent review, jarvis repo) — incident analysis from
  FEAT-J005-946D run-1 that motivated this fix
- TASK-ABFIX-004 — per-task layer's "approval-wins-over-timeout"
  mechanism (the symmetry this task closes at the feature layer)
- TASK-ATR-001 — sister task (per-task `task_timeout` frontmatter
  override; introduced the 3000s floor that broke pre-existing tests)
- TASK-ATR-002 — sister task (refresh `remaining_budget` between
  Phase 4/5 specialists)
