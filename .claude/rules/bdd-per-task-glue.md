# BDD Per-Task Glue Modules

> **Source:** TASK-AB-004 (FEAT-AB-FIX), 2026-05-09. Companion to the canonical
> conftest at `installer/core/templates/common/features/conftest.py.template`
> and the env-var contract in
> `guardkit/orchestrator/quality_gates/bdd_runner.py` (`_BDD_TASK_ID_ENV`).

## The rule

When the autobuild Player writes a pytest-bdd glue module that binds a
`features/<slug>/<slug>.feature` file, **the glue file MUST be named
`test_<slug>__<TASK-ID>.py`** — not `test_<slug>.py`. The runner advertises
the active task ID via the `GUARDKIT_BDD_TASK_ID` environment variable, and
the project's `features/conftest.py` collector picks the per-task module
over any shared `test_<slug>.py` when both exist.

The legacy shared name `test_<slug>.py` is still honoured as a fallback for
projects that have not yet adopted per-task glue, but **new Player writes in
autobuild MUST emit per-task names** so parallel tasks against the same
worktree do not race each other's bindings.

## Why this rule exists

In FEAT-FG-001, two parallel Wave-2 tasks (TASK-FG-002 Jarvis, TASK-FG-003
Graphiti) ran against the same worktree and both wrote into a single shared
`features/<slug>/test_<slug>.py`. Each task's Player rewrote the file for
*its* scenarios only, racing the other task. Even after fixing the import
bug (TASK-AB-001/002), TASK-FG-003's BDD oracle would collect zero scenarios
because the shared file binds only the FG-002 scenarios; the
`-m task_TASK_FG_003` filter would deselect everything that *is* bound.

Per-task glue files end the race by giving each task its own collection
target.

## Naming contract

For a feature file at `features/<slug>/<slug>.feature` and an active task
`TASK-FG-002`:

- **Per-task glue (preferred):**
  `features/<slug>/test_<slug>__TASK_FG_002.py`
- **Legacy shared (fallback):** `features/<slug>/test_<slug>.py`

**Sanitisation rules** (must match the runner and the conftest):

| Source | Step |
|---|---|
| `<slug>` | replace `-` with `_` (e.g. `fleet-gateway-common-and-interfaces` → `fleet_gateway_common_and_interfaces`) |
| `<TASK-ID>` | strip leading `@`, replace `:` with `_`, replace `-` with `_` (e.g. `TASK-FG-002` → `TASK_FG_002`) |

The same sanitisation is applied by:

- `guardkit/orchestrator/quality_gates/bdd_runner.py::_build_pytest_argv` (for the `-m` marker filter)
- `installer/core/templates/common/features/conftest.py.template::_sanitise_tag` (for tag→marker mapping and per-task glue lookup)
- The fleet-gateway worktree's `features/conftest.py` (same logic, applied locally to FEAT-FG-001).

## What the Player should write

Inside the per-task glue module (`test_<slug>__<TASK_ID>.py`):

```python
"""pytest-bdd glue for TASK-FG-002 against features/<slug>/<slug>.feature."""
from pathlib import Path

from pytest_bdd import scenario


_FEATURE = Path(__file__).with_name("<slug>.feature")


@scenario(_FEATURE, "First TASK-FG-002 scenario name")
def test_first_scenario():
    pass


@scenario(_FEATURE, "Second TASK-FG-002 scenario name")
def test_second_scenario():
    pass


# Step definitions specific to this task's scenarios go here, or import
# from a shared helpers module if multiple tasks share step text.
```

**Key points:**

- Bind only the scenarios tagged `@task:<this-task-id>`. Do NOT call
  `pytest_bdd.scenarios(_FEATURE)` (which binds *every* scenario in the
  file) — that re-introduces the same cross-task race the per-task naming
  was meant to eliminate.
- Step definitions can be inlined in the per-task module or factored into
  a sibling helpers module (`_steps_<slug>.py`) imported by every per-task
  glue file. Either is fine; inlining is simpler when steps are unique to
  one task.
- Do NOT delete or rewrite the legacy `test_<slug>.py` if it already
  exists for another task. The conftest's per-task lookup means both
  files can coexist without conflict.

## What to do if `GUARDKIT_BDD_TASK_ID` is not set

Some legacy callers run the BDD oracle without setting the env var (e.g.
local developer runs of `pytest features/<slug>/<slug>.feature`). In that
case the conftest falls back to `test_<slug>.py` and the per-task module
is silently ignored. This is intentional: the per-task convention is an
opt-in opt-out for parallel autobuild runs, not a requirement for every
local pytest invocation.

If you are writing a *single*-task project (no parallel autobuild waves),
the legacy shared `test_<slug>.py` name is still acceptable. Adopt
per-task naming when you actually have parallel tasks binding scenarios
in the same `.feature` file.

## Enforcement

There is no automated lint for this rule yet — it is enforced by the
Player's adherence to this guidance and by the conftest's lookup order
(which silently picks the right file when names match the contract). If
you find a worktree where two tasks fight over `test_<slug>.py`, the
remediation is to rename one of them to `test_<slug>__<TASK-ID>.py` and
re-run the BDD oracle for that task with `GUARDKIT_BDD_TASK_ID` set.

## Related

- **Env-var contract:** `guardkit/orchestrator/quality_gates/bdd_runner.py`
  (constant `_BDD_TASK_ID_ENV = "GUARDKIT_BDD_TASK_ID"`).
- **Canonical conftest template:**
  `installer/core/templates/common/features/conftest.py.template`.
- **FEAT-AB-FIX feature folder:**
  `tasks/in_progress/autobuild-bdd-oracle-fix/` (formerly `backlog/`).
- **Sibling rules:** `feature-build-invariants.md` (Player-Coach roles);
  `autobuild.md` (worktree layout).
