# Progressive Disclosure Improvements

## Origin

Created from review task TASK-REV-PD01 which verified the progressive disclosure and Claude rules structure implementations.

## Problem Statement

While the core progressive disclosure and rules structure implementations are working correctly (overall score 8.5/10), the review identified two technology-agnostic improvements to the core commands that would enhance the system further.

## Solution Approach

Two focused improvement tasks to address core command behavior:
1. Add path-specific loading to guidance files (template-create improvement)
2. Enrich pattern file content with codebase examples (template-create improvement)

**Note**: Template-specific agent improvements (e.g., xunit ASK section) are not tracked here - they will be addressed when `/template-create` and `/agent-enhance` are re-run on specific codebases.

## Subtasks

| Task ID | Title | Priority | Mode |
|---------|-------|----------|------|
| TASK-PDI-001 | Add paths frontmatter to guidance files | Low | direct |
| TASK-PDI-003 | Enrich pattern files with codebase examples | Medium | task-work |

## Execution Strategy

**Wave 1** (Quick Win):
- TASK-PDI-001: Update template-create to add paths frontmatter to guidance files

**Wave 2** (Requires planning):
- TASK-PDI-003: Update template-create to extract pattern examples from source codebase

## Review Reference

- Review Report: `.claude/reviews/TASK-REV-PD01-review-report.md`
- Review Task: `tasks/backlog/TASK-REV-PD01-verify-progressive-disclosure-output.md`
