# Review Complete

This directory contains review tasks that have completed their analysis phase.

## Task State: REVIEW_COMPLETE

Review tasks move here after executing `/task-review` and receiving human acceptance of the findings.

## Possible Next Actions

From `REVIEW_COMPLETE`, tasks can:

1. **Archive** - Accept findings and mark as completed
2. **Create Implementation** - Generate new implementation task based on recommendations
3. **Re-review** - Run additional review with different mode/depth

## State Transitions

```
IN_PROGRESS → REVIEW_COMPLETE (after /task-review completes)
REVIEW_COMPLETE → COMPLETED (archive findings)
REVIEW_COMPLETE → Creates new BACKLOG task (for implementation)
```

## Example Task Metadata

```yaml
---
id: TASK-XXX
title: Review authentication architecture
status: review_complete
task_type: review
review_mode: architectural
review_depth: standard
review_results:
  score: 72
  findings_count: 8
  recommendations_count: 5
  decision: refactor
  report_path: .claude/reviews/TASK-XXX-review-report.md
  completed_at: 2025-01-20T16:30:00Z
---
```
