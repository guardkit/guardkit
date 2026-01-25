---
id: TASK-REV-2EDF
title: "Analyze feature-build failure due to missing implementation plans"
status: completed
task_type: review
review_mode: decision
review_depth: standard
created: 2026-01-24T10:00:00Z
updated: 2026-01-25T07:45:07Z
completed: 2026-01-25T07:45:07Z
priority: high
tags: [feature-build, autobuild, bug-analysis, implementation-plan]
complexity: 5
review_results:
  mode: decision
  depth: standard
  options_evaluated: 4
  recommended_option: "Option B - Route direct mode through direct Player invocation"
  root_cause: "Tasks with implementation_mode: direct don't trigger stub creation, and feature-build routes ALL tasks through task-work delegation which requires plans"
  report_path: .claude/reviews/TASK-REV-2EDF-review-report.md
  completed_at: 2026-01-25T07:45:07Z
  decision: implement
  implementation_task: TASK-FB-2D8B
test_results:
  status: not_applicable
  coverage: null
  last_run: null
---

# Task: Analyze feature-build failure due to missing implementation plans

## Description

The `/feature-build` command (via `guardkit autobuild feature FEAT-XXX`) fails when tasks don't have pre-existing implementation plans. The Player phase expects implementation plans at specific paths but they don't exist.

## Evidence

From the log output at `docs/reviews/feature-build/no_implementation_plan_fordoc_tasks.md`:

**Error Pattern (repeated for each task)**:
```
ERROR:guardkit.orchestrator.agent_invoker:Implementation plan not found for TASK-DOC-002:
Implementation plan not found for TASK-DOC-002. Expected at one of:
['.../task-plans/TASK-DOC-002-implementation-plan.md',
 '.../task-plans/TASK-DOC-002-implementation-plan.json',
 '.../docs/state/TASK-DOC-002/implementation_plan.md',
 '.../docs/state/TASK-DOC-002/implementation_plan.json'].
Run task-work --design-only first to generate the plan.
```

**Affected Tasks**: All tasks in Wave 1 (TASK-DOC-001, TASK-DOC-002, TASK-DOC-005)

**Secondary Issue**: Git index.lock contention when running parallel tasks in shared worktree.

## Root Cause (Confirmed)

**Primary Issue**: Tasks with `implementation_mode: direct` (complexity ≤3) bypass stub plan creation in `state_bridge.py`:

```python
# state_bridge.py:388
is_task_work_mode = implementation_mode == "task-work"
should_create_stub = has_autobuild_config or has_autobuild_state or is_task_work_mode

if not should_create_stub:
    return None  # Silent failure for direct mode
```

**Architectural Mismatch**: Feature-build uses a single execution path (`task-work --implement-only` via `USE_TASK_WORK_DELEGATION`) for all tasks, ignoring the `implementation_mode` field. This path requires an implementation plan, which direct mode tasks don't have.

## Review Decision

**Decision**: [I]mplement

**Recommended Solution**: Option B - Route `direct` mode tasks through direct Player invocation with Coach compatibility layer.

**Implementation Task**: [TASK-FB-2D8B](../backlog/TASK-FB-2D8B-direct-mode-player-routing.md)

## Options Evaluated

| Option | Description | Verdict |
|--------|-------------|---------|
| A | Add `direct` to stub creation | Patches symptom, not cause |
| B | Route `direct` through direct Player | **Recommended** - respects design intent |
| C | IMPLEMENTATION-GUIDE injection | No value - task files already have patterns |
| D | Git-only state detection for direct | More changes to CoachValidator |

## Files Reviewed

- `guardkit/orchestrator/agent_invoker.py` - Where error is raised
- `guardkit/tasks/state_bridge.py` - Stub creation logic
- `guardkit/orchestrator/quality_gates/coach_validator.py` - Coach validation requirements
- Test project task files - Confirmed `implementation_mode: direct`

## Acceptance Criteria

- [x] Root cause identified and documented
- [x] Recommended fix approach determined
- [x] Decision made: Route direct mode through direct Player path
- [x] Implementation task created: TASK-FB-2D8B

## Review Report

See: [.claude/reviews/TASK-REV-2EDF-review-report.md](../../.claude/reviews/TASK-REV-2EDF-review-report.md)

## Related

- **Implementation Task**: [TASK-FB-2D8B](../backlog/TASK-FB-2D8B-direct-mode-player-routing.md)
- Feature: FEAT-F392 (Comprehensive API Documentation)
- Log file: `docs/reviews/feature-build/no_implementation_plan_fordoc_tasks.md`
- Secondary Issue: Git index lock contention (TASK-FB-LOCK - to be created)
