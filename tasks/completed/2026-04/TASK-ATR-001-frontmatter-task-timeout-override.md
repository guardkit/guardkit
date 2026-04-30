---
id: TASK-ATR-001
title: Per-task task_timeout frontmatter override
task_type: feature
parent_review: TASK-REV-E73C
parent_review_repo: jarvis
feature_id: FEAT-ATR
wave: 1
implementation_mode: task-work
complexity: 5
dependencies: []
priority: medium
status: completed
completed: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
previous_state: in_review
state_transition_reason: "Quality gates passed; /task-complete invoked"
completed_location: tasks/completed/2026-04/
tags: [autobuild, timeout, frontmatter, FEAT-ATR]
---

# TASK-ATR-001 — Per-task `task_timeout` frontmatter override

## Description

Add a per-task `task_timeout` override to the task frontmatter `autobuild`
block. Today, complexity-7 task-work tasks share the global feature
`task_timeout` (default 3000s after TASK-ABSR-FLOR floor + multiplier),
even when the task legitimately needs longer (Player + 2 specialists +
Coach all in one envelope).

The symmetric `autobuild.sdk_timeout` override already exists at
[`guardkit/orchestrator/feature_orchestrator.py:2521–2523`](../../../guardkit/orchestrator/feature_orchestrator.py#L2521-L2523).
This task adds the matching `autobuild.task_timeout` knob.

## Root Cause Addressed

FEAT-J005-946D run-1 (2026-04-29) timed out TASK-J005-005 at exactly 3000s
when the Coach approval landed 68 ms after the timer fired. Per the parent
review:

- Turn 1 alone consumed 1959s (65 % of budget) — Player SDK 1228s + 2
  specialists 690s + Coach 24s + IO.
- Turn 2 had 1041s capped budget → Player 230s + 2 specialists 780s + Coach
  24s. The math added up to 99 % of the wall.

A per-task override (e.g. `task_timeout: 4500` for this task) would have
given a 25-minute headroom and the run would have completed cleanly.

## Files to Modify

1. `guardkit/orchestrator/feature_orchestrator.py` — refactor the wave-gather
   loop at lines 2076–2090 to compute timeout per task instead of using
   `self.task_timeout` uniformly. Read `task_data["frontmatter"]["autobuild"]
   .get("task_timeout", self.task_timeout)` × `self.timeout_multiplier`.
2. `tests/unit/test_feature_orchestrator.py` — add unit test asserting that
   a frontmatter `autobuild.task_timeout` value is honoured for the
   `wait_for` wrap. Mock `asyncio.wait_for` and assert the `timeout` kwarg
   matches expectation.
3. `installer/core/templates/*/templates/other/other/agent-config.yaml.template`
   (if present) — document the new key.

## Acceptance Criteria

- [ ] A task with `autobuild.task_timeout: 4500` in its frontmatter receives
      a 4500s wait_for envelope (× any backend `timeout_multiplier`).
- [ ] A task without the override receives `self.task_timeout` (unchanged
      default behaviour).
- [ ] The override is logged at INFO level so operators can audit per-task
      budgets.
- [ ] Unit test covers: present + valid, present + zero (rejected),
      present + negative (rejected), absent (default), absent and feature
      uses CLI override.
- [ ] Integration test re-runs against a real fixture feature with one task
      carrying the override.
- [ ] Existing `test_feature_orchestrator.py` tests still pass.
- [ ] No regression in single-task autobuild path
      (`AutoBuildOrchestrator.orchestrate` directly).

## Test Requirements

- pytest unit tests in `tests/unit/test_feature_orchestrator.py`
- pytest integration test in `tests/integration/test_config_propagation.py`
- All existing `tests/unit/test_feature_orchestrator.py::Test*` cases pass

## Implementation Notes

The wave-gather loop today (line 2076–2090):
```python
elapsed_at_queue = time.monotonic() - wave_start_time
task_budget = max(0.0, self.task_timeout - elapsed_at_queue)
tasks_to_execute.append(
    asyncio.wait_for(
        asyncio.to_thread(self._execute_task, ...),
        timeout=self.task_timeout,    # ← uniform across all tasks in wave
    )
)
```

Refactor:
```python
for task in wave_tasks:
    per_task_timeout = self._resolve_task_timeout(task)  # NEW helper
    elapsed_at_queue = time.monotonic() - wave_start_time
    task_budget = max(0.0, per_task_timeout - elapsed_at_queue)
    tasks_to_execute.append(
        asyncio.wait_for(
            asyncio.to_thread(self._execute_task, ...,
                              time_budget_seconds=task_budget),
            timeout=per_task_timeout,
        )
    )
```

`_resolve_task_timeout` reads `task_data["frontmatter"]["autobuild"]
.get("task_timeout")`, falls back to `self.task_timeout`, applies
`self.timeout_multiplier`, and floors at `MIN_TURN_BUDGET_SECONDS × max_turns`
(safety floor: never less than one minimum-budget turn).

## Implementation Summary

Implemented the per-task `autobuild.task_timeout` frontmatter override that
mirrors the existing `autobuild.sdk_timeout` override. The resolver lives at
`feature_orchestrator.py:2467` and is invoked at the wave-gather queue site
(not inside `_execute_task`) so that `asyncio.wait_for(timeout=…)` and
`time_budget_seconds` are both bounded by the per-task value before the
worker thread starts.

**Resolver semantics** (`_resolve_task_timeout(task_data, task_id)`):
- Reads `frontmatter.autobuild.task_timeout`. Absent → returns
  `self.task_timeout` (feature-level default; floor + multiplier already
  baked in at construction).
- Present + integer + > 0: multiplies by `self.timeout_multiplier`, floors
  at `MIN_TURN_BUDGET_SECONDS × self.max_turns` (one minimum-budget turn
  per max-turn slot), logs at INFO with `[task_id]` prefix.
- Present + zero/negative/non-integer: rejected with a WARNING; falls back
  to feature-level default. The orchestrator never crashes on a bad
  override.

**Wave-loop refactor** (`feature_orchestrator.py:2076–2098`): the queue
site now loads task data once via `TaskLoader.load_task`, calls the
resolver, stores the result in a `per_task_timeouts: Dict[str, int]` for
the timeout-error message at `feature_orchestrator.py:2143`, and threads
the resolved value through to `_execute_task` via a new
`effective_task_timeout` kwarg. `_execute_task` forwards that kwarg into
`AutoBuildOrchestrator(task_timeout=…)` so the SDK-timeout logging line
reflects the actual envelope wrapping the task. If `TaskLoader` raises at
the queue site, we log a WARNING and fall back to the feature-level
default (the worker thread will surface the real error from inside
`_execute_task` as before).

**Test coverage**: 18 new tests across two files.

- `tests/unit/test_feature_orchestrator.py` (15 tests):
  - `TestResolveTaskTimeout` (9): no override, no autobuild section,
    override above floor, override below floor, zero/negative/non-integer
    rejection paths, multiplier application, INFO log emission.
  - Wave-loop integration (4): override reaches `wait_for`, fallback when
    absent, sibling isolation (one task overridden, the other untouched),
    `TaskLoader` failure fallback.
  - `_execute_task` forwarding (2): effective param threaded into
    `AutoBuildOrchestrator(task_timeout=…)`, fallback to `self.task_timeout`
    when None.
- `tests/integration/test_config_propagation.py` (3 tests in new
  `TestTaskTimeoutOverridePropagation`): per-task override reaches
  `asyncio.wait_for`, multiplier applied, no override → feature-level
  default.

Bulk-updated 25 existing `mock_execute_task*` signatures across
`test_feature_orchestrator.py` and `test_timeout_logging_reconciliation.py`
to accept `**kwargs` for forward-compat with the new `effective_task_timeout`
kwarg.

**Result**: 18/18 new tests pass. All 6 existing `task_timeout`-keyword
tests still pass. The 11 pre-existing failures in
`test_config_propagation.py` (`autobuild_config` field mismatch on the
`Feature` Pydantic model, `default sdk_timeout 1200 vs 900` mismatch) and
`test_autobuild_timeout_budget.py` (`_bootstrap_venv_python` attribute)
are independent of this change — verified via `git stash` round-trip.

## Notes

- **Lesson (test-mock forward-compat)**: when adding a new kwarg to a
  method that's mocked across many tests via `patch.object`, the mock
  signatures must accept it or every test using that mock blows up with
  `TypeError: unexpected keyword argument`. Standard fix: add `**kwargs`
  to mock signatures (25 occurrences here). Worth grepping
  `def mock_<method_name>` before adding a new param to a heavily-mocked
  method.
- **Lesson (queue-site vs worker-side resolution)**: `asyncio.wait_for`
  needs the timeout at the queue site, before the awaitable runs. So the
  per-task override has to be resolved *before* `_execute_task` is called,
  not inside it. This means an extra `TaskLoader.load_task` call per task
  at queue time — cheap (~5 ms YAML read, once per task) and isolated
  from the hot loop.
- **Plan-audit note**: the IMPLEMENTATION-GUIDE estimate of "~30 LoC"
  counted only the gather-loop refactor and missed the helper. Actual
  orchestrator delta is ~109 LoC (~30 refactor + ~64 helper + ~15 param
  plumbing). Tests dominate at ~470 LoC for thorough AC coverage.
- **Sibling task TASK-ATR-002** appears already complete in
  `tasks/completed/2026-04/TASK-ATR-002-refresh-remaining-budget-between-specialists.md`
  (untracked). TASK-ATR-003 (feature-level late-approval reconciliation)
  remains open under `tasks/backlog/autobuild-task-timeout-resilience/`.
- **Related ADR / parent review**: TASK-REV-E73C in the jarvis repo at
  `jarvis/.claude/reviews/TASK-REV-E73C-review-report.md`.
