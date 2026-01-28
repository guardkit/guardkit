# Feature: Feature-Build Regression Fix

**Feature ID**: FEAT-FBR
**Parent Review**: [TASK-REV-FB](.claude/reviews/TASK-REV-FB-review-report.md)
**Created**: 2026-01-25

## Problem Statement

The `/feature-build` command crashes after successful task execution due to two code quality issues:

1. **Critical**: Missing `recovery_count` field in `TaskExecutionResult` dataclass causes `AttributeError`
2. **High**: Hardcoded `max_turns=50` ignores CLI `--max-turns` parameter

## Solution Approach

Fix both regressions with minimal, focused changes:

1. Add missing `recovery_count` field to `TaskExecutionResult` (P0)
2. Propagate `max_turns` parameter through the invoker chain (P1)

## Subtasks

| Task ID | Title | Priority | Wave |
|---------|-------|----------|------|
| TASK-FBR-001 | Add recovery_count field to TaskExecutionResult | Critical | 1 |
| TASK-FBR-002 | Propagate max_turns parameter to SDK invocation | High | 1 |

## Execution Strategy

Both tasks can be executed in parallel (Wave 1) as they modify different code paths.

## Success Criteria

- [ ] Feature-build completes without `AttributeError`
- [ ] CLI `--max-turns` parameter is respected in SDK invocation
- [ ] All existing tests pass
- [ ] Regression scenario from error log works correctly
