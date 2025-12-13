# Feature: Claude Directory Improvements

## Overview

Implementation tasks to address gaps identified in TASK-REV-79E0 code quality review of the GuardKit `.claude/` directory.

**Review Score**: 7.5/10 (Good, with improvement opportunities)
**Target Score**: 8.5-9/10

## Source

This feature was auto-generated from the `[I]mplement` decision in `/task-review TASK-REV-79E0 --mode=code-quality`.

**Review Report**: [.claude/reviews/TASK-REV-79E0-review-report.md](../../../.claude/reviews/TASK-REV-79E0-review-report.md)

## Problem Statement

The TASK-STE-007 implementation achieved 89% of TASK-STE-001 recommendations. The remaining gaps are:

1. **Missing orchestrators.md** - Documented but not created
2. **dataclasses.md path too broad** - `**/*.py` matches all Python files
3. **debugging-specialist.md too large** - 1,140 lines, should be split
4. **No extended agent files** - Progressive disclosure not fully implemented

## Subtasks

| Task ID | Title | Mode | Wave | Priority |
|---------|-------|------|------|----------|
| TASK-CDI-001 | Create orchestrators.md pattern file | direct | 1 | High |
| TASK-CDI-002 | Narrow dataclasses.md path pattern | direct | 1 | High |
| TASK-CDI-003 | Split debugging-specialist.md | task-work | 1 | High |
| TASK-CDI-004 | Fix testing.md path overlap | direct | 2 | Medium |
| TASK-CDI-005 | Update review task to COMPLETED | direct | 2 | Low |

## Dependencies

- All tasks depend on completed TASK-REV-79E0 review (this feature)
- Wave 1 tasks can run in parallel
- Wave 2 tasks depend on Wave 1 completion

## Acceptance Criteria

- [ ] All high-priority recommendations implemented
- [ ] Rules structure has no overly broad path patterns
- [ ] Progressive disclosure implemented for large agent files
- [ ] Re-review scores 8.5+/10

## Estimated Effort

| Wave | Tasks | Parallel? | Effort |
|------|-------|-----------|--------|
| 1 | 3 | Yes | 2 hours |
| 2 | 2 | Yes | 30 min |
| **Total** | **5** | - | **2.5 hours** |
