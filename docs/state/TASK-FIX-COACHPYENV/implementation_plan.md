# Implementation Plan — TASK-FIX-COACHPYENV

## Root cause (AC-1, confirmed by code reading)

`CoachValidator` runs the Coach's *independent* tests in two paths, both of
which ignore the bootstrap venv interpreter:

1. **SDK path** (`coach_test_execution="sdk"`, the run-9 default) —
   `_run_tests_via_sdk` sends a Bash-tool prompt `pytest …`. The Bash
   subprocess resolves `pytest` via PATH. `_patched_pythonpath` prepends the
   worktree to PYTHONPATH but **PATH is untouched**, so `which pytest`
   resolves to the host Python 3.14 framework pytest → Pydantic-V1-on-3.14
   collection error → spurious "failed".
2. **Subprocess path** — `[sys.executable, "-m", "pytest"]` uses the
   orchestrator interpreter (`/usr/local/bin/python3` in run-9), **not** the
   bootstrap venv either.

Unlike `CoachVerifier` (fixed in TASK-FIX-7A05 to take `venv_python` and
resolve via `_resolve_venv_python`), **`CoachValidator.__init__` never
receives `venv_python`** — the bootstrap interpreter threaded from
`BootstrapResult.venv_python` (feature_orchestrator → AutoBuild →
AgentInvoker → CoachVerifier) stops short of the validator.

## Fix

Reuse the existing, tested helper `_resolve_venv_python` (no DRY violation).

### `guardkit/orchestrator/quality_gates/coach_validator.py`
- Import `_resolve_venv_python` from `coach_verification`.
- `__init__`: add `venv_python: Optional[str] = None`; store
  `self._venv_python = _resolve_venv_python(self.worktree_path, venv_python)`.
  **Guard (AC-4):** if `venv_python` was configured but resolution returns
  None or a different path, log a loud WARNING (Coach about to verify against
  the wrong interpreter).
- Add `_pytest_interpreter()` → `str(self._venv_python)` or `sys.executable`.
- Subprocess paths (isolated + main): use `_pytest_interpreter()` for argv[0]
  and `build_venv_env(...)` for PATH parity.
- SDK path: when a venv is resolved and `test_cmd` starts with `pytest`,
  rewrite to `<venv_python> -m pytest …` so the Bash tool pins the
  interpreter regardless of PATH; additionally prepend `<venv>/bin` to PATH
  via a scoped `_patched_path` (defence-in-depth, mirrors `_patched_pythonpath`).
- Extend the "Test execution environment" diagnostic to log the resolved
  bootstrap interpreter (AC-2 falsifier: the `…3.14/framework…` line no
  longer reflects the actual run).

### `guardkit/orchestrator/autobuild.py`
- Thread `venv_python=self._venv_python` into both `CoachValidator(...)`
  construction sites (LLM-Coach primary @ ~5565, legacy @ ~5422).

### Tests — `tests/orchestrator/test_coach_interpreter_selection.py`
- Resolved interpreter == configured bootstrap venv when it exists.
- Subprocess argv[0] uses the venv interpreter.
- SDK prompt/test_cmd pins `<venv_python> -m pytest`.
- Mismatch guard emits a loud warning (configured-but-missing).
- AutoBuild threads `venv_python` into CoachValidator.

## Out of scope
- Python 3.14 / Pydantic V1 portfolio dependency debt (anomaly J).
- Reasoning-extraction fix (guardkitfactory, COACHBUDG01-LG).
