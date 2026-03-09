---
id: TASK-RFX-528E
title: "Coach criteria soft gate Phase 1: structured results + pip normalization"
status: backlog
task_type: implementation
created: 2026-03-09T16:00:00Z
updated: 2026-03-09T16:00:00Z
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

- [ ] New `CommandExecutionResult` dataclass with: criterion_text, extracted_command, passed, exit_code, stdout, stderr, elapsed_seconds, timed_out
- [ ] `_execute_command_criteria()` returns `List[CommandExecutionResult]` instead of void
- [ ] Results stored on TurnRecord (new optional field `command_results`)
- [ ] Results included in Coach decision JSON (`coach_turn_N.json`)
- [ ] Progress display shows command execution summary (e.g., "Runtime Commands: 1/2 passed")
- [ ] Unit tests for CommandExecutionResult serialization
- [ ] Unit tests for structured result capture
- [ ] No behavior changes to Coach approve/reject decisions
