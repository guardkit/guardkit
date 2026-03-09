---
id: TASK-VR6-3B1F
title: Separate FBP-007 into its own wave in FEAT-1637
status: completed
task_type: implementation
created: 2026-03-09T00:00:00Z
updated: 2026-03-09T12:00:00Z
completed: 2026-03-09T12:00:00Z
completed_location: tasks/completed/TASK-VR6-3B1F/
priority: high
complexity: 1
wave: 1
implementation_mode: direct
parent_review: TASK-REV-35DC
feature_id: FEAT-81DD
tags: [autobuild, vllm, wave-separation, profiling]
dependencies: []
---

# Task: Separate FBP-007 into its own wave in FEAT-1637

## Description

Move FBP-007 from Wave 5 (co-located with FBP-006) into its own Wave 6 in the FEAT-1637 feature orchestration YAML. This eliminates budget starvation where FBP-006 (118 SDK turns, 97.4m) consumed most of Wave 5's budget before FBP-007 could execute.

## Context

Across Runs 4-6, FBP-006 and FBP-007 have been co-located in Wave 5 with `max_parallel=1`. This serialization means FBP-007's budget is `task_timeout - FBP-006_runtime`. In Run 6, FBP-007 received only 3723s of its 9600s budget and was cancelled by the anyio cancel scope.

Run 6 succeeded only because state recovery detected 12 changed files and 159 passing tests after the cancellation. This is non-deterministic — the same configuration could fail in Run 7.

## Acceptance Criteria

- [x] FBP-007 is in its own wave (Wave 6) in the FEAT-1637 feature YAML
- [x] FBP-006 remains in Wave 5 (alone or with other non-conflicting tasks)
- [x] Wave dependencies are correct (FBP-007 still depends on Waves 1-4 completing)
- [x] No other wave assignments are changed

## Files to Modify

- Feature YAML for FEAT-1637 (locate via `grep -r "FEAT-1637" tasks/`)

## Risk Assessment

**Risk: None.** FBP-007 has no dependency on FBP-006. Moving it to a separate wave only changes execution ordering from "serialized within same wave" to "sequential waves" — functionally identical but with a fresh budget.
