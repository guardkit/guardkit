---
id: TASK-REV-FB
title: Analyze feature-build regression and max_turns parameter issue
status: review_complete
created: 2025-01-25T12:00:00Z
updated: 2026-01-25T15:30:00Z
priority: high
tags: [regression, feature-build, bug-analysis, sdk-integration]
task_type: review
complexity: 5
review_mode: code-quality
review_depth: standard
review_results:
  mode: code-quality
  depth: standard
  score: 55
  findings_count: 2
  recommendations_count: 4
  decision: implement
  report_path: .claude/reviews/TASK-REV-FB-review-report.md
  completed_at: 2026-01-25T15:30:00Z
implementation_tasks:
  - TASK-FBR-001
  - TASK-FBR-002
implementation_folder: tasks/backlog/feature-build-regression-fix/
---

# Task: Analyze feature-build regression and max_turns parameter issue

## Description

Investigate a regression in the `/feature-build` command where the feature orchestrator fails with an AttributeError after successfully completing task execution. Additionally, investigate why the `--max-turns 10` CLI parameter is being overridden to `50` by the SDK integration layer.

## Issues Identified

### Issue 1: Missing `recovery_count` Attribute (CRITICAL)

**Error Location**: `guardkit/orchestrator/feature_orchestrator.py:937`

**Error Message**:
```
AttributeError: 'TaskExecutionResult' object has no attribute 'recovery_count'
```

**Context**:
- The error occurs in `_wave_phase` method
- Line 937: `recovered = sum(1 for r in wave_result.results if r.recovery_count > 0)`
- This is a regression since the same feature type ran successfully in a previous session (see `finally_success.md`)

**Root Cause Hypothesis**:
- The `TaskExecutionResult` dataclass/class is missing the `recovery_count` field
- OR there's a code path that creates `TaskExecutionResult` without this field
- OR a recent refactor added this field usage without updating all result creation paths

### Issue 2: max_turns Parameter Override (MEDIUM)

**Evidence from logs**:
```
# CLI shows max_turns=10 properly received:
INFO:guardkit.cli.autobuild:Starting feature orchestration: FEAT-FHE (max_turns=10, ...)

# But SDK invocation shows 50:
INFO:guardkit.orchestrator.agent_invoker:[TASK-FHE-001] Max turns: 50
```

**Location**: `guardkit/orchestrator/agent_invoker.py`

**Root Cause Hypothesis**:
- The `agent_invoker` is using a hardcoded default of 50 for SDK invocations
- The `max_turns` parameter is not being passed from `feature_orchestrator` through to `agent_invoker`
- OR there's a separate SDK-specific max_turns setting that overrides the feature-level setting

## Acceptance Criteria

- [ ] Identify the exact code path causing the `recovery_count` AttributeError
- [ ] Determine if this is a missing field or incorrect object type
- [ ] Find where the max_turns parameter chain is broken
- [ ] Verify if the successful run used a different code version
- [ ] Document the regression introduction point (git commit if possible)
- [ ] Provide fix recommendations for both issues

## Files to Investigate

1. `guardkit/orchestrator/feature_orchestrator.py` - Line 937 and wave_phase method
2. `guardkit/orchestrator/autobuild.py` - TaskExecutionResult definition
3. `guardkit/orchestrator/agent_invoker.py` - max_turns parameter handling
4. `guardkit/cli/autobuild.py` - CLI parameter parsing

## Evidence Files

- Error output: `docs/reviews/feature-build/orchestrator_error.md`
- Successful run: `docs/reviews/feature-build/finally_success.md`

## Review Mode

Mode: code-quality
Depth: standard

## Notes

This appears to be a regression introduced after the successful run documented in `finally_success.md`. The feature completed successfully for TASK-FHE-001 (Coach approved) before the error occurred during wave result aggregation.
