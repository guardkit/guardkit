---
id: TASK-RFX-B20B
title: SDK sessions for Player resumption after CancelledError (CRV-3B1A)
status: backlog
task_type: implementation
created: 2026-03-09T16:00:00Z
updated: 2026-03-09T16:00:00Z
priority: medium
complexity: 7
wave: 4
implementation_mode: task-work
parent_review: TASK-REV-A8C6
feature_id: FEAT-RFX
tags: [autobuild, sdk, cancelled-error, session-resume]
dependencies: [TASK-RFX-8332]
original_task: TASK-CRV-3B1A
---

# Task: SDK Sessions for Player Resumption After CancelledError

## Description

Enable Player session resumption after CancelledError by leveraging SDK session management. This is the long-term, complete fix for the CancelledError issue -- rather than catching and recovering from the error (TASK-RFX-8332), this eliminates it by allowing the Player to resume from where it left off.

This is the original TASK-CRV-3B1A from the coach-runtime-verification feature (Wave 4). Dependency (CRV-1540) is complete.

## Acceptance Criteria

- [ ] Player invocation can be resumed after CancelledError using SDK session ID
- [ ] Resumed session continues from the last completed tool use
- [ ] State recovery path is used only when session resume fails
- [ ] Unit tests for session creation and resumption
- [ ] Integration test: Player resumes after simulated CancelledError

## Implementation Notes

See `tasks/backlog/coach-runtime-verification/TASK-CRV-3B1A-sdk-sessions-player-resume.md` for original specification. Note: TASK-RFX-8332 (explicit gen.aclose()) is a shorter-term fix that should be implemented first. This task provides the definitive, long-term solution.
