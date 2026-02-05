---
id: TASK-AB-SD02
title: "Add trim/reduce/compress keywords to documentation type detector"
status: completed
priority: low
task_type: feature
complexity: 2
parent_review: TASK-REV-D4B1
wave: 2
implementation_mode: task-work
dependencies:
  - TASK-FIX-D4B1
tags:
  - task-type-detector
  - prevention
completed: 2026-02-05
completed_location: tasks/completed/TASK-AB-SD02/
---

## Description

Add content-reduction keywords ("trim", "reduce", "compress", "condense", "shorten") to the DOCUMENTATION keyword list in the task type detector. Currently, these words don't appear in any keyword list, causing tasks like "Trim orchestrators.md" to fall through to the default FEATURE type (or match REFACTOR if the description mentions "migration").

## Evidence

See [TASK-REV-D4B1 review report](.claude/reviews/TASK-REV-D4B1-review-report.md) Finding 6.

## Files Modified

1. `guardkit/lib/task_type_detector.py` — Added 5 content-reduction keywords to DOCUMENTATION list (lines 97-102)
2. `tests/unit/test_task_type_detector.py` — Added `test_content_reduction_keywords` test method (lines 79-84)

## Acceptance Criteria

- [x] `detect_task_type("Trim orchestrators.md")` returns `TaskType.DOCUMENTATION`
- [x] `detect_task_type("Reduce dataclass patterns doc")` returns `TaskType.DOCUMENTATION`
- [x] `detect_task_type("Compress verbose documentation")` returns `TaskType.DOCUMENTATION`
- [x] Existing test cases still pass
- [x] New test cases added for trim/reduce/compress/condense/shorten keywords
