---
id: TASK-FIX-7A03
title: Handle unknown SDK message types defensively in Player streaming loop
status: completed
created: 2026-04-24T12:55:00Z
updated: 2026-04-24T14:20:00Z
completed: 2026-04-24T14:20:00Z
previous_state: in_review
completed_location: tasks/completed/TASK-FIX-7A03/
organized_files:
  - TASK-FIX-7A03-defensive-sdk-message-handling.md
priority: high
tags: [autobuild, sdk, claude-agent-sdk, streaming, error-handling, resilience]
parent_review: TASK-REV-E4F5
feature_id: FEAT-7A00
implementation_mode: task-work
wave: 1
conductor_workspace: autobuild-sdk-stall-resilience-w1-2
complexity: 4
depends_on: []
---

# Task: Defensive SDK message handling in agent_invoker streaming loop

## Description

Address review TASK-REV-E4F5 finding **F2** and recommendation **R3**. In
`guardkit/orchestrator/agent_invoker.py` (≈ lines 2216–2319), the Player
SDK invocation iterates SDK messages and catches three specific exception
classes (`CLINotFoundError`, `ProcessError`, `CLIJSONDecodeError`) plus a
blanket `except Exception` that swallows everything else into an opaque
`AgentInvocationError("SDK invocation failed for {agent_type}: {str(e)}")`.

When the API streams a new message type the installed SDK version doesn't
recognise (e.g. `rate_limit_event` in Run 2 of FEAT-FORGE-002), the SDK
raises during `async for message in gen`, kills the whole turn, and the
generic catch-all wraps it opaquely. One unknown stream message destroys an
entire Player turn — even if the other messages in the stream would have
produced usable output.

## Acceptance Criteria

- [ ] `async for message in gen` iteration is wrapped in a per-message
      try/except that, on parse-type exceptions (`ValueError` and any
      SDK-specific parse exception types if they exist — grep
      `claude_agent_sdk.__all__`), **logs a WARNING naming the unknown
      message and continues** rather than aborting the turn.
- [ ] Add a typed `except ValueError as e` clause immediately above the
      blanket `except Exception` in `_invoke_with_role`, that preserves
      `type(e).__name__` and full message in the `AgentInvocationError`
      payload (as a structured `error_class` field), so downstream
      classification (TASK-FIX-7A02) can distinguish parse errors from
      other failures.
- [ ] The blanket `except Exception` remains as a final safety net but its
      error message is augmented to include `type(e).__name__` so the
      surfaced error string is no longer opaque.
- [ ] If **zero** messages parsed successfully in the stream, the turn still
      fails — classification falls through to TASK-FIX-7A02's
      `player_invocation_stall`. If ≥1 parsed, the turn completes with
      whatever was parsed, and a WARNING count of dropped unknowns is
      emitted.
- [ ] Unit tests:
      1. Simulated stream with one unknown message type followed by a valid
         `AssistantMessage` → turn completes, WARNING logged, output includes
         the valid message.
      2. Simulated stream with all unknown message types → turn fails with
         clear "N messages unparseable" error containing `type(e).__name__`.
      3. `ValueError` with specific parse-related content → wrapped with
         `error_class="ValueError"` preserved.
- [ ] No regression on existing timeout / CLI-not-found / ProcessError /
      CLIJSONDecodeError handling (existing tests still pass).

## Files

- `guardkit/orchestrator/agent_invoker.py` (`_invoke_with_role`,
  try/except cascade ≈ 2303–2319, streaming loop ≈ 2216–2228)
- `guardkit/orchestrator/exceptions.py` (if `AgentInvocationError` lives
  there) — add `error_class` attr if appropriate.
- `tests/orchestrator/test_agent_invoker_sdk_errors.py` (new or extend).

## Implementation Notes

- **Breaking change risk**: today a turn with one unknown message fails fast.
  After this change it may appear to succeed but with partial content. Guard
  against false positives: only drop messages whose exception is a
  well-defined parse error, not any `Exception`. If SDK exposes an
  `UnknownMessageType` class, prefer catching that specifically.
- Check whether `claude_agent_sdk` exposes a stream-level recovery
  affordance (e.g. a `strict=False` option on `query()`). If it does,
  consider using that instead of per-message try/except. Grep the SDK
  source on disk before implementing; default to per-message try/except
  if no SDK affordance exists.
- Don't add "production / dev fallback" `try/except ImportError` idioms
  — the namespace-hygiene rule (`.claude/rules/namespace-hygiene.md`)
  expressly warns against them.

## Notes

- Cross-link: finding F2 + recommendation R3 in TASK-REV-E4F5.
- Wave 1 parallel: touches only `agent_invoker.py` and associated test file;
  no conflict with W1-1 (pyproject + install.sh + autobuild.py startup log),
  W1-3 (feature_orchestrator.py + environment_bootstrap.py), or W1-4 (docs).
- Error classification signal produced here (preserving `type(e).__name__`)
  is consumed by TASK-FIX-7A02 in Wave 2.
