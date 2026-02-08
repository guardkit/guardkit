---
id: TASK-FIX-GCW4
title: Wire context_loader in FeatureOrchestrator and CLI callers
status: completed
task_type: implementation
created: 2026-02-08T16:30:00Z
updated: 2026-02-08T17:15:00Z
completed: 2026-02-08T17:15:00Z
priority: high
parent_review: TASK-REV-8BD8
tags: [autobuild, graphiti, context-retrieval, feature-orchestrator]
complexity: 3
wave: 2
dependencies: [TASK-FIX-GCW1, TASK-FIX-GCW2]
completed_location: tasks/completed/TASK-FIX-GCW4/
---

# Wire context_loader in FeatureOrchestrator and CLI Callers

## Description

Neither `FeatureOrchestrator._execute_task()` nor the CLI `task` command passes `context_loader` or `enable_context` to `AutoBuildOrchestrator`. Even if GCW3 (auto-init) handles this, the explicit callers should still forward the `enable_context` flag properly and allow DI override.

From review TASK-REV-8BD8, Recommendation R1.

**Note:** If TASK-FIX-GCW3 (auto-init) is implemented, this task becomes about ensuring callers can override `enable_context` via CLI flags and feature YAML config. The auto-init handles the default case.

## Changes Required

### FeatureOrchestrator

1. Add `enable_context: bool = True` parameter to `FeatureOrchestrator.__init__()`
2. Pass `enable_context` to `AutoBuildOrchestrator` in `_execute_task()`:
```python
task_orchestrator = AutoBuildOrchestrator(
    ...,
    enable_context=self.enable_context,
)
```

### CLI (`guardkit/cli/autobuild.py`)

1. Add `--enable-context/--no-context` flag to `task` command
2. Pass flag to `AutoBuildOrchestrator`:
```python
orchestrator = AutoBuildOrchestrator(
    ...,
    enable_context=enable_context,
)
```

### Feature YAML support (optional)

Allow `enable_context` to be configured per-feature:
```yaml
autobuild:
  enable_context: true
```

## Acceptance Criteria

- [x] `FeatureOrchestrator` accepts and forwards `enable_context` flag
- [x] CLI `task` command has `--enable-context/--no-context` flag
- [x] `enable_context` defaults to `True` in both callers
- [x] Flag can be set to `False` to disable context retrieval
- [x] Existing tests still pass
- [x] New tests for flag forwarding

## Files Modified

- `guardkit/orchestrator/feature_orchestrator.py` - Added `enable_context` parameter, stored on instance, forwarded to `AutoBuildOrchestrator`
- `guardkit/cli/autobuild.py` - Added `--enable-context/--no-context` flag to both `task` and `feature` commands, forwarded to orchestrators
- `tests/unit/test_feature_orchestrator.py` - 4 new tests for enable_context forwarding
- `tests/unit/test_cli_autobuild.py` - 3 new tests for CLI flag behavior

## Completion Notes

- All 7 new tests passing
- 0 regressions in existing tests (all pre-existing passing tests continue to pass)
- CLI `feature` command also wired (not just `task`) since FeatureOrchestrator now accepts the parameter
