---
id: TASK-AB-PERTASKFG01
title: "Per-task autobuild ships a verification false-green (hung test-orchestrator -> 0 tests read as 100% pass -> Coach approves unverified)"
status: backlog
task_type: fix
priority: high
created: 2026-06-18T00:00:00Z
updated: 2026-06-18T00:00:00Z
related: [TASK-AB-COACHRUNPARITY01, TASK-AB-WIREGATE01, TASK-DATA-COACHHARVEST]
implementation_mode: task-work
tags: [autobuild, coach, test-execution, absence-of-failure, green-not-correct, gpt-oss, langgraph]
---

# Per-task autobuild ships a verification false-green

## Why this task exists (live reproduction, 2026-06-18)

Validation smoke **TASK-SMOKE-REDACT01** (a trivial pure-util task) was run via
`guardkit autobuild task` on the current stack — **LangGraph default, Player
`gpt-oss-120b`, Coach `gemma4-coach`**, in `lpa-platform-poc`. Coach returned
**APPROVED on turn 1**. Independent inspection of the worktree showed the
implementation was in fact **correct** (`mask_account_number` verified directly
against all ACs) — but **the quality-gate pipeline never actually verified it**.
The code was correct *by luck of a trivial task*; on a wrong implementation this
same path ships broken-but-green work. This is the same `green != correct`
class as FEAT-FAUD, now reproduced on the **per-task** path with all the
feature-level fixes (COACHRUNPARITY01 / WIREGATE01) already in place — those are
post-wave / feature-only and do not protect `autobuild task`.

### The failure chain (evidence)

1. **Test execution never ran.** The Player's `test-orchestrator` specialist
   **hung** — `run_specialist(test-orchestrator) failed … hang detected
   (no model activity for 162s)` (the known gpt-oss specialist-hang trait,
   `[[gptoss-player-autobuild-traits]]`). Running pytest was delegated to an
   LLM specialist that stalled.
2. **Absence-of-failure false-green.** With no tests run, the Player's
   `task_work_results.json` `quality_gates` reported:
   `{"tests_passing": true, "tests_passed": 0, "tests_failed": 0,
   "coverage": 100.0, "coverage_met": true, "all_passed": true}` — i.e.
   **0 tests executed, reported as passing + 100% coverage**. The
   `tests_run > 0` precondition that guards the feature path did not fire here.
3. **Coach approved without verifying.** The Coach's own independent test run
   failed (worktree venv could not import `tests/conftest.py` —
   `ModuleNotFoundError: fastapi`, and separately `pytest_asyncio` is missing).
   The Coach **rationalised it away** and approved on the Player's claim —
   verbatim rationale: *"The failure in the independent test run is an
   environment error (missing 'fastapi' in conftest.py) and does not reflect on
   the correctness of the redaction utility … orchestrator quality gates confirm
   tests passed."* It then recorded `independent: {tests_run: true,
   tests_passed: true}` — a verdict it never actually obtained.
4. **Incomplete deliverable not caught.** The AC-required
   `src/lpa/utils/__init__.py` was missing; the tests cannot execute in the
   provided env. Neither was flagged.

## Root-cause framing

- **Running tests should be deterministic, not an LLM specialist.** The execution
  step hung because it is an agent turn (gpt-oss) rather than a subprocess. The
  Coach already has `test_execution: subprocess`; the Player-side test gate must
  not depend on a hangable LLM specialist for *execution* + self-reported counts.
- **Absent verification must never read as a pass** (the project's
  `absence-of-failure-is-not-success` rule). Both the Player gate (0 tests) and
  the Coach gate (independent test could not run) converted an *absent* signal
  into a *pass*.

## Acceptance Criteria

- **AC-001 — 0 tests is not a pass (per-task path).** When `tests_run == 0`
  (or the test-orchestrator specialist hung/failed), the Player quality-gate
  summary MUST NOT report `tests_passing: true` / `coverage: 100%` /
  `all_passed: true`. Surface it as an absent/blocking signal on the
  `autobuild task` path, mirroring the feature-path `tests_run > 0` precondition.
  Regression test exercising the hung-specialist / zero-cardinality case.
- **AC-002 — Coach must not approve on unrunnable verification.** When the
  Coach's independent test run cannot execute (collection/import/env error,
  exit before any test), it MUST treat that as **absent verification** —
  block or emit feedback — NOT approve on the Player's self-reported gates, and
  NOT record `independent.tests_passed: true`. The Coach prompt + the
  deterministic gate must forbid the "it's just an environment error, trust the
  orchestrator gates" rationalisation. Regression test on the
  independent-test-failed → must-not-approve path.
- **AC-003 — bootstrap venv runs the target repo's tests.** The Player/Coach
  test env must install the target project's *test* dependencies (e.g.
  `pytest_asyncio`, and whatever `conftest.py` imports) so independent
  verification can actually run; if it genuinely cannot, that is an absent
  signal per AC-002, never a silent pass. (Builds on TASK-AB-BOOTPY01 /
  TASK-AB-COACHVENV01.)
- **AC-004 — deterministic test execution (root cause).** Investigate and
  remove the dependency on a hangable LLM `test-orchestrator` specialist for the
  *execution* of tests on the per-task path; prefer a deterministic subprocess
  run whose real result feeds the gate (the LLM may still author tests, but must
  not be the thing that "runs" them and self-reports pass/coverage). Captures
  the user's point: running tests must not be able to hang.

## Notes / pointers

- Player gate construction (where `quality_gates` is assembled, incl. the
  hung-specialist path): `guardkit/orchestrator/specialist_invocations.py`
  (`run_specialist`, the no-model-activity watchdog) + the quality-gate assembly
  in `guardkit/orchestrator/agent_invoker.py` / `autobuild.py`.
- Coach approval + independent test: `guardkit/orchestrator/quality_gates/coach_validator.py`
  (`run_independent_tests`, the approve/feedback decision; `_is_langgraph_harness`
  forces subprocess for the Coach's own run).
- Rule family: `.claude/rules/absence-of-failure-is-not-success.md`
  (this is a new per-task-path instance), `.claude/rules/smoke-gate-is-feedback-not-terminator.md`
  (arm b: per-task runtime parity — feature-only today).
- The Coach **model** question (gemma4-coach MoE vs gemma4-31b vs a fine-tuned
  coach, `TASK-DATA-COACHHARVEST`) is tracked separately — the failure here is
  structural (the Coach was fed a false-green + an env error), so the
  deterministic gate fixes above come first and are model-independent.
- Reproduction artefacts: `lpa-platform-poc/.guardkit/worktrees/TASK-SMOKE-REDACT01/`
  (`.guardkit/autobuild/TASK-SMOKE-REDACT01/{player_turn_1,coach_turn_1}.json`).
