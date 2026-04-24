---
id: TASK-FIX-7A05
title: Wire bootstrap venv into Coach pytest invocation (use correct interpreter)
status: backlog
created: 2026-04-24T12:55:00Z
updated: 2026-04-24T12:55:00Z
priority: medium
tags: [autobuild, coach, pytest, environment-bootstrap, interpreter-correctness]
parent_review: TASK-REV-E4F5
feature_id: FEAT-7A00
implementation_mode: task-work
wave: 2
conductor_workspace: autobuild-sdk-stall-resilience-w2-2
complexity: 5
depends_on:
  - TASK-FIX-7A04
---

# Task: Pass bootstrap venv to Coach so tests run against the intended interpreter

## Description

Address review TASK-REV-E4F5 finding **F7** and recommendation **R4b**.
`guardkit/orchestrator/coach_verification.py::_run_tests` (≈ lines 239–320)
invokes pytest as a subprocess with `cmd = ["pytest", "--tb=no", "-q"]` and
`cwd=worktree_path`. **There is no reference to the bootstrap result.**
Coach uses whatever `pytest` / `python3` is resolvable on the shell PATH.

When `EnvironmentBootstrapper` created `.guardkit/venv/bin/python` with the
project-intended interpreter (e.g. Python 3.13 for forge), Coach is unaware
of it. Concretely:

- Global `python3` is 3.12 → Coach runs tests with Python 3.12
- Bootstrap venv has Python 3.13 → Coach ignores it
- Result: **silent version skew between what the Player builds for and what
  Coach verifies against**, producing false positives/negatives depending on
  which features changed behavior between 3.12 and 3.13.

Not causal for FEAT-FORGE-002 (Player never ran) but a latent correctness
hazard that will bite the next feature that depends on a non-global Python.

## Acceptance Criteria

- [ ] `CoachVerification` / `coach_verification.py` accepts an explicit
      interpreter path (from `BootstrapResult.venv_python` or from
      `.guardkit/bootstrap_state.json`). Default remains PATH-resolved
      for backwards-compat only when no bootstrap venv exists.
- [ ] `_run_tests` invokes pytest via `[venv_python, "-m", "pytest", ...]`
      instead of `["pytest", ...]` whenever a venv interpreter is known.
- [ ] Interpreter resolution order:
      1. Explicit param passed by orchestrator
      2. `.guardkit/venv/bin/python` if it exists in the worktree
      3. `sys.executable` fallback
- [ ] Orchestrator plumbing: `feature_orchestrator.py` threads the
      `BootstrapResult.venv_python` into per-task Coach instantiation so
      all verification happens in the intended environment.
- [ ] The startup / per-wave log clearly states which interpreter Coach will
      use for that wave.
- [ ] Unit tests:
      1. Bootstrap produced venv → Coach uses `venv/bin/python -m pytest`
      2. No bootstrap venv (e.g. non-Python project) → Coach uses
         `sys.executable -m pytest` or PATH `pytest` (preserve current
         behavior for that case)
      3. Integration test asserting the argv shape passed to `subprocess.run`.
- [ ] Existing tests that exercise Coach still pass (no regression on
      non-Python stacks).

## Files

- `guardkit/orchestrator/coach_verification.py` (`_run_tests` ≈ 239–320,
  constructor for interpreter injection)
- `guardkit/orchestrator/feature_orchestrator.py` (thread
  `BootstrapResult.venv_python` into Coach instantiation)
- `guardkit/orchestrator/environment_bootstrap.py` — confirm
  `BootstrapResult` already exposes `venv_python`; add if not.
- `guardkit/orchestrator/autobuild.py` — same Coach-constructor plumbing
  where applicable.
- `tests/orchestrator/test_coach_interpreter_selection.py` (new).

## Implementation Notes

- **Important**: do not require a bootstrap venv for repos where one
  isn't created (e.g. Node, .NET, infra-only). The interpreter wiring
  only kicks in when Python bootstrap produced a venv.
- Prefer reading the interpreter path from `BootstrapResult` over re-deriving
  from `worktree/.guardkit/venv/bin/python` — the former is the
  orchestrator-canonical source of truth.
- Don't set `PATH` in the subprocess env; pass the interpreter explicitly
  as argv[0]. This is the more explicit and debuggable approach.

## Notes

- Cross-link: findings F6+F7 + recommendation R4b in TASK-REV-E4F5.
- Wave 2 after TASK-FIX-7A04 because both touch `feature_orchestrator.py`
  (gate logic vs. Coach constructor plumbing) — rebase after W1.
- This closes the latent-hazard loop opened by TASK-FIX-7A04: even if
  `bootstrap_failure_mode=warn` lets a run proceed, Coach won't silently
  validate against the wrong interpreter when a venv exists.
