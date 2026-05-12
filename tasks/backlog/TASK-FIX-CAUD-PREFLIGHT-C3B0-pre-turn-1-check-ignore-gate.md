---
id: TASK-FIX-CAUD-PREFLIGHT-C3B0
title: "Claim-audit pre-flight: walk planned target list through `git check-ignore -v` before turn 1"
status: backlog
task_type: implementation
priority: medium
created: 2026-05-12
tags: [autobuild, coach, claim-audit, preflight, fail-fast]
related_tasks: [TASK-FIX-CAUD-J6F1, TASK-REV-J6F1]
parent_task: TASK-FIX-CAUD-J6F1
estimated_complexity: 4
---

# TASK-FIX-CAUD-PREFLIGHT-C3B0: pre-turn-1 git check-ignore gate

## Summary

Originally AC-005 of [TASK-FIX-CAUD-J6F1](../completed/TASK-FIX-CAUD-J6F1-claim-audit-path-normalisation.md).
Deferred to a follow-up because the J6F1 incident is fully closed by AC-001
(path normalisation) + AC-002 (diagnostic overhaul) + AC-003 (harness
allowlist) + AC-004 (verified F3c-addressed) + AC-006 (regression tests),
all delivered in the parent task. AC-005 is hardening for a *different*
scenario: the one the now-removed misleading "unanchored .gitignore rule"
diagnostic was speculating about — a planned target file that genuinely
*is* gitignored.

## Acceptance Criteria

### AC-001: pre-flight check-ignore on the planned target list

- [ ] Before turn 1 of any autobuild task, walk the task's planned
      target file list (sourced from the implementation plan if one is
      on disk, else the task's `files_to_create` / similar frontmatter
      field) through `git check-ignore -v` in the worktree.
- [ ] If any planned target IS git-ignored, fail-fast with an error
      message that names the exact rule and its source file (the very
      thing the previous Coach message *speculated* about but couldn't
      prove). Block the run before the Player burns SDK turns.
- [ ] If no implementation plan / file list is available, skip the
      pre-flight (don't fail-open with a warning — keep behaviour
      identical to the no-plan-on-disk path).

## Where this hooks in

- Insertion point: somewhere in the autobuild orchestrator's pre-turn-1
  hook. Likely candidates:
  - `guardkit/orchestrator/agent_invoker.py` — before the first SDK
    invocation for the task.
  - `guardkit/autobuild/...` (find the loop entry).
- Reuses existing infrastructure:
  - Plan loader at `installer/core/commands/lib/plan_audit.py` already
    knows how to load `docs/state/{task_id}/implementation_plan.md|json`.
  - The check-ignore subprocess wrapper at
    `guardkit/orchestrator/coach_verification.py` (`_classify_dropped_path`,
    `_git_check_ignore_rule`) is the canonical caller idiom — refactor
    or duplicate at the orchestrator-side as appropriate.

## Out of Scope

- The original J6F1 reproducer (closed by parent task).
- Pre-flight checks for non-gitignore filters (sparse-checkout,
  assume-unchanged, attribute filters). The parent task's revised
  diagnostic now correctly enumerates these as *next-step
  investigation* hypotheses; flagging them pre-flight is a separate
  hardening effort and not covered by AC-005's brief.

## Notes

- The matching rule output should be human-readable: `<source>:<line>:<pattern>`
  (the format `git check-ignore -v` already emits).
- For the "rebase the worktree" hint shape (project-root .gitignore vs
  worktree-local), reuse `coach_validator._ignore_rule_is_project_root`.
- Add unit + integration tests:
  - Plan with a gitignored target → fail-fast with rule string.
  - Plan with no gitignored targets → pre-flight passes silently.
  - No plan on disk → pre-flight skipped.
