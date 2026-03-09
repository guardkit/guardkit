---
id: TASK-PFI-A1B2
title: Suppress CancelledError WARNING when state recovery succeeds
status: completed
created: 2026-03-09T21:10:00Z
updated: 2026-03-09T22:00:00Z
priority: medium
tags: [autobuild, logging, cancellederror, noise-reduction]
complexity: 1
parent_review: TASK-REV-D326
feature_id: FEAT-PFI
wave: 1
implementation_mode: direct
dependencies: []
---

# Task: Suppress CancelledError WARNING When State Recovery Succeeds

## Description

The CancelledError WARNING in `agent_invoker.py` fires on ~40% of direct-mode task invocations. Since state recovery succeeds 100% of the time, the WARNING is misleading -- it suggests a problem when the system is functioning as designed.

Downgrade the log level from WARNING to DEBUG when state recovery succeeds, and only keep WARNING level if recovery fails.

## Context

From TASK-REV-D326 review:
- CancelledError occurs 4 times per FEAT-2AAA run (VID-001 + VID-005 x3)
- State recovery succeeds every time via `player_turn_N.json`
- The TASK-RFX-8332 `gen.aclose()` fix reduced the window but did not eliminate the race
- Root cause is in claude_agent_sdk async generator lifecycle -- not fixable from GuardKit

## Acceptance Criteria

- [x] CancelledError at `_invoke_player_direct` logged at DEBUG (not WARNING) when subsequent state recovery succeeds
- [x] CancelledError remains WARNING when state recovery fails
- [x] Log message updated to indicate recovery status: `"CancelledError caught for {task_id} (recovered: {bool})"`
- [x] No functional change to state recovery logic

## Files to Modify

- `guardkit/orchestrator/agent_invoker.py` (line ~1389: WARNING -> conditional DEBUG/WARNING)
- `guardkit/orchestrator/autobuild.py` (state recovery section: pass recovery status back)

## Implementation Notes

The CancelledError is caught at `agent_invoker.py:1386-1390`. State recovery happens at `autobuild.py` after `invoke_player()` returns. The simplest approach is to log at DEBUG in the catch handler and let `autobuild.py` log at INFO after successful recovery.
