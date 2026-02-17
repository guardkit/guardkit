---
id: TASK-INFR-6D4F
title: Add requires_infrastructure field and propagation path
status: in_progress
created: 2026-02-17T00:00:00Z
updated: 2026-02-17T00:00:00Z
priority: high
tags: [autobuild, infrastructure, feature-loader, coach-validator]
task_type: feature
complexity: 3
parent_review: TASK-REV-BA4B
feature_id: FEAT-INFRA
wave: 1
implementation_mode: task-work
dependencies: []
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Add requires_infrastructure field and propagation path

## Description

Add a `requires_infrastructure` field to the FeatureTask model and task markdown frontmatter, then propagate it through the AutoBuild validation chain so CoachValidator can use it for infrastructure-aware decisions.

This is the foundation task -- all other infrastructure-aware autobuild tasks depend on this field existing and flowing through the system.

## Acceptance Criteria

- [ ] `FeatureTask` model in `feature_loader.py` has `requires_infrastructure: List[str] = Field(default_factory=list)`
- [ ] `AutoBuildOrchestrator.orchestrate()` loads `requires_infrastructure` from task frontmatter (alongside existing `task_type` loading at autobuild.py:738-742)
- [ ] `requires_infrastructure` is passed through `_loop_phase` → `_execute_turn` → Coach's `task` dict (at autobuild.py:3564)
- [ ] `CoachValidator.validate()` can read `requires_infrastructure` from the `task` parameter
- [ ] Feature YAML `requires_infrastructure` propagates to generated task frontmatter when feature-build creates task files
- [ ] Precedence rule enforced: task frontmatter > feature YAML default
- [ ] Unit tests for field parsing, propagation, and precedence
- [ ] Existing tests continue to pass (no regressions from the new optional field)

## Key Files

- `guardkit/orchestrator/feature_loader.py` - FeatureTask model (line 189)
- `guardkit/orchestrator/autobuild.py` - Task metadata loading (line 738-742), task dict construction (line 3564)
- `guardkit/orchestrator/feature_orchestrator.py` - Task file propagation (_copy_tasks_to_worktree)
- `guardkit/orchestrator/quality_gates/coach_validator.py` - Validate method receives task dict

## Implementation Notes

The `task` dict passed to `CoachValidator.validate()` currently contains `acceptance_criteria` and `task_type`. Add `requires_infrastructure` as a third field:

```python
task={
    "acceptance_criteria": acceptance_criteria or [],
    "task_type": task_type,
    "requires_infrastructure": requires_infrastructure,  # NEW
},
```

The field uses `List[str]` to support multiple infrastructure types: `[postgresql, redis]`.
