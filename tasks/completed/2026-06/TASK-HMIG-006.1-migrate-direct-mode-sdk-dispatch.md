---
id: TASK-HMIG-006.1
title: Migrate direct-mode TaskWork SDK dispatch (agent_invoker.py:5269+) through HarnessAdapter
status: completed
task_type: implementation
created: 2026-05-20T18:00:00Z
updated: 2026-06-04T00:00:00Z
completed: 2026-06-04T00:00:00Z
completed_location: tasks/completed/2026-06/
previous_state: in_review
state_transition_reason: "Task complete; harness migration applied, all 4 ACs met, 21 acceptance tests passing, zero new regressions vs baseline. All three SDK call sites identified in TASK-REV-HMIG §3 now dispatch through the HarnessAdapter substrate seam."
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

- [x] AC-001: The direct-mode TaskWork dispatch path at
      `agent_invoker.py:5269+` no longer re-imports `claude_agent_sdk`
      directly. Instead it routes through `select_harness()`.
- [x] AC-002: Any direct-mode-only kwargs (e.g. different max_turns,
      different permission_mode) are preserved as orchestrator-side
      arguments to the harness constructor.
- [x] AC-003: Existing tests that exercise the direct-mode path
      continue to pass with `GUARDKIT_HARNESS=sdk`.
- [x] AC-004: New test cases verify the direct-mode path dispatches
      correctly when `GUARDKIT_HARNESS=langgraph` is set.

## References

- Parent task: [TASK-HMIG-006](../../design_approved/autobuild-harness-migration/TASK-HMIG-006-refactor-agent-invoker-cross-repo-dispatch.md)
- Parent review: TASK-REV-HMIG §3 (live execution-flow trace identifying second SDK call site)
- Implementation plan §1 (out-of-scope deferral)
- Pattern reference: [TASK-HMIG-006.3](../../completed/2026-06/TASK-HMIG-006.3-migrate-coach-independent-sdk-invocation.md) — Coach's independent SDK invocation migration; established the harness-migration pattern this task replays at the third SDK call site.
- Canonical Player-path pattern: `_invoke_with_role` at `guardkit/orchestrator/agent_invoker.py:2855-3003` (TASK-HMIG-006 Phase 3b).

## Implementation Summary

Refactored `AgentInvoker._invoke_task_work_implement` to dispatch through
the `HarnessAdapter` substrate seam established by TASK-HMIG-006 and
replayed by TASK-HMIG-006.3. The direct-mode TaskWork dispatch path now
routes through `select_harness()` exactly like the Player path in
`_invoke_with_role` and Coach's independent verifier in
`coach_validator._run_tests_via_sdk`, so `GUARDKIT_HARNESS=langgraph`
routes the **second** SDK call site consistently.

After this task lands, **all three** SDK call sites identified in
TASK-REV-HMIG §3 dispatch through the harness substrate seam:

1. `_invoke_with_role` (TASK-HMIG-006 — Player path, primary)
2. `_invoke_task_work_implement` (this task — direct-mode TaskWork)
3. `coach_validator._run_tests_via_sdk` (TASK-HMIG-006.3 — Coach's
   independent verification)

**Production change** (`guardkit/orchestrator/agent_invoker.py`):

- Removed the method-local `from claude_agent_sdk import (...)` block
  (and its ImportError diagnostic). Harness owns the lazy import
  (sdk_harness.py:212-232) and surfaces the same "Claude Agent SDK
  import failed.\n..." diagnostic via `AgentInvocationError` (D-4).
- Replaced the `ClaudeAgentOptions(**_tw_options_kwargs)` construction
  + `query(prompt=prompt, options=options)` call with
  `select_harness(sdk_timeout_seconds=..., allowed_tools=[...],
  permission_mode="acceptEdits", max_turns=effective_max_turns,
  resume_session_id=self._last_session_id, sdk_debug_dir=_sdk_debug_dir,
  cleanup_handler_installer=_install_sdk_cleanup_handler,
  setting_sources=["project"], cwd=self.worktree_path)` followed by
  `async for event in harness.invoke(...)`. Orchestrator-side concerns
  (per AC-002) — the Player tool list, `acceptEdits` permission mode,
  complexity-scaled `max_turns`, session resumption, sdk_debug, cleanup
  handler, project-only setting sources — all stay orchestrator-side
  and flow through harness kwargs.
- Translated the SDK message-type dispatch to typed `HarnessEvent`
  dispatch: `AssistantMessageEvent` → text collection +
  `event.raw.content` walk for `ToolUseBlock` / `ToolResultBlock` tool
  tracking and per-Bash `tool.exec` emission; `ResultMessageEvent` →
  `event.session_id` for resumption, `event.raw.num_turns` for
  `sdk_turns_used`, break. The content-block walk uses
  `type(block).__name__` duck-typing to match the heartbeat scan at
  `agent_invoker.py:2974-2989` and the SDK harness's own ToolUseBlock
  emission at `sdk_harness.py:319` — no hard SDK imports required.
- Replaced the four-clause SDK exception cascade
  (`CLINotFoundError` / `ProcessError` / `CLIJSONDecodeError` /
  `Exception`) with a single `AgentInvocationError` catch (D-4). The
  harness normalises all SDK-specific exceptions to
  `AgentInvocationError` with the **pre-migration message wording
  preserved verbatim** so downstream consumers (test assertions, log
  greps) keep working: "Claude Code CLI not installed.",
  "SDK process failed (exit ...)", "Failed to parse SDK response: ...".
- Preserved orchestrator-side concerns per Design Decision D-3:
  retry loop (TASK-FIX-46F2), heartbeat (`async_heartbeat`),
  sdk_debug preservation (`_sdk_preserve_prompt` / `_sdk_preserve_event`
  via `event.raw`), rate-limit detection
  (`detect_rate_limit` → `RateLimitExceededError`), session_id capture
  (TASK-RFX-B20B), and the `effective_max_turns` complexity-scaling
  (TASK-ABSR-MAXT). Each retry iteration constructs a fresh harness
  per Design Decision D-6 (single-use per invocation). The explicit
  `_tw_gen.aclose()` bookkeeping is gone — the harness's own finally
  block (sdk_harness.py:449-459) owns generator hygiene
  (TASK-RFX-8332 / TASK-FIX-GEN1).
- Surfaced the resume-intent drop loudly (TASK-HMIG-006 AC-007) when
  `_last_session_id` is set and the resolved harness does not support
  resume, matching the Player path warning at
  `agent_invoker.py:2886-2892`.

**Test changes**:

1. `tests/unit/test_agent_invoker.py`:
   - Renamed mock SDK block classes (`MockTextBlock` → `TextBlock`,
     `MockAssistantMessage` → `AssistantMessage`, etc.) in
     `TestInvokeTaskWorkImplement._create_mock_sdk` so the harness's
     duck-typing on `type(block).__name__` accepts the fixtures. With
     `sys.modules["claude_agent_sdk"]` patched, the harness's lazy
     imports resolve to these classes; the duck-typing only succeeds
     when the `__name__` matches the SDK literal exactly.
   - Added module-end `TestTaskWorkHarnessMigration` class (5 tests)
     mirroring TASK-HMIG-006.3's `TestCoachHarnessMigration` pattern:
     dispatch through `select_harness` with full Player kwargs
     (AC-001 + AC-002), text from `AssistantMessageEvent` flows to
     parser, `AgentInvocationError` → `TaskWorkResult(success=False)`
     with preserved message, `GUARDKIT_HARNESS=langgraph` dispatch
     boundary (AC-004), and `_last_session_id` round-trip
     (TASK-RFX-B20B parity).

2. `tests/unit/test_generator_close_fix.py`:
   - Updated `TestInvokeTaskWorkImplementGeneratorClose` (3 tests) and
     `TestSdkCleanupHandlerPreserved::test_cleanup_handler_in_task_work`
     (1 test) to assert the **new harness-ownership contract** instead
     of the pre-migration `_tw_gen = query(...)` /
     `await _tw_gen.aclose()` source patterns: dispatch through
     `select_harness` / `harness.invoke`, retry loop preserved,
     SDK-specific exception cascade gone, cleanup handler threaded
     through `cleanup_handler_installer=_install_sdk_cleanup_handler`.
     The behavioural guarantee (generator is `aclose()`d on every exit
     path) is now covered by harness-side tests in
     `tests/orchestrator/harness/test_sdk_harness.py`.

3. `tests/unit/test_sdk_environment_parity.py`:
   - Updated `TestBug472DefenseInExistingPaths` (2 tests) to assert
     the post-harness-migration call form
     `check_assistant_message_error(event.raw)` — the literal
     `check_assistant_message_error(message)` form is gone from
     both `_invoke_with_role` (TASK-HMIG-006) and now
     `_invoke_task_work_implement` (this task). The semantic
     contract (bug #472 defence) is upheld at both call sites; the
     count assertion (`>= 2`) now reflects the new literal form.
     One pre-existing failure (`test_agent_invoker_task_work_implement_checks_error`)
     fixed as a side effect.

## Test Outcomes

| Scope | Pre-migration | Post-migration | Δ |
|---|---|---|---|
| `TestInvokeTaskWorkImplement` (10) | 9 pass, 1 fail | 9 pass, 1 fail | 0 |
| `TestTaskWorkHarnessMigration` (5, new) | — | 5 pass | +5 |
| `TestInvokeTaskWorkImplementGeneratorClose` (3) | 3 pass | 3 pass | 0 |
| `TestSdkCleanupHandlerPreserved::test_cleanup_handler_in_task_work` (1) | 1 pass | 1 pass | 0 |
| `TestBug472DefenseInExistingPaths` (3) | 2 pass, 1 fail | 3 pass | +1 |
| **Aggregate broad sweep** (autobuild paths) | 882 pass, 26 fail | 887 pass, 26 fail | +5 new passes, 0 new failures |

The one pre-existing failure in `TestInvokeTaskWorkImplement` —
`test_invoke_task_work_implement_mode_passed` — asserts the literal
substring `"/task-work"` is absent from the rendered task-work
prompt; the prompt content has evolved to mention `/task-work` for
unrelated reasons. This failure pre-dates TASK-HMIG-006.1 and was
not addressed here (out of scope).

The 26 carry-over failures in the broad sweep are pre-existing
TASK-HMIG-006 / TASK-HMIG-006.3 fallout — primarily source-inspection
tests that grep for pre-harness-migration substrings in
`_invoke_with_role` and `coach_validator._run_tests_via_sdk`, plus
test-ordering flakiness in the autobuild orchestrator suite. None
were caused by, or are blocking, TASK-HMIG-006.1.

## Lessons

- **Existing harness-migrated paths produce a forgiving test seam**:
  with `sys.modules["claude_agent_sdk"]` patched, the harness's lazy
  imports resolve to the test's mock classes, and the harness's
  duck-typing accepts them as long as `type(block).__name__` matches
  the SDK literal. The minimal change to existing tests was renaming
  the mock classes to drop the `Mock` prefix — preserving all
  existing test logic and intent.
- **`event.raw` is the canonical bridge** between the typed-event
  contract and the SDK-shape walks the orchestrator already does for
  per-tool emission and API-error checks. The migration is a
  straightforward translation: `isinstance(message, AssistantMessage)`
  → `isinstance(event, AssistantMessageEvent)`, and any block-level
  walks read `event.raw.content`. The duck-typing pattern at
  `agent_invoker.py:2974-2989` (Player path) is the right model for
  block-level walks at any harness-migrated call site.
- **Single-use harness per retry iteration** (Design Decision D-6) is
  the correct posture for retry loops. The harness owns the SDK
  generator and its cleanup; the orchestrator owns the retry decision
  and the backoff. This separation kept the retry loop intact while
  letting the per-iteration generator hygiene move into the harness's
  finally block.
- **Wording-verbatim normalisation in the harness** (sdk_harness.py
  line-by-line matches the pre-migration diagnostic strings) is the
  reason the four-clause SDK exception cascade collapses to a single
  `AgentInvocationError` catch without breaking any test assertion
  or log monitoring downstream. Future harness-migration call sites
  should rely on this guarantee.

## Architectural Decisions

- **D-1**: Use typed `HarnessEvent` for primary dispatch; read
  `event.raw.content` for SDK-shape block walks (ToolUseBlock,
  ToolResultBlock, TextBlock for the progress-log heuristic). Matches
  the Player-path convention at `agent_invoker.py:2974-2989`.
- **D-2**: Construct a fresh harness per retry iteration (D-6 — single
  use per invocation). The retry loop (TASK-FIX-46F2) lives
  orchestrator-side; each iteration's harness owns its own generator
  lifecycle.
- **D-3**: Read `sdk_turns_used` from `event.raw.num_turns` on the
  `ResultMessageEvent`. The typed event does not expose `num_turns`
  (TASK-HMIG-006 D-1 left it on raw); LangGraph harness leaves
  `raw=None` so `sdk_turns_used` stays `None` on that path —
  acceptable because LangGraph manages its own turn loop.
- **D-4**: Replace the four-clause SDK exception cascade with a
  single `except AgentInvocationError` catch. Preserves all
  diagnostic information (the harness's normalised message strings
  match the pre-migration wording verbatim) while letting the
  orchestrator stay substrate-agnostic.
- **D-5**: Pass `cwd=self.worktree_path` unconditionally to
  `select_harness`. The SDK branch pops it (TASK-FIX-002R-CONSUME);
  the LangGraph branch consumes it to build the path-confined
  `LocalShellBackend`. Mirrors the Player path at
  `agent_invoker.py:2874`.
- **D-6**: Update source-inspection tests at the new contract surface
  (harness ownership of generator hygiene) rather than leave them
  broken. The behavioural guarantee (generator close on every exit
  path) is covered by the harness-side tests in
  `tests/orchestrator/harness/test_sdk_harness.py`; the
  orchestrator-side tests now assert dispatch-boundary placement
  instead.
