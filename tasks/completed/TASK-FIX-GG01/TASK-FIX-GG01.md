---
id: TASK-FIX-GG01
title: Wire seed_feature_spec() into /feature-plan execution path
status: completed
task_type: implementation
created: 2026-02-08T22:00:00Z
updated: 2026-02-09T00:00:00Z
completed: 2026-02-09T00:00:00Z
completed_location: tasks/completed/TASK-FIX-GG01/
priority: medium
parent_review: TASK-REV-DE4F
feature_id: FEAT-GG-001
tags: [graphiti, feature-plan, write-path, gap-closure]
complexity: 2
wave: 1
dependencies: []
---

# Wire seed_feature_spec() into /feature-plan Execution Path

## Description

`seed_feature_spec()` is fully implemented at `guardkit/knowledge/feature_plan_context.py:529-584` (TASK-FIX-GCI4) with:
- `upsert_episode()` for idempotent seeding
- ADR-GBF-001 compliant episode body format
- 3-layer graceful degradation
- 14 passing tests

However, **no production code calls this method**. The `/feature-plan` execution path calls `build_context()` (read) but never `seed_feature_spec()` (write).

## Changes Required

### 1. Add seeding call after feature spec generation

In `guardkit/commands/feature_plan_integration.py`, after `build_enriched_prompt()` completes successfully:

```python
# After context is built and feature spec is generated
if self.enable_context:
    try:
        await self.context_builder.seed_feature_spec(
            feature_id=feature_id,
            feature_spec=generated_spec
        )
    except Exception as e:
        logger.warning(f"[Graphiti] Failed to seed feature spec: {e}")
```

### 2. Update feature-plan.md spec

Add documentation noting that `/feature-plan` now seeds the generated spec back to Graphiti.

## Key Files

- `guardkit/commands/feature_plan_integration.py` - Add seeding call
- `guardkit/knowledge/feature_plan_context.py` - `seed_feature_spec()` already exists
- `installer/core/commands/feature-plan.md` - Spec update

## Acceptance Criteria

- [x] `seed_feature_spec()` is called after feature spec generation
- [x] Seeding is skipped when `enable_context=False`
- [x] Graceful degradation when Graphiti unavailable (no crash)
- [x] Tests verify seeding is called in happy path
- [x] Tests verify seeding is skipped when `--no-context`

## Test Requirements

- 4-6 new tests in `tests/unit/commands/test_feature_plan_integration.py`
- Verify mock `seed_feature_spec()` called after `build_context()`
- Verify not called when `enable_context=False`
