---
id: TASK-HMIG-006.3
title: Migrate Coach's independent SDK invocation (coach_validator.py:1869+) through HarnessAdapter
status: completed
task_type: implementation
created: 2026-05-20T18:00:00Z
updated: 2026-06-04T00:00:00Z
completed: 2026-06-04T00:00:00Z
completed_location: tasks/completed/2026-06/
previous_state: in_review
state_transition_reason: "Task complete; all quality gates passed, code review approved, follow-up filed as TASK-HMIG-006.5"
follow_up_tasks:
  - TASK-HMIG-006.5  # Restore Coach test-stream preservation (low priority)
implementation_commit: b300c9e3
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

## Implementation Summary

Refactored `CoachValidator._run_tests_via_sdk` to dispatch through the
`HarnessAdapter` substrate seam established by TASK-HMIG-006 and extended
by TASK-HMIG-006.2. Coach's independent verifier now routes through
`select_harness()` exactly like the Player path in
`agent_invoker._invoke_with_role`, so `GUARDKIT_HARNESS=langgraph` routes
both substrates consistently. Both Player and Coach are now harness-bound;
Coach is no longer SDK-bound on the LangGraph path.

**Production change** (`guardkit/orchestrator/quality_gates/coach_validator.py`):

- Lifted harness imports to module top (`AssistantMessageEvent`,
  `ResultMessageEvent`, `ToolResultEvent`, `select_harness`,
  `AgentInvocationError`, `check_assistant_message_error`), matching the
  Player-path import convention at `agent_invoker.py:71-77` and making
  `coach_validator.select_harness` a stable patch target for tests.
- Replaced the direct `claude_agent_sdk.query(prompt, options)` call with
  `select_harness(sdk_timeout_seconds=self.test_timeout, allowed_tools=["Bash"],
  permission_mode="bypassPermissions", max_turns=1, model=model,
  cwd=self.worktree_path)` followed by an `async for event in harness.invoke(...)`
  event-loop translation. Coach-specific orchestrator concerns
  (per AC-002) stay Coach-side.
- Added a method-local `_patched_pythonpath` context manager (Step D in
  the implementation plan) that scopes the `PYTHONPATH` prepend mutation
  around `harness.invoke()`. Chosen over adding an `env=` kwarg to
  `ClaudeSDKHarness.__init__` to avoid widening the harness interface
  for a Coach-only concern (ISP). The single-coach-turn-per-worktree
  invariant makes the process-global side effect acceptable.
- Translated the SDK message-type dispatch to typed `HarnessEvent` dispatch:
  `AssistantMessageEvent.text` → `collected_text`, `ToolResultEvent` →
  `bash_output` + tri-state `bash_is_error`, `ResultMessageEvent` →
  break. The `ToolResultEvent` branch is dead code on the current SDK
  harness (which does not walk `UserMessage.content`) and is documented
  as such; the heuristic-fallback branch on `collected_text` is the
  effective pass/fail determination for SDK invocations.
- Replaced the four-clause SDK exception cascade (`CLINotFoundError` /
  `ProcessError` / `CLIJSONDecodeError` / `Exception`) with a single
  `AgentInvocationError` catch. The harness normalises all SDK-specific
  exceptions to `AgentInvocationError` (D-4); the structured diagnostic
  info (`exit_code`, `stderr`, `error_class`) is preserved inside the
  exception message string and the `run_independent_tests` fallback log
  still captures `type(e).__name__`.

**Test change** (`tests/unit/test_coach_validator.py`):

- Added module-level autouse fixture
  `_default_coach_harness_simulates_sdk_failure` (with explicit opt-out
  for `TestSdkEnvMerge` and `TestCoachHarnessMigration` via
  `_HARNESS_OWNING_TEST_CLASSES`). The fixture patches `select_harness`
  at the `coach_validator` binding to return a harness whose `invoke()`
  raises `AgentInvocationError`, restoring the pre-migration
  "SDK fails → subprocess fallback" semantics for the ~250 pre-existing
  tests that depended on the implicit fallback chain. Single-point
  change; zero pre-existing test bodies modified except
  `TestSdkEnvMerge` (assertion mechanism updated).
- Rewrote `TestSdkEnvMerge` (3 tests): switched from the
  `CapturingOptions` kwarg-capture mechanism on the SDK module to an
  `os.environ` snapshot mechanism via the new `_FakeHarness` helper
  class. Added `test_pythonpath_restored_after_invoke` verifying the
  `_patched_pythonpath` context manager restores the original value.
- Added `TestCoachHarnessMigration` (6 tests): dispatch through
  `select_harness` with Coach kwargs, `ToolResultEvent(is_error=True)`
  → failure result, `ToolResultEvent(is_error=False)` → heuristic-pass,
  `AssistantMessageEvent` → heuristic-pass on SDK path,
  `GUARDKIT_HARNESS=langgraph` dispatch boundary, and
  `AgentInvocationError` re-raise.

**Filed follow-up**: `TASK-HMIG-006.5` (Restore Coach test-stream
preservation post-migration, low priority) — flagged by code review as
the only outstanding sdk_debug surface gap.

## Approach

Standard harness-migration: mirror the Player-path pattern at
`agent_invoker.py:2855-3003`. Tri-state `bash_is_error` mapping
documented inline at the dead branch. The autouse fixture was added in
Phase 4.5 of the fix-loop after discovery that the harness short-circuits
on `ResultMessageEvent` (eating the post-`ResultMessage` exception that
pre-migration code relied on to trigger subprocess fallback).

## Lessons

- **Harness migrations introduce a subtle behavioural divergence at the
  short-circuit boundary**: `ClaudeSDKHarness.invoke` breaks on
  `ResultMessageEvent`; pre-migration code iterated until
  `StopAsyncIteration`. Any post-`ResultMessage` exception is invisible
  to harness-using callers. Pre-existing tests that relied on
  "SDK raises → fall back" semantics need an explicit fixture (autouse
  or per-test) to restore that contract. Future harness migrations
  should expect this gap.
- **Module-top harness imports are the right convention** even for
  lazy-loadable code, because `patch("module.select_harness", ...)` is
  the standard test seam — method-local imports break that seam silently.
  Matches the Player-path convention at `agent_invoker.py:71-77`.
- **Code reviewer's nit about the unreachable `False` branch in the
  tri-state mapping** is a real maintenance signal. The `False→None`
  mapping in the `ToolResultEvent` handler makes
  `elif bash_is_error is False:` unreachable on the current SDK path;
  keeping the branch live for future harness extensions requires an
  inline annotation, not just a one-shot Phase 2.5 comment.
- **Coach is load-bearing**: AC-005's regression-surface check must
  include sibling test files (`test_coach_validator_aliases.py`,
  `_fuzzy.py`, `_consumer_context.py`, `test_coach_parallel_isolation.py`)
  not just the primary file. The autouse fixture covered them all via
  the single `select_harness` patch point.

## Architectural Decisions

- **D-1**: Lifted `select_harness` and harness event types to module
  top in `coach_validator.py` — matches Player-path convention; required
  for stable test patch target.
- **D-2**: Chose context-managed `os.environ` mutation over adding
  `env=` to `ClaudeSDKHarness.__init__` — keeps harness interface narrow
  (ISP); acceptable because Coach runs one test turn per worktree.
- **D-3**: Kept the `elif bash_is_error is False:` branch live despite
  being unreachable on the current SDK path — preserves the tri-state
  contract for future harness extensions; documented inline.
- **D-4**: Removed `sdk_debug` preservation (`_sdk_preserve_prompt`,
  `_sdk_preserve_event`) from Coach test path — diagnostic feature not
  yet ported to harness boundary; tracked as TASK-HMIG-006.5 follow-up.
- **D-5**: Single autouse fixture for AC-005 preservation, not per-test
  edits — minimises blast radius (modify 1 fixture vs 18 test bodies).
