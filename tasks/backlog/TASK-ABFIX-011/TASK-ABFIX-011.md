---
id: TASK-ABFIX-011
title: "Coach isolated pytest: inject a per-test --timeout (gated) so a single hanging test yields a named FAILED, not a whole-budget tests_run=0"
status: backlog
task_type: fix
created: 2026-06-24T00:00:00Z
priority: medium
complexity: 6
related:
  - TASK-ABFIX-010              # parent; this is its deferred W3
  - TASK-ABFIX-005              # parallel-wave Coach isolation (the 4th injection surface)
  - TASK-FIX-BSEXTRAS01         # worktree-venv extras install (the dependency-handling hook)
implementation_mode: task-work
tags: [autobuild, coach, pytest-timeout, test-isolation, stack-agnostic, deferred-from-abfix-010]
source_docs:
  - ../forge/docs/reviews/FEAT-FMDR-autobuild-false-green-analysis.md   # item 1 of the harness-side fix
---

# Task: gated per-test --timeout in the Coach's isolated pytest run

> **Provenance.** Deferred W3 of TASK-ABFIX-010 (the FEAT-FMDR harness fix).
> ABFIX-010 fixed the *consequence* (an absent timeout signal is now kept as
> `None`, not coerced to a failure). This task fixes the *cause* of the absent
> signal: a single hanging test consumes the whole 60s/300s subprocess budget and
> produces `tests_run=0` (no per-test attribution). A per-test `--timeout` would
> let the *specific* hung test be marked FAILED while the others run.

## Why this task exists (and why it was deferred, not done with ABFIX-010)

The originating analysis's **item 1** proposed "inject a per-test timeout into the
Coach's isolated pytest command." The ABFIX-010 regression review rated an
*unconditional* `--timeout` a **CRITICAL harness-wide regression** and split it
out: `pytest-timeout` is **not** in guardkit's deps and is **not** installed into
worktree venvs, so a bare `pytest --timeout=N` exits returncode 4
(`unrecognized arguments: --timeout`) on every project lacking it. That is the
*already-reverted* FEAT-FMDR-003 repo-side regression, replayed harness-wide. So
this task is the **fully-gated** version, shipped on its own with its own ACs.

This is also a `stack-plugin-architecture.md` concern: `pytest-timeout` is
Python-only; a multi-stack harness (TS/.NET/Go) must not grow a Python-specific
injection that breaks or misfires on other stacks.

## Code surface (verified against `main`, 2026-06-24)

| Site | File:line | Role |
|---|---|---|
| SDK path | [`coach_validator.py:3571`](../../guardkit/orchestrator/quality_gates/coach_validator.py#L3571) `_run_tests_via_sdk` → [`:3993`](../../guardkit/orchestrator/quality_gates/coach_validator.py#L3993) `_pin_pytest_command` (called at :3664) | hands `test_cmd` to a Bash tool |
| subprocess (standard) | [`coach_validator.py:4084`](../../guardkit/orchestrator/quality_gates/coach_validator.py#L4084) `parts = test_cmd.split()` → `subprocess.run` (:4088/:4097) | direct subprocess run |
| subprocess (isolated / parallel wave) | [`coach_validator.py:4325`](../../guardkit/orchestrator/quality_gates/coach_validator.py#L4325) `parts = test_cmd.split()` → `subprocess.run` (:4329/:4338), under `_run_isolated_tests` ([:4025](../../guardkit/orchestrator/quality_gates/coach_validator.py#L4025)) | the TASK-ABFIX-005 isolation snapshot path (`wave_size > 1`) |
| absent classifier | the `signal_absent` detection (returncode 5 / `No module named pytest` / `ImportError while loading conftest` / `errors during collection`) | must learn returncode-4 `unrecognized arguments` |
| dep install hook | [`environment_bootstrap.py`](../../guardkit/orchestrator/environment_bootstrap.py) `python_extras` (TASK-FIX-BSEXTRAS01, ~:106-260) | where pytest extras are installed into the worktree venv |

**The 4th-injection-site lesson (ABFIX-010 GAP 3):** the isolated/parallel path
(`:4325`) is easy to miss — patching only `_pin_pytest_command` leaves parallel
waves on process-level-only timeout, re-creating the `tests_run=0` condition
exactly on parallel waves.

## Design constraints (the gating — all mandatory)

1. **Dependency handling — never inject unconditionally.** Prefer **(a)** install
   `pytest-timeout` into the worktree venv for Python stacks via
   `environment_bootstrap.py` (mirror the BSEXTRAS01 extras install) so injection
   is unconditional-but-safe; **or (b)** probe
   (`importlib.util.find_spec('pytest_timeout')` in the *pinned* interpreter, or a
   `pytest --co --timeout=0 -q` dry-run) and inject only on success, else fall back
   to the existing process-level `self.test_timeout` (no regression, no per-test
   attribution that turn).
2. **Stack-agnostic gate** (`stack-plugin-architecture.md`): inject only on the
   Python branch — `test_cmd.startswith("pytest")` AND no active non-Python stack
   profile. Inject by argv-splitting (mirror the existing `parts = test_cmd.split()`
   sites), never string-append. .NET/JS/Go `whole_suite_command` get **no** timeout
   arg. Per-test timeout for non-Python stacks is an explicit non-goal.
3. **Defence-in-depth classifier.** Extend the `signal_absent` classifier to map
   `unrecognized arguments: --timeout` / returncode 4 → `signal_absent=True`. So the
   worst case (probe wrong, plugin missing) degrades to an *absent* signal (which
   ABFIX-010 now handles as `None`, fed back), never a counted failure. Fail toward
   feedback.
4. **All FOUR surfaces** (SDK `_pin_pytest_command`, the two subprocess split-sites
   at :4084 and :4325, and confirm no other pytest-cmd construction site). Audit
   before claiming coverage.
5. **`--timeout-method`** chosen for asyncio-heavy suites (guardkit's own tests use
   pytest-asyncio): validate `thread` vs `signal` does not spuriously interrupt
   GIL-holding / async tests and mis-report them as failures.

## Acceptance Criteria

- [ ] `--timeout` is injected **only** when `pytest-timeout` is resolvable in the
      pinned/worktree interpreter AND the stack is Python.
- [ ] When `pytest-timeout` is absent, no injection occurs and the run falls back
      to the existing process-level timeout — no `unrecognized arguments` failure on
      any project.
- [ ] A non-Python stack profile yields no `--timeout` arg.
- [ ] A `--timeout` usage error (returncode 4 / `unrecognized arguments`) is
      classified `signal_absent=True`, not ran-and-failed.
- [ ] All injection surfaces covered, including the `wave_size > 1` isolated path
      (:4325). A regression test exercises a hung test on a parallel wave.
- [ ] `--timeout-method` validated against an asyncio test (no spurious interrupt).
- [ ] With pytest-timeout present, a single hanging test in a multi-test file
      yields a named FAILED for that test and pass/fail verdicts for the others
      (not `tests_run=0`).
- [ ] CI: harness-touching tests pin `GUARDKIT_HARNESS=sdk` or `skipif`.

## Test strategy

- plugin-present → `--timeout` injected on the Python path (both subprocess sites + SDK).
- plugin-absent → no injection, process-level fallback, no usage error.
- non-Python stack → no injection.
- returncode-4 usage error → `signal_absent=True` (composes with ABFIX-010's `None`).
- hung test, single-task wave → named FAILED + others run.
- hung test, parallel wave (`wave_size > 1`, the :4325 path) → same.
- asyncio test under `--timeout-method` → not spuriously interrupted.

## Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| unconditional inject → harness-wide false-fail | CRITICAL | constraints 1+3 (gate + classifier); this is the whole reason W3 was split out |
| miss the :4325 isolated site | HIGH | AC enumerates all four surfaces + a parallel-wave test |
| python-only arg breaks multi-stack | HIGH | constraint 2 (Python-branch gate) |
| `--timeout-method` interrupts async/C-ext tests | MEDIUM | constraint 5 + asyncio test |

## Out of scope

- The absent-signal handling itself (landed in ABFIX-010 — a timeout still degrades
  to `None`/feedback if injection can't help).
- W4 (required test gate) — separate task TASK-ABFIX-012.
