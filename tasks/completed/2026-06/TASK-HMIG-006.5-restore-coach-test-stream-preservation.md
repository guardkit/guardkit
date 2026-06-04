---
id: TASK-HMIG-006.5
title: Restore sdk_debug preservation for Coach test path after HMIG-006.3 migration
status: completed
task_type: implementation
created: 2026-06-04T00:00:00Z
updated: 2026-06-04T00:00:00Z
completed: 2026-06-04T00:00:00Z
previous_state: in_review
state_transition_reason: "task-complete: all ACs verified, regression sweep clean"
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

- [x] AC-001: When `GUARDKIT_AUTOBUILD_PRESERVE_DEBUG=1`, the Coach
      test prompt is recorded under
      `sdk_debug/turn_<n>/coach/test_run/` mirroring the pre-migration
      shape produced by `_sdk_preserve_prompt`.
- [x] AC-002: Each `HarnessEvent` consumed by Coach's loop is recorded
      to a JSONL file under the same directory, mirroring
      `_sdk_preserve_event` semantics. The recorded shape should
      include the typed event class name plus the underlying raw
      payload when available (`event.raw` for SDK-harness events).
- [x] AC-003: The diagnostic call is a no-op when the env var is
      unset (zero overhead in production).
- [x] AC-004: A new test exercises the preservation path with the
      env var set and asserts the expected file shape.
- [x] AC-005: The implementation does not regress AC-001/AC-002 from
      TASK-HMIG-006.3 (`select_harness` dispatch boundary preserved,
      Coach-specific orchestrator concerns stay Coach-side).

## Implementation Summary

Restored TASK-DIAG-F4A2's diagnostic surface for the Coach
independent-test path that TASK-HMIG-006.3 dropped during the harness
substrate migration. Took shape (1) from the Implementation Notes
(inline restoration in `_run_tests_via_sdk`), not the broader
`preserve_harness_event` refactor — the Coach test call site is the
only consumer that needs the surface today.

### Changes

- **`guardkit/orchestrator/quality_gates/coach_validator.py`** — added
  `preserve_prompt` + `preserve_event` calls in `_run_tests_via_sdk`
  with a synthesised options-shaped snapshot dict capturing the
  post-migration intent (`cwd`, `allowed_tools`, `permission_mode`,
  `max_turns`, `model`, `harness` from `GUARDKIT_HARNESS`,
  `pythonpath_prepend`, `sdk_timeout_seconds`). Preservation hooks sit
  alongside the `select_harness` dispatch boundary, not inside it
  (AC-005 invariant preserved). Zero overhead when the env var is
  unset.

- **`guardkit/orchestrator/sdk_debug.py`** — fixed two latent defects
  the new call site exposed:
  1. `_event_to_jsonable` re-imposes `payload["type"] = type_name`
     after `dataclasses.asdict`, so `HarnessEvent`'s
     `type: Literal["assistant_message"]` field no longer shadows the
     class name in the JSONL line.
  2. `_options_to_jsonable` routes plain `dict`/`list`/`tuple` inputs
     through `_coerce_jsonable` directly — dict instances don't carry
     `__dict__`, so the synthesised snapshot would have fallen to the
     `repr()` branch and serialised as a Python literal string instead
     of a JSON object.
  Added `_maybe_inline_raw` helper that walks `event.raw` recursively
  through `_event_to_jsonable` for richer SDK-Message capture (AC-002
  "underlying raw payload when available" contract).

- **`tests/unit/test_coach_validator.py`** — added
  `TestCoachSdkDebugPreservation` (4 tests covering env-var off /
  full triple write / recursive `.raw` walk / per-turn idempotency).
  Class added to `_HARNESS_OWNING_TEST_CLASSES` so the autouse
  SDK-failure fixture defers to its explicit `select_harness` patch.

### Tests

- New: 4/4 pass (`TestCoachSdkDebugPreservation`).
- Regression sweep: `test_coach_validator.py` 283/283, sibling
  `TestCoachHarnessMigration` 6/6, `TestSdkEnvMerge` 3/3,
  `test_sdk_debug_preservation.py` 36/36. Zero new failures across
  `tests/unit/test_agent_invoker.py` either (pre-existing failures
  reproduced identically without the diff via `git stash`).

## Lessons

- `dataclasses.asdict` on `HarnessEvent` writes a `type:
  "<literal>"` field that silently shadows any class-name tag a
  diagnostic helper sets earlier in its payload dict. Any future
  helper that wraps `asdict` to add `type=ClassName` should re-impose
  the tag after the update, not before — exposed in the
  pre-migration code only because the old SDK Message classes lacked
  a `type` field at top level.
- `_options_to_jsonable`'s fallback chain (dataclass → pydantic →
  `__dict__` → `repr`) silently mis-serialises plain dicts because
  dict instances don't have `__dict__`. Post-migration call sites
  that synthesise an options-shaped record should hand the helper a
  shape it actually understands — fixed centrally here so future
  call sites don't have to know the trap.
- "Mirror pre-migration shape" is ambiguous for AC-002 when the
  wire format genuinely changed (raw SDK `Message` → wrapped
  `HarnessEvent`). The literal mirror — embedding the SDK Message
  via repr — would have satisfied the AC text but produced a less
  useful artefact than the recursive `.raw` walk. Worth flagging in
  follow-up AC drafting that "mirror" means "preserve diagnostic
  fidelity" not "preserve byte-for-byte JSONL shape".

## References

- Parent task: [TASK-HMIG-006.3](../../completed/2026-06/TASK-HMIG-006.3-migrate-coach-independent-sdk-invocation.md)
- Removed call sites restored: `coach_validator.py:2424-2435` and
  `coach_validator.py:2474` (pre-migration line numbers; see
  `b300c9e3` for the removal diff and the new restoration around
  `coach_validator.py:2427-2510` for the post-migration shape).
- Source modules: `guardkit/orchestrator/sdk_debug.py`
  (`preserve_prompt`, `preserve_event`, `_event_to_jsonable`,
  `_options_to_jsonable`, `_maybe_inline_raw`).
- Code-review reference: TASK-HMIG-006.3 code review (Phase 5)
  flagged this as the only outstanding follow-up before close.

## Original Implementation Notes (pre-completion)

Two viable shapes considered during planning:

1. **Inline in `_run_tests_via_sdk`** — easiest; mirrors the
   pre-migration call site by invoking `_sdk_preserve_prompt` against
   a synthesised `ClaudeAgentOptions`-shaped record and
   `_sdk_preserve_event` against each harness event before dispatch.
   Keeps the harness boundary clean. **← Chosen.**
2. **Generalise `sdk_debug` to accept harness events** — broader
   refactor; introduces a `preserve_harness_event` helper that walks
   `HarnessEvent` typed events and records them in a harness-agnostic
   JSONL shape. Player path could adopt the same helper.

Shape (1) selected for task scope; promote to shape (2) only if other
call sites need the same surface.
