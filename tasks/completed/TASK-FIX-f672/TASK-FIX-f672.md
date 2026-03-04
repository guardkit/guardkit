---
id: TASK-FIX-f672
title: Raise episode timeout for project_overview group to 180s
status: completed
task_type: implementation
created: 2026-03-04T12:00:00Z
updated: 2026-03-04T14:05:00Z
completed: 2026-03-04T14:05:00Z
completed_location: tasks/completed/TASK-FIX-f672/
priority: high
tags: [graphiti, timeout, project-overview, seeding]
complexity: 1
parent_review: TASK-REV-FE10
feature_id: FEAT-init-graphiti-remaining-fixes
wave: 1
implementation_mode: direct
dependencies: []
---

# Task: Raise episode timeout for project_overview group to 180s

## Description

Use a higher timeout (180s) for `project_overview` group episodes in `_create_episode()`. The current uniform 120s timeout causes the two most valuable knowledge graph episodes (`project_purpose` and `project_architecture`) to timeout during `guardkit init`.

These episodes contain unique per-project content parsed from CLAUDE.md — unlike agents/rules which are generic templates. They are the primary content searched via `guardkit graphiti search`.

## Evidence

From init_project_4.md:
- Episode 1 (`project_purpose_vllm-profiling`): **timed out at 120s**
- Episode 3 (`project_architecture_vllm-profiling`): **timed out at 120s**
- Episode 6 (role constraint, similar complexity): succeeded at 99.7s
- Episode 2 (different section): succeeded at 64.1s

The extraction pipeline involves ~40-80 LLM calls per episode. With OpenAI API latency at ~1-2s per call, the purpose/architecture episodes need ~130-150s — just over the 120s ceiling.

## Files to Modify

- `guardkit/knowledge/graphiti_client.py` — change timeout logic in `_create_episode()` (line 880)
- `tests/knowledge/test_graphiti_client.py` — add test for group-specific timeout

## Implementation

```python
# BEFORE (graphiti_client.py:880):
episode_timeout = 120.0  # 2 minutes max per episode

# AFTER:
episode_timeout = 180.0 if group_id == "project_overview" else 120.0
```

The `group_id` parameter is already available in `_create_episode()` — it's passed as a parameter on line 867.

## Why 180s

- Episode 6 (similar complexity) completed at 99.7s
- Episodes 1 and 3 need ~130-150s based on LLM call analysis
- 180s provides a 20-30% margin above estimated need
- Worst case: 60s longer wait per timeout (if episode still fails)
- Best case: both episodes succeed, project knowledge captured

## Acceptance Criteria

- [x] `_create_episode()` uses 180s timeout for `project_overview` group
- [x] Other groups retain 120s timeout
- [x] Tests pass (61 passed, 2 skipped integration)
- [x] `guardkit init` Step 2 `project_purpose` and `project_architecture` episodes more likely to succeed
