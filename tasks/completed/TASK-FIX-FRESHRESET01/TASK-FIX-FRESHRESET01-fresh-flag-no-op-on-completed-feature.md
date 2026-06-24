---
id: TASK-FIX-FRESHRESET01
title: --fresh flag silently no-ops on a previously-COMPLETED feature; should reset feature-state YAML alongside worktree wipe (Shape A)
status: completed
resolution: superseded
superseded_by: TASK-FIX-FRESHCLEAN01
task_type: fix
created: 2026-06-09T13:30:00Z
updated: 2026-06-18T00:00:00Z
completed: 2026-06-18T00:00:00Z
previous_state: backlog
state_transition_reason: "Superseded — the Shape A fix landed under TASK-FIX-FRESHCLEAN01 (commit 3b39764e, completed 2026-06-15); all ACs verified met on current main, no new code required."
completed_location: tasks/completed/TASK-FIX-FRESHRESET01/
priority: high
complexity: 2
effort_hours: 1
deadline: 2026-06-15
parent_review: TASK-REV-HMIG
parent_task: TASK-HMIG-010
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 3
implementation_mode: direct
intensity: standard
blocker: false
surfaced_in: docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-20.md
falsifier: "After landing: running `guardkit autobuild feature FEAT-AOF --fresh ...` immediately after a successful run (feature `status: completed` in `.guardkit/features/FEAT-AOF.yaml`) re-executes all three tasks from scratch rather than reporting `SKIPPED - already completed` with 0s duration."
---

# Task: --fresh flag silently no-ops on a previously-COMPLETED feature

## ⛔ Resolution — SUPERSEDED by TASK-FIX-FRESHCLEAN01 (2026-06-18)

This task was **filed** as a bug report (commit `0be5fcff2`) but the fix it
specifies (Shape A — drop the `is_incomplete` guard so `_clean_state` fires on
*every* `--fresh`) was independently **implemented and completed under
[`TASK-FIX-FRESHCLEAN01`](../../completed/TASK-FIX-FRESHCLEAN01/TASK-FIX-FRESHCLEAN01.md)**
(commit `3b39764e`, completed 2026-06-15), which surfaced from the same
class of failure during FEAT-9DDE run 12.

Verified against current `main` (no new code required):

- **Root-cause guard is gone.** [`feature_orchestrator.py:1052-1056`](../../../guardkit/orchestrator/feature_orchestrator.py#L1052-L1056)
  now calls `_clean_state` **unconditionally** under `if self.fresh:` (the
  `is_incomplete` guard cited in this task's root-cause section was removed),
  with an inline comment crediting FRESHCLEAN01.
- **State reset is complete.** `_clean_state` → `FeatureLoader.reset_state`
  ([`feature_loader.py:1569-1589`](../../../guardkit/orchestrator/feature_loader.py#L1569-L1589))
  resets feature `status` → `planned` and every task's `status` → `pending`,
  `result` → `None`, `turns_completed`/`current_turn` → `0`,
  `started_at`/`completed_at` → `None` — exactly the field list this task's
  "Verify `_clean_state` resets all relevant fields" section requested. This is
  what stops the Phase-2 skip-check (`task.status == "completed"`) from firing.

### AC verification (all met by FRESHCLEAN01)

- [x] **AC-1** — `--fresh` after a successful run re-executes all tasks (task
      statuses `pending` at Phase 2). Covered by `reset_state` + test
      `test_fresh_cleans_terminal_feature_without_branch_error`
      ([`tests/unit/test_feature_orchestrator.py:432`](../../../tests/unit/test_feature_orchestrator.py#L432))
      which asserts `all(t.status == "pending" ...)`.
- [x] **AC-2** — unit test covering the previously-completed → `--fresh` path:
      same test (drives the feature to `status: completed` + tasks `completed`,
      asserts cleanup + reset).
- [x] **AC-3** — `--fresh` on a previously-FAILED feature still clears state
      (no regression): `test_fresh_incomplete_feature_still_cleans`
      (`failed` ∈ `is_incomplete` states).
- [x] **AC-4** — downstream falsifier removed: the manual-revert bottleneck is
      gone; an operator can re-run a completed feature with `--fresh`.

`GUARDKIT_HARNESS=sdk pytest tests/unit/test_feature_orchestrator.py -k fresh`
→ **10 passed** on current main (2026-06-18).

**Out-of-scope note honoured as-written:** this task's optional sub-item
(also reset per-task markdown frontmatter `autobuild_state` blocks) was *not*
implemented by FRESHCLEAN01 — `reset_state` operates on the feature YAML, not
the `tasks/**/TASK-*.md` files. This is harmless for the documented falsifier
because the Phase-2 skip-check reads `task.status` from the feature object
(YAML), which *is* reset. This task explicitly marked that sub-item
"OR documented as out-of-scope and operator must revert manually," so no
follow-up is filed.

---

## Why this task exists

Run 19 of FEAT-AOF completed successfully (3/3 tasks `approve` on turn
1, [`docs/state/TASK-REV-HMIG/run-19-artifacts/`](../../../docs/state/TASK-REV-HMIG/run-19-artifacts/)).
Run 20 attempted to re-validate TASK-FIX-COACHTESTTO with the same
invocation plus `--fresh`. Outcome:
[run-20 log](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-20.md):

```
[2026-06-09T13:02:46.510Z] ⏭ TASK-FIX-IA03: SKIPPED - already completed
[2026-06-09T13:02:46.523Z] ⏭ TASK-FIX-GD02: SKIPPED - already completed
[2026-06-09T13:02:46.523Z] ⏭ TASK-FIX-TP05: SKIPPED - already completed

FEATURE RESULT: SUCCESS
Status: COMPLETED
Tasks: 3/3 completed
Total Turns: 3
Duration: 0s
```

The `--fresh` flag's docs say *"Start fresh, ignoring any saved state"*
(`guardkit autobuild feature --help`), but the code only clears state
when the feature is INCOMPLETE. After a successful run the feature is
in `status: completed`, the clean-state branch is skipped, and Phase 2's
per-task skip-check (line 2250) immediately marks every task as
`SKIPPED - already completed`.

Effect: the operator cannot re-validate a previously-passing feature
with `--fresh` to confirm stability or to test a code change that
should affect Coach/Player behaviour. They have to manually revert
`.guardkit/features/{feature}.yaml` + per-task frontmatter
`autobuild_state` blocks before each re-run. This is the exact bottleneck
that prevented run 20 from validating TASK-FIX-COACHTESTTO.

## Root cause (precise code citation)

[`guardkit/orchestrator/feature_orchestrator.py:932-937`](../../../guardkit/orchestrator/feature_orchestrator.py#L932-L937):

```python
# Handle fresh start
if self.fresh:
    if FeatureLoader.is_incomplete(feature):
        console.print("[yellow]⚠[/yellow] Clearing previous incomplete state")
        self._clean_state(feature)
    return self._create_new_worktree(feature, feature_id, base_branch)
```

The inner `is_incomplete` guard makes `_clean_state` *only* fire on
previously-failed/partial runs. For a previously-completed run,
`--fresh` skips the state reset entirely and only recreates the
worktree. Then Phase 2's skip-check fires:

[`guardkit/orchestrator/feature_orchestrator.py:2249-2265`](../../../guardkit/orchestrator/feature_orchestrator.py#L2249-L2265):

```python
# Skip already completed tasks (for resume)
if task.status == "completed":
    ...
    console.print(f"  [dim]⏭ Skipping {task_id} (already completed)[/dim]")
```

So the orchestrator does the correct skip behaviour for `--resume` but
inherits it for `--fresh` because the YAML wasn't reset.

## What to do — Shape A (broaden the condition)

Per the operator decision (Shape A vs Shape B in the run-20 analysis):
**Shape A**, narrow the existing condition so `_clean_state` fires on
*any* `--fresh` invocation, not only on incomplete features. The
documented contract is *"Start fresh, ignoring any saved state"* which
matches Shape A.

**Edit** [`guardkit/orchestrator/feature_orchestrator.py:932-937`](../../../guardkit/orchestrator/feature_orchestrator.py#L932-L937):

```python
# Handle fresh start
if self.fresh:
    # Always clear state when --fresh is requested, regardless of
    # whether the feature is currently incomplete or completed.
    # The documented contract is "Start fresh, ignoring any saved state".
    # Previously this only cleared incomplete state, which silently
    # no-op'd --fresh after a previously-successful run because the
    # per-task skip-check at line 2250 then fired (TASK-FIX-FRESHRESET01).
    if not FeatureLoader.is_completely_pending(feature):
        console.print("[yellow]⚠[/yellow] Clearing previous state")
        self._clean_state(feature)
    return self._create_new_worktree(feature, feature_id, base_branch)
```

(`FeatureLoader.is_completely_pending` — or whatever the negative
condition is called — should be added if it doesn't exist; the message
just needs to skip the "Clearing" log line when there's nothing to
clear. Or simpler: drop the inner guard entirely and always print +
clean — the `_clean_state` call should be a no-op when there's nothing
to clean.)

**Verify `_clean_state` resets all relevant fields**:
- Feature-level `status` → `pending`
- Each task's `status` → `pending`
- Each task's `result` → `null`
- Each task's `turns_completed` → `0`
- Each task's `current_turn` → `0`
- Each task's `started_at` / `completed_at` → `null`
- Per-task frontmatter `autobuild_state` blocks (if also written) — should also be reset, OR documented as out-of-scope and operator must revert manually

If `_clean_state` doesn't already reset the per-task `tasks/backlog/.../TASK-*.md` frontmatter `autobuild_state` block, add that — the run-19→20 evidence shows those files were also written and contribute to the "looks completed" state.

## Acceptance criteria

- [ ] **AC-1**: `guardkit autobuild feature FEAT-AOF --fresh ...` immediately after a successful run re-executes all tasks. Verify with a smoke test: after the next successful FEAT-AOF run, invoke `--fresh` and confirm:
  - Wave 1 / TASK-FIX-IA03 reaches `Started turn 1: Player Implementation` (not `SKIPPED`)
  - Total `Duration: > 0s` (not 0s)
  - `.guardkit/features/FEAT-AOF.yaml`'s task statuses are `pending` or `in_progress` at start of Phase 2, not `completed`

- [ ] **AC-2**: Unit test in `tests/unit/test_feature_orchestrator.py` covering the previously-completed → `--fresh` path. Given a feature with `status: completed` and three tasks in `status: completed`, calling `_handle_worktree_setup` (or whatever the entry point is) with `fresh=True` results in `_clean_state` being called.

- [ ] **AC-3**: The opposite case still works — `--fresh` on a previously-FAILED feature continues to clear state and recreate the worktree (no regression in the existing path).

- [ ] **AC-4 (downstream falsifier)**: TASK-FIX-COACHTESTTO can be validated by re-running FEAT-AOF with `--fresh`. The current bottleneck (manual revert before every re-run) is gone.

## Implementation notes

- **Tiny change**: removing or broadening the inner `is_incomplete` guard. ~5-10 lines + 1-2 regression tests.
- **No CLI surface change**: the user invocation stays
  `guardkit autobuild feature ... --fresh ...`. Only behaviour changes.
- **Operator-facing note worth adding**: log message could distinguish "Clearing completed-feature state for fresh re-run" vs "Clearing incomplete-feature state for fresh re-run" — informative without being noisy.
- **Confidence**: this is a well-bounded fix. The skip-check at line 2250 is correct *for resume* and stays unchanged; the bug is purely in the `--fresh` entry path not feeding it `pending` task statuses.

## Related

- **Surfaced in**: [`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-20.md`](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-20.md) — 0s run, all three tasks skipped
- **The downstream task it blocks validating**: TASK-FIX-COACHTESTTO (Coach independent-test 300s timeout, post-run-19 caveat #1)
- **Workaround in the meantime**: revert
  `.guardkit/features/FEAT-AOF.yaml` and per-task frontmatter
  `autobuild_state` blocks via `git checkout HEAD -- <files>` before
  each `--fresh` invocation. See [the run-20 analysis](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-20.md) for the precise file list.
- **Sibling pattern**: the per-task frontmatter `autobuild_state` writes that the orchestrator does after every run are the same shape — they too need clearing on `--fresh`. The fix should cover both.
- **Run-19 success snapshot** that produced the YAML state triggering the run-20 skip: [`docs/state/TASK-REV-HMIG/run-19-artifacts/`](../../../docs/state/TASK-REV-HMIG/run-19-artifacts/)
