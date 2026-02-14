# FEAT-STUB-QG: Stub Quality Gate Fixes — Implementation Guide

## Overview

Fixes the quality gate gaps that allowed a stub file (`guardkit/planning/system_plan.py`) to pass all gates and reach `in_review` status. Root cause: acceptance criteria are never passed to the Coach, plus missing anti-stub detection.

## Wave Breakdown

### Wave 1: Critical Fixes (2 tasks, parallel)

| Task | Title | Complexity | Mode | Dependencies |
|------|-------|-----------|------|-------------|
| TASK-FIX-STUB-A | Wire acceptance_criteria through _execute_turn() to Coach | 3 | task-work | None |
| TASK-FIX-STUB-B | Create anti-stub quality rule | 3 | direct | None |

**STUB-A** is the critical 3-line fix that restores acceptance criteria verification for ALL AutoBuild runs. **STUB-B** is a new rule file — no code changes, no file conflicts. These are independent and can run in parallel.

### Wave 2: Data Gap Fixes (2 tasks, parallel)

| Task | Title | Complexity | Mode | Dependencies |
|------|-------|-----------|------|-------------|
| TASK-FIX-STUB-C | Populate files_created/files_modified in task-work delegation | 5 | task-work | STUB-A (recommended) |
| TASK-FIX-STUB-D | Add anti-stub criteria to feature plan template | 2 | direct | STUB-B (recommended) |

**STUB-C** fixes the test discovery data gap in the task-work delegation path. **STUB-D** updates the feature plan template. Soft dependencies — the wave 1 fixes should land first so wave 2 can be validated against the improved pipeline.

## Key Files

| File | Tasks | Notes |
|------|-------|-------|
| `guardkit/orchestrator/autobuild.py` | STUB-A | `_execute_turn()`, `_loop_phase()`, `_invoke_coach_safely()` |
| `.claude/rules/anti-stub.md` | STUB-B | New file — stub pattern definitions |
| `guardkit/orchestrator/agent_invoker.py` | STUB-C | Task-work delegation results writer |
| Feature plan template (TBD) | STUB-D | Anti-stub acceptance criteria |

## Execution Strategy

```
Wave 1: STUB-A + STUB-B (parallel, Conductor recommended)
Wave 2: STUB-C + STUB-D (parallel, Conductor recommended)
```

Total: 4 tasks, 2 waves.

## Validation Plan

After Wave 1 (STUB-A):
- Run any AutoBuild task with acceptance criteria
- Verify `coach_turn_*.json` shows `criteria_total > 0` (currently always 0)
- Verify TASK-FIX-ACA7b's completion_promises matching activates

After Wave 2 (STUB-C):
- Run a task-work delegation task that creates files
- Verify `task_work_results.json` has non-empty `files_created`/`files_modified`
- Verify Coach's `_detect_tests_from_results()` finds test files via primary path

## Risk Assessment

| Task | Risk | Mitigation |
|------|------|-----------|
| STUB-A | LOW — Adding parameter with default None | Existing tests unaffected |
| STUB-B | NONE — New rule file only | No code changes |
| STUB-C | MEDIUM — Modifying results writer | Existing writer tests as regression guard |
| STUB-D | NONE — Template update only | No code changes |

## Relationship to Prior Fixes

This feature completes the acceptance criteria verification pipeline:

```
TASK-AQG-001 (structured criteria) ──┐
TASK-FIX-ACA7b (matching logic) ─────┤── All BLOCKED by missing input data
TASK-AQG-002 (zero-test blocking) ───┘
                                       │
TASK-FIX-STUB-A (wire criteria) ───────┘── UNBLOCKS all of the above
```
