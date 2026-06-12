---
id: TASK-FIX-BOOTPYTEST01
title: Worktree venv lacks pytest on early Coach turns — Coach cannot run independent tests until ~turn 3
status: backlog
task_type: fix
created: 2026-06-12T11:30:00Z
updated: 2026-06-12T11:30:00Z
priority: high
complexity: 4
related: [TASK-HMIG-BDDWIRE, TASK-FIX-LSTRACE01, TASK-OPS-COACHMOE01]
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

## Acceptance criteria

- [ ] **AC-1 (root cause):** documented — bootstrap-missing-test-deps vs
  interpreter-race — with the evidence from run 1 + a reproduction.
- [ ] **AC-2:** on a fresh Python-feature worktree, the Coach's pinned
  independent-test interpreter can `import pytest` (and the stack's BDD runner)
  from **turn 1** — no "missing pytest dependency" feedback on turn 1.
- [ ] **AC-3 (regression):** a test asserts the worktree-bootstrap result exposes
  a test-capable interpreter (pytest importable) for a Python project before the
  Coach independent-test gate runs.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Notes

- Surfaced alongside TASK-FIX-LSTRACE01 (the harness crash). Together they are the
  two infra blockers from FEAT-E2CB run 1; the third factor (weak Player on a hard
  cross-repo task) is substrate/task-sizing, not infra.
- The Coach's honesty held throughout (populated criteria_verification, accurate
  feedback, no false-green) — this task is about letting it actually verify, not
  about its judgement.
