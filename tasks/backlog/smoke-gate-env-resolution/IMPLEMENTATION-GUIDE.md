# Implementation Guide — FEAT-SGER (Smoke-Gate Environment Resolution)

## Wave 1 (Parallel — SGER-001 and SGER-002 independent)

### TASK-SGER-001 — Include stderr in failure-path log

**Mode**: `direct` — single-file edit, low risk, no contract change.

**File**: `guardkit/orchestrator/smoke_gates.py`
**Function**: `run_smoke_gate` (lines 126–259)
**Specific edit**: lines 240–247 (failure path of the timeout-or-exit-mismatch branch).

**Current code**:

```python
else:
    passed = False
    logger.warning(
        "Smoke gate failed after wave %d (exit=%d, expected=%d)",
        wave_number,
        proc.returncode,
        config.expected_exit,
    )
```

**Target code** (sketch — exact form to be decided in task-work):

```python
else:
    passed = False
    logger.warning(
        "Smoke gate failed after wave %d (exit=%d, expected=%d)\n"
        "stderr:\n%s\n"
        "stdout:\n%s",
        wave_number,
        proc.returncode,
        config.expected_exit,
        (proc.stderr or "(empty)").rstrip(),
        (proc.stdout or "(empty)").rstrip(),
    )
```

Also update the timeout path at lines 192–205 to log captured stderr (the
`subprocess.TimeoutExpired` exception carries partial output via `exc.stdout` /
`exc.stderr`, which are already decoded into the `SmokeGateResult` but not logged).

The `console.print(...)` calls in `feature_orchestrator.py:2049-2059` should be
updated to include a short tail of stderr (e.g. last 20 lines) so the human-facing
red banner is also self-diagnosing, not just the log file.

**Test additions**: extend `tests/unit/orchestrator/test_smoke_gates_*.py` to assert
that the failure-path WARNING contains the captured stderr text.

### TASK-SGER-002 — Fall back to `sys.executable` when bootstrap produces no worktree-local venv

**Mode**: `task-work` — contract change to bootstrap-result handling, needs new tests.

**Files**:

1. `guardkit/orchestrator/feature_orchestrator.py` (lines 1370–1391, the
   `if result.venv_python:` block) — extend the `else` branch so it captures
   `sys.executable` instead of leaving `_bootstrap_venv_python = None`, on the
   condition that the bootstrap actually ran an install successfully (i.e. the
   parent venv now has the worktree's package installed).

2. (Optional, depending on the fix shape) `guardkit/orchestrator/environment_bootstrap.py`
   — alternatively, set `result.venv_python = sys.executable` inside the bootstrapper
   itself when `uv pip install` succeeds against an external venv. This keeps the
   contract "result.venv_python is non-None when an install succeeded" coherent and
   pushes the fallback into the source of truth.

The second option (fix in the bootstrapper) is preferred because it makes the
contract simpler: every successful bootstrap returns a usable interpreter, full stop.
The first option (fix in the orchestrator) adds branching at the call site.

**Behavioural contract after the fix**:

- If a worktree-local venv was created (PEP 668 fallback / uv-no-venv path), use it.
- If the install ran against the orchestrator's parent venv (macOS uv happy path),
  return `sys.executable` of the orchestrator process — that interpreter has the
  worktree's package installed and is the correct interpreter for smoke gates.
- If no install ran (skipped, hash match), preserve the previous resolution logic
  (use the saved state's `venv_python`, or `None` if there was none).

**Test additions**:

- `tests/unit/orchestrator/test_environment_bootstrap_venv_resolution.py` (new
  file) — assert `result.venv_python` is non-None after a successful uv-against-parent-venv
  install.
- Extend `tests/unit/orchestrator/test_smoke_gates_venv.py` to cover the new
  fallback path: assert that when `venv_python = sys.executable`, the smoke gate's
  PATH is prepended with the parent venv's `bin/`, and that the gate sees the
  worktree's editable-installed package.
- An integration-style test that uses `tmp_path` for a fake worktree, bootstraps it
  against a fresh ephemeral venv, runs `run_smoke_gate` with a command that
  imports the editable-installed package, and asserts `passed=True`.

## Acceptance Criteria (FEAT-SGER overall)

- [ ] **SGER-001**: Failure-path WARNING in `smoke_gates.py:240-247` contains
      captured stderr and stdout. Tests assert presence.
- [ ] **SGER-001**: Timeout-path return at `smoke_gates.py:192-205` logs captured
      stderr/stdout via the same channel.
- [ ] **SGER-001**: `feature_orchestrator.py:2049-2059` red banner includes a stderr
      tail (last 20 lines is fine).
- [ ] **SGER-002**: `EnvironmentBootstrapper.bootstrap()` returns a non-None
      `venv_python` after any successful install path, including the macOS
      uv-against-parent-venv path.
- [ ] **SGER-002**: New test exercises the macOS path and asserts the resolved
      interpreter is the orchestrator's `sys.executable`.
- [ ] **SGER-002**: An end-to-end integration test runs a smoke gate with a bare
      `python -c "import <editable-installed-package>"` against a tmp-path worktree
      and asserts `passed=True` — locking in the regression guard for FEAT-61F1's
      failure shape.
- [ ] After both tasks land, manually re-run `guardkit autobuild feature FEAT-61F1
      --resume` against a fresh checkout (or any equivalent feature that creates new
      package files) and confirm the smoke gate passes on the macOS happy path.

## Out of Scope

- Reworking the smoke-gate command syntax or the `SmokeGates` config schema.
- Bootstrapper changes for non-Python stacks.
- Fixing the visual weight of APPROVED panels vs the smoke-gate WARNING in the
  final summary (review report's tertiary recommendation — file separately if the
  team wants it).
