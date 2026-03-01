# Implementation Guide: Coach Test Discovery Fix (FEAT-CTD)

## Problem Statement

The AutoBuild Coach's independent test verification can stall when workspace/template test files are included in the pytest command. These files belong to different project contexts and fail at collection time, creating an unbreakable feedback loop that wastes API budget.

**Root Cause**: Four technology seam failures in the Coach test discovery → pytest CLI → classification → approval chain. See [review report](../../../.claude/reviews/TASK-REV-0E44-review-report.md) for full C4 analysis.

## Wave Execution Strategy

### Wave 1 (Parallel — 3 tasks)

These tasks have no interdependencies and can be executed simultaneously:

| Task | Title | Complexity | File |
|------|-------|------------|------|
| TASK-FIX-7F48 | Filter collect_ignore_glob paths from test discovery | 4 | `coach_validator.py` |
| TASK-FIX-DF44 | Add collection_error classification | 4 | `coach_validator.py` |
| TASK-FIX-3A01 | Improve feedback detail for Player | 2 | `coach_validator.py` |

**Note**: All three modify `coach_validator.py` but target different methods with no overlapping lines:
- TASK-FIX-7F48: `_detect_tests_from_results()` (lines 2569-2615) + new helper methods
- TASK-FIX-DF44: `_classify_test_failure()` (lines 2631-2719)
- TASK-FIX-3A01: `validate()` feedback construction (lines 717-729)

**Parallel execution is safe** — different method scopes with no shared state.

### Wave 2 (Sequential — 2 tasks)

| Task | Title | Complexity | Depends On |
|------|-------|------------|------------|
| TASK-FIX-1D70 | Expand conditional approval path | 3 | TASK-FIX-DF44 |
| TASK-FIX-7D71 | Remediate TASK-EVAL-009 and resume feature | 3 | TASK-FIX-7F48 |

- TASK-FIX-1D70 depends on TASK-FIX-DF44 because it handles the new `"collection_error"` classification
- TASK-FIX-7D71 depends on TASK-FIX-7F48 to prevent the same stall when resuming FEAT-4296

**TASK-FIX-1D70 and TASK-FIX-7D71 can run in parallel** within Wave 2.

## File Impact Summary

| File | Tasks | Lines Affected |
|------|-------|---------------|
| `guardkit/orchestrator/quality_gates/coach_validator.py` | 7F48, DF44, 1D70, 3A01 | ~2569-2719, ~689-695, ~717-729, ~2830-2884 |
| `.guardkit/features/FEAT-4296.yaml` | 7D71 | status fields |
| `tasks/backlog/eval-runner-gkvv/TASK-EVAL-009-graphiti-storage.md` | 7D71 | status field |

## Testing Strategy

All tasks target `guardkit/orchestrator/quality_gates/coach_validator.py`. Tests should go in `tests/orchestrator/quality_gates/test_coach_validator.py` (existing file) or a new focused test file.

**Key test scenarios**:
1. Workspace template test file excluded from Coach command (Fix 1)
2. Collection error correctly classified as `("collection_error", "high")` (Fix 2)
3. Collection error + all gates → conditional approval (Fix 3)
4. Collection error + failed gate → feedback (Fix 3)
5. Existing infrastructure path unchanged (Fix 3 regression)
6. Feedback includes error detail (Fix 4)

## Verification

After all fixes are implemented, verify the original failure scenario doesn't recur:
1. Create a task that generates workspace template tests
2. Run AutoBuild on it
3. Verify Coach either excludes the workspace tests (Fix 1) or conditionally approves (Fix 3)
4. Verify no stall occurs
