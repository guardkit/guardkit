---
id: TASK-AB-PERTASKFG01
title: "Per-task autobuild ships a verification false-green (hung test-orchestrator -> 0 tests read as 100% pass -> Coach approves unverified)"
status: backlog
task_type: fix
priority: high
created: 2026-06-18T00:00:00Z
updated: 2026-06-18T12:00:00Z
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

## Status (2026-06-18)

- **AC-001 + AC-002 LANDED + live-validated** (commit `3b3ba070`): fixes #2
  (reconcile quality_gates vs authoritative phase_4), #3b (zero-test anomaly no
  longer masked by fabricated coverage), #4 (Coach absent-signal classifier
  widened for conftest/collection import failures). Re-ran the TASK-SMOKE-REDACT01
  smoke on langgraph/gpt-oss-120b/gemma4-coach: the turn-1 **APPROVE** false-green
  is now a turn-1 **FEEDBACK** (reconcile fires; Coach gives actionable feedback)
  → not approved. 788 affected unit tests pass; +10 new regression tests.
- **AC-003 (bootstrap-venv test deps) — GuardKit fix LANDED (commit `b793b2d2`),
  unit-validated.** Root cause: `ProjectEnvironmentDetector` only recognised
  standard manifests, so a project declaring deps solely in a non-standard
  `requirements*.txt` (lpa's `requirements.poc.txt`) installed NOTHING → empty
  worktree venv → the (deterministic) Coach independent test couldn't import
  app/test deps. Fix: detect `requirements*.txt` additively when no editable
  manifest exists (+4 tests; confirmed it now detects lpa's `requirements.poc.txt`).
  **E2e smoke on lpa still needs an lpa-side fix** (declare `pytest-asyncio`, which
  its conftest imports but `requirements.poc.txt` omits) before a clean APPROVE;
  the broken-env case is SAFE meanwhile (#4 → absent-signal → feedback).
- **AC-004 (deterministic Player-side test execution) — LANDED, unit-validated.**
  Phase-4 test EXECUTION is now a deterministic venv-pinned `<venv_python> -m
  pytest` subprocess by default (no hangable LLM turn — running tests can no
  longer hang). Implemented by reusing the Coach's proven
  `CoachValidator(coach_test_execution="subprocess").run_independent_tests`
  runner (`specialist_invocations._run_deterministic_phase_4`), so Player
  Phase-4 execution and Coach independent verification run the IDENTICAL pinned
  pytest command — single source of truth, no divergence. Wired into
  `invoke_test_orchestrator` behind `GUARDKIT_PHASE4_TEST_EXECUTION`
  (default `subprocess`; `sdk` is the emergency revert lever to the legacy LLM
  specialist, mirroring `GUARDKIT_HARNESS`). The result→phase_4 mapping is
  absence-of-failure-safe: an ABSENT oracle (collection/conftest import
  failure, runner absent, returncode-5, timeout) maps to `status="failed"`
  (never a pass) so the #2 reconcile fires and Phase 5 is skipped; "no
  detectable pytest command" returns to the LLM `test-orchestrator` specialist
  unchanged (preserves non-Python / npm / dotnet stacks). +14 regression tests
  (`tests/unit/orchestrator/test_specialist_invocations.py`), incl. a real
  subprocess-execution e2e proving genuine pytest runs with no LLM in the loop.
  403 affected tests pass.

**All four acceptance criteria are now LANDED + validated.** This task is
complete and ready for `/task-complete`.

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
- **AC-004 — deterministic test execution (root cause). ✅ LANDED.** Removed
  the dependency on a hangable LLM `test-orchestrator` specialist for the
  *execution* of tests on the per-task path: Phase-4 now runs a deterministic
  venv-pinned `pytest` subprocess whose real result feeds the gate (the LLM may
  still author tests in Phase 3, but no longer "runs" them or self-reports
  pass/coverage). Running tests can no longer hang. Default
  `GUARDKIT_PHASE4_TEST_EXECUTION=subprocess`; `=sdk` reverts to the legacy
  specialist. The deterministic runner reuses the Coach's `run_independent_tests`
  (single source of truth) and is absence-of-failure-safe (absent oracle ⇒
  `failed`, never a pass). Non-pytest stacks fall back to the specialist
  unchanged. Implemented in
  `guardkit/orchestrator/specialist_invocations.py`
  (`_run_deterministic_phase_4`, `_resolve_phase_4_execution_mode`,
  `_parse_pytest_counts`); +14 regression tests.

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

## Root causes & precise fixes (investigated 2026-06-18 — all model-independent)

The false-green required **four independent deterministic-logic holes** on the
per-task path to all fail together. Fix order: the two `S` fixes close the live
reproduction; the two `M` fixes are the durable root fix.

1. **[AC-004] Test execution is a hangable LLM turn, not a subprocess.**
   `invoke_test_orchestrator` (`specialist_invocations.py:962-976`) runs tests by
   asking the model to emit `Bash` tool calls (`_build_test_orchestrator_prompt`
   `:639-682`). gpt-oss (harmony format) emitted no parseable tool call → no
   harness activity ping → no-activity watchdog (`:204-218`, default 150s
   `:126-128`) tripped at 162s → specialist returns `failed`, `tests_run=0`
   (`:978-988`). **Fix (M/high):** reuse the Coach's existing venv-pinned
   `<venv_python> -m pytest` subprocess runner (`coach_validator.py:3063`,
   `4287-4296`, pin `:1366-1372`) for Phase-4 execution. **Interim (S/high):**
   on specialist `hang detected`/`tests_run==0`, run a subprocess pytest
   fallback before writing the phase-4 block.

2. **[AC-001] Player `quality_gates` is fabricated from narrative regex, not the
   authoritative specialist record.** `agent_invoker.py:9119-9132` builds
   `quality_gates` by regex-parsing the Player's prose (`COVERAGE_PATTERN`
   `:851` → 100.0; `QUALITY_GATES_PASSED_PATTERN` `:852` → True) even though
   `specialist_results.json` phase_4 = `status:failed, tests_run:0`. **Fix
   (M/high):** reconcile `quality_gates` against `specialist_results.json` at the
   merge (`agent_invoker.py:~8177`) — phase_4 failed / `tests_run==0` ⇒
   `all_passed` cannot be True; never write the false-green to disk.

3. **[AC-001] Coach trusts `all_passed==True` with no `tests_run>0`
   precondition.** `CoachValidator.verify_quality_gates`
   (`coach_validator.py:3389-3406`) sets `tests_passed=True` from
   `quality_gates['all_passed']` with no cardinality guard; the zero-test anomaly
   precondition (`:6666`) has a `coverage is None` clause a fabricated 100%
   slips past. **Fix (S/high):** add a positive-evidence precondition
   (`tests_run>0`/`tests_passed>0`) and drop the `coverage is None` escape so
   only a *genuine* independent pass suppresses the anomaly.

4. **[AC-002] Coach independent-test absent-signal classifier too narrow.**
   `run_independent_tests` (`coach_validator.py:4322-4334`) flags `signal_absent`
   only for "No module named pytest" or exit-5; a conftest `ModuleNotFoundError`
   (fastapi) is **exit-4** → recorded as a real "ran-and-failed"
   (`signal_absent=False`) → disarms the deterministic backstop
   `_reconcile_absent_independent_test_signal` (`agent_invoker.py:5323`) → LLM
   Coach rationalises and approves. **Fix (S/high):** widen `signal_absent` to
   treat collection/conftest import failures (exit 2/4 + "ImportError while
   loading conftest" + 0 tests executed) as absent → re-arms the existing
   approve→feedback override. (AC-003 venv-deps complements this.)

**Coach MODEL is NOT a root cause.** The investigation corroborated that
`gemma4-coach` (MoE, ~47 tok/s) and `gemma4-31b` (~9-10 tok/s, up to ~32
min/turn) are on-par on verdict quality — 31b is "slower, no better". This
failure was the Coach *narrating a deterministically-fabricated false-green*;
a fine-tuned/bigger Coach would not fix it. Keep the MoE Coach; **deprioritise**
the fine-tuned-coach lever (`TASK-DATA-COACHHARVEST`) for this defect — it is a
longer-term judgment-quality investment, not a false-green fix.
