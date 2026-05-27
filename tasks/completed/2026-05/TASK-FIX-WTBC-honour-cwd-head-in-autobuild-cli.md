---
id: TASK-FIX-WTBC
title: Honour cwd HEAD in autobuild task/feature CLI worktree creation
task_type: implementation
status: completed
created: 2026-05-27T15:30:00Z
updated: 2026-05-27T16:45:00Z
completed: 2026-05-27T16:45:00Z
completed_location: tasks/completed/2026-05/
previous_state: in_review
state_transition_reason: "task-complete: all ACs met, 211 tests passing"
priority: high
complexity: 3
effort_hours: 4
parent_review: TASK-REV-HM09
feature_id: FEAT-HMIG
parent_feature: hmig-pre-canary-fixes
wave: 1
conductor_workspace: hmig-pre-canary-fixes-wave1-2
implementation_mode: task-work
intensity: standard
depends_on: []
related_tasks:
  - TASK-HMIG-009B    # Unblocks the full canary (fixture-branch isolation)
tags:
  - autobuild
  - cli
  - worktree
  - pre-canary-blocker
  - bug-fix
falsifier: "After fix, invoke `guardkit autobuild task TASK-{fixture}` from a git worktree on branch `feature/test-branch`; assert `git -C .guardkit/worktrees/<task_id> rev-parse HEAD` matches `feature/test-branch` tip, not main HEAD."
---

# Task: Honour cwd HEAD in autobuild task/feature CLI worktree creation

## Description

When `guardkit autobuild task` or `guardkit autobuild feature` is invoked from a git worktree on a non-main branch, the inner `autobuild/<task_id>` worktree is created from main HEAD instead of the calling cwd's HEAD. This defeats fixture-branch isolation (the TASK-HMIG-009 canary's strategy) and affects any caller that depends on running autobuild from a non-main branch (parallel feature-build, multi-feature worktrees).

Diagnosed by [TASK-REV-HM09 review report §2](../../../.claude/reviews/TASK-REV-HM09-review-report.md#2-ac-002--f4-worktree-manager-dispatch-diagnosis).

## Root cause

The defect is a misrouted plumb, not a missing capability:

- `WorktreeManager.create(base_branch="main")` at [`worktrees/manager.py:345-348`](../../../guardkit/worktrees/manager.py#L345-L348) defaults to "main". The library default is fine.
- `AutoBuildOrchestrator.orchestrate(base_branch: str = "main", ...)` at [`orchestrator/autobuild.py:1177`](../../../guardkit/orchestrator/autobuild.py#L1177) also defaults to "main" and is never overridden by the CLI.
- The cwd-HEAD detection at [`cli/autobuild.py:1190-1199`](../../../guardkit/cli/autobuild.py#L1190-L1199) (inside `_find_worktree`) reads `git rev-parse --abbrev-ref HEAD` — but only to populate `Worktree.base_branch` for the `status` display command. It is never consumed by the create path.
- The `task` and `feature` CLI commands expose no `--base-branch` flag.

**Same defect exists in `feature_orchestrator.py:1026`** — the bug affects both `autobuild task` and `autobuild feature`.

## Acceptance Criteria

- [x] **AC-001** — `guardkit autobuild task TASK-{fixture}` invoked from a worktree on a non-main branch creates the inner `autobuild/<task_id>` branch from the cwd HEAD, not main HEAD. Verified by `git -C .guardkit/worktrees/<task_id> rev-parse HEAD`.
- [x] **AC-002** — Same applies to `guardkit autobuild feature FEAT-{fixture}`.
- [x] **AC-003** — A `--base-branch` CLI flag is added to both commands as an explicit override. Precedence: `--base-branch > cwd HEAD > "main"` (defensive default if `git rev-parse` fails).
- [x] **AC-004** — Regression tests in `tests/cli/test_autobuild.py` (or equivalent):
  - Invoke `autobuild task` from a fixture worktree on a non-main branch; assert inner worktree HEAD matches cwd HEAD.
  - Invoke `autobuild feature` equivalent.
  - `--base-branch` flag overrides cwd HEAD detection.
  - Graceful fallback to "main" when `git rev-parse --abbrev-ref HEAD` fails (e.g., detached HEAD).
- [x] **AC-005** — `WorktreeManager.create()`'s `base_branch="main"` default is **unchanged** (it's a sensible library default; the CLI is the right place for cwd detection).
- [x] **AC-006** — `--base-branch` flag documented in both commands' `--help` output.

## Implementation Summary (task-work, 2026-05-27)

**Fix** (`guardkit/cli/autobuild.py`):
- Added module-level helper `_detect_base_branch(default="main", cwd=None)` — reads
  the calling cwd's branch via `git rev-parse --abbrev-ref HEAD`; falls back to
  `default` on `CalledProcessError`/`FileNotFoundError` or detached HEAD (`"HEAD"`).
- Added `--base-branch` option to both `task` and `feature` commands.
- Both commands resolve `effective_base_branch = base_branch or _detect_base_branch()`
  (precedence `--base-branch > cwd HEAD > "main"`) and pass `base_branch=` into
  `orchestrate(...)` (previously omitted → defaulted to "main").
- DRY: refactored `_find_worktree` to reuse the helper via `cwd=worktree_path`,
  removing the duplicated inline subprocess block.

**Tests** (`tests/unit/test_cli_autobuild.py`):
- `TestDetectBaseBranch`: cwd HEAD detection, explicit-cwd, detached-HEAD fallback,
  not-a-repo fallback, missing-git fallback (AC-004 graceful fallback).
- task/feature passthrough + `--base-branch` override tests (AC-001/002/003).
- `--help` presence tests (AC-006).
- `test_worktree_created_from_cwd_head_end_to_end`: real-repo WorktreeManager.create
  proves inner worktree HEAD == feature-branch tip ≠ main tip (the falsifier; no SDK).
- Updated `test_task_command_success` for the new `base_branch` kwarg.

Also fixed two pre-existing exact-signature assertions in
`tests/unit/test_feature_orchestrator.py` broken by the additive `base_branch` kwarg.

**Result:** 211 passed across both affected test files. AC-005 verified by leaving
`manager.py` untouched.

## Implementation Notes

Factor the cwd-HEAD detection out of `_find_worktree` (currently buried in the status path) into a small helper:

```python
def _detect_base_branch(default: str = "main") -> str:
    """Read the cwd's current branch; fall back to default on failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        branch = result.stdout.strip()
        # HEAD detached → "HEAD"; fall back to default
        if branch and branch != "HEAD":
            return branch
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return default
```

Call from the `task` and `feature` commands; pass through to `orchestrate(base_branch=...)`.

## References

- Parent review: [TASK-REV-HM09 review report §4, §5](../../../.claude/reviews/TASK-REV-HM09-review-report.md#4-ac-004--f4-remediation-recommendation)
- Canary evidence: [`docs/state/TASK-REV-HMIG/canary-analysis.md` §3.F4](../../../docs/state/TASK-REV-HMIG/canary-analysis.md#f4-autobuild-worktree-manager-ignores-the-cwds-current-branch)
- Affected sites:
  - [`guardkit/worktrees/manager.py:345-348`](../../../guardkit/worktrees/manager.py#L345-L348)
  - [`guardkit/orchestrator/autobuild.py:1177, 1277, 1510-1513`](../../../guardkit/orchestrator/autobuild.py#L1510-L1513)
  - [`guardkit/orchestrator/feature_orchestrator.py:736, 1026-1029`](../../../guardkit/orchestrator/feature_orchestrator.py#L1026-L1029)
  - [`guardkit/cli/autobuild.py:147-507, 1190-1199`](../../../guardkit/cli/autobuild.py#L1190-L1199)
