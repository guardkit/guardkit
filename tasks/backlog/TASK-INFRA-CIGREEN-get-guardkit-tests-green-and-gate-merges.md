---
id: TASK-INFRA-CIGREEN
title: Get the guardkit test suite green and gate merges with a test CI
status: backlog
task_type: fix
created: 2026-06-10T00:00:00Z
updated: 2026-06-10T00:00:00Z
priority: high
complexity: 5
parent_task: TASK-HMIG-010
related: [TASK-INFRA-XREPOCONTRACT, TASK-FIX-BACKENDKWARG]
implementation_mode: task-work
tags: [ci, tests, infra, python-version]
---

# Task: Get the test suite green and gate merges with a test CI

## Why this task exists

The guardkit test suite currently fails, and **there is no test CI to catch it**
— `.github/workflows/` contains only `docs.yml`. With the suite red and ungated,
real regressions hide in the noise (run-24's `build_autobuild_backend` kwarg
crash, the run-22 display bug, etc. all reached a live run because nothing gated
them). This task makes `pytest tests/` green in a defined environment and wires a
CI job that fails the build when it isn't.

## Known failure categories (from this session's triage — confirm + complete)

1. **Python-version contradiction (the big one).** `pyproject.toml` declares
   `requires-python = ">=3.10"` and lists the 3.10 classifier, but the
   orchestrator uses `asyncio.timeout()` (**3.11+**) throughout. Under 3.10 this
   yields **~26 failures + 4 collection-error modules** (`test_sdk_harness`,
   `test_agent_invoker_sdk_errors`, `test_coach_sdk_stream_resilience`,
   `test_specialist_observability`). Under 3.12 those vanish.
   → **Fix**: bump `requires-python` to `>=3.11`, drop the 3.10 classifier, and
   pin CI to 3.11+/3.12. (Backporting `async_timeout` for genuine 3.10 support is
   a much larger scope and not worth it — pick the floor.)
2. **Dead-task-ID-reference lint** —
   `tests/rules/test_no_dead_task_id_references.py::test_no_dead_task_id_references_in_orchestrator`
   fails: ~14 hardcoded `TASK-*` literals in `guardkit/orchestrator/**/*.py`
   resolve to no file/state-dir. → **Fix**: per the lint's own rules — file the
   referenced tasks, remove the dead literal, or replace with a placeholder
   (`TASK-XXX-YYYY`).
3. **Environment-dependent tests** — e.g.
   `test_invoke_task_work_implement_mode_passed` (test worktree lacks
   `.venv/bin/python`) and
   `test_inter_wave_bootstrap::test_greenfield_scenario_wave1_creates_manifest`
   (a `uv venv`/`pip install` mock assertion). → **Fix**: make hermetic
   (provide the fixture) or `skipif` when the dependency is absent — no false reds
   in CI.
4. **New regressions from the recent change flurry** (COACHSPLIT → COACHTESTTO →
   COACHFG01 → COACHBFULL → COACHSYNTH → COACHTURNBUDGET → MAXPARALLEL01). Sweep
   for anything those introduced. (NB: the run-24 `build_autobuild_backend`
   crash is a *runtime cross-repo* miss that unit tests don't catch because
   guardkitfactory is mocked — covered by TASK-FIX-BACKENDKWARG +
   TASK-INFRA-XREPOCONTRACT, not this task.)

## Acceptance criteria

- [ ] **AC-1 (triage)**: run the full suite in the chosen CI env (3.11+/3.12) and
  categorize **every** remaining failure as version / lint-debt / env-dependent /
  genuine-regression, with counts. Document the list.
- [ ] **AC-2 (version floor)**: `requires-python` bumped to `>=3.11`, 3.10
  classifier removed, and the floor documented. The ~26 asyncio.timeout failures
  are gone.
- [ ] **AC-3 (lint green)**: the dead-task-ID lint passes (the ~14 refs
  filed/removed/placeholdered).
- [ ] **AC-4 (env tests hermetic)**: env-dependent tests pass or skip cleanly with
  no CI dependency on a developer machine's worktree/venv state.
- [ ] **AC-5 (green on main)**: `pytest tests/` exits 0 on a clean `main` in the CI
  env; any intentionally-skipped test is documented with its reason.
- [ ] **AC-6 (test CI gates merges)**: a `.github/workflows/tests.yml` (or equiv)
  runs the suite on 3.11+/3.12 on push/PR and fails the build on any failure —
  the suite is now *gated*, not just *green-once*.

## Notes

- The suite is **slow** (>4.6 min, didn't finish a 280s cap locally). Consider
  `pytest-xdist` (`-n auto`) in CI as a follow-up so the gate is fast enough to
  keep.
- Pairs with TASK-INFRA-XREPOCONTRACT (the cross-repo contract smoke-test should
  be part of the same CI gate) and TASK-FIX-BACKENDKWARG (the acute run-24 fix).
- The only existing workflow is `docs.yml` (Python 3.12) — reuse its
  setup-python pattern for the test job.
