---
id: TASK-RFX-7C63
title: Extended CoachValidator with runtime verification methods (CRV-9914)
status: backlog
task_type: implementation
created: 2026-03-09T16:00:00Z
updated: 2026-03-09T16:00:00Z
priority: medium
complexity: 6
wave: 4
implementation_mode: task-work
parent_review: TASK-REV-A8C6
feature_id: FEAT-RFX
tags: [autobuild, coach-validator, architecture]
dependencies: [TASK-RFX-F7F5]
original_task: TASK-CRV-9914
---

# Task: Extended CoachValidator with Runtime Verification Methods

## Description

Architectural refactor to move runtime verification from the orchestrator (`autobuild.py:_execute_command_criteria()`) into the CoachValidator. This creates a cleaner separation of concerns where the Coach owns all verification -- file-content, command-execution, and manual criteria.

This is the original TASK-CRV-9914 from the coach-runtime-verification feature (Wave 3). Dependencies (CRV-412F and CRV-537E) are now complete.

## Acceptance Criteria

- [ ] CoachValidator has a `verify_command_criteria()` method that executes runtime commands
- [ ] Command execution logic moved from `autobuild.py:_execute_command_criteria()` to Coach
- [ ] CoachValidator uses failure classifier from TASK-RFX-F7F5 for result categorisation
- [ ] Orchestrator passes worktree path to Coach for command execution context
- [ ] Backward compatible: existing quality gate profiles continue to work
- [ ] Unit tests for CoachValidator command verification
- [ ] Integration test: Coach executes and evaluates command criteria in same pipeline as file_content

## Implementation Notes

See `tasks/backlog/coach-runtime-verification/TASK-CRV-9914-extended-coach-validator.md` for original specification.
