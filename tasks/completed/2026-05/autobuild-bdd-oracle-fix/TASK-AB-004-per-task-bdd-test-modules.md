---
id: TASK-AB-004
title: "Per-task BDD test modules: bdd_runner accepts test_<slug>__<TASK-ID>.py"
task_type: feature
parent_review: TASK-REV-8413
feature_id: FEAT-AB-FIX
wave: 1
implementation_mode: task-work
complexity: 6
estimated_minutes: 120
dependencies: []
working_dir: /home/richardwoollcott/Projects/appmilla_github/guardkit
domain_tags:
  - guardkit
  - bdd-oracle
  - parallel-execution
  - template
status: completed
completed: 2026-05-10T00:00:00Z
updated: 2026-05-10T00:00:00Z
previous_state: in_review
completed_location: tasks/completed/2026-05/autobuild-bdd-oracle-fix/
state_transition_reason: "All 9 ACs satisfied; 135 tests passing; completed via /task-complete"
---

## Implementation Summary

Threaded per-task identity through the BDD oracle so two parallel autobuild
tasks against the same worktree no longer race each other's pytest-bdd glue
file. Three coordinated edits:

1. `guardkit/orchestrator/quality_gates/bdd_runner.py` — added
   `_BDD_TASK_ID_ENV = "GUARDKIT_BDD_TASK_ID"` constant; threaded `task_id`
   through `_invoke_pytest_bdd`, which builds `os.environ.copy()` plus the
   new env var when `task_id` is supplied (legacy `task_id=None` path
   preserved by `env=None`); `run_bdd_for_task` now passes `task_id`.
2. `installer/core/templates/common/features/conftest.py.template` (new
   canonical template) — `_FeatureFile.collect()` now consults
   `_select_glue` which prefers `test_<slug>__<sanitised_task_id>.py`
   when the env var is set, falls back to `test_<slug>.py` otherwise.
3. `~/Projects/appmilla_github/fleet-gateway/.guardkit/worktrees/FEAT-FG-001/features/conftest.py`
   — same per-task glue logic applied in-place so FEAT-FG-001 resume can
   honour per-task glue without waiting for a template re-deploy. Left
   uncommitted in fleet-gateway per the user's instruction.

Sanitisation rule (single source of truth across all three files): strip
leading `@`, replace `:` and `-` with `_`. Mirrors
`bdd_runner._build_pytest_argv`.

Tests added (12 new, 135 passing total):
- `tests/unit/orchestrator/quality_gates/test_bdd_runner.py` — env-var
  threading (3 tests in `TestBddTaskIdEnvThreading`) + task_id pass-through
  (1 test in `TestRunBddForTask`); `_Patcher` updated to record `task_id`.
- `tests/unit/templates/test_features_conftest_template.py` (new) — 9
  tests covering sanitisation idempotence, candidate priority, on-disk
  selection, and missing-glue fallback. Loads the `.template` file via
  explicit `SourceFileLoader` because importlib's extension-driven loader
  inference returns None for non-`.py` suffixes.

Player-guidance rule added at `.claude/rules/bdd-per-task-glue.md`
documenting the per-task glue naming contract and warning against
`pytest_bdd.scenarios()` in shared modules.

## Lessons

- pytest-bdd v8 has no built-in `pytest_collect_file` hook for `.feature`
  files — the project-side conftest is load-bearing infrastructure, not
  optional. Parallel-task safety has to live in that conftest, not in
  the runner alone.
- The `.template` file extension defeats `importlib.util.spec_from_file_location`'s
  default loader inference. Use `SourceFileLoader(name, path)` +
  `spec_from_loader` to test template files without renaming them.
- Backwards compatibility for `_invoke_pytest_bdd` is cleanly expressed
  by `task_id: Optional[str] = None` defaulting to `env=None` in the
  subprocess call, which is the OS-default inheritance behaviour. No
  feature-flag plumbing required.

## Notes

Verification recipe from the task spec is now reproducible against the
FEAT-FG-001 worktree:

```
mv features/fleet-gateway-common-and-interfaces/test_fleet_gateway_common_and_interfaces.py \
   features/fleet-gateway-common-and-interfaces/test_fleet_gateway_common_and_interfaces__TASK_FG_002.py
GUARDKIT_BDD_TASK_ID=TASK-FG-002 \
  pytest -m task_TASK_FG_002 features/fleet-gateway-common-and-interfaces/fleet-gateway-common-and-interfaces.feature
```

# TASK-AB-004: Per-task BDD test modules

## Repository

**Primary working directory:** this repo (`guardkit`) — bdd_runner + feature template `conftest.py`.

**Secondary edit:** `~/Projects/appmilla_github/fleet-gateway/features/conftest.py` (the
existing project's collection bridge needs the same logic, since template changes do not
retro-fit deployed projects). Parent diagnostic review lives in fleet-gateway at
`tasks/backlog/TASK-REV-8413-analyse-autobuild-feat-fg-001-stall.md`.

## Problem

In FEAT-FG-001, two parallel Wave-2 tasks (TASK-FG-002 Jarvis, TASK-FG-003 Graphiti) ran
against the same worktree and both wrote into a single shared
`features/<slug>/test_<slug>.py`. Each task's Player rewrote the file for *its* scenarios
only, racing the other task. Even after fixing the import bug (TASK-AB-001/002), TASK-FG-003's
BDD oracle would collect zero scenarios because the shared file binds only the FG-002
scenarios; the `-m task_TASK_FG_003` filter would deselect everything that *is* bound.

## Scope

Make the BDD oracle pipeline support per-task glue modules:
`features/<slug>/test_<slug>__<TASK-ID-sanitised>.py`. Both files (per-task glue and the
legacy shared `test_<slug>.py`) should be acceptable; per-task glue takes precedence when
present.

### Edits

1. **bdd_runner**
   ([`guardkit/orchestrator/quality_gates/bdd_runner.py`](../../../guardkit/orchestrator/quality_gates/bdd_runner.py)):
   propagate the task ID into the pytest subprocess so the conftest collection bridge can
   read it. Two viable mechanisms:
   - Environment variable (e.g. `GUARDKIT_BDD_TASK_ID=TASK-FG-002`), or
   - `--bdd-task-id=TASK-FG-002` argv flag handled by the conftest's `pytest_addoption`.

   Pick env var (simpler, no plugin registration needed). Document the contract.

2. **Template `features/conftest.py`** in the guardkit project templates: update
   `_FeatureFile.collect()` to look up glue candidates in priority order:
   1. `test_<slug>__<TASK_ID_sanitised>.py` (sanitised the same way as marker tags: `:` → `_`, `-` → `_`)
   2. `test_<slug>.py` (legacy fallback)

3. **Existing fleet-gateway conftest**
   (`~/Projects/appmilla_github/fleet-gateway/features/conftest.py`): apply the same change
   so FEAT-FG-001 can resume.

4. **Player guidance**: update the autobuild orchestrator's task-work invocation prompt (or
   the BDD-related rule docs in `.claude/rules/`) to instruct each task's Player to write
   its own `test_<slug>__<TASK-ID>.py` rather than overwriting the shared module.

## Acceptance Criteria

- [ ] bdd_runner sets `GUARDKIT_BDD_TASK_ID=<task_id>` in the pytest subprocess env.
- [ ] Template `features/conftest.py` `_FeatureFile.collect()` looks for `test_<slug>__<sanitised_task_id>.py` first, falls back to `test_<slug>.py`.
- [ ] When neither file exists, the conftest yields nothing (current behaviour preserved).
- [ ] Sanitisation matches `bdd_runner._build_pytest_argv`: strip `@`, replace `:` and `-` with `_`.
- [ ] The fleet-gateway worktree's `features/conftest.py` is updated with the same logic so FEAT-FG-001 resume works.
- [ ] Existing unit tests for the conftest bridge continue to pass.
- [ ] New unit test: with both `test_<slug>.py` and `test_<slug>__TASK_FG_002.py` present, the runner collects from the task-specific module when invoked with `GUARDKIT_BDD_TASK_ID=TASK-FG-002`.
- [ ] New unit test: with only `test_<slug>.py` present, the runner falls back to it.
- [ ] Player guidance updated in `.claude/rules/` (or wherever the BDD rule lives) so future autobuild Players write task-specific glue.

## Out of Scope

- Migrating other deployed projects' conftest.py files (out-of-tree projects handle their own copies).
- Changing the .feature file authoring convention (still one `.feature` per slug).
- Mass-rewriting existing test_<slug>.py modules into per-task variants (each Player will write its own on next autobuild run).

## Verification

```bash
# In fleet-gateway worktree:
mv features/fleet-gateway-common-and-interfaces/test_fleet_gateway_common_and_interfaces.py \
   features/fleet-gateway-common-and-interfaces/test_fleet_gateway_common_and_interfaces__TASK_FG_002.py
GUARDKIT_BDD_TASK_ID=TASK-FG-002 \
  pytest -m task_TASK_FG_002 features/fleet-gateway-common-and-interfaces/fleet-gateway-common-and-interfaces.feature
# Expected: 5 scenarios collected (post-import-fix); runs FG-002 bindings only.
```
