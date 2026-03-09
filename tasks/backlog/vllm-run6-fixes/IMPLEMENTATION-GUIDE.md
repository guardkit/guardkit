# Implementation Guide: vLLM Run 6 Fixes (FEAT-81DD)

**Parent Review**: TASK-REV-35DC
**Feature ID**: FEAT-81DD

## Problem Statement

vLLM AutoBuild Run 6 succeeded (7/7, 285m) but revealed structural issues:
1. FBP-007 succeeded via non-deterministic state recovery after budget starvation
2. SDK turn inflation (50-174%) caused by slim protocol introduced in TASK-VOPT-001
3. Wave assignment algorithm has no awareness of `max_parallel` serialization risk
4. Previous review (TASK-REV-5E1F) contains factual errors about remaining_budget

## Execution Strategy

### Wave 1: Immediate Fixes (3 tasks, parallel)

These tasks have no interdependencies and can execute concurrently:

| Task | Method | Effort | Description |
|------|--------|--------|-------------|
| TASK-VR6-3B1F | direct | 15min | Move FBP-007 to own wave in FEAT-1637 YAML |
| TASK-VR6-DAF4 | task-work | 2-3h | Add max_parallel-aware wave separation to parallel_analyzer.py |
| TASK-VR6-5497 | direct | 15min | Correct TASK-REV-5E1F report errors |

### Wave 2: Investigation (1 task, depends on Wave 1)

| Task | Method | Effort | Description |
|------|--------|--------|-------------|
| TASK-VR6-65A0 | direct (review) | 1-2h | Investigate slim protocol turn inflation; recommend Run 7 config |

**Why Wave 2?** The investigation should account for the Wave 1 fixes (especially wave separation) when making recommendations. Session resume (TASK-RFX-B20B from commit 821dfda5) may also affect turn counts.

## Compatibility with Commit 821dfda5

All tasks verified compatible with `821dfda5` ("Improves turn-based autonomy & runtime verification"):

| Task | Overlap with 821dfda5 | Risk |
|------|----------------------|------|
| TASK-VR6-3B1F | None (YAML change only) | None |
| TASK-VR6-DAF4 | None (`parallel_analyzer.py` untouched) | None |
| TASK-VR6-65A0 | Positive interaction: session resume may mitigate turn inflation | None |
| TASK-VR6-5497 | None (review report correction) | None |

## Key Code References

| File | Lines | Relevance |
|------|-------|-----------|
| `installer/core/lib/parallel_analyzer.py` | 178-296 | TASK-VR6-DAF4: Wave assignment algorithm |
| `guardkit/orchestrator/agent_invoker.py` | 1134-1199 | Context: remaining_budget flow |
| `guardkit/orchestrator/agent_invoker.py` | 4028-4035 | TASK-VR6-65A0: Protocol selection logic |
| `guardkit/orchestrator/prompts/autobuild_execution_protocol.md` | 1-573 | TASK-VR6-65A0: Full protocol |
| `guardkit/orchestrator/prompts/autobuild_execution_protocol_slim.md` | 1-131 | TASK-VR6-65A0: Slim protocol |
| `.claude/reviews/TASK-REV-5E1F-review-report.md` | - | TASK-VR6-5497: Report to correct |

## Success Criteria

1. **Run 7 reliability**: FBP-007 completes with full budget (no starvation)
2. **Automated prevention**: `/feature-plan` generates single-task waves when `max_parallel=1`
3. **Accurate records**: TASK-REV-5E1F report corrected
4. **Informed decision**: Slim protocol recommendation based on data
