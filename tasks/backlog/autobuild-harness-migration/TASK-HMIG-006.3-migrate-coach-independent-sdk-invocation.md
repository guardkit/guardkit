---
id: TASK-HMIG-006.3
title: Migrate Coach's independent SDK invocation (coach_validator.py:1869+) through HarnessAdapter
status: backlog
task_type: implementation
created: 2026-05-20T18:00:00Z
priority: medium
complexity: 5
parent_task: TASK-HMIG-006
parent_review: TASK-REV-HMIG
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 3
intensity: standard
effort_hours: 4
depends_on:
  - TASK-HMIG-006   # Establishes the substrate seam
tags:
  - autobuild
  - harness
  - langgraph-migration
  - coach
---

# Task: Migrate Coach's independent SDK invocation through HarnessAdapter

## Description

TASK-HMIG-006 explicitly excluded the **third SDK call site** at
`guardkit/orchestrator/quality_gates/coach_validator.py:1869+` from
scope. This is Coach's independent SDK invocation — the
"trust-but-verify" pytest run Coach uses to validate Player claims.

Per parent task AC-004 plan note: "CoachValidator is not modified by
this task." This follow-up migrates that boundary.

## Why this is a separate task

Per the parent task implementation plan §1:

> Coverage of `coach_validator.py:1992` (`isinstance(message,
> AssistantMessage)`). That's the Coach's own SDK invocation, not
> consuming the Player's events.

And §7 risk row:

> When Coach runs the LangGraph substrate later in the migration,
> *that* boundary will need its own harness dispatch.

After this task lands, **both** Player and Coach dispatch through the
HarnessAdapter substrate seam. Until then, Coach remains SDK-bound
even when `GUARDKIT_HARNESS=langgraph`.

## Acceptance Criteria

- [ ] AC-001: `coach_validator.py:1869+` dispatches through
      `select_harness()` (same pattern as the Player path migrated in
      TASK-HMIG-006 Phase 3b).
- [ ] AC-002: Coach-specific orchestrator concerns
      (`coach_max_turns`, `bypassPermissions` permission mode,
      verifier-specific allowed_tools) remain orchestrator-side.
- [ ] AC-003: Existing Coach tests continue to pass with
      `GUARDKIT_HARNESS=sdk`.
- [ ] AC-004: New tests verify Coach dispatch when
      `GUARDKIT_HARNESS=langgraph`.
- [ ] AC-005: AC-008 surface preserved (Coach is a key validator;
      regressions break feature-build).

## Dependencies

This task depends on **TASK-HMIG-006.2** for true LangGraph-path
parity — if TASK-HMIG-006.2 has not landed, Coach's independent
verification on the LangGraph path will be lossy in the same ways
described in the Wave-2 divergences table.

## References

- Parent task: [TASK-HMIG-006](../../design_approved/autobuild-harness-migration/TASK-HMIG-006-refactor-agent-invoker-cross-repo-dispatch.md)
- Parent review: TASK-REV-HMIG §3 (live execution-flow trace identifying third SDK call site)
- Implementation plan §1 (explicit out-of-scope deferral)
