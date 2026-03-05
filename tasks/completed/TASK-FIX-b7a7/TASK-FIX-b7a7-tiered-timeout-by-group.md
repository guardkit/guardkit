---
id: TASK-FIX-b7a7
title: Expand tiered episode timeouts for role_constraints and agents groups
status: completed
completed: 2026-03-04T00:00:00Z
task_type: implementation
created: 2026-03-04T00:00:00Z
updated: 2026-03-04T00:00:00Z
priority: high
tags: [graphiti, falkordb, timeout, init, performance]
complexity: 2
parent_review: TASK-REV-BAC1
feature_id: FEAT-init-graphiti-remaining-fixes
test_results:
  status: passed
  coverage: 100
  last_run: 2026-03-04T00:00:00Z
---

# Task: Expand tiered episode timeouts for role_constraints and agents groups

## Description

Expand the existing tiered timeout conditional in `_create_episode()` to cover two additional groups that are timing out at the default 120s ceiling:

- **role_constraints**: coach episode hit 120.0s exactly (was 116.2s in init_project_5, needs ~130-135s)
- **agents**: fastapi-testing-specialist hit 120.0s (was 64.0s in init_project_5, needs ~130-140s with graph growth)
- **project_overview**: raise from 240s to 300s (project_architecture hit 240.0s ceiling exactly)

## Root Cause (from TASK-REV-BAC1 deep analysis)

The `_create_episode()` timeout conditional only handles `project_overview` (240s) and `rules` (180s). All other group_ids fall to the default 120s bucket, including `role_constraints` and `agents` which have borderline episodes that crossed the 120s ceiling due to graph-size scaling from `--copy-graphiti-from` amplification.

The fundamental bottleneck is graphiti-core's O(edges × graph_size) edge deduplication pipeline. GuardKit's timeout is the control boundary where this manifests.

## Change

**File**: `guardkit/knowledge/graphiti_client.py` (around line 880)

```python
# BEFORE:
if group_id.endswith("project_overview"):
    episode_timeout = 240.0
elif group_id == "rules":
    episode_timeout = 180.0
else:
    episode_timeout = 120.0

# AFTER:
if group_id.endswith("project_overview"):
    episode_timeout = 300.0   # Was 240s; project_architecture hit ceiling
elif group_id == "rules":
    episode_timeout = 180.0   # Working for 10/12 rules
elif group_id == "role_constraints":
    episode_timeout = 150.0   # Coach at 120s needs ~130s with growth
elif group_id == "agents":
    episode_timeout = 150.0   # testing-specialist at 120s needs ~130s
else:
    episode_timeout = 120.0   # templates, implementation_modes: safe
```

## Expected Impact

| Episode | Current Ceiling | Proposed | Expected Result |
|---------|----------------|----------|-----------------|
| project_architecture | 240s | 300s | SUCCESS (~260-280s) |
| role_constraint_coach | 120s | 150s | SUCCESS (~125-135s) |
| agent testing-specialist | 120s | 150s | LIKELY SUCCESS (~120-135s) |
| rule_crud | 180s | 180s | Still fails (needs ~200s+) |
| rule_schemas | 180s | 180s | Still fails (needs ~200s+) |

Net: 17/24 → 19-20/24 items synced (~80% → ~83%).

## Acceptance Criteria

- [x] Timeout logic expanded in `_create_episode()` with 5 tiers
- [x] project_overview uses 300s timeout
- [x] rules uses 180s timeout (unchanged)
- [x] role_constraints uses 150s timeout
- [x] agents uses 150s timeout
- [x] All other groups retain 120s default
- [x] Existing tests updated and pass
