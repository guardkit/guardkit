---
id: TASK-FIX-LATEAPPR
title: "Fix _check_late_approval to search worktree autobuild dirs + replace misleading TIMEOUT warning text"
status: completed
created: 2026-05-11T00:00:00Z
updated: 2026-05-11T00:00:00Z
completed: 2026-05-11T00:00:00Z
previous_state: in_review
state_transition_reason: "All ACs satisfied: 17/17 late-approval and warning tests pass; 146/146 test_feature_orchestrator.py pass; no new ruff/dead-id failures."
priority: high
task_type: feature
parent_review: TASK-REV-RAG8R2
implementation_mode: task-work
complexity: 4
tags: [autobuild, orchestrator, late-approval, status-rollup, observability, RAG8R2-followup]
related_tasks:
  - TASK-FIX-CRSTL-MULT  # Just-landed (commit 850d0d14); this task addresses the next layer the CRSTL fix exposed
  - TASK-ATR-003         # The original APPROVED_LATE reclassification work whose path lookup we are fixing
  - TASK-ABFIX-006       # Per-task feature-level timeout / cancellation event wiring
upstream_evidence:
  - "appmilla_github/specialist-agent: .claude/reviews/TASK-REV-RAG8R2-review-report.md"
  - "appmilla_github/specialist-agent: .claude/reviews/TASK-REV-CRSTL-review-report.md"
  - "appmilla_github/specialist-agent: docs/history/autobuild-FEAT-RAG-08-fail-run-2.md"
load_bearing_files:
  - guardkit/orchestrator/feature_orchestrator.py
  - tests/orchestrator/test_feature_orchestrator.py  # or wherever _check_late_approval tests live
---

# Task: Fix _check_late_approval to search worktree autobuild dirs + replace misleading TIMEOUT warning

## Description

`AutoBuildFeatureOrchestrator._check_late_approval`
([feature_orchestrator.py:3114-3166](../../guardkit/orchestrator/feature_orchestrator.py#L3114-L3166))
reconciles late-arriving Coach approvals against feature-level
`asyncio.TimeoutError` outcomes, reclassifying a task from `TIMEOUT`
to `APPROVED_LATE` when Coach wrote `coach_turn_*.json` within
`LATE_APPROVAL_GRACE_S` (=60s) of the timer fire.

It looks for `coach_turn_*.json` only under
`self.repo_root / ".guardkit" / "autobuild" / task_id`.

For **worktree-backed runs** (every `FEAT-*` autobuild), Coach actually
writes to
`.guardkit/worktrees/{feature_id}/.guardkit/autobuild/{task_id}/coach_turn_<N>.json`
— a different directory. The lookup glob returns `[]`, the function
returns `None`, and the late-approval reclassification is a permanent
no-op for worktree-backed runs. The wave records `TIMEOUT` even when
Coach approved within 11s of the timer fire.

This was hidden behind the CRSTL R1 fix (`TASK-FIX-CRSTL-MULT`,
commit `850d0d14`). Before R1, high-complexity specialist invocations
hit `SDKTimeoutError` inside the worker thread and never reached
Coach grace; `_check_late_approval` correctly returned `None` because
no `coach_turn_*.json` ever existed. Once R1 widened the per-specialist
budget, the failure mode shifted to "feature timer fires while worker
is mid-Coach-grace" — and `_check_late_approval` now needs to find
the file the worker just wrote.

Production evidence: FEAT-RAG-08 run-2
([transcript](../../../specialist-agent/docs/history/autobuild-FEAT-RAG-08-fail-run-2.md)).
TASK-AIV2-003 — Coach approved at `22:19:57Z` (line 522), feature
timer fired at `22:19:46Z` (line 478), `mtime_delta ≈ 11s` (well
under the 60s window), but the wave still recorded `TIMEOUT`
(line 561) because the lookup directory contained only `progress.log`.
On-disk state of both directories is documented in the parent review,
§F1.

This task also lands **R3** from the parent review: the TIMEOUT
warning text in
[feature_orchestrator.py:2471-2493](../../guardkit/orchestrator/feature_orchestrator.py#L2471-L2493)
hard-codes `self.sdk_timeout` (the orchestrator-level base, =1200s),
producing the misleading message "SDK timeout budget was 1200s per
invocation" *even after CRSTL R1 has scaled the actual per-invocation
timeout to ~2700s+*. This wasted diagnostic time during the parent
review and would do so again on every future high-complexity
TIMEOUT.

## Acceptance Criteria

### R1 — Late-approval lookup is worktree-aware

- [ ] AC-R1.1: `_check_late_approval` searches both
      `self.repo_root/.guardkit/autobuild/{task_id}/` AND every
      `self.repo_root/.guardkit/worktrees/*/.guardkit/autobuild/{task_id}/`
      directory for `coach_turn_*.json`. Search is additive (existing
      direct-mode runs continue to work).
- [ ] AC-R1.2: When multiple candidate files exist, the one with the
      latest `mtime` is selected. mtime-delta against `timer_fire_time`
      determines reclassification (unchanged semantics).
- [ ] AC-R1.3: The audit-log glob at
      [feature_orchestrator.py:2412-2447](../../guardkit/orchestrator/feature_orchestrator.py#L2412-L2447)
      is updated to use the same candidate-dirs walk so
      `coach_audit_path` correctly identifies the source.
- [ ] AC-R1.4: All three return paths (`None` for "no candidate found",
      `None` for "outside grace window", decision string for "inside
      grace window") preserve their existing semantics.

### R3 — TIMEOUT warning carries actual per-invocation timeout

- [ ] AC-R3.1: The TIMEOUT warning at
      [feature_orchestrator.py:2471-2493](../../guardkit/orchestrator/feature_orchestrator.py#L2471-L2493)
      either (a) reads the most-recent `[<task_id>] SDK timeout: <N>s`
      entry from the per-task `progress.log` (the file is already
      consulted for `last_state`), or (b) drops the misleading
      `SDK timeout budget was {sdk_timeout}s per invocation` clause and
      replaces with a pointer (e.g. `See per-invocation '[<task_id>]
      SDK timeout: <N>s' lines in progress.log for actual values
      applied`).
- [ ] AC-R3.2: The new wording does not regress the warning's
      diagnostic density — `effective_task_timeout` and `last_state`
      remain present.

### Regression coverage

- [ ] AC-T1: New unit test
      `test_check_late_approval_finds_coach_in_worktree_autobuild` —
      seeds a `coach_turn_1.json` only inside a fake worktree dir,
      asserts `_check_late_approval` returns `"approve"` when mtime
      is fresh.
- [ ] AC-T2: New unit test
      `test_check_late_approval_prefers_latest_across_candidate_dirs`
      — seeds an old file at the repo-root path and a fresh file in
      the worktree; asserts the worktree (latest mtime) wins.
- [ ] AC-T3: Existing repo-root-only behaviour preserved — the prior
      test (or a new one if absent) seeds only at the repo-root path
      and asserts the function still returns `"approve"`.
- [ ] AC-T4: Test for R3 — assert the TIMEOUT warning does not
      contain the literal string `"SDK timeout budget was 1200s per
      invocation"` when the actual per-invocation value differs (or
      asserts the new wording, depending on which option from R3 is
      taken).
- [ ] AC-T5: All existing tests under `tests/orchestrator/` continue
      to pass; no new ruff failures.

## Implementation Sketch

`_check_late_approval` patch (full sketch in parent review §R1):

```python
def _check_late_approval(self, task_id, timer_fire_time):
    candidate_dirs = [self.repo_root / ".guardkit" / "autobuild" / task_id]
    worktrees_root = self.repo_root / ".guardkit" / "worktrees"
    if worktrees_root.exists():
        for wt_dir in worktrees_root.iterdir():
            if not wt_dir.is_dir():
                continue
            candidate_dirs.append(wt_dir / ".guardkit" / "autobuild" / task_id)

    coach_files: list[Path] = []
    for d in candidate_dirs:
        if d.exists():
            coach_files.extend(d.glob("coach_turn_*.json"))
    if not coach_files:
        return None
    latest = max(coach_files, key=lambda p: p.stat().st_mtime)
    mtime_delta = abs(latest.stat().st_mtime - timer_fire_time)
    if mtime_delta > LATE_APPROVAL_GRACE_S:
        return None
    try:
        return json.loads(latest.read_text()).get("decision")
    except Exception as exc:
        logger.debug(f"[{task_id}] _check_late_approval skipped: {exc}")
        return None
```

The TIMEOUT-warning fix is the smaller of the two changes — pick option
(b) unless option (a) is trivial in the surrounding code (the
`progress.log` is already opened for `last_state`).

## Why R2 (CRSTL F2 / reviewer working set) is NOT in this task

The parent review flagged R2 (bound the code-reviewer SDK turn count
or working set) as the next blocker after this fix lands. It is
deliberately deferred:

1. R1 is load-bearing for *all* worktree-backed autobuild runs. R2 is
   load-bearing only for high-complexity reviewer invocations. R1 ships
   sooner and unblocks more.
2. With R1 in place, run-2's existing on-disk Coach approval flips
   TASK-AIV2-003 to `APPROVED_LATE` and the wave passes. R2's value
   becomes "prevent the next blocker" rather than "fix the current
   one".
3. R2 needs production data — at least one wave with R1 live — to
   size the SDK-turn / working-set bound correctly.

Open R2 as a separate task referencing this one once R1 has shipped
to at least one production wave.

## Out of Scope

- CRSTL R2b (extend heartbeat to include SDK turn count + last tool
  in each "in progress... (Ns elapsed)" line). Tracked in the parent
  review as F5; should be opened as its own follow-up.
- The Coach write/late-approval read race (parent review F4). Margin
  is comfortable (11s observed vs 60s window); not blocking. Worth a
  separate task only if production data shows the margin tightening.
- Any change to `_cap_specialist_timeout` or the multiplier formula
  itself — that work is `TASK-FIX-CRSTL-MULT` (already complete).

## Risk

Low. The patch is additive (search both directories rather than
switching). The mtime-delta semantics are unchanged. The only
behaviour change for non-worktree (direct) runs is that they now
check the same single directory as before but via a one-element
candidate list. The R3 warning-text change is cosmetic.

## Implementation Summary

Landed R1 + R3 from parent review TASK-REV-RAG8R2.

**R1 — Worktree-aware candidate-dirs walk.** Added two private helpers
on `AutoBuildFeatureOrchestrator`:

- `_autobuild_candidate_dirs(task_id)` yields every
  `.guardkit/autobuild/<task_id>/` directory Coach may have written
  to — both the repo-root path (direct-mode runs) and every
  `.guardkit/worktrees/*/.guardkit/autobuild/<task_id>/` path
  (worktree-backed `FEAT-*` runs). Additive — direct-mode runs see
  exactly the repo-root entry as before.
- `_latest_coach_turn_path(task_id)` collects `coach_turn_*.json`
  matches across the candidate dirs and returns the one with the
  latest mtime, or `None`.

`_check_late_approval` now delegates to `_latest_coach_turn_path`
([feature_orchestrator.py:3110-3199](../../../guardkit/orchestrator/feature_orchestrator.py#L3110-L3199)),
so worktree-backed runs reclassify TIMEOUT → APPROVED_LATE correctly
when Coach approved within `LATE_APPROVAL_GRACE_S` of the timer fire.
The APPROVED_LATE audit-log block at
[feature_orchestrator.py:2412-2436](../../../guardkit/orchestrator/feature_orchestrator.py#L2412-L2436)
was updated to use the same helper, so the `source=` field in the
audit log correctly identifies the worktree path.

**R3 — Dropped misleading hardcoded SDK-timeout clause.** Removed the
`SDK timeout budget was {sdk_timeout}s per invocation` clause from
the TIMEOUT warning at
[feature_orchestrator.py:2470-2498](../../../guardkit/orchestrator/feature_orchestrator.py#L2470-L2498).
After TASK-FIX-CRSTL-MULT scales the actual per-specialist timeout
by complexity, the orchestrator-level `self.sdk_timeout` (=1200s
default) is no longer the value in effect. Replaced with a pointer
to the per-task `progress.log` where the real per-invocation
`[<task_id>] SDK timeout: <N>s` lines live. `effective_task_timeout`
and `last_state` retained (AC-R3.2 diagnostic density preserved).

**Tests.** Added four new tests to
`tests/unit/test_feature_orchestrator.py`:
- `test_check_late_approval_finds_coach_in_worktree_autobuild`
  (AC-T1) — models the FEAT-RAG-08 run-2 reproducer.
- `test_check_late_approval_prefers_latest_across_candidate_dirs`
  (AC-T2) — stale repo-root + fresh worktree → worktree wins.
- `test_check_late_approval_repo_root_only_still_works` (AC-T3) —
  direct-mode regression guard with worktrees root explicitly absent.
- `test_timeout_warning_does_not_carry_hardcoded_sdk_timeout_budget`
  (AC-T4) — asserts the misleading `1200s per invocation` clause is
  gone and the new progress.log pointer is present.

All 17 late-approval + warning tests pass; full 146-test
`test_feature_orchestrator.py` suite passes. No new ruff failures.
The 18 pre-existing failures elsewhere in the orchestrator tree
(4 digest-token + 6 design-context + 8 venv + 1 dead-id) all
reproduce on `main` and are unrelated.

**Lessons.**

- The CRSTL R1 fix (per-specialist timeout scaled by complexity)
  unmasked this defect by widening the window in which Coach
  legitimately writes after the feature timer fires. Before CRSTL,
  the worker thread always SDKTimeoutError'd before reaching the
  Coach write, so `_check_late_approval` correctly returned `None`
  for a different reason — no `coach_turn_*.json` ever existed. The
  R1 fix shifted the failure mode from "no Coach write" to "Coach
  write to the wrong directory the lookup never checks", and the
  late-approval reclassifier silently kept returning `None`. This
  is an instance of the broader pattern in
  `.claude/rules/absence-of-failure-is-not-success.md`: an oracle
  that returns "no signal" when its real failure is "wrong place to
  look".
- Centralising the candidate-dirs walk in `_autobuild_candidate_dirs`
  / `_latest_coach_turn_path` means future code that needs to find
  Coach output for a task only has to call one helper, not
  re-implement the worktree-vs-direct logic. The audit-log block
  already needed the same walk (AC-R1.3) — without the helper, that
  block would have been a second copy of the same logic.

**R2 deferral.** The parent review's R2 (bound code-reviewer SDK
turn count or working set) is intentionally not in this task — see
the `Why R2 (CRSTL F2 / reviewer working set) is NOT in this task`
section above. With R1 in place, run-2's existing on-disk Coach
approval flips TASK-AIV2-003 to `APPROVED_LATE` and the wave
passes. R2 should be opened as a separate follow-up after at least
one production wave runs with R1 live, so the SDK-turn / working-set
bound can be sized against real data.

## See Also

- Parent review: `TASK-REV-RAG8R2`
  ([report](../../../specialist-agent/.claude/reviews/TASK-REV-RAG8R2-review-report.md)).
- Sibling already-landed fix: `TASK-FIX-CRSTL-MULT`
  ([completed/2026-05/](../completed/2026-05/TASK-FIX-CRSTL-MULT-propagate-complexity-to-specialists.md)).
- Original TASK-ATR-003 work that introduced the late-approval
  mechanism — referenced via `LATE_APPROVAL_GRACE_S` declaration at
  [feature_orchestrator.py:259-272](../../guardkit/orchestrator/feature_orchestrator.py#L259-L272).
