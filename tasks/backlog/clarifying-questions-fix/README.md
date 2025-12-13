# Feature: Clarifying Questions Integration Fix

**Source Review**: TASK-REV-0614
**Created**: 2025-12-13
**Priority**: High

## Problem Statement

The clarifying questions feature was designed and documented but never integrated into the actual Python orchestrators. When users run `/feature-plan` or `/task-review` with ambiguous input, no clarification questions are asked despite documentation stating they should be.

## Root Cause

`task_review_orchestrator.py` does not import or call any functions from the `lib/clarification/` module. The clarification code exists and passes unit tests, but is never executed in the production workflow.

## Solution

Wire the existing clarification module into the orchestrators:
1. Add Phase 1.5 (Clarification) to task-review orchestrator
2. Create explicit feature-plan orchestrator for enforcement
3. Update integration tests to test real orchestrator paths
4. Add end-to-end smoke test

## Subtasks

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| TASK-CLQ-FIX-001 | Critical | 2-3h | None |
| TASK-CLQ-FIX-002 | High | 2-3h | 001 |
| TASK-CLQ-FIX-003 | Medium | 1-2h | 001 |
| TASK-CLQ-FIX-004 | Medium | 1h | 001 |

## Execution Strategy

**Wave 1** (Sequential - Core fix):
- TASK-CLQ-FIX-001: Integrate clarification into task-review orchestrator

**Wave 2** (Parallel - Extensions):
- TASK-CLQ-FIX-002: Create feature-plan orchestrator
- TASK-CLQ-FIX-003: Update integration tests
- TASK-CLQ-FIX-004: Add smoke test

## Success Criteria

- [ ] `/task-review TASK-XXX --mode=decision` asks clarification questions
- [ ] `/feature-plan "ambiguous description"` asks clarification questions
- [ ] `--no-questions` flag skips clarification
- [ ] Complexity gating works (simple tasks skip, complex tasks ask)
- [ ] Answers persist to task frontmatter

## Related Documentation

- [Review Report](.claude/reviews/TASK-REV-0614-review-report.md)
- [Feature Plan Command](installer/core/commands/feature-plan.md)
- [Task Review Command](installer/core/commands/task-review.md)
- [Clarification Module](installer/core/commands/lib/clarification/)
