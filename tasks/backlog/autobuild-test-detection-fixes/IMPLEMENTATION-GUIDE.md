# Implementation Guide: AutoBuild Test Detection Fixes (FEAT-ABF)

## Parent Review

**TASK-REV-F3BE** — Analyse PostgreSQL DB integration autobuild stall

Full report: `.claude/reviews/TASK-REV-F3BE-review-report.md`

## Problem Summary

TASK-DB-003 (Implement User model schemas and CRUD) entered an unrecoverable stall after 6 turns because:

1. Checkpoint commits (`git add -A && git commit`) make test files invisible to git-based detection on subsequent turns
2. The SDK output override clobbers git-enriched file lists
3. `tests_written` is gated behind `if tests_info:` — never populated when Player skips `tests_info`
4. The fallback glob `tests/**/test_task_db_003*.py` doesn't match domain-named test files
5. The zero-test anomaly feedback provides no actionable guidance

## Execution Strategy

### Wave 1: Data Quality Fixes (Parallel)

These fix the upstream data that feeds into test detection. No dependencies between them.

| Task | Description | File | Effort |
|------|-------------|------|--------|
| TASK-ABF-001 | Fix `tests_written` conditional gate | `agent_invoker.py:1480-1492` | ~10 lines |
| TASK-ABF-002 | Fix output override to merge not replace | `agent_invoker.py:1568-1575` | ~15 lines |

**Parallel execution**: These tasks modify different sections of the same file (`agent_invoker.py`) but do not overlap. They can be executed in parallel using separate Conductor workspaces.

Suggested workspaces:
- `autobuild-test-detection-fixes-wave1-1` (TASK-ABF-001)
- `autobuild-test-detection-fixes-wave1-2` (TASK-ABF-002)

### Wave 2: Feedback and Fallback Improvements (Parallel)

These improve the Coach's ability to find and report on tests. Depend on Wave 1 for cleaner data.

| Task | Description | File | Effort |
|------|-------------|------|--------|
| TASK-ABF-003 | Actionable zero-test anomaly feedback | `coach_validator.py:1830-1837` | ~5 lines |
| TASK-ABF-004 | Cumulative git diff fallback | `coach_validator.py:1544-1611` | ~30 lines |

**Parallel execution**: These tasks modify different sections of `coach_validator.py` and do not overlap.

Suggested workspaces:
- `autobuild-test-detection-fixes-wave2-1` (TASK-ABF-003)
- `autobuild-test-detection-fixes-wave2-2` (TASK-ABF-004)

## Defense-in-Depth

Any ONE of the 4 fixes would have prevented the TASK-DB-003 stall. Together they provide layered protection:

```
Layer 1 (ABF-001): tests_written correctly populated → Coach sees test files exist
Layer 2 (ABF-002): git-enriched files survive → primary detection finds test files
Layer 3 (ABF-003): actionable feedback → Player fixes naming on next turn
Layer 4 (ABF-004): cumulative diff → Coach finds test files across checkpoints
```

## Regression Safety

All fixes have been analysed for regression impact:

| Task | Risk | Why Safe |
|------|------|----------|
| ABF-001 | Low | Aligns with direct mode behavior (already unconditional at line 1778-1784) |
| ABF-002 | Low | Union preserves all existing data, only adds; matches TASK-FIX-PIPELINE intent |
| ABF-003 | None | Text-only change; tests check `category`/`severity`, not description |
| ABF-004 | Low | Third fallback only; scoped to task lifetime via git history; scaffolding tasks never reach this path |

## Verification

After all 4 tasks are implemented:

1. Run existing test suite: `pytest tests/unit/test_coach_validator.py -v`
2. Run existing agent_invoker tests (if any)
3. Re-run FEAT-BA28 scenario (or equivalent `feature` task type) through autobuild
4. Verify TASK-DB-003 equivalent no longer stalls

## Files Modified

| File | Tasks |
|------|-------|
| `guardkit/orchestrator/agent_invoker.py` | ABF-001, ABF-002 |
| `guardkit/orchestrator/quality_gates/coach_validator.py` | ABF-003, ABF-004 |
