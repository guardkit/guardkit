---
id: TASK-HMIG-006.5
title: Restore sdk_debug preservation for Coach test path after HMIG-006.3 migration
status: backlog
task_type: implementation
created: 2026-06-04T00:00:00Z
priority: low
complexity: 3
parent_task: TASK-HMIG-006.3
parent_review: TASK-REV-HMIG
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
intensity: light
effort_hours: 1
depends_on:
  - TASK-HMIG-006.3
tags:
  - autobuild
  - harness
  - sdk-debug
  - diagnostics
  - follow-up
---

# Task: Restore sdk_debug preservation for Coach test path after HMIG-006.3 migration

## Description

TASK-HMIG-006.3 migrated `CoachValidator._run_tests_via_sdk` to dispatch
through the HarnessAdapter substrate seam. The pre-migration method
called `_sdk_preserve_prompt` and `_sdk_preserve_event` (from
`guardkit.orchestrator.sdk_debug`) under
`GUARDKIT_AUTOBUILD_PRESERVE_DEBUG=1` to record the Coach test prompt
and the SDK message stream under
`sdk_debug/turn_<n>/coach/test_run/` (TASK-DIAG-F4A2). The migration
removed those calls because the harness owns the message stream and
no equivalent hook exists yet at the harness boundary.

This follow-up restores the diagnostic surface for Coach test runs.

## Why this is a separate task

Per TASK-HMIG-006.3 implementation plan Section 8 ("Out of scope /
non-goals"):

> Modifying sdk_debug preservation for Coach test runs (pre-migration,
> `_sdk_preserve_prompt` at line 2428 records the prompt + options;
> post-migration this is deferred to a follow-up if needed).

The Coach test path is the lowest-traffic SDK call site and the
diagnostic loss is bounded — Player events are still captured by
the orchestrator-owned heartbeat / `agent_invoker` preservation. The
Coach-specific debug trail is only consulted during incident analysis
of `_run_tests_via_sdk` failures (rare), so deferring this to a
small follow-up was acceptable for the parent task.

## Acceptance Criteria

- [ ] AC-001: When `GUARDKIT_AUTOBUILD_PRESERVE_DEBUG=1`, the Coach
      test prompt is recorded under
      `sdk_debug/turn_<n>/coach/test_run/` mirroring the pre-migration
      shape produced by `_sdk_preserve_prompt`.
- [ ] AC-002: Each `HarnessEvent` consumed by Coach's loop is recorded
      to a JSONL file under the same directory, mirroring
      `_sdk_preserve_event` semantics. The recorded shape should
      include the typed event class name plus the underlying raw
      payload when available (`event.raw` for SDK-harness events).
- [ ] AC-003: The diagnostic call is a no-op when the env var is
      unset (zero overhead in production).
- [ ] AC-004: A new test exercises the preservation path with the
      env var set and asserts the expected file shape.
- [ ] AC-005: The implementation does not regress AC-001/AC-002 from
      TASK-HMIG-006.3 (`select_harness` dispatch boundary preserved,
      Coach-specific orchestrator concerns stay Coach-side).

## Implementation Notes

Two viable shapes:

1. **Inline in `_run_tests_via_sdk`** — easiest; mirrors the
   pre-migration call site by invoking `_sdk_preserve_prompt` against
   a synthesised `ClaudeAgentOptions`-shaped record and
   `_sdk_preserve_event` against each harness event before dispatch.
   Keeps the harness boundary clean.
2. **Generalise `sdk_debug` to accept harness events** — broader
   refactor; introduces a `preserve_harness_event` helper that walks
   `HarnessEvent` typed events and records them in a harness-agnostic
   JSONL shape. Player path could adopt the same helper.

Recommend (1) for this task scope; promote to (2) only if other
call sites need the same surface.

## References

- Parent task: [TASK-HMIG-006.3](../../in_progress/autobuild-harness-migration/TASK-HMIG-006.3-migrate-coach-independent-sdk-invocation.md)
- Removed call sites (pre-migration): `coach_validator.py:2424-2435` and
  `coach_validator.py:2474` (see git history for full context).
- Source modules: `guardkit/orchestrator/sdk_debug.py`
  (`preserve_prompt`, `preserve_event`).
- Code-review reference: TASK-HMIG-006.3 code review (Phase 5)
  flagged this as the only outstanding follow-up before close.
