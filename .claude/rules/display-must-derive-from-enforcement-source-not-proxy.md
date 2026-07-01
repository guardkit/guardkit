# A status display must derive a runtime property from the enforcement source, not a proxy

> **Source**: Seeded by TASK-FIX-MAXPARALLEL01 (fix commit `cb350019e`,
> 2026-06-10). Pair with the Graphiti design-rule node of the same intent under
> `guardkit__project_decisions`. Member of the low-fidelity-oracle meta-frame
> family alongside
> [`absence-of-failure-is-not-success.md`](absence-of-failure-is-not-success.md)
> (false-green) and
> [`path-string-mismatch-is-not-dishonesty.md`](path-string-mismatch-is-not-dishonesty.md)
> (false-red): *a binary/numeric verdict from an oracle that cannot distinguish
> the thing it measures from the thing it reports*. This rule is the
> **human-facing display** instance of that shape.

## The rule

When a progress/status display reports a **runtime property** — concurrency,
pass/fail, existence, a resource cap actually being enforced — it MUST derive
that property from the **same source the runtime uses to enforce it**, never
from a different quantity that merely correlates with it.

A display that computes a count from one quantity (e.g. wave size =
`len(task_ids)`) and prints it *as if* it were another (effective concurrency)
is a false-signal generator: a human reads the reported quantity as the runtime
property, and the two silently diverge whenever the enforcement source says
something the proxy cannot.

Concretely: resolve the enforcement decision **once**, then feed that same
decision to both the executor (which enforces it) and the display (which reports
it). In GuardKit's wave loop this is `resolve_max_parallel(...)` — the display
calls it read-only (`log=False`), the executor calls it authoritatively, and the
banner shows `min(max_parallel, wave_size)`.

## Why this rule exists

Run-22 of FEAT-AOF was launched with `--max-parallel 1` to avoid parallel
substrate pressure. Wave 2's banner printed `Wave 2/2: TASK-FIX-GD02,
TASK-FIX-TP05 (parallel: 2)`, which a reviewer correctly read as *parallel
execution* — and that false read motivated filing TASK-FIX-MAXPARALLEL01 and
influenced sibling-task reasoning (the run-22 / COACHSYNTH F20 investigation).

The premise turned out to be wrong in an instructive way. The **executor** had
honoured `--max-parallel 1` all along: the `asyncio.Semaphore(max_parallel)`
enforcement landed in commit `524d8aaa` (2026-02-27) and the
`resolve_max_parallel` consumer in `108420b0` (2026-03-09), both predating
run-22. The run-22 log proved serial execution (TP05 activity began only after
GD02 completed). The defect was **display-only**:
`WaveProgressDisplay.start_wave` computed the `(parallel: N)` indicator as
`len(task_ids)` — the wave *size*, a proxy — not the effective concurrency the
executor enforced.

Confirmed code (all resolve today):

- `guardkit/cli/display.py:189-196` — `start_wave` now computes
  `effective_parallel = min(max_parallel, wave_size)` (guarding `max_parallel is
  None or <= 0` → unlimited = `wave_size`) and only renders the indicator when
  `wave_size > 1`. The `max_parallel` parameter was added at
  `display.py:153-158`; the INFO log at `display.py:209-212` includes the
  effective value for grep.
- `guardkit/orchestrator/feature_orchestrator.py:2280-2289` — `_wave_phase`
  resolves the effective cap **once**, read-only (`log=False`), and passes it to
  `start_wave(...)`.
- `guardkit/orchestrator/feature_orchestrator.py:3018-3030` — the executor
  (`_execute_wave_parallel`) resolves the **same** `resolve_max_parallel`
  decision (authoritative, `log=True`) and enforces it via
  `parallel_strategy.bound_concurrency`. Display and executor now consume one
  decision and cannot diverge in STATIC mode.
- `guardkit/orchestrator/parallel_strategy.py:50-118` — `resolve_max_parallel`
  gained a `log: bool = True` parameter so the display's read-only resolution
  does not double-log the dispatcher's authoritative decision;
  `bound_concurrency` (`parallel_strategy.py:121-156`, `asyncio.Semaphore`) was
  extracted verbatim from the inline loop so the bound is unit-testable.

## Symptom

- A banner/dashboard claims a runtime property (concurrency, "ran in parallel",
  a cap being applied) that a reviewer later finds untrue when reading execution
  logs or timing.
- The displayed number equals some *nearby* quantity (a collection size, a
  configured maximum, a request count) rather than what the runtime enforced.
- Two code paths compute "the same" property from **different** sources — the
  executor from the enforcement decision, the display from a proxy — with no
  shared resolution point.

## Detection recipe

```bash
# 1. Display code deriving a runtime property from a collection size / config,
#    not from the enforcement decision.
rg -n "parallel|concurren" guardkit/cli/display.py

# 2. The one-resolution invariant: the display and executor must consume the
#    SAME resolve_max_parallel call.
rg -n "resolve_max_parallel" guardkit/orchestrator/feature_orchestrator.py
#    -> expect two calls: display (log=False) at ~2281, executor at ~3018.

# 3. The effective-concurrency computation (min of cap and wave size), not
#    len(task_ids) alone.
rg -n "min\(max_parallel, wave_size\)|effective_parallel" guardkit/cli/display.py

# 4. Sibling meta-frame rules.
rg "display-must-derive|absence-of-failure|path-string-mismatch" .claude/rules/
```

## Remediation

1. **Resolve the enforcement decision once.** Whatever function the runtime uses
   to decide the property (`resolve_max_parallel`, a gate result, an existence
   check) is the single source of truth.
2. **Feed that same value to the display.** The display's call is read-only —
   suppress side effects (here `log=False`) so it does not double-log or mutate
   the authoritative path.
3. **Show the enforced quantity, not the proxy.** For a cap over a collection,
   that is `min(cap, collection_size)`, not the collection size.
4. **Add a display-parity test.** MAXPARALLEL01 pins this with
   `tests/unit/test_wave_progress_display.py::...test_start_wave_max_parallel_1_shows_serial`,
   `...test_start_wave_unlimited_shows_wave_size`, and drives the real
   `bound_concurrency` bound in
   `tests/unit/test_max_parallel.py::TestBoundConcurrencyWaveDispatch`.

## Grep-able signature (for next agent)

```bash
# One-resolution invariant (MUST MATCH — two calls, display read-only + executor):
rg -n "resolve_max_parallel" guardkit/orchestrator/feature_orchestrator.py
# Effective-concurrency, not wave-size (MUST MATCH):
rg -n "min\(max_parallel, wave_size\)" guardkit/cli/display.py
# The log=False suppression on the display's read-only resolution (MUST MATCH):
rg -n "log=False" guardkit/orchestrator/feature_orchestrator.py
# Sibling-rule lookup:
rg "display-must-derive|absence-of-failure|path-string-mismatch" .claude/rules/
```

## When this rule triggers

- Before adding or changing any status/progress display that reports a runtime
  property (concurrency, pass/fail, a resource cap, existence) rather than
  static configuration.
- Before introducing a second code path that computes "the same" property the
  runtime already enforces — wire it to the shared resolution point instead.
- During Phase 2.5 review for anything touching `guardkit/cli/display.py`,
  `WaveProgressDisplay`, or `resolve_max_parallel` / `parallel_strategy`.
- During any diagnostic session investigating a "the log said X ran in parallel
  but timing shows it was serial" (or the inverse) report.

## What it does NOT cover

- Displays of **static configuration** that is never enforced at runtime (e.g.
  echoing a `--max-parallel` flag as *"requested cap"*) — those legitimately
  show the input, provided they are labelled as the request, not the effect.
- DYNAMIC/PER_WAVE resolution where the executor's decision can still change
  after the display resolves (e.g. GPU-pressure-driven `MaxParallelMode.DYNAMIC`
  re-evaluated per wave). The one-resolution guarantee holds in STATIC mode;
  under non-static modes the display shows the best read-only estimate and the
  authoritative executor decision remains the source of truth.
- Non-display divergences (executor computing the wrong value itself) — that is
  an enforcement bug, not a display-vs-proxy bug.
