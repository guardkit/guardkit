---
id: TASK-FIX-BOOTPYTEST01
title: Worktree venv lacks pytest on early Coach turns — Coach cannot run independent tests until ~turn 3
status: completed
task_type: fix
created: 2026-06-12T11:30:00Z
updated: 2026-06-12T12:30:00Z
completed: 2026-06-12T12:30:00Z
completed_location: tasks/completed/autobuild-harness-migration/
previous_state: in_review
state_transition_reason: "All acceptance criteria met; quality gates passed (35 + 377 tests green, ruff-clean)"
priority: high
complexity: 4
related: [TASK-HMIG-BDDWIRE, TASK-FIX-LSTRACE01, TASK-OPS-COACHMOE01, TASK-FIX-COACHPYENV, TASK-GK-BS-001]
implementation_mode: task-work
tags: [autobuild, environment-bootstrap, worktree-venv, coach, independent-tests, pytest]
---

# Task: Worktree venv missing pytest on early Coach turns

## Why this task exists

FEAT-E2CB autobuild run 1 (2026-06-12): the Coach **could not verify** the
Player's work on early turns because the worktree venv lacked pytest.

- **Coach turn 2 rationale (verbatim):** *"The implementation failed to meet any
  of the acceptance criteria. The integration tests could not be verified due to
  a **missing pytest dependency in the environment**, and the core functional
  requirements were not evidenced in the results."*
- **Turn 3:** the same independent test ran — *"Independent tests passed in 4.4s"*.

So pytest was absent turns 1–2 and present by turn 3. The Coach behaved correctly
(treated "couldn't verify" as ABSENT SIGNAL → feedback, per
`absence-of-failure-is-not-success.md`) — but it could not actually *do its job*
on the early turns, which burned turns and contributed to the timeout. This is a
**bootstrap-completeness / interpreter-pinning** gap, not a Coach defect.

## Investigate (cheap, first)

1. Does the worktree-local venv bootstrap (`guardkit/orchestrator/environment_bootstrap.py`,
   "FFC6: creating worktree-local venv via uv (seeded)") install the project's
   **test** deps (pytest, pytest-bdd, pytest-asyncio) — or only runtime deps from
   the seeded manifest? In run 1 the logged dep-installs were runtime-only (click,
   rich, pydantic, graphiti-core, gherkin-official, npm ci) — **no pytest**.
2. The Coach pins its independent-test interpreter (log: *"CoachValidator pinning
   independent-test interpreter to .../.guardkit/worktrees/FEAT-E2CB/.venv/bin/python"*).
   Confirm whether that venv has pytest from turn 1, or whether early turns ran
   before the install completed (a bootstrap **timing/race**), or used a different
   interpreter.
3. Why did turn 3 succeed but 1–2 fail? (install completed by turn 3? different
   interpreter? the Player added pytest?) — this disambiguates "missing dep" vs
   "race".

## Likely fix

Ensure the worktree venv includes the **test** toolchain (pytest + the stack's
BDD/test plugins) **before the first Coach independent-test run** — e.g. install
the project's `[dev]`/`[test]` extra (or an explicit pytest set) during bootstrap,
or block the first Coach turn until the test interpreter is verified to import
pytest. Pair with `coach_validator.py`'s interpreter-pinning so the pinned
interpreter is guaranteed to have pytest.

## Root cause & resolution (AC-1)

**Verdict: bootstrap-missing-test-deps, NOT an interpreter race.**

Evidence chain (run 1, FEAT-E2CB):

1. `FEAT-E2CB.yaml` declares **neither** `bootstrap_extras` **nor** a
   `smoke_gates` block.
2. `feature_orchestrator._bootstrap_environment` calls
   `derive_bootstrap_extras(feature, worktree.path)`
   (`feature_orchestrator.py:1382`). On the old code this hit the
   `if feature.smoke_gates is None: return []` early-out — so
   `python_extras = ()`.
3. With no extras, `ProjectEnvironmentDetector` emits
   `pip install -e .` (no `[dev]`). For guardkit's own worktree the
   project is "complete", so the editable install runs and installs only
   `[project.dependencies]` — **runtime deps only**. pytest lives in
   guardkit's `[project.optional-dependencies].dev` / `.test`
   (`pyproject.toml:68-89`), which were never installed.
4. The eager worktree venv (`environment_bootstrap._ensure_worktree_venv`,
   "FFC6: creating worktree-local venv via uv (seeded)") therefore had
   **no pytest**. `BootstrapResult.venv_python` =
   `<worktree>/.venv/bin/python`.
5. The Coach pins its independent-test interpreter to exactly that venv
   (`coach_validator._resolve_venv_python`, log: *"CoachValidator pinning
   independent-test interpreter to …/.venv/bin/python"*), so on turns 1-2
   it could not `import pytest` → emitted the "missing pytest dependency"
   feedback (correctly treated as absent-signal per
   `absence-of-failure-is-not-success.md`).
6. **Why turn 3 "worked":** the bootstrap runs **synchronously before
   Wave 1** (no async race possible), so the absence is structural, not a
   timing race. By turn 3 the Player had incidentally installed pytest
   into the worktree venv while making its own tests pass — disambiguating
   "missing dep" from "race" in favour of missing-dep.

**Fix.** Add resolution branch 3 to `derive_bootstrap_extras`
(`feature_loader.py`): the Coach's independent-test gate runs pytest for
*every* Python task unconditionally, so even with no operator declaration
and no pytest smoke gate, a `[dev]`/`[test]` extra that **provides** pytest
(new `_extra_provides_pytest` helper, word-boundary `\bpytest\b` match,
also accepts plugins like `pytest-bdd`) is now installed. For guardkit's
own worktree this resolves to `["dev"]` → `pip install -e .[dev]` →
pytest in `<worktree>/.venv` → the Coach's pinned interpreter is
test-capable from turn 1. Branches 1 (operator-declared) and 2 (pytest
smoke gate) are unchanged; a `[dev]` of only linters is deliberately NOT
force-added (precision guard).

**Reproduction = regression.**
`TestCoachAlwaysNeedsPytest::test_no_smoke_gate_auto_adds_dev_when_dev_provides_pytest`
reproduces the exact FEAT-E2CB shape (Python project, `[dev]` carries
pytest, feature with no smoke gate) and asserts `["dev"]`; on pre-fix
`main` it returns `[]`.

## Acceptance criteria

- [x] **AC-1 (root cause):** documented — bootstrap-missing-test-deps (not an
  interpreter-race) — with the evidence from run 1 + a reproduction. See
  *Root cause & resolution* above.
- [x] **AC-2:** on a fresh Python-feature worktree, the Coach's pinned
  independent-test interpreter can `import pytest` (and the stack's BDD runner)
  from **turn 1** — no "missing pytest dependency" feedback on turn 1.
  `derive_bootstrap_extras` now resolves to `["dev"]` for a Python worktree
  whose `[dev]` extra provides pytest, threading `.[dev]` into the editable
  install that populates the venv the Coach pins to. (Live validation: the
  FEAT-E2CB `--fresh` re-run.)
- [x] **AC-3 (regression):** `tests/unit/orchestrator/test_environment_bootstrap_extras.py`
  — new `TestCoachAlwaysNeedsPytest` class (8 tests) + the end-to-end
  `test_no_smoke_gate_pytest_extra_threads_to_install_command` asserting the
  install command carries `.[dev]` before the Coach gate runs.
- [x] All modified files pass project-configured lint/format checks with zero
  errors. (ruff: 0 new findings on both modified files; the repo configures no
  formatter — both files already diverge from black on `main`, so the
  hand-formatted style is matched.)

## Resolution

- **Files changed:**
  - `guardkit/orchestrator/feature_loader.py` — new `_extra_provides_pytest`
    helper + branch 3 in `derive_bootstrap_extras`.
  - `tests/unit/orchestrator/test_environment_bootstrap_extras.py` — new
    `TestCoachAlwaysNeedsPytest` class; AC-3 end-to-end test; 3 existing
    branch-2 tests had fixtures isolated to non-pytest extras (their "no
    extras" intent preserved; rationale inline).
- **Tests:** `test_environment_bootstrap_extras.py` 35 passed; the related
  bootstrap + feature_loader + smoke-gate suites (377 tests) all green.

## Notes

- Surfaced alongside TASK-FIX-LSTRACE01 (the harness crash). Together they are the
  two infra blockers from FEAT-E2CB run 1; the third factor (weak Player on a hard
  cross-repo task) is substrate/task-sizing, not infra.
- The Coach's honesty held throughout (populated criteria_verification, accurate
  feedback, no false-green) — this task is about letting it actually verify, not
  about its judgement.
- **Known caveat (out of scope):** `EnvironmentBootstrapper._compute_hash` keys
  dedup on manifest *file contents*, not the resolved install command. A
  non-`--fresh` re-run against an already-bootstrapped worktree (state hash
  match + prior `success:true`) would skip the install and not pick up `[dev]`.
  The autobuild norm — and the FEAT-E2CB re-run recipe — uses `--fresh` (new
  worktree, no stale state), so the fix takes effect. Folding the resolved
  extras into the bootstrap hash is a separate, broader change.
- Companion to **TASK-FIX-COACHPYENV** (which pinned the Coach to the worktree
  venv) and **TASK-GK-BS-001** (which introduced `bootstrap_extras` +
  smoke-gate auto-detection). This task closes the gap they left: the Coach's
  pytest need is *unconditional*, not keyed on smoke-gate config.
