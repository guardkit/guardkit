---
id: TASK-FIX-FRESHCLEAN01
title: "--fresh must force-clean worktree/branch + reset state for terminal (completed/merged) features, not just incomplete ones"
status: completed
task_type: fix
created: 2026-06-15T00:00:00Z
updated: 2026-06-15T00:00:00Z
completed: 2026-06-15T00:00:00Z
previous_state: in_review
state_transition_reason: "task-complete — all acceptance criteria met"
completed_location: tasks/completed/TASK-FIX-FRESHCLEAN01/
priority: medium
complexity: 3
related: [FEAT-9DDE, TASK-AB-COACHRUNPARITY01]
implementation_mode: task-work
tags: [autobuild, feature-orchestrator, fresh, worktree, state-reset, ux-wart]
---

# Task: `--fresh` should force-clean regardless of feature completion status

## Why this task exists

Surfaced during **FEAT-9DDE run 12** (2026-06-15 validation session — see
[`docs/retro/session-handoff-2026-06-15-coachrunparity-validated-directfg01-exercised.md`](../../../docs/retro/session-handoff-2026-06-15-coachrunparity-validated-directfg01-exercised.md),
learning #1). After a *successful* run left `FEAT-9DDE.yaml` in
`status: completed`, re-launching with `--fresh` failed at worktree creation:

```
ERROR: Failed to create worktree for FEAT-9DDE: branch 'autobuild/FEAT-9DDE'
already exists and automatic cleanup failed.
fatal: a branch named 'autobuild/FEAT-9DDE' already exists
```

`--fresh`'s CLI help promises *"Start from scratch, ignoring saved state
(clears previous state)"* — but it does not deliver that for a terminal
feature.

## Root cause

[`feature_orchestrator.py:994-998`](../../../guardkit/orchestrator/feature_orchestrator.py#L994):

```python
# Handle fresh start
if self.fresh:
    if FeatureLoader.is_incomplete(feature):              # <-- the bug
        console.print("[yellow]⚠[/yellow] Clearing previous incomplete state")
        self._clean_state(feature)
    return self._create_new_worktree(feature, feature_id, base_branch)
```

`_clean_state` ([`:1832`](../../../guardkit/orchestrator/feature_orchestrator.py#L1832)
— removes the existing worktree + `autobuild/<id>` branch AND calls
`FeatureLoader.reset_state`) is **gated on `FeatureLoader.is_incomplete`**
([`feature_loader.py:1467`](../../../guardkit/orchestrator/feature_loader.py#L1467)),
which returns `True` only for `in_progress` / `paused` / `failed`. For a
**`completed` / `merged` / `planned`** feature `is_incomplete` is `False`, so
under `--fresh`:

1. the stale worktree + `autobuild/<id>` branch are **not removed** →
   `_create_new_worktree` fails with "branch already exists"; and
2. `reset_state` ([`feature_loader.py:1569`](../../../guardkit/orchestrator/feature_loader.py#L1569))
   never runs → all tasks stay `completed` and would be **skipped as
   already-completed** ([`feature_orchestrator.py:2492`](../../../guardkit/orchestrator/feature_orchestrator.py#L2492))
   even if the branch conflict were resolved.

The `is_incomplete` guard is correct for the *resume/prompt* paths below it,
but wrong for `--fresh`: "fresh" means unconditional.

**Current manual workaround** (what the operator did in run 12):
```bash
git worktree remove .guardkit/worktrees/<FEAT> --force
git branch -D autobuild/<FEAT>
# + hand-reset the feature YAML to a clean planned/pending fixture
```

## Acceptance Criteria

- [x] `--fresh` on a `completed` / `merged` feature with an existing
      worktree + `autobuild/<id>` branch **succeeds**: it removes the worktree
      and branch, resets all task statuses to `pending` (feature → `planned`),
      then creates a fresh worktree — no "branch already exists" failure.
- [x] `--fresh` on a terminal feature actually **re-runs the tasks** (Wave 1
      starts; tasks are not skipped as already-completed).
- [x] `--fresh` on an *incomplete* feature behaves exactly as today.
- [x] `--fresh` with no existing worktree/state behaves exactly as today.
- [x] If the existing worktree holds **unmerged approved commits**, `--fresh`
      emits a clear WARNING before discarding it (never-auto-merge spirit: the
      operator asked for fresh, but should be told what is being thrown away).
- [x] Regression test: feature in `completed` state + existing worktree/branch
      → `--fresh` → no error, tasks reset to pending, run starts at Wave 1.

## Resolution (2026-06-15)

Fixed in [`feature_orchestrator.py`](../../../guardkit/orchestrator/feature_orchestrator.py):

1. **Dropped the `is_incomplete` guard** under `if self.fresh:` in `_setup_phase`
   so `_clean_state` runs **unconditionally** for `--fresh`. `_clean_state` is
   idempotent (no-ops when there is nothing to clean) and already removes the
   worktree *before* deleting the branch (correct ordering for the
   "branch in use by worktree" case), then calls `reset_state` (tasks → pending,
   feature → `planned`). The reported `merged`-state fixture retains
   `execution.worktree_path`, so cleanup fires and the branch conflict is gone.
2. **Added `_warn_unmerged_before_fresh`** — read-only, warning-only (any git
   failure is suppressed so it can never abort cleanup). When the
   `autobuild/<id>` branch is ahead of `base_branch`, it emits a WARNING naming
   the unmerged commit count before the branch is discarded.

Regression tests added to
[`tests/unit/test_feature_orchestrator.py`](../../../tests/unit/test_feature_orchestrator.py)
(section "Fresh Start — Terminal Feature"): 6 tests covering all six ACs.
Full `tests/unit/test_feature_orchestrator.py` +
`tests/integration/test_autobuild_fresh_cleanup.py` +
`tests/orchestrator/test_feature_orchestrator_pth_warning.py` = 165 passed.

## Implementation sketch

In `_setup_phase`, drop the `is_incomplete` guard under `if self.fresh:` so
`_clean_state` runs **unconditionally** for `--fresh` (it is already
idempotent — no-ops when there is nothing to clean). Confirm `_clean_state`'s
worktree cleanup handles the "branch in use by worktree" ordering (remove
worktree before deleting branch) and that `reset_state` fires for terminal
features. Keep the `⚠ Clearing previous … state` banner; add the unmerged-work
WARNING.

## Risk

Low–medium. Removing a worktree under `--fresh` is destructive, but that is the
documented intent of `--fresh` ("ignoring saved state"). The new WARNING on
unmerged commits mitigates accidental loss. No change to resume/refresh paths.

## Notes

- Discovered 2026-06-15; the broader FEAT-9DDE validation it surfaced from is
  complete (COACHRUNPARITY01 arm-b + DIRECTFG01 + EVBINST02 all validated).
- This is a general orchestrator UX fix, not FEAT-9DDE-specific; filed here
  because that is where it surfaced.
