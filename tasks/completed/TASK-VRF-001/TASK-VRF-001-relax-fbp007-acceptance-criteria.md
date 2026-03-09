---
id: TASK-VRF-001
title: Relax TASK-FBP-007 acceptance criteria (remove zero-Any requirement)
status: completed
priority: critical
complexity: 2
tags: [autobuild, vllm, acceptance-criteria, quality-gates]
parent_review: TASK-REV-5E1F
feature_id: FEAT-9db9
wave: 1
implementation_mode: direct
dependencies: []
created: 2026-03-09
completed: 2026-03-09
completed_location: tasks/completed/TASK-VRF-001/
---

# Task: Relax TASK-FBP-007 Acceptance Criteria

## Description

Remove the infeasible acceptance criterion AC-008 ("All type annotations complete - no Any types unless explicitly justified") from TASK-FBP-007 in the vLLM profiling feature plan. Replace with a more achievable mypy configuration.

## Context

From TASK-REV-5E1F review: AC-008 was **never met in any of 8 turns**. Third-party library stubs make zero-Any infeasible regardless of backend. The Coach oscillated between 0-89% criteria visibility across turns.

## Changes Required

1. Update the TASK-FBP-007 task file in the vLLM profiling project's feature plan
2. Replace AC-008 with: "Type annotations present on all public functions; mypy passes with `--disallow-untyped-defs` (not `--strict`)"
3. Optionally adjust AC-002 to remove `strict mode` requirement, keeping `disallow_untyped_defs=true`
4. Optionally adjust AC-006 from "zero errors in strict mode" to "zero errors with configured settings"

## Acceptance Criteria

- [x] AC-008 replaced with feasible alternative
- [x] AC-002 and AC-006 adjusted if they reference `--strict`
- [x] Updated criteria are self-consistent
