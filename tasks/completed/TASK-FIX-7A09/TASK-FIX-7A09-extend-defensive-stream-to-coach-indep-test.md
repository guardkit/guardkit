---
id: TASK-FIX-7A09
title: Extend 7A03 defensive SDK handling to Coach independent-test path
status: completed
created: 2026-04-24T18:30:00Z
updated: 2026-04-24T19:20:00Z
completed: 2026-04-24T19:20:00Z
completed_location: tasks/completed/TASK-FIX-7A09/
previous_state: in_review
state_transition_reason: "Task-complete invoked; all ACs met, tests passing, Graphiti seed written"
priority: high
task_type: implementation
tags: [autobuild, sdk, coach, stream-resilience, defensive-handling]
parent_review: TASK-REV-F3D7
feature_id: FEAT-F3D7
implementation_mode: task-work
wave: 1
conductor_workspace: autobuild-sdk-stall-resilience-phase2-w1-2
complexity: 3
depends_on: []
---

# Task: Extend 7A03 defensive SDK handling to Coach independent-test path

## Description

TASK-FIX-7A03 wrapped the Player/Coach agent-invocation path (`_invoke_with_role`
in `agent_invoker.py`) with per-message `(MessageParseError, ValueError)`
try/except plus outer `error_class` population on `AgentInvocationError`. That
protection works for the streaming loop it covers.

The **Coach independent-test SDK path** is a structurally separate SDK call at
[coach_validator.py:1375](../../../guardkit/orchestrator/quality_gates/coach_validator.py#L1375)
(`_run_tests_via_sdk`) that does not flow through `_invoke_with_role`. It uses
a bare `async for message in query(prompt=prompt, options=options):` with only
a catch-all `except (CLINotFoundError, ProcessError, CLIJSONDecodeError, Exception)
as e: ... raise` at `:1474`. The caller at `:1732-1736` then logs
`"SDK test execution failed, falling back to subprocess: {e}"` — opaque, with
no `stderr`, no `error_class`, no phase information.

The transcript of forge-run-3 (lines 218-223, 288-293, 727-729) shows this
path firing three times in Wave 1 and at least once per task in Wave 2, always
falling back silently to subprocess. The underlying cause is transport-level
(bundled CLI subprocess exit-code-1) — surfaced as `ProcessError` *before or
between* messages, which 7A03's per-message try/except cannot reach even if
applied to this loop.

This task symmetrises 7A03's protection and surfaces the transport failure
shape so upstream classification (TASK-FIX-7A02, TASK-FIX-7A07) can see it.

## Acceptance Criteria

- [ ] `_run_tests_via_sdk` in
      [coach_validator.py](../../../guardkit/orchestrator/quality_gates/coach_validator.py#L1308)
      (around line 1375) wraps its `async for message in query(...):` with the
      same per-message `(MessageParseError, ValueError)` try/except shape used
      in 7A03 at `agent_invoker.py:2257-2271` — message-level parse errors are
      logged and skipped, the stream continues.
- [ ] The catch-all at `:1474` is broken into explicit `ProcessError` and
      `CLIJSONDecodeError` handlers (before the bare `Exception`). Each
      populates structured information (`exit_code`, `stderr`, `error_class`)
      available to callers.
- [ ] The fallback log at `:1732-1736` no longer logs the opaque `{e}`. Instead
      it logs something like:
      `"SDK test execution failed (error_class={cls}, exit_code={rc}), falling
      back to subprocess. stderr: {stderr_head}"` — truncating stderr to a
      sensible head (e.g. 500 chars).
- [ ] New test file `tests/orchestrator/test_coach_sdk_stream_resilience.py`
      with:
      - (a) Simulated stream that raises `ProcessError(exit_code=1, stderr="...")`
            mid-stream → fallback log line contains `exit_code=1` and a
            substring of the stderr.
      - (b) Simulated stream with `MessageParseError` on one message →
            non-terminal, stream continues and warning logged.
      - (c) Simulated stream with a valid `ResultMessage` followed by
            `ProcessError` → the `ResultMessage` is still processed and no
            silent data loss occurs.
- [ ] No change to the subprocess-pytest fallback semantics — it still runs;
      the change is only in what diagnostic information is emitted when the
      SDK path fails.
- [ ] Arch review (Phase 2.5) scores ≥60/100.
- [ ] Coverage on changed lines ≥80% (standard intensity).

## Implementation Notes

- **Reuse, don't reimplement**: 7A03's handler shape is already in
  `agent_invoker.py:2257-2321`. Factor shared logic if a natural helper exists;
  otherwise copy the pattern (both sites are SDK streaming loops with the same
  shape).
- **`error_class` field**: already exists on `AgentInvocationError`
  (`exceptions.py:217-231`, populated inconsistently per TASK-REV-F3D7
  findings). Populate it here consistently; do not introduce a new exception
  type.
- **Classifier interaction**: once `error_class` is populated on the Coach
  independent-test path, the existing summary-layer classifier (TASK-FIX-7A02's
  framework) will correctly route transport-level failures in future incidents.
  This task does **not** need to add new classifier code — just surface the
  signal.
- **Do not** relax the subprocess fallback behaviour. It is the intentional
  safety net; this task improves the log emitted when falling back, not
  whether fallback happens.

## Key References

- **Review report**: [docs/reviews/bdd-acceptance-wired-up/forge-run-3-analysis.md](../../../docs/reviews/bdd-acceptance-wired-up/forge-run-3-analysis.md)
- **Transcript evidence**: [docs/reviews/bdd-acceptance-wired-up/forge-run-3.md](../../../docs/reviews/bdd-acceptance-wired-up/forge-run-3.md)
  (lines 218-223, 288-293, 727-729)
- **7A03 prior art**: `tasks/completed/TASK-FIX-7A03/TASK-FIX-7A03-defensive-sdk-message-handling.md`
- **7A03 implementation**: `guardkit/orchestrator/agent_invoker.py:2257-2423`
- **Target site**: `guardkit/orchestrator/quality_gates/coach_validator.py:1308-1477, 1717-1736`
- **Exception shape**: `guardkit/orchestrator/exceptions.py:217-231`
- **Graphiti seed** (to add post-completion): `guardkit__project_decisions` —
  *"Coach independent-test SDK path shares 7A03's stream-resilience shape;
  defensive handling must be symmetric between Player-invocation and Coach
  independent-test code paths"*
