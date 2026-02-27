---
id: TASK-SFC-004
title: Add feature-spec integration point to seed_integration_points.py
task_type: implementation
status: completed
created: 2026-02-23T14:00:00Z
updated: 2026-02-27T00:00:00Z
completed: 2026-02-27T00:00:00Z
priority: medium
tags: [graphiti, seeding, feature-spec, integration-points]
complexity: 2
parent_review: TASK-REV-5FA4
feature_id: FEAT-SFC
wave: 2
implementation_mode: task-work
dependencies: [TASK-SFC-001]
completed_location: tasks/completed/TASK-SFC-004/
---

# Task: Add Feature-Spec Integration Point to seed_integration_points.py

## Description

Add a new integration point episode documenting how `/feature-spec` connects to `/feature-plan` and how its outputs are consumed by the AutoBuild Coach.

This addresses finding F9 (MEDIUM) from the TASK-REV-5FA4 review.

## Context

- Source of truth: `installer/core/commands/feature-spec.md` and `docs/commands/feature-spec.md`
- Current module has 2 episodes; update docstring to reflect 3
- The `/feature-spec` -> `/feature-plan` integration is documented in the feature spec research document (Section 4.3)

## Changes Required

### 1. Add `integration_feature_spec_to_plan` episode (NEW)

```python
("integration_feature_spec_to_plan", {
    "issue_type": "integration_point",
    "name": "feature_spec_to_feature_plan",
    "connects": ["/feature-spec", "/feature-plan", "AutoBuild Coach"],
    "correct_pattern": "/feature-plan 'Feature' --context features/{name}/{name}_summary.md",
    "outputs_produced": {
        "feature_file": "features/{name}/{name}.feature - consumed by Coach during AutoBuild",
        "assumptions_manifest": "features/{name}/{name}_assumptions.yaml - consumed by Coach for divergence detection",
        "summary": "features/{name}/{name}_summary.md - consumed by /feature-plan as structured context"
    },
    "rule": "/feature-plan reads _summary.md for task decomposition; Coach reads .feature and _assumptions.yaml during AutoBuild validation"
}),
```

### 2. Update module docstring

Change "Creates 2 episodes" to "Creates 3 episodes".

## Acceptance Criteria

- [x] New `integration_feature_spec_to_plan` episode exists
- [x] Episode documents all 3 output files and their consumers
- [x] Episode specifies the correct `--context` pattern for `/feature-plan`
- [x] Module docstring updated to 3 episodes
- [x] `ruff check guardkit/knowledge/seed_integration_points.py` passes

## Files Modified

| File | Action |
|------|--------|
| `guardkit/knowledge/seed_integration_points.py` | Modified (added 1 episode, updated docstring) |
