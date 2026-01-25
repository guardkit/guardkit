# Implementation Plan: TASK-FB-FIX-010

## Overview

Implement `enable_pre_loop` configuration cascade so that the setting can be controlled via CLI, feature YAML, and task frontmatter with proper priority ordering.

## Configuration Cascade Priority (Highest to Lowest)

1. **CLI flag** (`--enable-pre-loop` / `--no-pre-loop`)
2. **Task frontmatter** (`autobuild.enable_pre_loop`)
3. **Feature YAML** (`autobuild.enable_pre_loop`)
4. **Default** (`True`)

## Implementation Steps

### Step 1: Add CLI Options to `feature` command

**File**: `guardkit/cli/autobuild.py`

Add `--enable-pre-loop/--no-pre-loop` option to the `feature` command, similar to existing `--sdk-timeout` pattern.

### Step 2: Update FeatureOrchestrator Constructor

**File**: `guardkit/orchestrator/feature_orchestrator.py`

Add `enable_pre_loop: Optional[bool] = None` parameter to `__init__` and store it as `self.enable_pre_loop`.

### Step 3: Implement Cascade Resolution Logic

**File**: `guardkit/orchestrator/feature_orchestrator.py`

Add method `_resolve_enable_pre_loop(feature, task_data)` that implements the cascade priority:
1. Check CLI value (self.enable_pre_loop)
2. Check task frontmatter (task_data.frontmatter.autobuild.enable_pre_loop)
3. Check feature YAML (feature autobuild config)
4. Return default (True)

### Step 4: Pass to AutoBuildOrchestrator in _execute_task

**File**: `guardkit/orchestrator/feature_orchestrator.py`

Call `_resolve_enable_pre_loop()` before creating `AutoBuildOrchestrator` and pass the resolved value.

### Step 5: Add Unit Tests

**File**: `tests/unit/test_feature_orchestrator.py`

Add tests for:
- CLI override takes precedence
- Task frontmatter overrides feature YAML
- Feature YAML used when no CLI/task override
- Default True when no config specified

**File**: `tests/unit/test_cli_autobuild.py`

Add tests for:
- CLI flag parsing for `--enable-pre-loop` and `--no-pre-loop`

## Files to Modify

| File | Change |
|------|--------|
| `guardkit/cli/autobuild.py` | Add CLI option |
| `guardkit/orchestrator/feature_orchestrator.py` | Add parameter, cascade logic, pass to orchestrator |
| `tests/unit/test_feature_orchestrator.py` | Add cascade tests |
| `tests/unit/test_cli_autobuild.py` | Add CLI option tests |

## Risk Assessment

- **Low risk**: Changes are additive and follow existing patterns (sdk_timeout cascade)
- **No breaking changes**: Default behavior remains `True`

## Complexity: 5/10

- 4 files to modify
- Clear pattern to follow (sdk_timeout implementation)
- Standard pytest testing patterns
