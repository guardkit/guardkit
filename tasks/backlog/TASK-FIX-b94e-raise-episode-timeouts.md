---
id: TASK-FIX-b94e
title: Raise episode timeouts for rules (180s) and project_overview (240s)
status: completed
task_type: implementation
created: 2026-03-04T00:00:00Z
updated: 2026-03-04T00:00:00Z
priority: high
tags: [graphiti, falkordb, timeout, init, performance]
complexity: 1
parent_review: TASK-REV-EE12
feature_id: FEAT-init-graphiti-remaining-fixes
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Raise episode timeouts for rules (180s) and project_overview (240s)

## Description

Single-line code change in `graphiti_client.py:880` to raise episode timeouts for two specific groups:

- **rules**: 120s → 180s (6/12 rules timing out at 120s; actual processing time ~121-150s based on cross-run analysis)
- **project_overview**: 180s → 240s (episodes at 171.7s and 176.7s with only 1.8-4.6% headroom)
- **all other groups**: remain at 120s (agents at 48-64s, templates at 104s — comfortable)

## Root Cause (from TASK-REV-EE12)

Rule timeouts are caused by graph-size scaling in graphiti-core's LLM deduplication pipeline, NOT by payload size (all rule payloads are ~900-1100 bytes). Successfully seeding more content (from TASK-FIX-9d45 and TASK-FIX-f672 fixes) created a larger graph, pushing borderline rules over the 120s ceiling.

## Change

**File**: `guardkit/knowledge/graphiti_client.py:880`

```python
# BEFORE:
episode_timeout = 180.0 if group_id.endswith("project_overview") else 120.0

# AFTER:
if group_id.endswith("project_overview"):
    episode_timeout = 240.0
elif group_id == "rules":
    episode_timeout = 180.0
else:
    episode_timeout = 120.0
```

## Expected Impact

- Rule sync success: 50% → 83-100% (6/12 → 10-12/12)
- Project overview reliability: marginal → robust (35% headroom instead of 1.8%)
- Total init time: roughly similar (~35-40 min), but with dramatically more content in the knowledge graph

## Acceptance Criteria

- [x] Timeout logic updated in `_create_episode()`
- [x] project_overview episodes use 240s timeout
- [x] rules episodes use 180s timeout
- [x] all other groups retain 120s timeout
- [x] Existing tests updated and pass (61 passed, 2 skipped)
