---
id: TASK-FIX-GD02
title: Scope git detection to per-task file changes in shared worktrees
status: backlog
created: 2026-02-20T00:00:00Z
updated: 2026-02-20T00:00:00Z
priority: high
tags: [autobuild, bugfix, git-detection, worktree, file-attribution]
task_type: feature
complexity: 6
parent_review: TASK-REV-A515
feature_id: FEAT-AOF
wave: 2
implementation_mode: task-work
dependencies: [TASK-FIX-PV01]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Scope git detection to per-task file changes in shared worktrees

## Description

Fix the most impactful bug from TASK-REV-A515: `_detect_git_changes()` in `guardkit/orchestrator/agent_invoker.py` reports cumulative changes across the entire shared worktree rather than per-task deltas.

When multiple tasks share a worktree (`.guardkit/worktrees/FEAT-XXX`), later-completing tasks inherit the file changes of all previously completed tasks. TASK-RK01-012 (a documentation task) reported `24 files created, 66 modified` when it only touched ~4 files — the remaining 84 files came from 11 previously completed tasks.

This renders per-task file metrics, scope-creep detection, and documentation constraints unreliable for any task after Wave 1.

## Source

- Review report: `.claude/reviews/TASK-REV-A515-review-report.md` (Finding 2)
- Evidence: `Git detection added: 64 modified, 20 created files` for TASK-RK01-012

## Files to Modify

- `guardkit/orchestrator/agent_invoker.py` (primary)
- `guardkit/orchestrator/autobuild.py` (may need baseline hook)

## Implementation Plan

### Approach: Per-task baseline snapshot

Capture the git state before each task starts, then compute only the delta at completion.

### Step 1: Add baseline snapshot method

```python
def _snapshot_worktree_state(self) -> Dict[str, set]:
    """Capture current worktree state for per-task delta detection."""
    changes = self._detect_git_changes()
    return {
        "modified": set(changes.get("modified", [])),
        "created": set(changes.get("created", [])),
    }
```

### Step 2: Capture baseline before task invocation

In `invoke_player()` (both task-work and direct paths), capture baseline before invoking the SDK:

```python
self._baseline_state = self._snapshot_worktree_state()
```

### Step 3: Compute delta in `_create_player_report_from_task_work`

Replace the current union-based git enrichment with delta computation:

```python
current = self._detect_git_changes()
delta_modified = set(current.get("modified", [])) - self._baseline_state.get("modified", set())
delta_created = set(current.get("created", [])) - self._baseline_state.get("created", set())
```

### Step 4: Apply same delta logic in `_create_synthetic_direct_mode_report`

The direct mode path also uses `_detect_git_changes()` — apply the same baseline delta.

### Step 5: Log the baseline vs delta for observability

```python
logger.info(
    f"Git detection for {task_id}: baseline={len(baseline_modified)}+{len(baseline_created)}, "
    f"delta={len(delta_modified)}+{len(delta_created)}"
)
```

## Edge Cases

- **First task in worktree**: Baseline will be empty, delta = full git diff (correct)
- **Parallel tasks in same wave**: Each task snapshots at its own start time; concurrent changes from sibling tasks may appear in both deltas. This is acceptable — the counts will be approximate but much closer to reality than cumulative totals
- **Resume after interruption**: Baseline must be captured fresh (not persisted) since worktree state may have changed

## Acceptance Criteria

- [ ] Baseline captured before each task invocation (both task-work and direct paths)
- [ ] Git-detected file counts reflect only per-task changes, not cumulative feature changes
- [ ] `_create_player_report_from_task_work` uses delta instead of union
- [ ] `_create_synthetic_direct_mode_report` uses delta instead of raw git state
- [ ] First task in worktree still reports correct file counts
- [ ] Unit tests verify delta computation with mock git state
- [ ] Logging shows baseline vs delta counts for observability
