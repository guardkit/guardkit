---
id: TASK-VRF-005
title: Fix synthetic report corruption in state recovery
status: completed
completed: 2026-03-09T12:00:00Z
completed_location: tasks/completed/TASK-VRF-005/
priority: medium
complexity: 7
tags: [autobuild, state-recovery, synthetic-report, coach]
parent_review: TASK-REV-5E1F
feature_id: FEAT-9db9
wave: 4
implementation_mode: task-work
dependencies: [TASK-VRF-003]
created: 2026-03-09
---

# Task: Fix Synthetic Report Corruption in State Recovery

## Description

Investigate and fix the non-deterministic criteria visibility in synthetic reports generated during state recovery. The current system oscillates between 0-89% criteria visibility across turns instead of converging.

## Context

From TASK-REV-5E1F review deep-dive C: FBP-007's criteria assessment oscillated wildly:
- Turn 1: 89% → Turn 4: 11% → Turns 5-6: 0% → Turn 7: 56% → Turn 8: 0%

The `requirements_addressed` extraction from file content is non-deterministic. The Coach's hybrid fallback (promise matching → text matching) produces varying results turn-to-turn.

## Investigation Areas

1. **Synthetic report generation** in `autobuild.py`:
   - How `requirements_addressed` is extracted from player reports after state recovery
   - Why text matching produces different results for identical codebase state
   - Whether promise matching failure should use a different fallback strategy

2. **Cumulative criteria state**:
   - Currently each turn starts fresh from synthetic report
   - Should criteria state persist across turns?
   - Could a "high water mark" approach prevent regression?

3. **Coach validation stability**:
   - `coach_validator.py` hybrid fallback logic
   - Why Turn 4 collapsed from 89% to 11%
   - Whether Graphiti context invalidation affects criteria detection

## Acceptance Criteria

- [x] Root cause of criteria oscillation identified
- [x] Fix implemented that prevents criteria regression between turns
- [x] Synthetic report generation produces stable results for unchanged codebase
- [x] Existing tests pass
