---
id: TASK-CL-005
title: Remove duplicate task files
status: backlog
created: 2026-01-26T14:45:00Z
updated: 2026-01-26T14:45:00Z
priority: medium
tags: [cleanup, housekeeping]
task_type: implementation
complexity: 2
parent_review: TASK-REV-BL01
feature_id: FEAT-CLEANUP
implementation_mode: direct
parallel_group: wave-2
depends_on: [TASK-CL-001]
---

# Task: Remove duplicate task files

## Description

Remove 2 duplicate task files that exist in multiple directories. Keep the version in the directory matching the current status.

## Actions Required

### TASK-FBP-003 (duplicate in in_progress and in_review)

The in_review version has status `in_review`, the in_progress version has status `in_progress`.

**Decision**: Keep in_review version (more recent timestamp), remove in_progress duplicate.

```bash
rm tasks/in_progress/TASK-FBP-003-integration-tests.md
```

### TASK-REV-FMT (duplicate in in_review and backlog)

The in_review version has status `review_complete`, the backlog version appears to be a draft.

**Decision**: Keep in_review version (will be moved to review_complete by TASK-CL-001), remove backlog duplicate.

```bash
rm tasks/backlog/TASK-REV-FMT-feature-build-analysis.md
```

## Duplicate Analysis

| Task ID | Location 1 | Status 1 | Location 2 | Status 2 | Keep |
|---------|------------|----------|------------|----------|------|
| TASK-FBP-003 | in_progress/ | in_progress | in_review/ | in_review | in_review/ |
| TASK-REV-FMT | backlog/ | (draft) | in_review/ | review_complete | in_review/ |

## Acceptance Criteria

- [ ] TASK-FBP-003 exists only in tasks/in_review/
- [ ] TASK-REV-FMT exists only in tasks/review_complete/ (after TASK-CL-001 moves it)
- [ ] No duplicate task IDs across directories

## Verification Commands

```bash
# Should return 1 result each
find tasks/ -name "TASK-FBP-003*.md" | wc -l
find tasks/ -name "TASK-REV-FMT*.md" | wc -l
```

## Notes

- Run after TASK-CL-001 to ensure status/directory alignment
- Duplicates create confusion about actual task status
- Git rm without -f since files are tracked
