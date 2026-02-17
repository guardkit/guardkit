# Implementation Guide: Player/Coach Test Divergence Fix (FEAT-27F2)

## Parent Review

- **Review Task**: TASK-REV-D7B2
- **Review Report**: `.claude/reviews/TASK-REV-D7B2-review-report.md`
- **Architecture Score**: 35/100 (pre-fix)
- **Root Cause**: 5 interacting bugs forming a failure cascade

## Execution Strategy

### Wave 1: Quick Wins (R1 + R2 + R3)

**Task**: TASK-PCTD-5208
**Method**: `/task-work`
**Estimated Time**: 3-4 hours
**Dependencies**: None

Three independent fixes bundled into one task:
- **R1**: Enhance `_summarize_test_output()` in `coach_validator.py` — include error type and traceback
- **R2**: Add `_normalize_feedback_for_stall()` in `autobuild.py` — normalize before MD5 hash
- **R3**: Add `_normalize_to_relative()` in `coach_validator.py` — fix path dedup

**Impact**: Eliminates symptoms — non-actionable feedback, stall detection gap, duplicate test paths. With R2, stall detection would have caught the TASK-DB-003 loop at Turn 5 (saving 13 turns / ~35 minutes).

### Wave 2: Infrastructure Classification (R4)

**Task**: TASK-PCTD-9BEB
**Method**: `/task-work`
**Estimated Time**: 4-6 hours
**Dependencies**: TASK-PCTD-5208 (R1 feedback enhancement needed first)

Classify test failures as infrastructure vs code:
- Add `_classify_test_failure()` to `CoachValidator`
- Store raw output in `IndependentTestResult.raw_output`
- Generate actionable feedback for infrastructure failures (mock fixtures, SQLite, pytest marks)

**Impact**: Prevents infinite loops for infrastructure-dependent tests (DB, Redis, external services). Player receives specific remediation options instead of generic "tests failed".

### Wave 3: Environment Parity / Option C (R5)

**Task**: TASK-PCTD-3182
**Method**: `/task-work`
**Estimated Time**: 6-8 hours
**Dependencies**: TASK-PCTD-5208 (R1 summary enhancement feeds into SDK output parsing)
**Complexity**: 7 (Phase 2.8 human checkpoint expected)

Root cause fix — use SDK Bash tool for Coach test execution:
- Add `_run_tests_via_sdk()` async method to `CoachValidator`
- Modify `run_independent_tests()` for SDK-first execution
- Add `coach_test_execution` config option (`"sdk"` default / `"subprocess"`)
- Add `_load_coach_config()` to `AutoBuildOrchestrator`

**Impact**: Eliminates the root cause (F1: environment parity gap). Coach tests run in identical environment to Player — 100% parity with venv, conda, poetry, nvm, pyenv, direnv, Docker.

**CRITICAL**: The review report contains a fully validated implementation with 9 GAP-FIX annotations traced against SDK v0.1.18. Follow the implementation code exactly to avoid technology seam failures.

## Key Files Modified

| File | Wave 1 | Wave 2 | Wave 3 |
|------|--------|--------|--------|
| `guardkit/orchestrator/quality_gates/coach_validator.py` | R1, R3 | R4 | R5 |
| `guardkit/orchestrator/autobuild.py` | R2 | — | R5 |

## File Conflict Analysis

- **Wave 1 and Wave 2** both modify `coach_validator.py` but touch different methods — no conflict
- **Wave 1 and Wave 3** both modify `coach_validator.py` and `autobuild.py` — Wave 3 depends on Wave 1's `_summarize_test_output()` changes
- **Wave 2 and Wave 3** are independent (different methods in `coach_validator.py`)

## Verification

After all three waves:
1. Run existing test suite: `pytest tests/ -v --tb=short`
2. Run a test AutoBuild session with a DB-dependent task to verify:
   - Coach tests run via SDK Bash tool (check logs for "SDK Coach test run")
   - Stall detection fires within 5 turns if tests keep failing
   - Feedback includes error type and traceback information
   - Infrastructure failures produce actionable remediation options
