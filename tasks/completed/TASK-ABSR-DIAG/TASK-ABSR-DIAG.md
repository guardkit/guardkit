---
id: TASK-ABSR-DIAG
title: Fix heartbeat label confusion for orchestrator-invoked specialists
status: completed
created: 2026-04-28T00:00:00Z
updated: 2026-04-28T00:00:00Z
completed: 2026-04-28T00:00:00Z
previous_state: in_review
completed_location: tasks/completed/TASK-ABSR-DIAG/
priority: medium
tags: [autobuild, diagnostics, observability, FEAT-ABSR-9C6E, R6.b]
parent_review: TASK-REV-9D13
feature_id: FEAT-ABSR-9C6E
implementation_mode: task-work
task_type: feature
wave: 1
historical_wave: 3
complexity: 3
depends_on: []
test_results:
  status: passed
  coverage: null
  last_run: 2026-04-28T00:00:00Z
  notes: |
    AC-008: pytest tests/unit/orchestrator/test_specialist_invocations.py
    tests/unit/test_agent_invoker*.py — 588 passed, 1 pre-existing failure
    on main (test_invoke_task_work_implement_mode_passed) unrelated to this
    task. Three new tests added (TestHeartbeatLabelOverride class +
    parametrized run_specialist test) all pass.
    AC-009: mypy strict produces identical 103-error count on main and on
    this branch — zero new errors introduced.
    AC-010: ruff produces identical 21-error count on main and on this
    branch — zero new lint findings.
---

# TASK-ABSR-DIAG — Fix heartbeat label confusion for specialists

## Description

The `async_heartbeat` context manager at `agent_invoker.py:179-219` logs `f"[{task_id}] {phase} in progress... ({elapsed}s elapsed)"`, where `phase` is supplied by the caller. At `agent_invoker.py:2264`, `_invoke_with_role` uses `f"{agent_type.capitalize()} invocation"` as the phase. Because `_SPECIALIST_INVOCATION_PROFILE["test-orchestrator"] = ("player", "acceptEdits")` (specialist_invocations.py:90), a `run_specialist("test-orchestrator")` call produces heartbeats labelled `"Player invocation in progress..."` — identical to actual Player heartbeats.

The actual Player path uses a different label (`"task-work implementation"`, agent_invoker.py:4878). Operators reading run history conflate the two.

**This caused v1 of [TASK-REV-9D13](../../../.claude/reviews/TASK-REV-9D13-report.md) to misdiagnose the J004-013 timing**: 40 heartbeats from `(30s elapsed)` to `(1200s elapsed)` were attributed to the Player when they were actually the Phase-4 specialist's. v2 untangles this by cross-referencing the run-2 history (Player heartbeats at lines 2845-2894 vs specialist heartbeats at lines 2911-2950).

**Targets**: Bug E in TASK-REV-9D13 v2 §0. **MED priority — pure diagnostic improvement, no semantic change.**

## Acceptance Criteria

- [ ] AC-001: `run_specialist` in `specialist_invocations.py` accepts an optional `heartbeat_label_override: Optional[str] = None` parameter and threads it through to `_invoke_with_role` via a new keyword argument on `AgentInvoker._invoke_with_role`.
- [ ] AC-002: `run_specialist` constructs the override as `f"specialist:{specialist_name} invocation"` (e.g. `"specialist:test-orchestrator invocation"`, `"specialist:code-reviewer invocation"`) and passes it.
- [ ] AC-003: `_invoke_with_role` at `agent_invoker.py:2261-2266` uses the override when provided: `phase_label = heartbeat_label_override or f"{agent_type.capitalize()} invocation"`. Default behaviour (no override) is unchanged.
- [ ] AC-004: New test `test_run_specialist_heartbeat_label_includes_specialist_name` in `tests/unit/orchestrator/test_specialist_invocations.py`: mock `_invoke_with_role` to capture its kwargs, invoke `run_specialist("test-orchestrator", ...)`, assert the captured `heartbeat_label_override` contains the substring `"specialist:test-orchestrator"`. (Async helper test fixture pattern matches existing tests in that file.)
- [ ] AC-005: New test `test_invoke_with_role_uses_override_when_provided` in `tests/unit/test_agent_invoker.py` (or wherever `_invoke_with_role` tests live): patch `async_heartbeat` to capture its `phase` argument; call `_invoke_with_role(agent_type="player", heartbeat_label_override="specialist:foo invocation", ...)`; assert phase is `"specialist:foo invocation"`. A second test asserts that without the override, phase is `"Player invocation"` (current behaviour preserved).
- [ ] AC-006: Existing 11 tests in `tests/unit/orchestrator/test_specialist_invocations.py` and any tests of `_invoke_with_role` (likely in `tests/unit/test_agent_invoker_*.py`) continue to pass without modification.
- [ ] AC-007: Documentation update: add a one-line note in [`docs/guides/autobuild-instrumentation-guide.md`](../../../docs/guides/autobuild-instrumentation-guide.md) that heartbeat labels for orchestrator-invoked specialists are prefixed `"specialist:"` (e.g., `"specialist:test-orchestrator invocation"`); the actual Player uses `"task-work implementation"`.
- [ ] AC-008: `pytest tests/unit/orchestrator/test_specialist_invocations.py tests/unit/test_agent_invoker*.py -v` passes.
- [ ] AC-009: `mypy guardkit/orchestrator/specialist_invocations.py guardkit/orchestrator/agent_invoker.py` strict-clean.
- [ ] AC-010: Lint/format pass.

## Implementation Notes

Exact code in [TASK-REV-9D13 v2 §4 R6.b](../../../.claude/reviews/TASK-REV-9D13-report.md#r6--phase-25-complexity-heuristic--heartbeat-label-fix-medium).

The change is purely additive: a new optional kwarg on `_invoke_with_role`, defaulting to `None`. No existing call site needs updating except `run_specialist`.

**Regression risk**: Diagnostic-only. No orchestration semantics change. Operators reading logs will see clearer labels.

**Coordination**: Independent of R1, R2, R3. Can be parallel-developed in its own Conductor workspace. Naturally lands in Wave 3 alongside the other diagnostic-clarity fixes.
