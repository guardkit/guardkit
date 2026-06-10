---
id: TASK-FIX-MAXPARALLEL01
title: Enforce --max-parallel in wave execution — strategy computes it, dispatcher ignores it
status: backlog
task_type: fix
created: 2026-06-10T00:00:00Z
updated: 2026-06-10T00:00:00Z
priority: high
complexity: 3
parent_task: TASK-HMIG-010
related: [TASK-FIX-FRESHRESET01, TASK-PERF-COACHSYNTH, TASK-ARCH-COACHBFULL]
implementation_mode: task-work
tags: [autobuild, orchestrator, state-management, parallelism]
---

# Task: Enforce --max-parallel in wave execution

## Why this task exists

`--max-parallel 1` is **silently ignored**. Run-22 was launched with
`--max-parallel 1` specifically to avoid the run-21 parallel-substrate
pressure, but Wave 2 ran both tasks in parallel anyway
([run-22-attempt-2.md:286](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-22-attempt-2.md#L286)):

```
Wave 2/2: TASK-FIX-GD02, TASK-FIX-TP05 (parallel: 2)
```

The next two log lines expose a **decision-vs-execution disconnect**
([293-294](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-22-attempt-2.md#L293-L294)):

```
parallel_strategy:Wave 2: max_parallel=1 (static)
feature_orchestrator:Starting parallel gather for wave 2:
  tasks=['TASK-FIX-GD02', 'TASK-FIX-TP05'] ...
```

`parallel_strategy` computes `max_parallel=1` **correctly**, but
`feature_orchestrator`'s wave dispatch **ignores that decision** and launches
all wave tasks via unbounded `asyncio.gather`. The strategy is computed and
then never enforced.

This blocks clean experimentation: you cannot currently run B-full **serially**
to isolate per-task substrate behaviour (the run-22 / TASK-PERF-COACHSYNTH
validation needs serial execution).

## The defect (precise surface)

| Element | Location | State |
|---|---|---|
| `max_parallel` decision | `guardkit/orchestrator/parallel_strategy.py` (computes `max_parallel=N`) | correct — logged "max_parallel=1 (static)" |
| Wave dispatch | `guardkit/orchestrator/feature_orchestrator.py` — the "Starting parallel gather for wave N" path (`asyncio.gather` over all wave tasks) | **does not consume `max_parallel`** |

(Confirm exact function names when implementing — grep
`feature_orchestrator.py` for `parallel gather`, `asyncio.gather`,
`max_parallel`, and the `parallel_strategy` consumer.)

## The fix

Make the wave dispatcher **consume** the `parallel_strategy` decision and
enforce it — either an `asyncio.Semaphore(max_parallel)` wrapping the per-task
coroutines, or sequential `await` when `max_parallel == 1`. The strategy module
already produces the number; the dispatcher must apply it.

## Acceptance criteria

- [ ] **AC-1**: `--max-parallel 1` runs each wave's tasks **sequentially** — the
  log shows `(parallel: 1)` and the tasks' Player/Coach turns do not overlap.
- [ ] **AC-2**: `--max-parallel N` (N≥2) limits in-flight tasks per wave to N
  (a wave of >N tasks runs at most N concurrently).
- [ ] **AC-3**: default behaviour (flag unset / strategy default) is unchanged —
  no regression to the current concurrency for runs that don't set the flag.
- [ ] **AC-4**: a regression/unit test drives a 3-task wave with `max_parallel=1`
  and asserts at most one task coroutine is in-flight at a time (e.g. via a
  concurrency counter / semaphore probe), and a second test asserts N=2 caps at 2.
- [ ] **AC-5**: existing feature-orchestrator + wave tests stay green.

## Notes

- Part of the orchestrator-state-management cleanup cluster:
  TASK-FIX-FRESHRESET01 (`--fresh` no-op on completed feature),
  WTCLEANUP01 (worktree cleanup), FEATYAMLPATH01 — all "the flag/decision is
  computed but the executor does something else."
- Surfaced reviewing the run-22 snapshot (`docs/state/TASK-REV-HMIG/run-22-artifacts/README.md`,
  Finding 1).
- Pairs with TASK-PERF-COACHSYNTH: COACHSYNTH fixes the gather F20 overflow;
  MAXPARALLEL01 lets you run serial to validate it cleanly without parallel
  substrate contention as a confound.
