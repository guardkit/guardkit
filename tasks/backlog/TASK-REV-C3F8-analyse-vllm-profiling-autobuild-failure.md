---
id: TASK-REV-C3F8
title: Analyse vllm-profiling AutoBuild failure (CancelledError)
status: review_complete
task_type: review
created: 2026-03-07T10:00:00Z
updated: 2026-03-07T10:00:00Z
priority: high
tags: [autobuild, bug-analysis, feature-orchestrator, async, vllm-profiling]
complexity: 4
review_results:
  mode: root-cause-analysis
  depth: standard
  findings_count: 7
  recommendations_count: 7
  report_path: .claude/reviews/TASK-REV-C3F8-review-report.md
  completed_at: 2026-03-07T12:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Analyse vllm-profiling AutoBuild failure (CancelledError)

## Description

Analyse the AutoBuild feature orchestration failure captured in `docs/reviews/vllm-profiling/anthropic_run_1.md`. The run executed feature FEAT-1637 (FastAPI Base Project, 7 tasks across 5 waves) and failed in the final wave (Wave 5) with an unhandled `CancelledError` in the parallel wave execution path.

## Source Material

- **Run log**: `docs/reviews/vllm-profiling/anthropic_run_1.md`
- **Feature**: FEAT-1637 (FastAPI Base Project)
- **Target repo**: vllm-profiling
- **Error location**: `guardkit/orchestrator/feature_orchestrator.py:1564`

## Failure Summary

### Root Error
```
AttributeError: 'CancelledError' object has no attribute 'success'
```

At `feature_orchestrator.py:1564`:
```python
status = "success" if result.success else "failed"
```

The `result` variable holds a `CancelledError` exception instead of a task result object because the parallel wave execution did not properly catch task cancellation.

### Context
- **Wave 5** contained 2 tasks: TASK-FBP-006 (integration tests) and TASK-FBP-007 (quality gates)
- TASK-FBP-006 completed successfully (approved, 1 turn)
- TASK-FBP-007 was still executing (660s+ elapsed) when the failure occurred
- It appears TASK-FBP-007 may have been cancelled or timed out while TASK-FBP-006 completed
- The `_execute_wave_parallel` method doesn't handle `CancelledError` when collecting task results

### Additional Observations
- **Waves 1-4**: All completed successfully (tasks FBP-001 through FBP-005)
- **Independent test verification**: Failed with `collection_error` on tasks FBP-002, FBP-003, FBP-004, FBP-005 — all were conditionally approved
- **Documentation constraint**: TASK-FBP-001 violated documentation level constraint (9 files vs 2 max for minimal)

## Review Objectives

1. **Root cause analysis**: Determine exactly why `CancelledError` was raised for TASK-FBP-007
   - Was it a timeout? (task_timeout=2400s, but task was only at ~660s)
   - Was it cancelled due to a sibling task completing?
   - Was it a Python asyncio cancellation from signal handling?

2. **Error handling gap**: Analyse the `_execute_wave_parallel` method for proper exception handling
   - `asyncio.gather` with `return_exceptions=True` should return exceptions as results
   - If exceptions are returned, the result processing code must check `isinstance(result, Exception)`

3. **Independent test collection errors**: Assess whether the repeated `collection_error` failures across 4 tasks indicate a systemic issue with the test environment setup in the worktree

4. **Recommendations**: Propose fixes for:
   - Handling `CancelledError` and other exceptions in wave result processing
   - Improving timeout/cancellation visibility in logs
   - Addressing the independent test collection errors pattern

## Acceptance Criteria

- [ ] Root cause of `CancelledError` identified with evidence from logs
- [ ] Error handling gap in `_execute_wave_parallel` documented
- [ ] Independent test collection error pattern assessed
- [ ] Fix recommendations provided with specific code locations
- [ ] Severity and priority assessment for each finding

## Implementation Notes

Key files to review:
- `guardkit/orchestrator/feature_orchestrator.py` (lines ~1550-1620, `_execute_wave_parallel`)
- `guardkit/orchestrator/quality_gates/coach_validator.py` (conditional approval logic)
- `guardkit/orchestrator/agent_invoker.py` (task timeout handling)

## Test Execution Log
[Automatically populated by /task-work]
