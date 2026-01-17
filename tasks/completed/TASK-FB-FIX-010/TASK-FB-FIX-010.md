---
id: TASK-FB-FIX-010
title: Implement enable_pre_loop configuration cascade
status: completed
created: 2026-01-12T00:00:00Z
updated: 2026-01-12T16:00:00Z
completed: 2026-01-12T16:00:00Z
priority: high
complexity: 5
tags: [feature-build, enable-pre-loop, config-propagation, config-cascade]
parent_review: TASK-REV-FB08
completed_location: tasks/completed/TASK-FB-FIX-010/
---

# Task: Implement enable_pre_loop configuration cascade

## Description

The `enable_pre_loop: false` setting in both feature YAML and task frontmatter is being ignored. The flag always defaults to `True` because:

1. No CLI option exists to set it
2. Feature YAML `autobuild.enable_pre_loop` is never read
3. Task frontmatter `autobuild.enable_pre_loop` is never read
4. The value is never passed to `AutoBuildOrchestrator`

## Configuration Cascade Priority

Implement this priority order (highest to lowest):
1. **CLI flag** (`--enable-pre-loop` / `--no-pre-loop`)
2. **Task frontmatter** (`autobuild.enable_pre_loop`)
3. **Feature YAML** (`autobuild.enable_pre_loop`)
4. **Default** (`True`)

## Requirements

1. Add `--enable-pre-loop` / `--no-pre-loop` CLI options to `feature` command
2. Read `enable_pre_loop` from feature YAML in `FeatureOrchestrator`
3. Read `enable_pre_loop` from task frontmatter in `_execute_task`
4. Implement cascade priority logic
5. Pass resolved value to `AutoBuildOrchestrator`

## Acceptance Criteria

- [x] CLI `--no-pre-loop` flag disables pre-loop phase
- [x] CLI `--enable-pre-loop` flag enables pre-loop phase (explicit override)
- [x] Feature YAML `autobuild.enable_pre_loop: false` disables pre-loop when no CLI flag
- [x] Task frontmatter `autobuild.enable_pre_loop: false` overrides feature YAML
- [x] Default remains `True` when no config specified
- [x] Log shows correct `enable_pre_loop` value from config source
- [x] Unit tests verify cascade priority
- [x] Existing tests continue to pass

## Implementation Guide

### Step 1: Add CLI Options

```python
# cli/autobuild.py - Add to feature command options
@click.option(
    "--enable-pre-loop/--no-pre-loop",
    "enable_pre_loop",
    default=None,  # None means "not specified, use cascade"
    help="Enable/disable pre-loop quality gates (default: use feature YAML or True)",
)
```

### Step 2: Update FeatureOrchestrator.__init__

```python
def __init__(
    self,
    repo_root: Path,
    max_turns: int = 5,
    # ... existing params ...
    enable_pre_loop: Optional[bool] = None,  # ADD THIS
):
    # ... existing code ...
    self.enable_pre_loop = enable_pre_loop  # Store CLI value (may be None)
```

### Step 3: Read from Feature YAML

```python
# In FeatureOrchestrator._load_feature or similar
def _resolve_enable_pre_loop(self, feature: Feature, task_data: Dict) -> bool:
    """Resolve enable_pre_loop with cascade priority."""
    # 1. CLI flag (highest priority)
    if self.enable_pre_loop is not None:
        return self.enable_pre_loop

    # 2. Task frontmatter
    task_frontmatter = task_data.get("frontmatter", {})
    task_autobuild = task_frontmatter.get("autobuild", {})
    if "enable_pre_loop" in task_autobuild:
        return task_autobuild["enable_pre_loop"]

    # 3. Feature YAML
    feature_autobuild = feature.autobuild_config or {}
    if "enable_pre_loop" in feature_autobuild:
        return feature_autobuild["enable_pre_loop"]

    # 4. Default
    return True
```

### Step 4: Pass to AutoBuildOrchestrator

```python
# In _execute_task
effective_enable_pre_loop = self._resolve_enable_pre_loop(feature, task_data)

task_orchestrator = AutoBuildOrchestrator(
    repo_root=self.repo_root,
    max_turns=self.max_turns,
    resume=False,
    existing_worktree=worktree,
    worktree_manager=self._worktree_manager,
    sdk_timeout=effective_sdk_timeout,
    enable_pre_loop=effective_enable_pre_loop,  # ADD THIS
)
```

## Test Cases

1. **test_enable_pre_loop_cli_override**
   - Set feature YAML to `enable_pre_loop: true`
   - Pass `--no-pre-loop` CLI flag
   - Verify pre-loop is skipped

2. **test_enable_pre_loop_task_frontmatter_override**
   - Set feature YAML to `enable_pre_loop: true`
   - Set task frontmatter to `enable_pre_loop: false`
   - No CLI flag
   - Verify pre-loop is skipped for that task

3. **test_enable_pre_loop_feature_yaml**
   - Set feature YAML to `enable_pre_loop: false`
   - No task frontmatter override
   - No CLI flag
   - Verify pre-loop is skipped

4. **test_enable_pre_loop_default**
   - No config anywhere
   - Verify pre-loop runs (default True)

## Files to Modify

- `guardkit/cli/autobuild.py`
- `guardkit/orchestrator/feature_orchestrator.py`
- `guardkit/orchestrator/feature_loader.py` (if Feature model needs update)
- `tests/unit/test_feature_orchestrator.py`
- `tests/unit/test_cli_autobuild.py`
