---
id: TASK-EMB-003
title: Auto-offer --copy-graphiti during guardkit init when parent yaml exists
status: completed
created: 2026-03-09T00:00:00Z
updated: 2026-03-09T00:00:00Z
completed: 2026-03-09T00:00:00Z
priority: high
tags: [init, graphiti, config, ux]
task_type: implementation
complexity: 4
parent_review: TASK-REV-D2B5
feature_id: FEAT-EMB
wave: 2
implementation_mode: task-work
dependencies: []
---

# Task: Auto-offer --copy-graphiti during guardkit init

## Description

When `guardkit init` is run without `--copy-graphiti`, it only writes `project_id` to `graphiti.yaml`. If a parent directory has a complete `graphiti.yaml`, the user should be prompted to copy it. This prevents sparse configs that lead to dimension mismatches on shared FalkorDB instances.

## Acceptance Criteria

- [x] During `guardkit init`, if a `.guardkit/graphiti.yaml` exists in a parent directory, auto-detect and prompt:
  ```
  Found existing graphiti.yaml at ../guardkit/.guardkit/graphiti.yaml
  Copy infrastructure config to this project? [Y/n]:
  ```
- [x] If user accepts (or default), copy full yaml with project_id replaced
- [x] If user declines, proceed with project_id-only yaml (current behavior)
- [x] `--copy-graphiti` flag still works as before (explicit auto-discover)
- [x] `--no-questions` flag skips prompt and uses project_id-only (backward compatible)
- [x] Tests cover: prompt shown, Y accepted, n declined, --no-questions skips

## Key Files

- `guardkit/cli/init.py` — `_cmd_init()`, `write_graphiti_config()`, `_find_source_graphiti_config()`

## Implementation Notes

In `_cmd_init()`, after applying the template, check if `--copy-graphiti` was NOT specified but a parent graphiti.yaml exists. If so, prompt the user. The `_find_source_graphiti_config("auto")` function already does parent discovery.

## Implementation Summary

### Changes Made

**`guardkit/cli/init.py`**:
- Added `no_questions: bool = False` parameter to `_cmd_init()`
- Replaced the simple `elif write_graphiti_config(...)` fallback with auto-offer logic:
  - `source_config = None if no_questions else _find_source_graphiti_config("auto")`
  - If a parent config is found, prints `Found existing graphiti.yaml at {path}` and prompts with `Confirm.ask(..., default=True)`
  - Y (default): calls `copy_graphiti_config()` with fallback to `write_graphiti_config()`
  - n: calls `write_graphiti_config()` (project_id-only)
  - `--no-questions`: skips auto-discovery, goes straight to `write_graphiti_config()`
- Added `--no-questions` click option to the `init()` command
- Passed `no_questions` to `_cmd_init()`

**`tests/cli/test_init.py`**:
- Updated `test_no_copy_graphiti_flag_uses_existing_behavior` to expect `_find_source_graphiti_config("auto")` to be called (returning None)
- Added 5 new tests in `TestCopyGraphitiFlagCLI`:
  - `test_auto_offer_prompt_shown_when_parent_config_found`
  - `test_auto_offer_y_accepted_copies_config`
  - `test_auto_offer_n_declined_uses_project_id_only`
  - `test_no_questions_skips_auto_offer_prompt`
  - `test_no_questions_flag_in_help`

### Test Results
92 tests passed (up from 87), 0 failed.
