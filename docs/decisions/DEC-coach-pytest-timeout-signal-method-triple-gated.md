# DEC — Coach per-test pytest `--timeout` uses `signal` method, triple-gated injection

**Status:** ACCEPTED (implemented) · **Date:** 2026-06-24 · **Task:** TASK-ABFIX-011 · **Commit:** `8bf47747c`

## Context

In the FEAT-FMDR autobuild post-mortem, a Coach isolated pytest run hit a single
hanging test that consumed the whole subprocess budget (60s/300s) and returned
`tests_run=0` — no per-test attribution. Downstream this became the FEAT-FMDR
false-green (a process-level timeout with zero verdicts).

An earlier draft (the already-reverted FEAT-FMDR-003) proposed injecting
`pytest --timeout=N` **unconditionally**. The ABFIX-010 regression review rated
that a CRITICAL harness-wide regression: `pytest-timeout` is not a guaranteed
dependency, so a bare `--timeout` exits returncode 4 (`unrecognized arguments:
--timeout`) on every project lacking the plugin. TASK-ABFIX-011 is the split-out,
fully-gated version. It also had to choose between the two pytest-timeout enforcement
methods (`signal` vs `thread`) for a codebase whose own tests are asyncio-heavy.

## Decision

The Coach's per-test `--timeout` injection uses **`--timeout-method=signal`** as the
default (not `thread`), and the injection is **triple-gated**:

1. **Operator flag** — `GUARDKIT_COACH_PYTEST_TIMEOUT` (default enabled; disabled
   when set to `0`/`false`/`off`/`no`).
2. **Python stack only** — inject only when no non-Python stack profile is active
   (per `stack-plugin-architecture.md`); a Python-only arg must never reach a
   `.NET`/`JS`/`Go` `whole_suite_command`.
3. **Plugin resolvable** — `pytest-timeout` is probed in the pinned interpreter
   (in-process `find_spec` when it is `sys.executable`, else an out-of-process
   probe) before any injection.

The per-test method is overridable via `GUARDKIT_COACH_PYTEST_TIMEOUT_METHOD`, and
the per-test deadline (default 60s) via `GUARDKIT_COACH_PYTEST_TIMEOUT_SECONDS`.

## Rationale

**`signal` over `thread`** — empirically verified: `signal` raises inside the hung
test and lets the pytest session **continue**, so the other tests still run and
report verdicts (yields e.g. `1 failed, 2 passed` with the hung test named FAILED).
That is exactly the per-test attribution the task requires. `thread` dumps
tracebacks then `os._exit`-kills the whole session, so the other tests never report
— defeating the purpose. `signal`'s alarm fires only once a test exceeds the
deadline, so a healthy asyncio test (event loop on the main thread) is never
spuriously interrupted — validated against pytest-asyncio, which guardkit's own
suite uses.

**Triple gate over unconditional injection** — the unconditional `--timeout` was
rejected as replaying the reverted FEAT-FMDR-003 regression harness-wide. Gating
confines injection to the case where it is both safe (plugin present) and
meaningful (Python/pytest stack), and is operator-disableable.

**Fail toward feedback** — the worst case (plugin vanishes between probe and run →
rc-4 `unrecognized arguments: --timeout`) is classified `signal_absent=True`, an
instance of the `absence-of-failure-is-not-success` /
`absence-must-survive-every-reconciliation-layer` family: it is carried by
ABFIX-010 as `None` (fed back to the Player), never a counted Player failure.

## Consequences / Implementation

In `guardkit/orchestrator/quality_gates/coach_validator.py`:

- **`_pytest_timeout_method()`** (`:4365`) — returns `signal` by default, honouring
  `GUARDKIT_COACH_PYTEST_TIMEOUT_METHOD` (`:4378`); accepts only `signal`/`thread`.
- **`_pytest_timeout_injection_enabled()`** (`:4280`) — the triple gate: operator
  flag `GUARDKIT_COACH_PYTEST_TIMEOUT` (`:4290`), `_active_stack_profile is None`
  (`:4293`), and `_pytest_timeout_available()` (`:4295`, a cached
  `_probe_pytest_timeout()` at `:4303`).
- **`_pytest_timeout_argv()`** (`:4386`) — the single argv fragment
  (`--timeout N --timeout-method signal`) shared by all three pytest construction
  sites so the gate cannot drift: SDK `_pin_pytest_command` (`:4222`), standard
  subprocess (`:4471`), and the isolated/parallel-wave `_run_isolated_tests`
  path (`:4755`).
- **`_is_pytest_timeout_usage_error()`** (`:4263`) — matches returncode 4 +
  `unrecognized arguments` + `--timeout`, wired to set `signal_absent=True` on both
  subprocess paths (`:4504`/`:4507` standard; `:4851`/`:4870` isolated).
- **`_per_test_timeout_seconds()`** (`:4342`) and module constant
  `_DEFAULT_COACH_PER_TEST_TIMEOUT_S = 60` (`:117`).

Dogfood: `pytest-timeout>=2.1,<3` added to guardkit's `dev` and `all` extras
(`pyproject.toml:81`, `:113`) so guardkit self-build worktrees carry the plugin.
Regression coverage: `tests/unit/test_coach_pytest_timeout_injection.py` (39 tests
— gating, probe, the three injection sites, the classifier on both subprocess
paths, a real hung test on single and parallel waves, and an asyncio test proving
no spurious interrupt).

## References

- **Task:** `tasks/completed/TASK-ABFIX-011/TASK-ABFIX-011.md`
- **Commit:** `8bf47747c` — "fix(coach): gated per-test pytest --timeout so a hung
  test is named-FAILED, not tests_run=0 (TASK-ABFIX-011)"
- **Parent task:** TASK-ABFIX-010 (kept the absent timeout signal as `None`; this
  task fixes the *cause* of that absent signal)
- **Related rules:** `.claude/rules/stack-plugin-architecture.md` (Python-only
  gate), `.claude/rules/absence-of-failure-is-not-success.md` and
  `.claude/rules/absence-must-survive-every-reconciliation-layer.md` (the
  `signal_absent` fail-toward-feedback classification)
