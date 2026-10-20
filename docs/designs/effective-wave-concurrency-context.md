# Effective wave concurrency for test isolation

## Problem

A feature wave has two different sizes:

- nominal membership: the task identifiers declared in the wave; and
- effective concurrency: the maximum number of runnable tasks that can overlap
  after completed, deferred, and dependency-blocked tasks are removed and the
  per-wave concurrency policy is resolved.

The feature orchestrator currently computes the second fact only as
`shares_working_copy`. It still passes nominal membership as `wave_size`.
A two-task group serialized by an explicit cap or a same-area conflict
therefore sends `shares_working_copy=false` and `wave_size=2`.

The Coach selects an isolated filesystem copy for independent tests whenever
`wave_size > 1`. That copy intentionally omits version-control metadata.
Selecting it for a serialized task can make ordinary repository checks fail
even though the task has exclusive use of the real worktree.

`wave_size` also drives established policies beyond snapshot selection:
contention classification, conditional parallel-failure handling, runtime
parity, non-Python test routing, and whole-feature repair checks. This bounded
repair must not silently redefine all of those policies.

## Decision

Carry one new, explicit scheduler fact:

```text
effective_concurrency =
    runnable_count                          when the resolved cap is unlimited
    min(runnable_count, resolved_cap)       when the resolved cap is positive
```

A cap of zero retains its existing meaning of unlimited. An empty queue starts
no task and passes no concurrency context.

Use `effective_concurrency` only to decide whether non-SDK independent tests
need the parallel-wave isolated copy. Keep `wave_size` nominal and keep every
other current consumer unchanged.

The snapshot rule becomes:

```text
test_isolation_concurrency =
    effective_concurrency                   when explicitly supplied
    wave_size                               for legacy and direct callers

use_isolated_test_copy = test_isolation_concurrency > 1
```

The optional value must propagate to every `CoachValidator` that can call
`run_independent_tests`, including deterministic Phase 4 and both primary
and legacy Coach paths.

The conservative fallback is part of the contract. A direct caller that sends
`wave_size=2` but no scheduler fact must remain isolated. The existing
`shares_working_copy=false` default cannot disable isolation because false
means either “proved serialized” or “an older caller supplied no fact.”

## Scheduler boundary

`FeatureOrchestrator._execute_wave_parallel` is the only producer with all
required inputs:

1. It filters nominal `task_ids` into the calls that will actually run.
2. `resolve_max_parallel` applies the configured cap and the existing
   same-area serialization rule.
3. A small helper in `parallel_strategy` calculates effective concurrency
   from `len(queued_calls)` and the resolved cap.
4. `tasks_run_at_the_same_time` derives its answer from the same helper, so
   `shares_working_copy` and effective concurrency cannot drift.
5. The orchestrator injects both facts into each runnable task only after the
   cap is resolved.

For scheduler-originated task calls this invariant holds:

```text
shares_working_copy == (effective_concurrency > 1)
```

Nominal membership remains `len(task_ids)` and continues to populate
`wave_size`, display, queue depth, completion results, and lifecycle
reporting.

## Propagation and consumers

The new optional value follows the existing internal call chain:

1. `FeatureOrchestrator._execute_task` passes it to
   `AutoBuildOrchestrator`.
2. AutoBuild stores it beside nominal `wave_size`.
3. AutoBuild passes it to the deterministic Phase-4 invocation and the Coach
   invocation.
4. The deterministic Phase-4 helper, primary Coach path, and legacy Coach path
   pass it into `CoachValidator`.
5. `CoachValidator.run_independent_tests` uses the resolved isolation
   concurrency when selecting the isolated-copy or real-worktree subprocess
   path.

The following consumers retain nominal `wave_size` behavior:

- `CoachValidator.is_parallel`;
- contention and source-overlap classification;
- conditional parallel-failure treatment;
- runtime-parity deferral;
- non-Python whole-suite routing;
- whole-feature repair check deferral;
- prompts, records, and logs that describe nominal wave membership.

`shares_working_copy` also remains separate. It controls whether synthetic or
recovered Player reports may claim Git-derived file ownership and requirement
coverage. It is not used as an implicit test-isolation override.

## Compatibility and safety

- A one-task wave supplies nominal one and effective one, and tests run in the
  real worktree.
- A multi-task wave serialized by an explicit cap or declared path conflict
  retains nominal `wave_size > 1`, supplies effective one, and runs
  independent tests in the real worktree.
- A larger nominal group with only one runnable task behaves the same way.
- Two or more runnable tasks with an unlimited or greater-than-one cap supply
  effective concurrency greater than one and retain the current isolated test
  path.
- A direct or older caller that omits the new value falls back to nominal
  `wave_size`; its current isolation behavior is unchanged.
- A three-task group capped at two supplies effective two. Nominal reporting
  still says three.
- Test failures still fail. The execution root changes only when the scheduler
  explicitly proves that no peer task can overlap.

The repair does not copy, mount, or link version-control metadata into an
isolated directory. It does not retry a runnable failing suite in the shared
worktree, disable tests, suppress assertions, change the existing
cannot-start fallback, relax pass criteria, or edit a target repository.
Git-dependent checks inside a genuinely concurrent isolated copy remain an
honestly reported compatibility failure outside this bounded correction.

## Implementation scope

Production changes are limited to the internal context path:

- `guardkit/orchestrator/parallel_strategy.py`: calculate effective
  concurrency and reuse it in the existing overlap predicate;
- `guardkit/orchestrator/feature_orchestrator.py`: produce and pass the
  explicit value after filtering and policy resolution;
- `guardkit/orchestrator/autobuild.py`: store and forward the optional value;
- `guardkit/orchestrator/specialist_invocations.py`: carry it through
  deterministic Phase 4;
- `guardkit/orchestrator/quality_gates/coach_validator.py`: apply the
  conservative fallback and use the resolved value only for isolated-copy
  selection.

Focused tests belong in the existing parallel-strategy, feature-orchestrator,
same-area sequencing, specialist invocation, and Coach isolation suites. No
product, isolated-copy implementation, feature schema, CLI setting, or
test-command change is required.

## Acceptance controls

### Scheduler facts

- An explicit concurrency cap of one on a two-task group passes
  `wave_size=2`, `effective_concurrency=1`, and
  `shares_working_copy=false` to both runnable calls.
- A two-task declared-path conflict that resolves the cap to one passes the
  same triple through the real `_execute_wave_parallel` caller.
- A two-task group with one already completed, deferred, or
  dependency-blocked task passes nominal two, effective one, and false to the
  only runnable call.
- Two runnable tasks in disjoint areas with an unlimited or at-least-two cap
  pass nominal two, effective two, and true.
- Three runnable tasks capped at two pass nominal three, effective two, and
  true.
- The helper preserves zero-as-unlimited behavior and reports no overlap for
  fewer than two runnable tasks.
- Nominal task identifiers and existing display, queue, completion, and event
  values are unchanged.

### Real isolation decision

- The real FeatureOrchestrator-to-AutoBuild-to-Coach path gives a serialized
  task a nominally parallel validator whose isolation decision is false; the
  independent subprocess check runs in the real worktree.
- The deterministic Phase-4 path receives the same explicit fact and makes the
  same execution-root decision.
- The same production caller with genuine overlap selects the existing
  isolated-copy path.
- A clean check in that genuinely concurrent path remains a positive signal.
- A runnable failing check in that path remains a failure and is not retried in
  the shared worktree merely because it failed.
- A validator with `wave_size=2` and no explicit effective concurrency still
  isolates, proving conservative compatibility.
- A validator with `wave_size=1` and no explicit value still uses the real
  worktree.
- Existing nominal-parallel controls for contention classification,
  conditional approval, runtime parity, non-Python routing, and whole-feature
  repair remain unchanged.
- `shares_working_copy=false` without explicit effective concurrency does not
  alter isolation.

### Later test execution

After implementation, run focused controls on the Dell through `dell-test`,
without xdist and with candidate source first on `PYTHONPATH`:

```text
~/.local/bin/dell-test timeout 1800 env PYTHONPATH=<candidate>/src:<candidate> <venv>/bin/python -m pytest -q -p no:xdist -p no:cacheprovider -o addopts= tests/unit/test_feature_orchestrator.py tests/unit/test_wave_same_area_sequencing.py tests/integration/test_parallel_wave_isolation.py tests/orchestrator/test_direct_mode_timeouts.py tests/orchestrator/test_declared_toolchain_detection.py
```

Then run the repository's normal broader orchestrator suite through the same
wrapper. Preserve the exact candidate commit, command, result count, and raw
log. Compare any failure against the unchanged pinned base before changing
the design or weakening a control.

## Review

Implementation begins only after independent design acceptance. Implementation
review must verify the exact candidate, the conservative fallback, every
serialized and genuinely parallel control, and the absence of target
repository or isolated-copy changes.
