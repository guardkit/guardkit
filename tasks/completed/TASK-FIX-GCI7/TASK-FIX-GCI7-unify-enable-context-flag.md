---
id: TASK-FIX-GCI7
title: Unify --enable-context flag across commands
status: completed
task_type: implementation
created: 2026-02-08T23:00:00Z
updated: 2026-02-08T23:30:00Z
completed: 2026-02-08T23:30:00Z
priority: medium
parent_review: TASK-REV-C7EB
tags: [graphiti, cli, configuration, consistency]
complexity: 3
wave: 3
dependencies: [TASK-FIX-GCI1, TASK-FIX-GCI4]
---

# Unify --enable-context Flag Across Commands

## CRITICAL: No Stubs Policy

**All code written for this task MUST be fully functional.** No placeholder flags that aren't connected to real logic, no TODO comments deferring implementation. Every `--enable-context/--no-context` flag must actually control Graphiti behaviour in the command's execution path. Every flag must be tested.

## Description

Currently, only AutoBuild commands have `--enable-context/--no-context` flags (added in TASK-FIX-GCW4 at `guardkit/cli/autobuild.py`). Other commands with Graphiti integration (`/feature-plan`, `/task-review`) have no CLI mechanism to control Graphiti behaviour.

This task adds consistent `--enable-context/--no-context` flags to all commands that interact with Graphiti.

## Current State

| Command | Flag | Status |
|---------|------|--------|
| `guardkit autobuild task` | `--enable-context/--no-context` | Implemented |
| `guardkit autobuild feature` | `--enable-context/--no-context` | Implemented |
| `/feature-plan` | None | Missing |
| `/task-review` | `--capture-knowledge` only | Partial (different flag) |
| `/task-work` | None | Missing (depends on GCI1) |

## Changes Required

### 1. Add flag to /feature-plan
Control whether Graphiti context enrichment runs during planning:
```python
@click.option("--enable-context/--no-context", "enable_context",
              default=True, help="Enable/disable Graphiti context enrichment")
```

### 2. Add flag to /task-work (after GCI1)
Control whether Graphiti context loading runs during task execution:
```python
@click.option("--enable-context/--no-context", "enable_context",
              default=True, help="Enable/disable Graphiti context loading")
```

### 3. Consider flag for /task-review
The `--capture-knowledge` flag controls writing. Consider adding `--enable-context` for read-side consistency, or document that `/task-review` uses `--capture-knowledge` for its Graphiti interaction.

## Acceptance Criteria

- [x] `/feature-plan` accepts `--enable-context/--no-context` (via FeaturePlanIntegration.enable_context parameter)
- [x] `guardkit review` accepts `--enable-context/--no-context` (CLI flag added)
- [x] All flags default to `True` (Graphiti enabled when available)
- [x] All flags pass through to their respective context loading code
- [x] Consistent flag naming and help text across all commands
- [x] Tests for flag parsing (14 new tests, 54 total passing)

## Files to Modify

- Feature-plan CLI handler
- Task-work CLI handler (after GCI1 is complete)
- Updated tests for CLI flag parsing

## Reference Implementation (guardkit/cli/autobuild.py)

The existing AutoBuild CLI shows the exact pattern to follow:

### Flag declaration (lines 201-206)
```python
@click.option(
    "--enable-context/--no-context",
    "enable_context",
    default=True,
    help="Enable/disable Graphiti context retrieval (default: enabled)",
)
```

### Flag pass-through in task command (lines 209-233)
```python
def task(ctx, task_id: str, ..., enable_context: bool, ...):
    # Flag is passed directly to the orchestrator
    orchestrator = AutoBuildOrchestrator(
        ...,
        enable_context=enable_context,
    )
```

### Flag pass-through in feature command (lines 525-528)
```python
def feature(ctx, task_id: str, ..., enable_context: bool, ...):
    orchestrator = FeatureOrchestrator(
        ...,
        enable_context=enable_context,
    )
```

### Graceful degradation (already built into the system)

The `enable_context` flag is a **user-level control**. Even when `True`, the system handles Graphiti unavailability gracefully:
1. `AutoBuildContextLoader.__init__()` checks `get_graphiti()` availability
2. If Graphiti is unavailable, context loading is silently skipped
3. `--no-context` is an explicit opt-out (useful for debugging or offline work)

## Files for Reference

- `guardkit/cli/autobuild.py:201-206, 525-528` - Existing flag implementation (THE PATTERN)
- `guardkit/orchestrator/autobuild.py` - How `enable_context` flows to `AutoBuildContextLoader`
- `guardkit/orchestrator/feature_orchestrator.py` - How `enable_context` flows to feature orchestration
