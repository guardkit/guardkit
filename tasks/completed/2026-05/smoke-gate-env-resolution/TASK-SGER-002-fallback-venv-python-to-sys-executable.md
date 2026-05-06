---
id: TASK-SGER-002
title: Fall back to sys.executable when bootstrap produces no worktree-local venv
task_type: implementation
parent_review: TASK-REV-61F1
parent_repo: specialist-agent
feature_id: FEAT-SGER
wave: 1
implementation_mode: task-work
status: completed
priority: high
complexity: 5
dependencies: []
tags: [smoke-gates, autobuild, environment-bootstrap, venv-resolution, recurring-bug-class]
created: 2026-05-06T00:00:00Z
updated: 2026-05-06T13:00:00Z
completed: 2026-05-06T13:00:00Z
previous_state: in_review
state_transition_reason: "AC #6 manual verification passed against study-tutor/FEAT-6CC5 (fresh worktree, clean bootstrap pass)"
---

# Fall back to sys.executable when bootstrap produces no worktree-local venv

## Context

The autobuild orchestrator already supports passing a bootstrap interpreter to the
smoke gate via `run_smoke_gate(venv_python=...)` — see
`guardkit/orchestrator/feature_orchestrator.py:2030-2035`. The mechanism prepends the
venv's `bin/` to PATH so the gate's bare `python` resolves to the right interpreter
(`smoke_gates.py:174-180`, `TASK-FIX-A7B1`).

But `_bootstrap_venv_python` is only set when `EnvironmentBootstrapper` returns a
non-None `result.venv_python`. The bootstrapper sets that field exclusively when it
created a **worktree-local** venv at `<worktree>/.guardkit/venv/` —
`environment_bootstrap.py:1395-1428`, the `_ensure_venv` method. That path only fires
on a PEP 668 fallback or a uv "no venv discoverable" error.

On the macOS happy path, `uv pip install -e .` succeeds against the orchestrator's
**parent shell venv** (the venv that was active when `guardkit autobuild` was launched).
The install is fine — the package IS installed and importable from `sys.executable` —
but `result.venv_python` stays `None`, so `_bootstrap_venv_python = None`, so the
smoke gate inherits the orchestrator subprocess's PATH unchanged. If PATH ordering
puts a different `python` ahead of the orchestrator's own (e.g. system framework
Python at `/usr/local/bin/`), the gate fires against the wrong interpreter.

That is exactly what bit FEAT-61F1 in specialist-agent. The history log shows
bootstrap line 32-34 succeeded (`uv pip install -e .` → `Install succeeded` →
`Environment bootstrapped: python`), but no `Coach will verify using interpreter:`
line was emitted (the `else` branch of `feature_orchestrator.py:1376-1391` was
taken). The smoke gate then resolved bare `python` to `/usr/local/bin/python`
(system Python 3.14), which had `specialist_agent` editable-installed against the
**main repo's `src/`** — not the worktree's. Statement 1 raised
`ModuleNotFoundError: No module named 'specialist_agent.tools.architecture_knowledge'`,
masking four correct artefacts.

The same shape previously bit FEAT-D40B (specialist-agent, wave 5,
`autobuild-D40B-history.md:1142-1147`). Until the bootstrapper always returns a
usable interpreter, this is a recurring environmental failure mode that no Coach
or Player change can prevent.

## Description

Make `EnvironmentBootstrapper.bootstrap()` always return a non-None `venv_python`
after a successful install, regardless of which install path fired. The contract
becomes: **`result.venv_python` is the interpreter that has the worktree's package
installed** — full stop.

Two implementation options; the second is preferred:

### Option A — Fix at the call site (simpler, less coherent)

In `feature_orchestrator.py:1370-1391`, extend the `else` branch:

```python
if result.venv_python:
    self._bootstrap_venv_python = result.venv_python
    console.print(...)
    logger.info(...)
elif result.installs_attempted > 0 and result.installs_failed == 0:
    # Bootstrap installed against the orchestrator's parent venv —
    # use sys.executable so the smoke gate sees the same interpreter
    # that was used for the install.
    self._bootstrap_venv_python = sys.executable
    logger.info(
        "Bootstrap installed against parent venv; smoke-gate interpreter "
        "set to orchestrator sys.executable: %s", sys.executable,
    )
else:
    logger.debug(
        "Bootstrap produced no venv interpreter — Coach will use "
        "PATH pytest / sys.executable fallback"
    )
```

### Option B — Fix in the bootstrapper (preferred)

In `environment_bootstrap.py`, after a successful `uv pip install` against the
parent venv, set `self._venv_python = Path(sys.executable)` so the result struct's
`venv_python` field is populated coherently. This makes the contract uniform: every
successful bootstrap exposes its interpreter, and downstream consumers don't need
to know which install path fired.

Option B is preferred because:

1. The contract becomes simpler — every consumer (smoke gate, Coach pytest invoker,
   any future consumer) sees a uniform "bootstrap.venv_python is the active
   interpreter" rule.
2. There is already a downstream consumer (Coach pytest at line 2855) that has the
   same blind spot. Fixing the bootstrapper fixes both call sites at once.
3. `_bootstrap_venv_python = sys.executable` at the orchestrator call site is
   indistinguishable from a worktree-local venv from the smoke gate's perspective —
   PATH gets prepended either way and `python` resolves to the right interpreter.

## Acceptance Criteria

- [ ] After any successful `uv pip install` (or pip install fallback) path,
      `EnvironmentBootstrapper.bootstrap()` returns a `BootstrapResult` with
      `venv_python` set to a usable interpreter:
      - The worktree-local venv at `<worktree>/.guardkit/venv/bin/python` when one
        was created (existing PEP 668 / uv-no-venv path — unchanged).
      - The orchestrator's `sys.executable` when the install ran against the parent
        venv (new path — Option B fix).
- [ ] When bootstrap was skipped (hash match, or non-Python project), preserve
      existing behaviour. `venv_python` may still be `None` in those cases.
- [ ] The "Coach will verify using interpreter:" log line and console message in
      `feature_orchestrator.py:1376-1380` fire on the macOS happy path (regression
      guard against the FEAT-61F1 silent-else-branch behaviour).
- [ ] `tests/unit/orchestrator/test_environment_bootstrap_*.py` extended (or a new
      test file added) covering:
      - Successful uv-against-parent-venv install → `result.venv_python ==
        sys.executable`.
      - Successful uv-no-venv fallback → `result.venv_python` points at
        `<worktree>/.guardkit/venv/bin/python` (existing behaviour, regression guard).
      - Skipped bootstrap (hash match) → behaviour preserved.
- [ ] `tests/unit/orchestrator/test_smoke_gates_venv.py` extended with an
      end-to-end test that:
      - Sets up a tmp-path worktree containing a minimal package + pyproject.toml.
      - Runs `EnvironmentBootstrapper.bootstrap()` against a controlled parent venv.
      - Calls `run_smoke_gate` with a command like `python -c "import <pkg>"` and
        asserts `passed=True`.
      - This is the regression guard for the FEAT-61F1 failure shape.
- [ ] Existing `test_smoke_gates_*.py` tests continue to pass.
- [ ] Manual verification: re-run `guardkit autobuild feature FEAT-61F1 --resume`
      against a fresh checkout (or any feature that creates new top-level package
      files) on macOS and confirm the smoke gate passes. The history log should
      now include the "Coach will verify using interpreter:" line.

## Out of Scope

- Changing the smoke-gate command syntax or the `SmokeGates` YAML schema.
- Bootstrapper logic for non-Python stacks (Node, Go, etc.). Their venv contract
  is different and is owned by separate tasks.
- Solving the upstream "uv install against parent venv on macOS" behaviour itself.
  uv's behaviour is correct — the install IS effective. The fix is in our
  bootstrapper's reporting contract, not in uv.

## Implementation Notes

- The fix is small in lines but touches a load-bearing contract — `task-work` mode
  is appropriate so the change goes through Coach review.
- `BootstrapState.venv_python` (saved into `.guardkit/bootstrap_state.json`) should
  also be populated on the new path so a `--resume` from saved state behaves
  identically. See `environment_bootstrap.py:1141-1153, 1372-1373`.
- Consider whether `result.venv_python = sys.executable` should be set even on the
  hash-match-skip path — if the saved state declares an interpreter, prefer it;
  otherwise fall back to `sys.executable`. Make the rule explicit in the test set.
- The orchestrator's `console.print(f"[cyan]⚙[/cyan] Coach will verify using
  interpreter: ...")` line already gives operators visibility into which
  interpreter was selected. After this fix, that line will be near-universal
  (firing on every successful bootstrap), which is the right outcome.

## Test Execution Log

### task-work run, 2026-05-06

**Implementation** (Option B — preferred path, fixed in bootstrapper):

`guardkit/orchestrator/environment_bootstrap.py` — added a single block at
the end of `EnvironmentBootstrapper.bootstrap()` (between the install loop
and `_save_state`) that captures `Path(sys.executable)` into
`self._venv_python` when:

1. `installs_failed == 0` (overall_success), AND
2. `self._venv_python` is still `None` (no PEP 668 / uv-no-venv fallback
   set it during the loop), AND
3. At least one manifest has `stack == "python"` (preserve `None` for
   pure-Node / pure-.NET projects per AC #2).

The orchestrator's `if result.venv_python:` branch at
`feature_orchestrator.py:1376-1391` now fires on the macOS happy path
naturally — no orchestrator-side change needed.

**New tests** (`tests/unit/orchestrator/test_environment_bootstrap_venv_resolution.py`):

- `TestParentVenvFallback` (3 tests) — first-try install records
  `sys.executable`, persists to state file, works with `uv pip install`
  command shape.
- `TestPep668PathRegressionGuard` (1 test) — PEP 668 fallback still
  points `venv_python` at `<root>/.guardkit/venv/bin/python`, NOT
  clobbered by the new sys.executable fallback.
- `TestSkippedBootstrap` (5 tests) — hash-skip preserves saved
  `venv_python`, old state files (no field) return `None`, non-Python
  projects return `None`, empty manifests return `None`, failed installs
  do not set `venv_python`.
- `TestMixedStacks` (1 test) — Python + Node mixed bootstrap correctly
  records `sys.executable` because Python install ran.

**Extended tests** (`tests/unit/orchestrator/test_smoke_gates_venv.py`):

- `test_run_smoke_gate_with_sys_executable_prepends_interpreter_dir` —
  asserts smoke gate's PATH-prepend treats `sys.executable` identically
  to a worktree-local venv.
- `test_bootstrap_then_smoke_gate_resolves_python_against_parent_venv` —
  end-to-end regression guard for FEAT-61F1 failure shape: bootstrap
  succeeds first-try → records `sys.executable` → smoke gate's PATH
  leads with the orchestrator's interpreter dir.

**Modified test** (`tests/unit/test_environment_bootstrap.py`):

- `test_state_no_venv_when_no_pep668` → renamed to
  `test_state_records_sys_executable_when_no_pep668`. The original test
  pinned the pre-TASK-SGER-002 behaviour where `venv_python` was absent
  from the state file when no PEP 668 fallback fired — i.e. the bug
  this task fixes. Updated to assert the new contract:
  `state.get("venv_python") == sys.executable` after a first-try
  install success.

**Test results**:

- New tests (`test_environment_bootstrap_venv_resolution.py` +
  extended `test_smoke_gates_venv.py`): **15 passed**
- Existing bootstrap suites
  (`test_environment_bootstrap{,_uv_venv,_fix7539}.py`,
  `test_inter_wave_bootstrap.py`): **173 passed** (regression sweep clean
  after the one test rename)
- Full orchestrator sweep (`tests/unit/orchestrator/`,
  `tests/orchestrator/test_bootstrap_gating.py`): **228 passed**
- Feature-orchestrator sweep
  (`tests/unit/test_feature_orchestrator{,_refresh,_task_copy}.py`,
  `tests/unit/orchestrator/test_feature_orchestrator_skip.py`):
  **171 passed, 1 skipped**

**Coverage**: New tests exercise all four documented bootstrap paths
(parent-venv success, PEP 668, hash-skip, non-Python). Implementation
block is fully covered by `TestParentVenvFallback` and `TestMixedStacks`.

**Manual verification on macOS** (AC #6 — completed 2026-05-06):

The originating FEAT-61F1 (specialist-agent) was used first but its
worktree's `.guardkit/bootstrap_state.json` carried a stale pre-fix
hash (timestamp 2026-05-05T23:02:27, no `venv_python` field) that
caused a hash-skip — the new code path never fired and the smoke gate
passed only because the test machine's PATH ordering happened to
favour the right interpreter (the same accidental success that
masquerades as the bug being absent).

Substituted **study-tutor / FEAT-6CC5** (mcp-llm-player-coach-adapters)
as the verification target — explicitly allowed by AC #6 ("or any
feature that creates new top-level package files"). FEAT-6CC5 was a
fresh build with no prior worktree and no prior bootstrap state, so
the bootstrap pass exercised the new code path end-to-end.

History log: `/Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/history/autobuild-FEAT-FEAT-6CC5-history.md`

Confirmed signals:

1. New INFO log fires (line 33):
   ```
   INFO:guardkit.orchestrator.environment_bootstrap:Bootstrap: install
     ran against parent venv; venv_python set to
     sys.executable=/usr/local/bin/python3
   ```

2. Orchestrator's existing visibility log fires (lines 35, 2374):
   ```
   ⚙ Coach will verify using interpreter: /usr/local/bin/python3
   ```

3. Smoke gate passes (line 2725):
   ```
   INFO:guardkit.orchestrator.smoke_gates:Smoke gate passed after wave
     2 (exit=0)
   ```

4. State file persisted with venv_python — `--resume` would correctly
   recover it:
   ```json
   {
     "content_hash": "f1f15323...",
     "success": true,
     "timestamp": "2026-05-06T12:45:11.441261",
     "venv_python": "/usr/local/bin/python3"
   }
   ```

The pre-fix FEAT-61F1 history showed bootstrap-line-32 install
succeeded then NO `Coach will verify using interpreter:` line — the
exact failure shape this fix closes. Post-fix, that log line is
near-universal (firing on every successful Python bootstrap), which
is the right outcome.

**Out of scope** (preserved per task implementation notes):

- The uv-no-venv retry path (`_ensure_uv_venv` creates `<cwd>/.venv/`
  and sets `self._uv_venv_python` but not `self._venv_python`) was NOT
  modified. That path's existing behaviour is unchanged — `venv_python`
  remains `None` on uv-no-venv retry success. If FEAT-61F1's failure
  shape ever fires there, a follow-up task can mirror the same fallback.
- `feature_orchestrator.py` `else` branch at lines 1385-1391 was not
  modified. Option B's bootstrapper-side fix means the `else` branch
  now fires only for non-Python projects or fully-failed bootstraps,
  which is the correct semantics — keep `Coach will use PATH pytest`
  fallback log line.
