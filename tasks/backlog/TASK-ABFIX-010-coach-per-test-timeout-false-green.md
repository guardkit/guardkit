---
id: TASK-ABFIX-010
title: Coach isolated pytest needs per-test timeout; stop misreading hung tests as false-green
status: backlog
task_type: bug
feature_id: FEAT-CD4C
sub_feature: ABFIX
wave: 1
implementation_mode: task-work
complexity: 5
estimate_hours: 3
dependencies:
  - TASK-ABFIX-005
---

# Coach isolated pytest needs per-test timeout; stop misreading hung tests as false-green

## Description

Follow-up to **TASK-ABFIX-005** (parallel-wave Coach test isolation). A real
AutoBuild run (`forge` FEAT-FMDR, 2026-06-23) terminated **TASK-FMDR-001 as
`unrecoverable_stall`** even though the implementation had converged to a fully
passing test suite (verified: 34/34 pass in ~0.2s against the final worktree).

Root cause is in the Coach validation harness, not the implementation:

1. The Coach's isolated pytest command
   (`pytest <files> -v --tb=short`, run in a temp snapshot for `wave_size>1`)
   carries **no per-test timeout**. An early-turn test version that blocked on a
   real connection/subprocess consumed the entire ~60s isolated budget and
   produced **no parseable result** (`tests_run=0 tests_failed=0`).
2. `agent_invoker` / `coach_validator` then classified `tests_run=0 + timeout`
   as **"absent test signal"** and applied a **"narrative false-green" override**
   (Player claimed `tests_passing=True` → overridden to NOT passed). This
   conflates *infra/SDK transport timeout* (genuinely no signal) with *a specific
   test that hung* (a real, attributable FAILURE).
3. `worktree_checkpoints` counted three such harness timeouts as
   "3 consecutive test failures" → **context pollution → `unrecoverable_stall`**
   with "no passing checkpoint exists", killing a task whose code was converging.

Evidence and full write-up: `forge` repo
`docs/reviews/FEAT-FMDR-autobuild-false-green-analysis.md`.

A repo-side mitigation was tried in forge (`addopts = "--timeout=30
--timeout-method=thread"`) and **reverted**: the AutoBuild worktree `.venv` does
not install `pytest-timeout`, so the global `addopts` made *every* pytest run in
the worktree (BDD runner + Coach independent run) fail with
`unrecognized arguments: --timeout`. This is direct evidence that the timeout
must be injected by the harness in a way that **degrades gracefully when
pytest-timeout is absent** (e.g. wrap pytest in an OS-level `timeout`/subprocess
deadline, or detect the plugin and only pass `--timeout` when importable) —
never assume the target repo's test env has the plugin.

## Source locations

- `guardkit/orchestrator/quality_gates/coach_validator.py` — builds and runs the
  isolated pytest command; owns `self.test_timeout` (default 300, but isolated
  wave runs observed at 60s) and the runtime-parity check.
- `guardkit/orchestrator/agent_invoker.py` — "absent test signal" reconciliation
  and "narrative false-green" override.
- `guardkit/orchestrator/worktree_checkpoints.py` — context-pollution /
  consecutive-failure stall detection.

## Acceptance Criteria

- [ ] The Coach's isolated pytest invocation injects a per-test timeout
      (e.g. `--timeout=<N> --timeout-method=thread` when `pytest-timeout` is
      available, with a documented fallback when it is not) so a single hanging
      test yields a **named FAILED result**, not `tests_run=0`.
- [ ] The harness distinguishes *infra/SDK transport timeout* (no signal) from
      *a test that hung* (real failure). A per-test timeout firing is reported as
      a normal test failure attributable to the offending node id.
- [ ] The context-pollution / `unrecoverable_stall` guard does **not** count
      pure infra timeouts (`tests_run=0` with no failing node) toward the
      consecutive-failure threshold; a task converging to green is not killed by
      harness timeouts.
- [ ] Regression test: simulate a hanging test in an isolated Coach run and
      assert it is reported as a single failing node (not "absent test signal"),
      and that one such event does not by itself trigger `unrecoverable_stall`.
- [ ] No change to legitimate false-green detection: a Player that genuinely
      claims green while a test really fails is still overridden to NOT passed.

## Related finding — false *approval* (same root: test-result trust)

The same FEAT-FMDR run surfaced the mirror failure on TASK-FMDR-004: the Coach
**approved** an e2e task whose own run was 5/9 red, because (a) the task's test
gate was `required=False` and (b) the LLM Coach classified the failures as
"substrate failure … evidence ABSENT, not failed". It was half-right (4 failures
were a missing host `psql`), but the approval masked two real test-code bugs
(nonexistent `get_runbook_by_id`; asserting an unpersisted `runbooks.status`).
Both this task (hang → false reject) and that case (red → false approve) reduce
to the harness trusting a non-deterministic read of test results. Worth a
companion fix: for `task_type: testing`, make the test gate required, and
distinguish *substrate* failure from *code* failure deterministically rather than
by LLM prose. Evidence:
`forge:docs/reviews/FEAT-FMDR-autobuild-false-green-analysis.md` (Second finding).

## Notes / out of scope

- Graphiti/FalkorDB `bound to a different event loop` warnings during Coach
  context loading are a separate, non-fatal issue — not covered here.
- Same-wave tasks editing overlapping files (FMDR-001/002 both touched
  `test_cli_runbook.py`) is a planning concern for `/feature-plan`, not this task.
