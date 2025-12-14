# CLAUDE.md Size Optimization

## Problem Statement

Claude Code displays a performance warning when loading GuardKit:

```
⚠ Large CLAUDE.md will impact performance (57.0k chars > 40.0k)
```

## Solution

Reduce CLAUDE.md from 57,821 chars to under 40,000 chars by:
1. Moving detailed content to existing docs/guides/
2. Consolidating duplicate sections
3. Using .claude/rules/ for conditional loading

## Phase 1 Tasks (Target: 39,384 chars)

| Task | Action | Savings |
|------|--------|---------|
| TASK-OPT-8085.1 | Move Core AI Agents to docs link | 4,696 chars |
| TASK-OPT-8085.2 | Move BDD Workflow to docs link | 4,240 chars |
| TASK-OPT-8085.3 | Consolidate duplicate Boundaries | 3,490 chars |
| TASK-OPT-8085.4 | Move Clarifying Questions to rules/ | 3,068 chars |
| TASK-OPT-8085.5 | Move Incremental Enhancement to docs link | 2,943 chars |

**Total savings**: 18,437 chars
**Result**: 39,384 chars (under 40k threshold)

## Execution Strategy

Tasks can be executed in parallel (no file conflicts between sections).

## Success Criteria

- [ ] CLAUDE.md under 40,000 characters
- [ ] No Claude Code performance warning
- [ ] All "See:" links point to valid docs
- [ ] No information loss (content moved, not deleted)

## Related

- Review: TASK-REV-BFC1
- Report: [.claude/reviews/TASK-REV-BFC1-review-report.md](../../../.claude/reviews/TASK-REV-BFC1-review-report.md)
