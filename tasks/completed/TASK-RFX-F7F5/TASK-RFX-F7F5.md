---
id: TASK-RFX-F7F5
title: "Coach criteria soft gate Phase 2: failure classifier + advisory injection"
status: completed
previous_state: in_review
state_transition_reason: "All acceptance criteria met, quality gates passed"
completed: 2026-03-09T17:00:00Z
task_type: implementation
created: 2026-03-09T16:00:00Z
updated: 2026-03-09T16:00:00Z
priority: medium
complexity: 6
wave: 3
implementation_mode: task-work
parent_review: TASK-REV-A8C6
feature_id: FEAT-RFX
tags: [autobuild, coach-validator, criteria, command-execution]
dependencies: [TASK-RFX-528E]
---

# Task: Coach Criteria Soft Gate Phase 2 -- Failure Classifier + Advisory Injection

## Description

Implement failure classifier to categorise command execution failures (environment, implementation, transient). Inject implementation-classified failures as advisory text into Coach feedback when the Coach is already rejecting for file_content reasons. Environment failures are suppressed.

## Failure Classification Heuristics

| Type | Detection | Action |
|------|-----------|--------|
| Environment | Exit 127, "command not found", ModuleNotFoundError for system tools | Suppress |
| Implementation | Traceback in project files, import errors for project modules | Include in advisory |
| Transient | "ConnectionRefused", "timeout", "DNS resolution" | Suppress |
| Unknown | Default | Include with caveat |

## Acceptance Criteria

- [x] `classify_command_failure(result: CommandExecutionResult) -> str` function implemented
- [x] Returns one of: "environment", "implementation", "transient", "unknown"
- [x] Implementation-classified failures appended to Coach feedback text when Coach rejects
- [x] Environment-classified failures NOT included in feedback
- [x] Coach approve/reject threshold unchanged (still based on file_content criteria only)
- [x] Player receives command failure context on next turn via existing `previous_feedback` mechanism
- [x] Unit tests for failure classification with real failure outputs from Run 2/3 logs
- [x] Integration test: implementation failure appears in Coach feedback text
- [x] Integration test: environment failure does NOT appear in Coach feedback text
