---
id: TASK-SFT-008
title: Seam tests S7 — Task-work delegation to results writer
task_type: testing
parent_review: TASK-REV-AC1A
feature_id: FEAT-AC1A
wave: 2
implementation_mode: task-work
complexity: 4
dependencies:
  - TASK-SFT-001
priority: medium
---

# Seam Tests S7: Task-Work Delegation → Results Writer

## Objective

Write seam tests verifying that task-work delegation results (files_created, files_modified, test results) are actually written to the results JSON — catching the historical bug where `files_created` was always empty.

## Seam Definition

**Layer A**: Task-work delegation / AutoBuild turn execution
**Layer B**: Results file writer (`task_work_results.json`)

## Acceptance Criteria

- [ ] `tests/seam/test_task_delegation.py` created
- [ ] Test: After task-work execution, `task_work_results.json` contains `files_created` list
- [ ] Test: After task-work execution, `task_work_results.json` contains `files_modified` list
- [ ] Test: After task-work execution, `task_work_results.json` contains `tests_passed` status
- [ ] Test: Results file is written to `.guardkit/autobuild/TASK-XXX/` directory
- [ ] Test: Coach can read and parse the results file written by Player
- [ ] All tests pass with `pytest tests/seam/test_task_delegation.py -v`

## Implementation Notes

- Study `guardkit/orchestrator/quality_gates/task_work_interface.py` for results format
- The key verification is that the results file exists AND contains non-empty data
- Use tmp directories for isolation
