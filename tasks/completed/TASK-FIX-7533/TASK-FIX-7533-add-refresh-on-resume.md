---
id: TASK-FIX-7533
title: Add --refresh flag for worktree rebase-on-resume in feature orchestrator
task_type: feature
parent_review: TASK-REV-7530
feature_id: FEAT-CF57
wave: 2
implementation_mode: task-work
complexity: 5
priority: medium
dependencies:
  - TASK-FIX-7531
status: completed
completed: 2026-03-02T12:00:00Z
tags: [autobuild, feature-orchestrator, worktree, resume, rebase]
test_results:
  status: passed
  coverage: null
  last_run: 2026-03-02T12:00:00Z
  tests_passed: 105
  tests_failed: 0
---

# Task: Add --refresh Flag for Worktree Rebase-on-Resume

## Context

When `guardkit autobuild feature FEAT-XXX --resume` is used, the existing worktree is reused as-is with no mechanism to incorporate changes from main. This caused FEAT-CF57 run_2 to fail because ABFIX fixes landed on main after the worktree was created, but the resume path never pulled them in.

## Problem

The `feature_orchestrator.py` resume path:
1. Detects incomplete state
2. Prompts `[R]esume / [F]resh`
3. Reuses worktree path as-is
4. Has zero `rebase`, `merge`, `pull`, or `fetch` operations

The `--fresh` flag exists but destroys all prior work, which is not acceptable when 6/14 tasks are already completed.

## Implementation

### New Flag

Add `--refresh` (or `--rebase`) flag to the feature orchestrator and CLI:

```bash
guardkit autobuild feature FEAT-XXX --resume --refresh
```

### Behaviour

When `--refresh` is used with `--resume`:
1. Fetch latest main: `git fetch origin main`
2. Attempt rebase: `git rebase origin/main`
3. If conflicts detected:
   - Abort rebase: `git rebase --abort`
   - Warn user: "Rebase failed due to conflicts. Use --fresh or resolve manually."
   - Exit without proceeding
4. If rebase succeeds, continue with normal resume flow

### Files Modified

- `guardkit/orchestrator/feature_orchestrator.py` — Added `refresh` parameter, `_refresh_worktree()` method, wired into both resume paths, extended `_prompt_resume()` with `[U]pdate` option
- `guardkit/cli/autobuild.py` — Added `--refresh` CLI flag, mutual exclusion validation, pass-through to orchestrator
- `tests/unit/test_feature_orchestrator_refresh.py` — **NEW** 16 tests covering init validation, fetch/rebase, conflict abort, setup phase integration, prompt options, banner display

### Trade-offs

| Pro | Con |
|-----|-----|
| Picks up bug fixes from main | May introduce merge conflicts |
| Prevents stale-code failures | Adds complexity to resume path |
| Non-destructive (aborts on conflict) | Rebase rewrites history on worktree branch |

### Expected Interface

The resume prompt has been extended:

```
Options:
  [R]esume - Continue from where you left off
  [U]pdate - Rebase on latest main, then resume
  [F]resh  - Start over from the beginning
```

## Acceptance Criteria

- [x] `--refresh` flag accepted by CLI
- [x] Rebase attempted when `--refresh` + `--resume` used together
- [x] Graceful abort on merge conflicts (no data loss)
- [x] Clear user messaging for success and failure cases
- [x] Tests for rebase success, conflict abort, and flag validation
