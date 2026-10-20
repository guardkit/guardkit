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

A missing, zero, or negative cap retains its existing meaning of unlimited.
This follows the current `parallel_strategy` contract; the repair adds no new
cap validation. An empty queue starts no task and passes no concurrency
context.

The scheduler fact remains valid only while the wave has not timed out. A
timed-out `asyncio.to_thread` worker can keep running after its semaphore slot
is released. Starting another queued task could therefore mutate the
worktree beneath the older task's already-running real-worktree check. After
the first task timeout, the dispatcher must start no remaining queued task in
that wave and no later task, gate, or repair dispatch in that feature
invocation.

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

`AutoBuildOrchestrator` and `CoachValidator` both accept positional
construction today. Their new optional input must therefore be keyword-only
where practical or appended at the end of the existing positional signature.
It must never shift an existing positional binding. Production propagation
uses the explicit keyword in either case. The same placement rule applies to
every changed callable signature in the propagation chain, including
`_execute_task` and `_invoke_coach_safely`.

The conservative fallback is part of the contract. A direct caller that sends
`wave_size=2` but no scheduler fact must remain isolated. The existing
`shares_working_copy=false` default cannot disable isolation because false
means either “scheduled one at a time” or “an older caller supplied no fact.”

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
5. A sticky per-feature-invocation timeout flag is initialized clear in
   `FeatureOrchestrator.__init__`. All reads use a clear-by-default accessor so
   bare objects and direct internal callers retain their current behavior.
   Only entry to a public `orchestrate` call resets the flag. A small async
   dispatch wrapper runs inside the actual `bound_concurrency` slot and checks
   the flag before it creates `to_thread` or calls `_execute_task`.
6. The wrapper otherwise awaits the existing
   `wait_for(to_thread(...), timeout)` unchanged. If that raises
   `TimeoutError`, the wrapper sets the flag and re-raises before the outer
   concurrency wrapper releases its semaphore slot.
7. A later wrapper that sees the flag returns an explicit unsuccessful
   `TaskExecutionResult` with `final_decision="error"`, zero turns, and an
   error stating that the task did not start because another task in its wave
   timed out. It does not start a Player, Coach, subprocess, or worker thread.
   Its existing `started_at` remains the queue timestamp; this repair does not
   redefine or clear persisted timestamp fields.
8. Every dispatch owner checks the same flag immediately after its wave
   return: `_wave_phase` for normal waves, the smoke and wiring retry helpers,
   and `_run_feature_check` for whole-feature repair. `_wave_phase` also
   checks before inter-wave bootstrap and before final boot/feature checks.
   No subsequent gate, repair, or task dispatch runs in that invocation.
9. Finalization forces the invocation to failed when the flag is set, even if
   late-approval reconciliation changed the timed-out task's own result to
   successful. Task records and counts remain intact. The next explicit public
   `orchestrate` call resets the flag, including when the same object is reused.

For scheduler-originated task calls this invariant holds:

```text
shares_working_copy == (effective_concurrency > 1)
```

This is resolved fresh context for tasks that actually start. The timeout
guard changes which queued tasks start; it does not recalculate
`shares_working_copy` or pass a weakened context. Existing timeout and
cancellation events, late-approval reconciliation, result ordering, and
semaphore limits remain unchanged. A late approval does not clear the flag or
start unstarted peers. The repair does not stop or join the older worker.

`_execute_wave` continues to own the async loop through `asyncio.run`. The
local Python runtime gives default-executor shutdown 300 seconds and can then
return without proving that a worker has stopped. The sticky invocation fence
therefore controls later dispatch and final success; it does not claim worker
quiescence. Resetting at a later public invocation is explicit new-run scope,
not evidence that an older thread was killed.

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

This selection applies only to the ordinary non-SDK subprocess branch. In the
existing SDK exception fallback, `use_sdk` remains true and the fallback
subprocess already skips snapshot creation. Preserve that behavior exactly:
do not reset `use_sdk`, route the fallback through the snapshot branch, or
claim that effective concurrency chooses every possible execution root.

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
Its existing timeout behavior is outside this snapshot repair.

## Compatibility and safety

- A one-task wave supplies nominal one and effective one, and tests run in the
  real worktree.
- A multi-task wave serialized by an explicit cap or declared path conflict
  retains nominal `wave_size > 1`, supplies effective one, and runs
  independent tests in the real worktree while earlier tasks complete within
  their time limits.
- After any task timeout, every queued task that has not started is returned
  as an explicit unsuccessful did-not-start result. The rule remains in force
  for the rest of that wave even if the older worker later exits or records a
  late approval.
- The sticky fence also prevents all later waves, post-wave gates, boot smoke,
  whole-feature checks, and gate-driven repair dispatch in that invocation.
  Finalization reports failure even when a sole or last timed-out task is
  reclassified as approved late.
- A later public `orchestrate` call resets the fence. Reusing an orchestrator
  object or starting a fresh resume is not permanently poisoned by an earlier
  invocation's timeout.
- A larger nominal group with only one runnable task behaves the same way.
- Two or more runnable tasks with an unlimited or greater-than-one cap supply
  effective concurrency greater than one and retain the current isolated test
  path.
- A direct or older caller that omits the new value falls back to nominal
  `wave_size`; its current isolation behavior is unchanged.
- A fresh normally constructed orchestrator and a bare object created without
  `__init__` both read the timeout fence as clear. Direct
  `_execute_wave_parallel` and `_finalize_phase` calls therefore retain their
  current behavior unless a public invocation or timeout has set the fence.
  Internal entry points do not reset an already-set fence.
- Existing positional construction of AutoBuild and CoachValidator retains
  every binding; the new value is optional and passed by keyword.
- A three-task group capped at two supplies effective two. Nominal reporting
  still says three.
- Test failures still fail. A real-worktree selection means the scheduler
  resolved the wave to one task at a time and no earlier task timed out; it is
  not a claim that Python can terminate worker threads.

The repair does not copy, mount, or link version-control metadata into an
isolated directory. It does not retry a runnable failing suite in the shared
worktree, disable tests, suppress assertions, change the existing
cannot-start fallback, relax pass criteria, or edit a target repository.
Git-dependent checks inside a genuinely concurrent isolated copy remain an
honestly reported compatibility failure outside this bounded correction.

Stopping later dispatch after a timeout is an explicit bounded scheduler
policy change required to make the real-worktree path safe. It does not change
the timeout duration, cancellation checkpoints, late-approval task record,
thread join policy, or treatment of calls already running when the timeout
fires.

## Implementation scope

Production changes are limited to the internal context path:

- `guardkit/orchestrator/parallel_strategy.py`: calculate effective
  concurrency and reuse it in the existing overlap predicate;
- `guardkit/orchestrator/feature_orchestrator.py`: produce and pass the
  explicit value after filtering and policy resolution; set, enforce, and
  reset the invocation timeout fence; return explicit errors for unstarted
  peers; skip later dispatch; and force failed finalization;
- `guardkit/orchestrator/autobuild.py`: store and forward the optional value;
- `guardkit/orchestrator/specialist_invocations.py`: carry it through
  deterministic Phase 4;
- `guardkit/orchestrator/quality_gates/coach_validator.py`: apply the
  conservative fallback and use the resolved value only for isolated-copy
  selection.

New focused controls belong in the existing parallel-strategy,
feature-orchestrator, timeout, gate, specialist invocation, and Coach
isolation suites. Mandatory validation runs every non-quarantined test under
`tests/unit`, `tests/integration`, `tests/orchestrator`, and `tests/seam` and
records the quarantine skips; this avoids relying on a hand-maintained list
while the fence touches dispatch, timeout, gate, and finalization paths. No product, isolated-copy
implementation, feature schema, CLI setting, or product test-command change is
required.

## Acceptance controls

### Scheduler facts

- An explicit concurrency cap of one on a two-task group passes
  `wave_size=2`, `effective_concurrency=1`, and
  `shares_working_copy=false` to both runnable calls when neither times out.
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
  fewer than two runnable tasks. Missing and negative caps also retain their
  current unlimited meaning. Controls cover an empty queue, one runnable
  task, caps of one and two, and a cap greater than the runnable count.
- Nominal task identifiers and existing display, queue, completion, and event
  values are unchanged.
- A controlled cap-one regression uses the real `bound_concurrency` and
  `wait_for(to_thread(...))` path. Its first worker reaches a controlled
  real-worktree independent-test boundary, blocks on a test-owned event, and
  remains alive when the timeout fires. The guard is set before the slot
  releases, the second queued task never calls `_execute_task`, and its result
  is unsuccessful `error` with zero turns and a plain did-not-start reason.
  The test releases the worker in `finally` and makes a bounded assertion that
  the worker finished, so the test cannot leak a thread.
- With a cap of two and three queued tasks, a sibling already running when the
  timeout fires may finish normally; the third task does not start. The guard
  does not retroactively cancel work that already held a slot.
- A timed-out task keeps its existing timeout result and late-approval record
  policy. A late approval does not clear the guard or launch an unstarted peer.
- Did-not-start peers are never `deferred` or successful. The standard false
  result path persists them as failed and leaves them eligible for a later
  resume. Their `started_at` field remains the existing queue time; status,
  `final_decision="error"`, zero turns, and the explicit error reason truthfully
  record that execution did not start.
- Existing timeout-event and cancellation-event timing is unchanged.
- The sticky fence stops the next wave even with `stop_on_failure=false` and
  prevents post-wave smoke, wiring, final boot-smoke, whole-feature check, and
  all three gate-repair re-entry paths from dispatching after a timeout.
- A timeout on the last or only runnable task followed by `approved_late`
  still produces the existing approved-late task record, but finalization
  reports the feature invocation failed with a timeout-stop reason.
- A second public `orchestrate` call on the same object, including a resume,
  starts with a clear fence. The first invocation's fence does not poison it.
- Direct `_execute_wave_parallel` and `_finalize_phase` calls on a fresh
  ordinary object and an `__new__`-constructed bare object observe a clear
  default and preserve their existing result and finalization behavior.
- Source inspection records the runtime's 300-second default-executor shutdown
  bound; no test waits for that duration. The design makes no claim that the
  old worker is quiescent when the invocation returns, and adds no join or kill.

### Real isolation decision

- The real FeatureOrchestrator-to-AutoBuild-to-Coach path gives a serialized
  task on the clean path a nominally parallel validator whose isolation
  decision is false; the independent subprocess check runs in the real
  worktree.
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
- Existing positional calls into the changed propagation chain retain their
  current bindings; focused tests pin this compatibility where AutoBuild,
  CoachValidator, `_execute_task`, or `_invoke_coach_safely` are exercised
  positionally. Omission and explicit `None` both retain the nominal fallback.
- A successful or failed SDK result continues to return directly without
  entering subprocess snapshot selection.
- If the configured SDK path raises and falls back to a subprocess, the
  current `use_sdk=true` state continues to skip snapshot creation. Explicit
  effective concurrency does not change that pre-existing execution root.
- Component, infrastructure, custom-base, and LangGraph cases that force
  `use_sdk=false` continue through the ordinary subprocess snapshot rule and
  use effective concurrency when it is explicitly present.
- Existing nominal-parallel controls for contention classification,
  conditional approval, runtime parity, non-Python routing, and whole-feature
  repair remain unchanged.
- `shares_working_copy=false` without explicit effective concurrency does not
  alter isolation.

### New fence-control homes

Each new control has an explicit existing file home. This table locates the
new nodes; the mandatory root runs below remain the regression boundary.

| Control | File home |
| --- | --- |
| Cap-one timeout with a still-running real-worktree check; queued peer does not start | `tests/unit/test_timeout_logging_reconciliation.py` |
| Cap-two timeout with an already-running sibling and an unstarted third task | `tests/unit/test_max_parallel.py` |
| Did-not-start result is false/error/zero-turn, never deferred, and retains queue-time `started_at` | `tests/unit/orchestrator/test_feature_orchestrator_skip.py` |
| Late approval cannot clear the fence | `tests/unit/test_timeout_logging_reconciliation.py` |
| `stop_on_failure=false` cannot start the next wave or inter-wave bootstrap | `tests/unit/test_inter_wave_bootstrap.py` |
| Smoke feedback retry cannot re-enter dispatch | `tests/unit/orchestrator/test_smoke_feedback_retry.py` |
| Wiring-gate retry cannot re-enter dispatch | `tests/unit/orchestrator/test_wiring_gate.py` |
| Whole-feature repair cannot re-enter dispatch | `tests/orchestrator/test_feature_check.py` |
| Final boot smoke and feature check do not run after a timeout | `tests/orchestrator/test_boot_smoke_wiring.py` and `tests/orchestrator/test_feature_check_three_outcomes.py` |
| Finalization forces failure while preserving task records and counts | `tests/integration/autobuild/test_smoke_gate_blocks_wave.py` |
| A second public invocation resets the fence on the same object | `tests/unit/test_feature_orchestrator.py` |
| Fresh normal and bare objects keep direct dispatch and finalization behavior | `tests/unit/test_feature_orchestrator.py` and `tests/orchestrator/test_feature_check_three_outcomes.py` |

The propagation and compatibility controls also live in named,
non-quarantined files:

| Propagation control | File home |
| --- | --- |
| Effective-concurrency arithmetic and scheduler-to-Feature context | `tests/unit/test_parallel_strategy.py` and `tests/unit/test_feature_orchestrator.py` |
| Feature-to-AutoBuild forwarding | `tests/unit/test_feature_orchestrator.py` |
| Primary and legacy Coach forwarding | `tests/orchestrator/test_behavioural_oracle_threading.py` |
| Deterministic Phase-4 forwarding | `tests/unit/orchestrator/test_specialist_wave_size_threading.py` |
| Positional compatibility, omitted/`None` fallback, and subprocess snapshot choice | `tests/unit/test_coach_parallel_isolation.py` |

### Later test execution

After implementation, run the new exact nodes first on the Dell through
`dell-test`, without xdist and with candidate source first on `PYTHONPATH`.
Then run all four mandatory roots as separate commands:

```text
~/.local/bin/dell-test timeout 3600 env PYTHONPATH=<candidate>/src:<candidate> <venv>/bin/python -m pytest -q -p no:xdist -p no:cacheprovider -o addopts= tests/unit
~/.local/bin/dell-test timeout 3600 env PYTHONPATH=<candidate>/src:<candidate> <venv>/bin/python -m pytest -q -p no:xdist -p no:cacheprovider -o addopts= tests/integration
~/.local/bin/dell-test timeout 3600 env PYTHONPATH=<candidate>/src:<candidate> <venv>/bin/python -m pytest -q -p no:xdist -p no:cacheprovider -o addopts= tests/orchestrator
~/.local/bin/dell-test timeout 3600 env PYTHONPATH=<candidate>/src:<candidate> <venv>/bin/python -m pytest -q -p no:xdist -p no:cacheprovider -o addopts= tests/seam
```

All four root commands are mandatory. Preserve each exact command, candidate
commit, complete pass/fail/skip count, exit status, elapsed time, and raw log.
Reproduce every candidate failure against the unchanged pinned base with the
same root or exact failing nodes before changing production logic or weakening
a control. Report unexecuted tests honestly if a bounded command does not
complete.

## Review

Implementation begins only after independent design acceptance. Implementation
review must verify the exact candidate, the conservative fallback, every
serialized and genuinely parallel control, and the absence of target
repository or isolated-copy changes.
