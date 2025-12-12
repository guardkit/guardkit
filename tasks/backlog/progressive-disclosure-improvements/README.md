# Progressive Disclosure Improvements

## Origin

Created from review task TASK-REV-PD01 which verified the progressive disclosure and Claude rules structure implementations.

## Problem Statement

While the core progressive disclosure and rules structure implementations are working correctly (overall score 8.5/10), the review identified three minor improvements that would enhance the system further.

## Solution Approach

Three focused improvement tasks to address:
1. Add path-specific loading to guidance files
2. Enhance xunit-nsubstitute-testing-specialist ASK section
3. Enrich pattern file content with codebase examples

## Subtasks

| Task ID | Title | Priority | Mode |
|---------|-------|----------|------|
| TASK-PDI-001 | Add paths frontmatter to guidance files | Low | direct |
| TASK-PDI-002 | Enhance xunit testing specialist ASK section | Low | direct |
| TASK-PDI-003 | Enrich pattern files with codebase examples | Medium | task-work |

## Execution Strategy

**Wave 1** (Parallel - Low effort):
- TASK-PDI-001: Add paths frontmatter
- TASK-PDI-002: Enhance ASK section

**Wave 2** (Sequential - Requires template context):
- TASK-PDI-003: Pattern file enrichment

## Review Reference

- Review Report: `.claude/reviews/TASK-REV-PD01-review-report.md`
- Review Task: `tasks/backlog/TASK-REV-PD01-verify-progressive-disclosure-output.md`
