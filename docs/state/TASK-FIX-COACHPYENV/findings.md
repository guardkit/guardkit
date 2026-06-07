# TASK-FIX-COACHPYENV — Root-cause confirmation (AC-1)

**Date:** 2026-06-07
**Confidence at review time:** medium (inferred from run-9 env log lines).
**Confidence now:** high (structural confirmation by code reading — stronger
than a single captured stdout, which run-9 did not preserve).

## What run-9 logged

- `Coach pytest interpreter set from bootstrap venv: …/.venv/bin/python`
  (`feature_orchestrator.py:1446-1449`) — the bootstrap interpreter *was*
  captured into `FeatureOrchestrator._bootstrap_venv_python`.
- `Test execution environment: sys.executable=/usr/local/bin/python3,
  which pytest=/…/Python.framework/Versions/3.14/bin/pytest,
  coach_test_execution=sdk` — the Coach validator ran under a *different*
  interpreter than the bootstrap venv.
- `Core Pydantic V1 functionality isn't compatible with Python 3.14…` —
  the 3.14 framework pytest tripped the Pydantic-V1 incompatibility,
  producing collection errors the SDK heuristic reads as "failed".

## The structural gap (confirmed in code)

`BootstrapResult.venv_python` is threaded:
`feature_orchestrator → AutoBuildOrchestrator(venv_python=…) →
AgentInvoker(venv_python=…) → CoachVerifier(venv_python=…)`.

But it **stops at `CoachVerifier`** (honesty checks). The independent-test
runner, `CoachValidator`, was constructed at
`autobuild.py:5422` (legacy) and `autobuild.py:5565` (LLM-Coach primary)
**without** `venv_python`. `CoachValidator.__init__` had no such parameter.

Consequently both of its test paths ignored the bootstrap interpreter:

1. **SDK path** (`coach_test_execution="sdk"`, the run-9 default):
   `_run_tests_via_sdk` sends a Bash-tool prompt `pytest …`. `os.environ`
   is mutated only for PYTHONPATH (`_patched_pythonpath`); **PATH is never
   patched**, so the Bash subprocess resolves `pytest` from the host PATH →
   the 3.14 framework pytest. → spurious "failed".
2. **Subprocess path**: `[sys.executable, "-m", "pytest"]` → the
   orchestrator interpreter (`/usr/local/bin/python3`), still not the
   bootstrap venv.

This is the inverse of TASK-FIX-7A05, which fixed exactly this shape for
`CoachVerifier` (interpreter pin via `_resolve_venv_python`). The validator
was simply never wired the same way.

## Verdict

The run-9 independent-test failures were **interpreter-induced, not
Player-code defects** — the mechanism is structural and reproduces for any
host whose PATH `pytest` differs from the bootstrap venv. Fix: thread
`venv_python` into `CoachValidator` and pin the interpreter on both test
paths (reusing `_resolve_venv_python`). See `implementation_plan.md`.

## AC status

- AC-1 (root cause confirmed + documented): **done** (this file).
- AC-2 (`…3.14/framework…` no longer the actual run interpreter): **done** —
  SDK command pinned to `<venv> -m pytest`; subprocess argv pinned;
  diagnostic now logs `resolved_interpreter`. Unit-locked.
- AC-3 (known-correct turn → passing Coach tests on `/v1/responses`):
  **structurally satisfied + unit-locked**; final live confirmation is the
  next FEAT-AOF run (this AC is itself the run-level falsifier).
- AC-4 (mismatch guard + regression test): **done** — loud WARNING on
  configured-vs-resolved mismatch; `TestCoachValidatorInterpreter` added.
