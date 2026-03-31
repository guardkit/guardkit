---
id: TASK-VRF-002
title: Separate TASK-FBP-007 into its own wave to eliminate budget starvation
status: completed
priority: high
complexity: 2
tags: [autobuild, vllm, wave-structure, timeout]
parent_review: TASK-REV-5E1F
feature_id: FEAT-9db9
wave: 1
implementation_mode: direct
dependencies: []
created: 2026-03-09
completed: 2026-03-09
---

# Task: Separate TASK-FBP-007 Into Its Own Wave

## Description

Move TASK-FBP-007 from Wave 5 (shared with TASK-FBP-006) to a new Wave 6 in the vLLM profiling feature plan. With `max_parallel=1`, co-locating both tasks in Wave 5 creates deterministic budget starvation when FBP-006 runs long.

## Context

From TASK-REV-5E1F review: FBP-006 consumed 6749s (112 min) in Run 5, leaving FBP-007 only 2820s (47 min) of its 9600s budget. With its own wave, FBP-007 would get the full 9600s budget.

## Changes Required

1. Update the feature plan YAML/task files to place FBP-007 in Wave 6 (after current Wave 5)
2. Ensure FBP-007 has no dependencies on FBP-006 (they are independent quality gate tasks)
3. Update IMPLEMENTATION-GUIDE.md if it exists

## Acceptance Criteria

- [x] TASK-FBP-007 is in its own wave (Wave 5, separated from FBP-006 in Wave 4)
- [x] TASK-FBP-006 remains in Wave 4 (unchanged)
- [x] Wave dependency chain is valid (FBP-007 depends on FBP-005, not FBP-006)
