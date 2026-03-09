---
id: TASK-RFX-528E
title: "Coach criteria soft gate Phase 1: structured results + pip normalization"
status: completed
task_type: implementation
created: 2026-03-09T16:00:00Z
updated: 2026-03-09T19:00:00Z
completed: 2026-03-09T19:00:00Z
completed_location: tasks/completed/TASK-RFX-528E/
previous_state: in_review
state_transition_reason: "All acceptance criteria met, 38/38 tests passing"
priority: medium
complexity: 3
wave: 3
implementation_mode: task-work
parent_review: TASK-REV-A8C6
feature_id: FEAT-RFX
tags: [autobuild, coach-validator, criteria, command-execution]
dependencies: [TASK-RFX-BAD9]
---

# Task: Coach Criteria Soft Gate Phase 1 -- Structured Results

## Description

Add structured `CommandExecutionResult` dataclass and return values from `_execute_command_criteria()`. Persist results in TurnRecord and Coach decision JSON for visibility. This is the foundation for Phase 2 (failure classifier + advisory injection).

## Acceptance Criteria

- [x] New `CommandExecutionResult` dataclass with: criterion_text, extracted_command, passed, exit_code, stdout, stderr, elapsed_seconds, timed_out
- [x] `_execute_command_criteria()` returns `List[CommandExecutionResult]` instead of void
- [x] Results stored on TurnRecord (new optional field `command_results`)
- [x] Results included in Coach decision JSON (`coach_turn_N.json`)
- [x] Progress display shows command execution summary (e.g., "Runtime Commands: 1/2 passed")
- [x] Unit tests for CommandExecutionResult serialization
- [x] Unit tests for structured result capture
- [x] No behavior changes to Coach approve/reject decisions
