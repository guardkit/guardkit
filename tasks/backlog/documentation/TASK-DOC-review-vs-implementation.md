# Add Review vs Implementation Workflows Guide to MkDocs

**Priority**: Important
**Category**: Documentation Gap - Workflow Clarity
**Estimated Effort**: 2-3 hours

## Problem

CLAUDE.md has extensive coverage distinguishing `/task-review` from `/task-work` workflows, but README.md only mentions review workflow briefly. The MkDocs site likely lacks a clear comparison guide.

## Current State

**CLAUDE.md includes**:
- Clear distinction: implementation vs review workflows
- When to use each command
- Review modes (architectural, code-quality, decision, technical-debt, security)
- Review depth levels (quick, standard, comprehensive)
- Example review workflow with decision checkpoint
- Decision options ([A]ccept, [R]evise, [I]mplement, [C]ancel)

**MkDocs site**: Unclear comparison

## Acceptance Criteria

1. Create new page: `docs/workflows/review-vs-implementation.md`
2. Add to MkDocs navigation under "Task Review"
3. Content must include:
   - Implementation workflow (`/task-work`) overview
   - Review workflow (`/task-review`) overview
   - Decision matrix: when to use each
   - Review modes table with use cases
   - Review depth levels comparison
   - Complete example workflow for each
   - Decision checkpoint explanation
   - How review tasks can spawn implementation tasks
4. Add comparison table showing phases for each workflow

## Implementation Notes

- Extract from CLAUDE.md review workflow section
- Show side-by-side phase comparison
- Include scenario-based guidance
- Link to docs/workflows/task-review-workflow.md

## Scenarios Table

| Scenario | Command |
|----------|---------|
| "Implement feature X" | `/task-work` |
| "Should we implement X?" | `/task-review` |
| "Fix bug in X" | `/task-work` |
| "Review architecture of X" | `/task-review` |

## References

- CLAUDE.md (Review vs Implementation Workflows)
- docs/workflows/task-review-workflow.md
- installer/global/commands/task-review.md
