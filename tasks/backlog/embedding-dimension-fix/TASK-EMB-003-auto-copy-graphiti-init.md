---
id: TASK-EMB-003
title: Auto-offer --copy-graphiti during guardkit init when parent yaml exists
status: backlog
created: 2026-03-09T00:00:00Z
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

- [ ] During `guardkit init`, if a `.guardkit/graphiti.yaml` exists in a parent directory, auto-detect and prompt:
  ```
  Found existing graphiti.yaml at ../guardkit/.guardkit/graphiti.yaml
  Copy infrastructure config to this project? [Y/n]:
  ```
- [ ] If user accepts (or default), copy full yaml with project_id replaced
- [ ] If user declines, proceed with project_id-only yaml (current behavior)
- [ ] `--copy-graphiti` flag still works as before (explicit auto-discover)
- [ ] `--no-questions` flag skips prompt and uses project_id-only (backward compatible)
- [ ] Tests cover: prompt shown, Y accepted, n declined, --no-questions skips

## Key Files

- `guardkit/cli/init.py` — `_cmd_init()`, `write_graphiti_config()`, `_find_source_graphiti_config()`

## Implementation Notes

In `_cmd_init()`, after applying the template, check if `--copy-graphiti` was NOT specified but a parent graphiti.yaml exists. If so, prompt the user. The `_find_source_graphiti_config("auto")` function already does parent discovery.
