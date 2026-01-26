---
id: TASK-REV-BL01
title: Cleanup tasks/backlog and archive completed tasks and features
status: review_complete
created: 2025-01-26T09:00:00Z
updated: 2026-01-26T14:30:00Z
review_results:
  mode: architectural
  depth: standard
  score: 55
  findings_count: 6
  recommendations_count: 5
  decision: refactor
  report_path: .claude/reviews/TASK-REV-BL01-review-report.md
  completed_at: 2026-01-26T14:30:00Z
priority: normal
tags: [housekeeping, cleanup, archive]
task_type: review
complexity: 5
---

# Task: Cleanup tasks/backlog and archive completed tasks and features

## Description

Review the `tasks/` directory structure and perform housekeeping activities including:
- Identifying and archiving completed tasks that remain in `in_review` status
- Identifying orphaned feature directories in `backlog/` that are no longer active
- Consolidating or removing duplicate review tasks
- Cleaning up stale tasks that are no longer relevant
- Ensuring proper task status transitions

## Scope

### Areas to Review

1. **tasks/in_review/** (63+ files)
   - Identify tasks that should be moved to `completed/`
   - Identify tasks stuck in review that need attention
   - Check for review tasks that have been addressed

2. **tasks/in_progress/** (11 files)
   - Verify these tasks are actively being worked on
   - Identify stale tasks that should be moved to `backlog/` or `blocked/`

3. **tasks/backlog/** (90+ items including feature directories)
   - Review feature directories for completeness/relevance:
     - `arch-score-fix/`
     - `autobuild-task-work-delegation/`
     - `beads-integration/`
     - `block-research-fidelity/`
     - `claude-md-reduction/`
     - `coach-security-integration/`
     - `context-sensitive-coach/`
     - `design-url-integration/`
     - `direct-mode-race-fix/`
     - `documentation/`
     - `fastmcp-python-template/`
     - `feature-build/` (and related: feature-build-*)
     - `feature-complete/`
     - `graphiti-integration/`
     - `mcp-typescript-template/`
     - `progressive-disclosure/`
     - `provenance-intensity/`
     - `quality-gates-integration/`
     - `sdk-delegation-fix/`
     - `sdk-error-handling/`
     - `testing/`
   - Identify duplicate or overlapping review tasks (many TASK-REV-FB* tasks)
   - Archive or consolidate redundant tasks

4. **tasks/blocked/** (2 files)
   - Review if blockers are still valid
   - Determine if tasks should be unblocked or closed

## Acceptance Criteria

- [ ] All tasks with `status: completed` in frontmatter are in `tasks/completed/`
- [ ] No stale tasks remain in `in_progress/` (tasks not touched in 30+ days)
- [ ] Duplicate review tasks are consolidated with clear cross-references
- [ ] Feature directories with all completed subtasks are archived
- [ ] Blocked tasks have documented reasons or are moved to appropriate status
- [ ] Summary report of actions taken is created

## Deliverables

1. **Cleanup Report** - Document all changes made
2. **Consolidated Review Tasks** - Merge related TASK-REV-FB* tasks where appropriate
3. **Archive Summary** - List of what was archived and why
4. **Updated Task Status** - Ensure all task statuses match their directory location

## Notes

- This is a review/housekeeping task, not an implementation task
- Consider using `/task-review` workflow for the analysis phase
- Some tasks may need human decision on whether to archive vs keep
- Preserve git history by using `git mv` for file moves

## Related Tasks

- Many TASK-REV-FB* tasks in backlog appear related to feature-build debugging
- Security tasks (TASK-SEC-*) in in_review may be related to `coach-security-integration/`
- Progressive disclosure tasks may be consolidatable

## Estimated Effort

- Review: 2-3 hours
- Cleanup actions: 1-2 hours
- Documentation: 30 minutes
