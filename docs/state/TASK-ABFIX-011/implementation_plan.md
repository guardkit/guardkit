# Implementation Plan — TASK-ABFIX-011

> Gated per-test `--timeout` in the Coach's isolated pytest run.
> Deferred W3 of TASK-ABFIX-010. Complexity 6, task_type=fix.

## Problem (one line)

A single hanging test consumes the whole Coach subprocess budget and yields
`tests_run=0` (no per-test attribution). A **gated** per-test `--timeout`
(pytest-timeout, `--timeout-method=signal`) marks the *specific* hung test
FAILED while the others still run — but injecting it unconditionally is a
CRITICAL harness-wide regression (returncode-4 `unrecognized arguments` on any
project lacking the plugin). So every injection must be triple-gated.

## Empirical findings (verified pre-implementation, 2026-06-24)

- `--timeout-method=signal` → `1 failed, 2 passed`, hung test named `FAILED` and
  the **others run**. ← satisfies the AC.
- `--timeout-method=thread` → dumps tracebacks then `os._exit`-kills the session;
  others never report. ← wrong for the AC. **Default = `signal`.**
- `pytest_timeout` is importable in this dev env but declared in **no** manifest
  → availability is environment-dependent → the **probe must be load-bearing**.
- guardkit `addopts` has **no** global `timeout` → adding `pytest-timeout` to dev
  deps is fully inert until our gated `--timeout` is passed.
- Gate-stack freeze window `2026-05-11→2026-05-17` is **expired** (37 days).

## Code surface (verified against `main`)

| # | Site | File:line | Action |
|---|---|---|---|
| 1 | SDK string | `_pin_pytest_command` (4005/4007) | append timeout suffix to the pinned string (venv branches only) |
| 2 | isolated / parallel wave | `_run_isolated_tests` (4087) | append `_pytest_timeout_argv()` to the argv list |
| 3 | standard subprocess | `run_independent_tests` (4328) | append `_pytest_timeout_argv()` to the argv list |
| 4 | absent classifier | standard path (4392–4428) **and** isolated path (4107) | rc-4 / `unrecognized arguments: --timeout` → `signal_absent=True` |

Out of scope (audited, not pytest test-runs): `_gather_runtime_parity` smoke
(3089), `run_evidence_repo_tests` sibling-repo command (3344), AC-command
verification (4903). Non-goal per task: per-test timeout for non-Python stacks.

## Design — triple gate (constraints 1+2, never inject unconditionally)

New helpers on `CoachValidator`:

- `_probe_pytest_timeout() -> bool` — run `<pinned_interp> -c "find_spec('pytest_timeout')"`;
  non-zero / timeout / OSError ⇒ False (fail toward no-injection).
- `_pytest_timeout_available() -> bool` — cached (`self._pytest_timeout_available_cache`).
- `_pytest_timeout_injection_enabled() -> bool` — master gate:
  1. operator not disabled (`GUARDKIT_COACH_PYTEST_TIMEOUT` ∉ {0,false,off,no}),
  2. **Python stack** (`self._active_stack_profile is None`) — stack-plugin-architecture.md,
  3. plugin resolvable in the pinned interpreter (probe).
- `_pytest_timeout_argv() -> List[str]` — `["--timeout", N, "--timeout-method", M]` or `[]`.
- `_per_test_timeout_seconds() -> int` — env `GUARDKIT_COACH_PYTEST_TIMEOUT_SECONDS`, default `_DEFAULT_COACH_PER_TEST_TIMEOUT_S = 60`.
- `_pytest_timeout_method() -> str` — env `GUARDKIT_COACH_PYTEST_TIMEOUT_METHOD`, default `signal`.
- `_is_pytest_timeout_usage_error(returncode, combined) -> bool` (staticmethod) —
  `rc == 4 and "unrecognized arguments" in combined and "--timeout" in combined`.

Probe targets `self._pytest_interpreter()` = the interpreter that actually runs
pytest on the subprocess paths (and the SDK path when a venv is pinned). The SDK
no-venv branch already passes through unchanged ⇒ no injection there (avoids a
probe-interpreter ≠ run-interpreter mismatch).

## Defence-in-depth (constraint 3, fail toward feedback)

If the probe is ever wrong (plugin vanished between probe and run), the run exits
rc-4 `unrecognized arguments: --timeout`. The classifier maps that to
`signal_absent=True` — which ABFIX-010 already carries as `None` (fed back), never
a counted Player failure. The new classification is added to **both** subprocess
paths (standard + isolated). Narrow match cannot mask a genuine exit-1 failure.

## Dependency (constraint 1a, dogfood)

Add `pytest-timeout>=2.1,<3` to guardkit `dev` + `all` extras (mirrors the
existing pytest-bdd dogfood) so guardkit self-builds actually carry the plugin and
get per-test attribution. Inert elsewhere (probe-gated). No change to
`environment_bootstrap.py` generic logic (its `python_extras` installs only
*project-declared* extras, so it cannot inject an arbitrary helper generically —
the probe is the correct general mechanism).

## Files

- `guardkit/orchestrator/quality_gates/coach_validator.py` — helpers, 3 injections, classifier ×2, ctor cache, module constant.
- `pyproject.toml` — pytest-timeout in dev + all.
- `tests/unit/test_coach_pytest_timeout_injection.py` — new (gating, probe, 3 sites, classifier, real hung-test single+parallel, asyncio).

## Acceptance-criteria → evidence map

| AC | Covered by |
|---|---|
| inject only when plugin resolvable AND Python | `_pytest_timeout_injection_enabled` + gating tests |
| plugin absent ⇒ no injection, process fallback, no usage error | probe-False test + no-`--timeout` assertion |
| non-Python stack ⇒ no arg | stack-gate test |
| rc-4 usage error ⇒ signal_absent | classifier tests (both paths) |
| all surfaces incl. `wave_size>1` isolated | injection tests ×3 + parallel-wave real test |
| `--timeout-method` validated vs asyncio | asyncio real-execution test |
| plugin present ⇒ named FAILED + others run | hung-test real-execution test |
| CI harness-touching pin sdk/skipif | tests use `coach_test_execution="subprocess"`, no harness |
