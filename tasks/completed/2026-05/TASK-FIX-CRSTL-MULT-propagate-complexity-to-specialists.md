---
id: TASK-FIX-CRSTL-MULT
title: "Propagate complexity multiplier to orchestrator-invoked specialists + tighten heartbeat instrumentation"
status: completed
created: 2026-05-10T22:50:00Z
updated: 2026-05-10T23:45:00Z
completed: 2026-05-10T23:45:00Z
previous_state: in_review
state_transition_reason: "All quality gates passed: 13 new tests pass, no regressions, no new ruff failures"
priority: high
task_type: feature
parent_review: TASK-REV-CRSTL
implementation_mode: task-work
complexity: 5
tags: [autobuild, orchestrator, specialist-invocations, code-reviewer, sdk-timeout, observability, OSI-followup]
related_tasks:
  - TASK-OSI-005  # The runner this task fixes (in completed/2026-04/)
  - TASK-OSI-004  # Sister runner (test-orchestrator) — same asymmetry
  - TASK-ABSR-WALL  # Where _cap_specialist_timeout's wall-clock cap was introduced
upstream_evidence:
  - "appmilla_github/specialist-agent: .claude/reviews/TASK-REV-CRSTL-review-report.md"
  - "appmilla_github/specialist-agent: .claude/reviews/TASK-REV-RAG8-review-report.md"
  - "appmilla_github/specialist-agent: docs/history/autobuild-FEAT-RAG-08-fail-run-1.md"
load_bearing_files:
  - guardkit/orchestrator/autobuild.py
  - guardkit/orchestrator/specialist_invocations.py
  - guardkit/orchestrator/agent_invoker.py
  - tests/orchestrator/test_specialist_invocations.py
  - tests/orchestrator/test_autobuild.py
---

# Task: Propagate complexity multiplier to orchestrator-invoked specialists + tighten heartbeat instrumentation

## Description

`AutoBuildOrchestrator._cap_specialist_timeout`
([autobuild.py:2447-2471](../../guardkit/orchestrator/autobuild.py#L2447-L2471))
returns `min(self.sdk_timeout or 1200, remaining_budget - grace)` —
flat base, no `mode_multiplier`, no `complexity_multiplier`. The
Player-side `_calculate_sdk_timeout`
([agent_invoker.py:4072-4157](../../guardkit/orchestrator/agent_invoker.py#L4072-L4157))
applies `1.5x` (task-work) and `1.0 + complexity/10` (1.1x–2.0x). The
docstring on `_cap_specialist_timeout` claims it "mirrors" the
Player-side cap; it mirrors only the wall-clock clamp, not the
scaling.

In a production FEAT-RAG-08 run, TASK-AIV2-003 (complexity 7,
task-work) put the Player on a `2999s` envelope (which finished in
`152.7s` / 16 SDK turns) and the orchestrator-invoked code-reviewer
specialist on a `1200s` envelope (`SDKTimeoutError: exceeded 1200s` →
SIGTERM). Same task, same worktree, ~20× headroom for the Player vs
no headroom for the specialist. See evidence in the parent reviews.

Additionally, when the specialist *is* slow, the 30s supervising
heartbeat carries zero signal beyond wall-clock elapsed time. The
visible `[{task_id}] ToolUseBlock {block.name} input keys: ...` log
lines that appear for the Player come from the task-work delegation
path
([agent_invoker.py:5260-5293](../../guardkit/orchestrator/agent_invoker.py#L5260-L5293)),
not from `_invoke_with_role` which the specialist uses. Result:
operators and post-mortem diagnosticians cannot tell whether a slow
specialist is LLM-bound, tool-bound, or hung.

This task lands two surgical fixes:

1. **R1** — make `_cap_specialist_timeout` delegate to
   `_calculate_sdk_timeout` for the scaled base, preserving the
   wall-clock cap.
2. **R2** — surface per-turn / per-tool signal in the supervising
   heartbeat for specialist invocations, so the next stall is
   diagnosable.

## Acceptance Criteria

### R1 — Timeout multiplier propagation

- [x] `AutoBuildOrchestrator._cap_specialist_timeout` accepts a
      `task_id: str` parameter (required) and delegates the base
      calculation to
      `self._agent_invoker._calculate_sdk_timeout(task_id, remaining_budget=remaining_budget)`.
- [x] The wall-clock cap (`min(..., remaining_budget - COACH_GRACE_PERIOD_SECONDS)`)
      remains as the second clamp.
- [x] The `GUARDKIT_SPECIALIST_TIMEOUT_CAP=disable` short-circuit
      still works; when disabled it returns the scaled value
      *without* the wall clamp (the existing semantic — disable
      means "no wall cap", not "no scaling").
- [x] Both call sites in `autobuild.py` (Phase 4 at
      [autobuild.py:2952-2958](../../guardkit/orchestrator/autobuild.py#L2952-L2958)
      and Phase 5 at
      [autobuild.py:2982-2988](../../guardkit/orchestrator/autobuild.py#L2982-L2988))
      pass the in-scope `task_id`.
- [x] Unit test in `tests/orchestrator/test_autobuild.py` (or a new
      `test_cap_specialist_timeout.py`) asserts:
      - Given `remaining_budget=2787.0`, `task_id="TASK-X"`, and a
        mocked `_calculate_sdk_timeout` returning `2999`, the
        function returns `min(2999, 2787 − COACH_GRACE_PERIOD_SECONDS)`.
      - `_calculate_sdk_timeout` is called with exactly
        `(task_id="TASK-X", remaining_budget=2787.0)`.
      - With `GUARDKIT_SPECIALIST_TIMEOUT_CAP=disable`, the function
        returns the scaled value (no wall clamp), and
        `_calculate_sdk_timeout` is called with `remaining_budget=None`.
      - With `remaining_budget=None`, the function returns the
        scaled value (no wall clamp).
- [x] Existing tests in `tests/orchestrator/test_specialist_invocations.py`
      and `tests/orchestrator/test_autobuild.py` still pass with no
      regressions.

### R2 — Heartbeat instrumentation

- [x] `_invoke_with_role`'s SDK message loop emits an operator-visible
      log line for each `ToolUseBlock` it observes during a
      specialist invocation, of shape:
      `[{task_id}] {heartbeat_label} ToolUseBlock {block.name} input keys: {sorted_keys}`
      (mirroring the format already used at
      [agent_invoker.py:5279-5281](../../guardkit/orchestrator/agent_invoker.py#L5279-L5281)
      for the task-work delegation path).
- [x] When `heartbeat_label_override` is set (i.e. the specialist
      path via `run_specialist`), the log is unconditionally emitted
      at `INFO` level. When `heartbeat_label_override` is `None`
      (Player/Coach paths via `_invoke_with_role`), the log is gated
      behind a debug flag or remains as-is — do not double-log on
      the Player path, since the task-work delegation path already
      emits it.
- [ ] Optionally (should-have, not must-have): `async_heartbeat`
      accepts an optional `tracker` callable or object that the SDK
      loop increments per `AssistantMessage`. The heartbeat line
      becomes:
      `[{task_id}] {phase} in progress... ({elapsed}s elapsed, {turn_count} turns, last_tool={name})`
      when a tracker is wired. Backwards-compatible: default tracker
      is None and the heartbeat line keeps its current shape.
      **Deferred** — should-have, not must-have. The per-ToolUseBlock
      log line satisfies the immediate diagnosability requirement; the
      heartbeat-tracker enrichment is left for a follow-up after R2's
      log-line shape sees production use.
- [x] Unit test in `tests/orchestrator/test_agent_invoker.py` (or a
      new `test_specialist_observability.py`) asserts that a
      simulated specialist invocation issuing a single `Read` tool
      call produces a `caplog` entry matching
      `r"specialist:code-reviewer.*ToolUseBlock Read input keys"`.

### Non-regression / shape

- [x] `ruff check guardkit/ tests/` passes clean **on the changed lines**.
      Pre-existing repo-wide lint errors (40 in `guardkit/`, 5 in
      `tests/unit/test_autobuild_timeout_budget.py`) were verified to
      be present on `main` *before* this change — they are not
      regressions from this task. The error count is identical
      pre/post-change.
- [x] No public-API breakage: `run_specialist`, `invoke_test_orchestrator`,
      and `invoke_code_reviewer` keep their current signatures.
      `_cap_specialist_timeout` is a private method; adding the
      `task_id` parameter is allowed.
- [x] Behaviour preserved for the existing emergency escape hatch:
      `GUARDKIT_SPECIALIST_TIMEOUT_CAP=disable` continues to bypass
      the wall clamp (now it bypasses *the wall clamp*, not the
      scaling — the scaling is the new contract).
- [x] The doctring on `_cap_specialist_timeout` is updated to
      describe the *full* mirror (both halves) instead of claiming a
      full mirror while only implementing the wall clamp.

## Implementation Sketch

### R1 patch (autobuild.py)

```python
def _cap_specialist_timeout(
    self,
    remaining_budget: Optional[float],
    task_id: str,
) -> int:
    """Cap orchestrator-invoked specialist sdk_timeout via the Player-side scaler.

    Delegates the base computation to
    ``AgentInvoker._calculate_sdk_timeout`` so the specialist receives
    the same mode/complexity multipliers the Player gets for the same
    task. Then applies the wall-clock clamp on top so a single
    specialist (Phase 4 or Phase 5) cannot consume the entire
    remaining wall budget.

    Set ``GUARDKIT_SPECIALIST_TIMEOUT_CAP=disable`` to short-circuit
    the wall clamp (the scaling still applies — disable means "no
    wall cap", not "no scaling").
    """
    if os.environ.get("GUARDKIT_SPECIALIST_TIMEOUT_CAP") == "disable":
        return self._agent_invoker._calculate_sdk_timeout(
            task_id, remaining_budget=None,
        )

    scaled = self._agent_invoker._calculate_sdk_timeout(
        task_id, remaining_budget=remaining_budget,
    )
    if remaining_budget is None:
        return scaled
    reserved = remaining_budget - COACH_GRACE_PERIOD_SECONDS
    cap = max(60, int(reserved))
    return min(scaled, cap)
```

Caller updates:

```python
# Phase 4 call site (autobuild.py:2952-2958)
sdk_timeout=self._cap_specialist_timeout(
    remaining_budget=remaining_budget,
    task_id=task_id,
),

# Phase 5 call site (autobuild.py:2982-2988)
sdk_timeout=self._cap_specialist_timeout(
    remaining_budget=phase5_remaining,
    task_id=task_id,
),
```

### R2 patch (agent_invoker.py)

Inside `_invoke_with_role`'s message loop (after line 2509's
`_track_tool_use(message)` call), add a visible log emit when the
heartbeat label was overridden (i.e. the specialist path):

```python
if heartbeat_label_override is not None:
    for block in getattr(message, "content", []) or []:
        if type(block).__name__ == "ToolUseBlock":
            tool_input = getattr(block, "input", {}) or {}
            keys = sorted(tool_input.keys()) if isinstance(tool_input, dict) else []
            logger.info(
                f"[{task_id}] {heartbeat_label_override} "
                f"ToolUseBlock {getattr(block, 'name', '?')} input keys: {keys}"
            )
```

(Final placement is at implementer's discretion — either lifted into
`_track_tool_use` itself with a `should_log_emit` flag, or inlined
into the message loop next to it. The contract is that the log line
appears.)

## Risk / Blast Radius

- **R1** touches a private method on a single class with two
  call sites. The delegated `_calculate_sdk_timeout` is well-tested
  and already used by every Player invocation. Risk: low. Main
  failure mode would be a test that hard-codes the 1200s assumption
  — grep the test suite for `1200` to surface those.
- **R2a** adds a new INFO log line on the specialist path. Risk:
  log-volume only. Specialist invocations are rare (1-2 per task per
  turn), and each typically issues <20 tool calls, so the volume is
  bounded.
- **R2b (heartbeat tracker)** changes the `async_heartbeat`
  signature. Backwards-compatible default keeps it safe, but every
  existing caller should be audited to make sure none rely on the
  current log-line shape via parsing.

## What "Done" Looks Like

A re-run of FEAT-RAG-08 (post-R1) on TASK-AIV2-003 shows:

```
[TASK-AIV2-003] SDK timeout: 2757s (base=1200s, mode=task-work x1.5,
  complexity=7 x1.7, budget_cap=2757s)
```

…appearing in the specialist invocation startup log (or equivalent),
and the reviewer either completes within that envelope OR continues
to fail — *but the failure is no longer attributable to a 1200s
floor that the Player would not have hit*.

A re-run also shows (post-R2):

```
[TASK-AIV2-003] specialist:code-reviewer invocation in progress... (300s elapsed)
[TASK-AIV2-003] specialist:code-reviewer ToolUseBlock Read input keys: ['file_path']
[TASK-AIV2-003] specialist:code-reviewer ToolUseBlock Grep input keys: ['pattern', 'path']
[TASK-AIV2-003] specialist:code-reviewer invocation in progress... (330s elapsed)
```

…so any *residual* slowness can be diagnosed from the log alone.

## Out of Scope

- **Bounding the reviewer's runtime working-set** (R3.a from the
  parent review). The reviewer's `Read`/`Grep` accumulation may
  still grow unboundedly even after R1+R2. That's a separate task
  that should be opened *after* R2's instrumentation lands, when
  there's data on what the typical working-set size actually is.
- **Parsing reviewer response messages into `specialist_results.json`**
  (F4 from the parent review). Currently
  `_PHASE_5_AGENT_FIELD_DEFAULTS` flat-defaults `issues`,
  `recommendations`, and `quality_score`. Connecting the SDK
  message stream into those fields is orthogonal to the stall
  problem.
- **Auditing other specialists (test-orchestrator)** for the same
  asymmetry. test-orchestrator finished in <90s in the FEAT-RAG-08
  run so the asymmetry didn't bite, but the *same* fix in R1
  applies to its `_cap_specialist_timeout` call site and lands for
  free.

## Implementation Summary

Both fixes landed surgically with no public-API breakage.

**R1 — Timeout multiplier propagation** (`guardkit/orchestrator/autobuild.py:2447-2480`):
`_cap_specialist_timeout` now requires `task_id: str` and delegates the
base computation to `AgentInvoker._calculate_sdk_timeout(task_id, remaining_budget=...)`,
then applies the orchestrator's Coach-grace wall clamp on top. The
`GUARDKIT_SPECIALIST_TIMEOUT_CAP=disable` escape hatch still bypasses
the wall clamp but now also preserves scaling (calls the scaler with
`remaining_budget=None`). Both call sites — Phase 4 test-orchestrator
(`autobuild.py:2964`) and Phase 5 code-reviewer (`autobuild.py:2995`)
— pass `task_id=task_id`. Docstring rewritten to describe the full
mirror.

**R2 — Specialist heartbeat instrumentation** (`guardkit/orchestrator/agent_invoker.py:2510-2535`):
`_invoke_with_role`'s SDK message loop now emits
`[{task_id}] {label} ToolUseBlock {name} input keys: {sorted_keys}` at
INFO level for every ToolUseBlock observed during a specialist
invocation. Gated on `heartbeat_label_override is not None` so
Player/Coach paths stay silent (the task-work delegation path already
logs Write/Edit ToolUseBlock lines at `agent_invoker.py:5279-5281`).

**Tests** — 13 new tests, all passing:
- `tests/unit/test_autobuild_timeout_budget.py::TestCapSpecialistTimeout`
  — 7 tests (replaces old base-only assertions; covers scaled+clamped
  path, disable env, None budget, the FEAT-RAG-08 / TASK-AIV2-003
  reproducer scenario, task_id-required TypeError).
- `tests/orchestrator/test_specialist_observability.py` — 5 tests
  (specialist emits, multi-tool, non-dict input, Player path silent,
  text-only message silent).

`TestSpecialistBudgetRefresh::_wrap_cap` signature updated to thread
`task_id` through to the wrapped call. All 25 agent-invoker
session/SDK-error regression tests pass. Repo-wide ruff baseline
unchanged (40+5 pre-existing errors verified to exist on `main`
before this change).

## Lessons

- **`_calculate_sdk_timeout` already applies a budget cap** when
  `remaining_budget` is non-None (`agent_invoker.py:4146-4147`). When
  the orchestrator delegates to it with the same `remaining_budget`,
  the Player-style budget cap fires before the orchestrator's tighter
  Coach-grace wall clamp. The two clamps compose correctly (the tighter
  reserve wins) but it's important to understand both layers exist
  rather than treating the orchestrator clamp as the only wall guard.
- **Disable semantics are a real contract, not just a backout**.
  Existing prose ("`GUARDKIT_SPECIALIST_TIMEOUT_CAP=disable` → return
  base regardless") was load-bearing for the *wall cap* but ambiguous
  about scaling. Tightening it to "disable = no wall cap, scaling
  still applies" preserves the emergency-backout intent while ensuring
  the disable path doesn't silently reintroduce the asymmetry that R1
  fixed.
- **Test-helper signature changes ripple**. `TestSpecialistBudgetRefresh::_wrap_cap`
  used a tight positional-kwarg shape (`def capture_cap(remaining_budget=None):`)
  that broke when the wrapped function gained a required kwarg.
  Wrappers that simulate a function should default to permissive
  signatures (e.g. `def capture_cap(*args, **kwargs):`) when the
  goal is observation rather than enforcement.

## References

- **Parent review (this repo's view of the bug)**:
  `appmilla_github/specialist-agent/.claude/reviews/TASK-REV-CRSTL-review-report.md`
- **Grand-parent review (broader FEAT-RAG-08 analysis)**:
  `appmilla_github/specialist-agent/.claude/reviews/TASK-REV-RAG8-review-report.md`
- **Reproducer transcript**:
  `appmilla_github/specialist-agent/docs/history/autobuild-FEAT-RAG-08-fail-run-1.md`
  (see lines 108, ~595 for the asymmetric timeouts)
- **Sibling task that created the runner being fixed**:
  `tasks/completed/2026-04/TASK-OSI-005-code-reviewer-runner.md`
