---
id: TASK-4B7F
title: Add --copy-graphiti flag to guardkit init CLI
status: completed
created: 2026-03-03T00:00:00Z
updated: 2026-03-03T00:00:00Z
completed: 2026-03-03T00:00:00Z
completed_location: tasks/completed/TASK-4B7F/
priority: high
tags: [cli, graphiti, init, developer-experience]
complexity: 3
task_type: implementation
parent_review: TASK-REV-5842
test_results:
  status: passed
  total: 83
  passed: 83
  failed: 0
  last_run: 2026-03-03T00:00:00Z
---

# Task: Add --copy-graphiti flag to guardkit init CLI

## Description

Add a `--copy-graphiti` flag to `guardkit init` that auto-discovers and copies an existing project's `.guardkit/graphiti.yaml` config, replacing only the `project_id` with the new project's name. This eliminates the manual step of copying FalkorDB connection settings, LLM/embedding provider config, and group IDs when initializing a new project.

## Context

Currently `write_graphiti_config()` in `guardkit/cli/init.py` only writes the `project_id` field. When creating a new project (e.g., `guardkit init fastapi-python -n vllm-profiling`), the user must manually copy ~15 fields from an existing project's `.guardkit/graphiti.yaml`. This is error-prone and a poor developer experience.

Identified during review TASK-REV-5842 (review of vLLM profiling project setup).

## Requirements

1. Add `--copy-graphiti` Click option that takes an **optional** path argument (default: auto-discover)
2. Auto-discovery: search parent directories of cwd for an existing `.guardkit/graphiti.yaml` using the existing `_find_project_root()` pattern from `guardkit/knowledge/config.py`
3. When source config found: load it, replace `project_id` with the new normalized project name, write full config to target
4. When source config NOT found: warn and fall back to current behavior (write `project_id` only)
5. Preserve comments where possible (or accept clean yaml.dump output)
6. The explicit path form `--copy-graphiti ~/path/to/project` should also work

## Key Files

- `guardkit/cli/init.py` - `write_graphiti_config()`, Click command definition, `_cmd_init()`
- `guardkit/knowledge/config.py` - `_find_project_root()`, `get_config_path()` (reference for discovery pattern)
- `tests/cli/test_init.py` - Existing test patterns
- `.guardkit/graphiti.yaml` - Example of a complete config file

## Acceptance Criteria

- [x] `guardkit init fastapi-python -n vllm-profiling --copy-graphiti auto` auto-discovers and copies config from parent project
- [x] `guardkit init fastapi-python -n vllm-profiling --copy-graphiti /path/to/project` copies from explicit path
- [x] Only `project_id` is changed in the copied config; all other fields preserved
- [x] Graceful fallback with warning when no source config is found
- [x] Existing behavior unchanged when `--copy-graphiti` is not used
- [x] Tests cover: auto-discovery, explicit path, no source found, project_id replacement

## Implementation Notes

### Changes Made

**guardkit/cli/init.py:**
- Added `_find_source_graphiti_config(copy_graphiti: str) -> Optional[Path]` - auto-discovers or resolves explicit path to source graphiti.yaml
- Added `copy_graphiti_config(project_name, target_dir, source_config) -> bool` - copies full config with project_id replacement
- Updated `_cmd_init()` with `copy_graphiti` parameter and fallback logic
- Added `--copy-graphiti` Click option to `init` command

**tests/cli/test_init.py:**
- `TestFindSourceGraphitiConfig` (6 tests): auto-discovery, explicit path, tilde expansion, parent-not-cwd search
- `TestCopyGraphitiConfig` (5 tests): full copy, normalization, dir creation, validation, group_ids preservation
- `TestCopyGraphitiFlagCLI` (7 tests): CLI help, auto mode, explicit path, fallbacks, existing behavior, end-to-end

### CLI Interface

```bash
guardkit init --copy-graphiti auto              # Auto-discover from parent directories
guardkit init --copy-graphiti /path/to/project  # Explicit source path
guardkit init                                    # Existing behavior (project_id only)
```

## Test Execution Log

83 tests passed in 2.19s. All tests passing at 100%.
