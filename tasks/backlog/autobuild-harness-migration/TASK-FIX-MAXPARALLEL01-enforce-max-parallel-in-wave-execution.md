---
id: TASK-FIX-MAXPARALLEL01
title: Enforce --max-parallel in wave execution — strategy computes it, dispatcher ignores it
status: in_review
task_type: fix
created: 2026-06-10T00:00:00Z
updated: 2026-06-10T12:00:00Z
previous_state: in_progress
state_transition_reason: "task-work complete: all quality gates passed (corrected root cause — see Resolution)"
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

- [x] **AC-1**: `--max-parallel 1` runs each wave's tasks **sequentially** — the
  log shows `(parallel: 1)` and the tasks' Player/Coach turns do not overlap.
  *Sequential execution was already enforced by the semaphore (see Resolution);
  the display now shows `(parallel: 1)` —
  `test_start_wave_max_parallel_1_shows_serial` + `test_max_parallel_1_serialises_three_task_wave`.*
- [x] **AC-2**: `--max-parallel N` (N≥2) limits in-flight tasks per wave to N
  (a wave of >N tasks runs at most N concurrently). *`test_max_parallel_2_caps_three_task_wave_at_two`
  (peak==2) + `test_start_wave_max_parallel_2_caps_display`.*
- [x] **AC-3**: default behaviour (flag unset / strategy default) is unchanged —
  no regression to the current concurrency for runs that don't set the flag.
  *`test_max_parallel_none_is_unlimited` (peak==3) + `test_start_wave_unlimited_shows_wave_size`.*
- [x] **AC-4**: a regression/unit test drives a 3-task wave with `max_parallel=1`
  and asserts at most one task coroutine is in-flight at a time (e.g. via a
  concurrency counter / semaphore probe), and a second test asserts N=2 caps at 2.
  *`tests/unit/test_max_parallel.py::TestBoundConcurrencyWaveDispatch` drives the
  production `bound_concurrency` helper with a concurrency probe.*
- [x] **AC-5**: existing feature-orchestrator + wave tests stay green. *267 unit +
  11 integration parallel-wave tests pass; the one pre-existing failure
  (`test_inter_wave_bootstrap::test_greenfield_scenario_wave1_creates_manifest`,
  an unrelated `uv venv`/`pip install` mock assertion) fails identically on the
  clean tree.*

## Resolution (2026-06-10) — corrected root cause

**The task's premise was wrong.** The dispatcher does **not** ignore
`max_parallel`, and the gather is **not** unbounded. The
`asyncio.Semaphore(max_parallel)` enforcement has been in
`_execute_wave_parallel` since 2026-02-27 (commit `524d8aaa`) with the
`resolve_max_parallel` consumer since 2026-03-09 (`108420b0`) — **both predate
run-22**. The run-22 log proves execution was already serial:
`Orchestration complete: TASK-FIX-GD02` (line 621) lands **before**
`Starting orchestration for TASK-FIX-TP05` (line 627), with zero TP05 activity
in between. `--max-parallel 1` *was* honoured at the execution level.

**The real defect was display-only.** `WaveProgressDisplay.start_wave`
computed the `(parallel: N)` indicator as `len(task_ids)` — the wave *size* —
not the effective concurrency. So a 2-task wave under `--max-parallel 1`
printed `(parallel: 2)`, which the reviewer correctly read as "ran in parallel"
even though the executor serialised the tasks. This is another instance of the
project's *low-fidelity-oracle* meta-frame (cf.
`.claude/rules/absence-of-failure-is-not-success.md`): a banner that cannot
distinguish wave-size from concurrency.

**Fix delivered:**
1. `WaveProgressDisplay.start_wave(..., max_parallel=None)` now shows
   `min(max_parallel, wave_size)` (and includes it in the INFO log for grep).
2. `_wave_phase` resolves the effective `max_parallel` once (read-only,
   `log=False`) and passes it to the banner, so display and executor consume
   the *same* `resolve_max_parallel` decision and can never diverge in STATIC
   mode.
3. The inline semaphore loop was extracted verbatim to
   `parallel_strategy.bound_concurrency()` — behaviour-preserving — so the
   concurrency bound is unit-testable in isolation (AC-4) instead of only via
   full autobuild runs.
4. Added `log=False` to `resolve_max_parallel` so the display's read-only
   resolution doesn't double-log the authoritative dispatcher decision.

**Files:** `guardkit/cli/display.py`,
`guardkit/orchestrator/feature_orchestrator.py`,
`guardkit/orchestrator/parallel_strategy.py` (+3 test files).

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
