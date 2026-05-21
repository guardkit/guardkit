---
id: TASK-HMIG-006.1
title: Migrate direct-mode TaskWork SDK dispatch (agent_invoker.py:5269+) through HarnessAdapter
status: backlog
task_type: implementation
created: 2026-05-20T18:00:00Z
priority: high
complexity: 5
parent_task: TASK-HMIG-006
parent_review: TASK-REV-HMIG
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 3
intensity: standard
effort_hours: 4
depends_on:
  - TASK-HMIG-006   # Wave 2 — establishes the HarnessAdapter substrate seam
tags:
  - autobuild
  - harness
  - langgraph-migration
  - frozen-path-touch
---

# Task: Migrate direct-mode TaskWork SDK dispatch through HarnessAdapter

## Description

TASK-HMIG-006 migrated the **primary** SDK call site
(`AgentInvoker._invoke_with_role` at `guardkit/orchestrator/agent_invoker.py:2359-2740`)
behind the `HarnessAdapter` interface. A **second SDK call site** at
`guardkit/orchestrator/agent_invoker.py:5269+` (direct-mode TaskWork
dispatch) was explicitly deferred per plan §1.

This task migrates that second boundary.

## Why this is a separate task

Per the parent task implementation plan §1:

> The second SDK call site at `agent_invoker.py:5270+` (direct-mode
> TaskWork dispatch). It re-imports `claude_agent_sdk` and runs its own
> query loop. Per parent review's §3 trace, that boundary is a separate
> refactor — file a follow-up task `TASK-HMIG-006.1` to migrate the
> direct-mode path once this task lands.

The substrate seam is now established; this task replays the Phase 3b
refactor at the second site.

## Acceptance Criteria

- [ ] AC-001: The direct-mode TaskWork dispatch path at
      `agent_invoker.py:5269+` no longer re-imports `claude_agent_sdk`
      directly. Instead it routes through `select_harness()`.
- [ ] AC-002: Any direct-mode-only kwargs (e.g. different max_turns,
      different permission_mode) are preserved as orchestrator-side
      arguments to the harness constructor.
- [ ] AC-003: Existing tests that exercise the direct-mode path
      continue to pass with `GUARDKIT_HARNESS=sdk`.
- [ ] AC-004: New test cases verify the direct-mode path dispatches
      correctly when `GUARDKIT_HARNESS=langgraph` is set.

## References

- Parent task: [TASK-HMIG-006](../../design_approved/autobuild-harness-migration/TASK-HMIG-006-refactor-agent-invoker-cross-repo-dispatch.md)
- Parent review: TASK-REV-HMIG §3 (live execution-flow trace identifying second SDK call site)
- Implementation plan §1 (out-of-scope deferral)
