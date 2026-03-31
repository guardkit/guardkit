---
id: TASK-REV-93E1
title: "Analyse FEAT-E880 task type classification and test glob pattern failures"
status: review_complete
created: 2026-02-11T18:00:00Z
updated: 2026-02-11T18:00:00Z
priority: high
tags: [autobuild, quality-gates, zero-test-anomaly, task-type-detection, test-glob, regression-analysis]
task_type: review
complexity: 7
---

# Task: Analyse FEAT-E880 Task Type Classification and Test Glob Pattern Failures

## Description

FEAT-E880 (PostgreSQL Database Integration) failed across two runs (25 + 50 max-turns) with TASK-DB-006 ("Integrate database health check") stuck in an infinite rejection loop. The task consumed 35+ adversarial turns without ever being approved. This review must deeply analyse the root causes, assess proposed fixes against the full history of zero-test anomaly and quality gate changes, and produce a regression-safe fix plan.

## Context

### The Failure Pattern

TASK-DB-006 alternates between two failure modes every turn:

1. **ImportError in conftest** (odd turns): Coach runs independent tests and hits `ImportError while loading conftest`. Tests exist at `tests/health/test_router.py` and `tests/health/test_task_db_006_database_health.py` but conftest imports fail (likely async DB session dependencies).

2. **Zero-test anomaly** (even turns): After the Player "fixes" things, Coach can't find task-specific tests — the glob pattern `tests/test_task_db_006*.py` only searches flat `tests/` but Player creates tests under `tests/health/`. With `tests_written=[]` in the Player report, the zero-test anomaly fires with `severity=error` (blocking, because task_type=feature).

### Preliminary Root Cause Identification

Three interacting issues identified in conversation analysis:

1. **Task type misclassification**: "Integrate database health check" classified as `feature` (default) because no keywords match. The `feature` profile enforces `tests_required=True` and `zero_test_blocking=True`. This task is an integration/wiring task that modifies existing health endpoints — arguably closer to `scaffolding` or a new `integration` type.

2. **Test glob blind spot**: The pattern at `coach_validator.py:1354` is `tests/test_{prefix}*.py` (flat directory only). Many real projects use nested test directories (`tests/health/`, `tests/api/`, `tests/unit/`). The glob does NOT recurse.

3. **Direct mode `tests_written` inconsistency**: On some turns, direct mode Player reports `tests_written: []` even when test files were created/modified, because `_detect_tests_from_results()` (the primary path) relies on `files_created`/`files_modified` from the Player's self-report, which isn't always populated.

### Key Files

| File | Relevance |
|------|-----------|
| `guardkit/lib/task_type_detector.py` | Keyword-based task type classification |
| `guardkit/models/task_types.py` | TaskType enum + QualityGateProfile definitions |
| `guardkit/orchestrator/quality_gates/coach_validator.py:1288-1443` | Test glob pattern, `_detect_test_command()`, `_detect_tests_from_results()` |
| `guardkit/orchestrator/quality_gates/coach_validator.py:1526-1618` | `_check_zero_test_anomaly()` |
| `guardkit/orchestrator/agent_invoker.py:2208-2285` | `_write_direct_mode_results()` |
| `installer/core/commands/feature-plan.md:1248-1267` | task_type assignment rules |
| `installer/core/lib/implement_orchestrator.py:260` | `detect_task_type()` call site |

### Prior Fix Chain (MUST NOT Regress)

This review sits at the intersection of multiple prior fix chains. Each must be explicitly analysed:

1. **TASK-FIX-CEE8a** (direct mode test count): `_write_direct_mode_results()` now derives `tests_passed_count` from `tests_written` list when `tests_passed=True` and no explicit count. Changing how `tests_written` is populated could break this.

2. **TASK-FIX-CEE8b** (zero-test anomaly defense-in-depth): `_check_zero_test_anomaly()` now accepts `independent_tests` param with early return when `tests_passed=True` AND `test_command != "skipped"`. Changing the anomaly check conditions requires careful analysis of all code paths.

3. **TASK-FIX-ACA7a** (project-wide pass bypass): After the independent-tests early return, added check for `tests_written==[]` + `independent_tests.test_command=="skipped"`. This specifically catches the case where tests_written is empty AND no independent tests found.

4. **TASK-FIX-ACA7b** (criteria verification): Switched from legacy text matching to ID-based matching via `completion_promises`. Direct mode writers now include `completion_promises`.

5. **TASK-FIX-64EE** (null quality gates): `verify_quality_gates()` falls through when `all_passed: null`. The zero-test anomaly intentionally does NOT fire when `all_passed is None`.

6. **TASK-AQG-002** (zero-test blocking): `QualityGateProfile.zero_test_blocking` field. FEATURE and REFACTOR profiles set `True`.

7. **TASK-REV-FB01** (feature-build timeout): Player report not written + Coach validator path bug + timeout. The report-writing mechanism is now different — must verify fix doesn't reintroduce.

## Acceptance Criteria

### Analysis Phase

- [ ] AC-001: Reproduce and document the exact failure cycle for TASK-DB-006 from the log file (`docs/reviews/fastapi_test/db_max_turns_1.md`), mapping each turn to the specific failure mode (conftest ImportError vs zero-test anomaly)
- [ ] AC-002: Trace the complete code path for task type assignment from feature-plan through to Coach profile selection, identifying where "Integrate database health check" falls through to `feature`
- [ ] AC-003: Trace the test glob pattern construction and identify all projects where nested test directories would cause the same blind spot
- [ ] AC-004: Analyse the direct mode `tests_written` population path vs task-work delegation path, documenting when/why `tests_written` can be empty despite test files existing
- [ ] AC-005: Map each proposed fix against all 7 prior fix chains, documenting regression risk per fix

### Fix Assessment Phase

- [ ] AC-006: Evaluate three options for task type improvement: (A) new INTEGRATION TaskType, (B) add integration keywords to SCAFFOLDING, (C) expand keyword set for existing types — with pros/cons for each, including impact on quality gate strictness
- [ ] AC-007: Evaluate the recursive glob fix (`tests/**/test_{prefix}*.py`) for performance impact on large repos and correctness (Python glob `**` behavior with `Path.glob()`)
- [ ] AC-008: Assess whether the conftest ImportError is a task-type issue, a test isolation issue, or a missing test infrastructure dependency — and whether it can be resolved by task-type change alone
- [ ] AC-009: Produce a prioritised fix plan with explicit "must not regress" constraints per fix

### Output

- [ ] AC-010: Generate structured review report at `.claude/reviews/TASK-REV-93E1-review-report.md`

## Reference Reports

- `.claude/reviews/TASK-REV-FB01-timeout-analysis-report.md` — Feature-build timeout root cause (Player report + Coach path bugs)
- `.claude/reviews/TASK-REV-CEE8-review-report.md` — Direct mode zero-test anomaly false positive (dual bug)
- `.claude/reviews/TASK-REV-ACA7-review-report.md` — FEAT-CEE8 run 3 validation (CEE8a/CEE8b fixes + ACA7a/ACA7b new bugs)
- `docs/reviews/fastapi_test/db_max_turns_1.md` — The raw FEAT-E880 execution log (two runs)

## Implementation Notes

This is a review-only task. The output is an analysis report with a fix plan. Implementation tasks should be created from the findings.
