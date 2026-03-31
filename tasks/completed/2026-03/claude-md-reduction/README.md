# Feature: Reduce CLAUDE.md Size Below 40k Limit

## Problem Statement

Claude Code displays a performance warning when CLAUDE.md exceeds 40,000 characters:
```
Large CLAUDE.md will impact performance (53.2k chars > 40.0k)
```

Current state: 55,546 chars (38.9% over limit)

## Solution Approach

Leverage GuardKit's existing progressive disclosure and rules/ structure to move detailed documentation out of the root CLAUDE.md while maintaining full functionality.

## Subtasks

| Task | Description | Mode | Wave |
|------|-------------|------|------|
| TASK-CMD1-001 | Create rules/autobuild.md | direct | 1 |
| TASK-CMD1-002 | Create rules/hash-based-ids.md | direct | 1 |
| TASK-CMD1-003 | Consolidate .claude/CLAUDE.md | direct | 1 |
| TASK-CMD1-004 | Condense workflow sections | direct | 2 |
| TASK-CMD1-005 | Condense FAQ and examples | direct | 2 |
| TASK-CMD1-006 | Validate final character count | task-work | 3 |

## Expected Outcome

- Root CLAUDE.md: 55,546 → ~30,850 chars (-44%)
- Total context: 63,963 → ~35,750 chars (below 40k target)
- Performance warning eliminated

## Review Report

See: [.claude/reviews/TASK-REV-CMD1-review-report.md](../../../.claude/reviews/TASK-REV-CMD1-review-report.md)
