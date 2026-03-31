---
id: TASK-REV-BC41
title: Backlog cleanup — archive completed tasks and review superseded items
status: review_complete
created: 2026-03-30T12:30:00Z
updated: 2026-03-30T18:00:00Z
priority: high
tags: [review, backlog, cleanup, housekeeping]
task_type: review
review_mode: decision
complexity: 5
depends_on: []
review_results:
  mode: decision
  depth: standard
  findings_count: 6
  recommendations_count: 3
  items_archived: 121
  backlog_before: 293
  backlog_after: 172
  reduction_percent: 41
  report_path: .claude/reviews/TASK-REV-BC41-review-report.md
  completed_at: 2026-03-30T18:00:00Z
---

# Task: Backlog Cleanup — Archive Completed Tasks and Review Superseded Items

## Description

The `tasks/backlog/` directory has accumulated 160+ task files and 100+ feature subdirectories. Many of these represent completed work that was never moved to `tasks/completed/`, review tasks whose findings have already been actioned, or tasks that have been superseded by subsequent work.

This review will:
1. Identify tasks/features that are actually completed and should be archived
2. Present decision checkpoints for tasks that may have been superseded
3. Recommend bulk cleanup actions
4. Leave only genuinely actionable backlog items

## Review Scope

### 1. Completed Task Detection
- Cross-reference backlog tasks against `tasks/completed/` for related work
- Check git history for implementation evidence
- Identify review tasks (TASK-REV-*) whose findings have been actioned

### 2. Superseded Task Detection
- Identify tasks made redundant by later work (e.g., earlier fix attempts superseded by broader refactors)
- Identify feature directories where all subtasks are complete
- Flag tasks referencing infrastructure/tooling that has changed (e.g., Graphiti, vLLM configs)

### 3. Decision Checkpoints
For each category of potentially superseded tasks, present:
- What the task aimed to do
- Evidence it's been superseded or is still relevant
- Recommendation: ARCHIVE, KEEP, or MERGE with another task

### 4. Feature Directory Cleanup
- Identify feature subdirectories that can be archived (all work complete)
- Identify feature subdirectories with mixed status (some done, some remaining)

## Acceptance Criteria

- [x] All genuinely completed tasks identified and archived (61 tasks)
- [x] Superseded tasks reviewed with decision checkpoints (6 checkpoints presented)
- [x] Feature directories assessed for archival (111 dirs assessed, 59 archived/deleted)
- [x] Backlog reduced to only actionable items (293 → 172, 41% reduction)
- [x] Review report generated (.claude/reviews/TASK-REV-BC41-review-report.md)

## Suggested Review Approach

```bash
/task-review TASK-REV-BC41 --mode=decision --depth=standard
```
