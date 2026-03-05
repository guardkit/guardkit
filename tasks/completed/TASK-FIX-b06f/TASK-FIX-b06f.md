---
id: TASK-FIX-b06f
title: Add "templates" to 180s timeout tier in graphiti_client.py
status: completed
task_type: implementation
created: 2026-03-04T00:00:00Z
updated: 2026-03-04T00:00:00Z
completed: 2026-03-04T00:00:00Z
completed_location: tasks/completed/TASK-FIX-b06f/
priority: high
tags: [graphiti, falkordb, timeout, seeding, circuit-breaker]
complexity: 1
parent_review: TASK-REV-49AB
feature_id: FEAT-SQF
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Add "templates" to 180s timeout tier

## Description

Add `"templates"` as an explicit timeout tier in `_create_episode()` at 180s. Currently `"templates"` falls through to the default 120s tier, but template episodes (nextjs-fullstack, react-fastapi-monorepo, react-typescript) need 111-150s on a clean graph, causing 3 consecutive timeouts at exactly 120s which trips the circuit breaker and silently skips all subsequent seed categories.

## Root Cause (from TASK-REV-49AB)

- `seed_templates.py:158` calls `_add_episodes(client, episodes, "templates", ...)`
- `"templates"` is in `SYSTEM_GROUP_IDS` (`_group_defs.py:40`) → no prefix applied
- `_create_episode()` receives `group_id="templates"` (`graphiti_client.py:863-899`)
- Timeout logic: `"templates"` doesn't match `endswith("project_overview")`, `== "rules"`, `== "role_constraints"`, or `== "agents"` → falls to default 120s
- 3 consecutive timeouts → circuit breaker trips → categories 11-17 all return None silently

## Change

**File**: `guardkit/knowledge/graphiti_client.py:897`

```python
# BEFORE (line 897-899):
        elif group_id == "agents":
            episode_timeout = 150.0   # testing-specialist at 120s needs ~130s
        else:
            episode_timeout = 120.0   # templates, implementation_modes: safe

# AFTER:
        elif group_id == "agents":
            episode_timeout = 150.0   # testing-specialist at 120s needs ~130s
        elif group_id == "templates":
            episode_timeout = 180.0   # template manifests need 111-150s on clean graph
        else:
            episode_timeout = 120.0   # implementation_modes etc: safe
```

## Evidence

From `reseed_init_project_8.md`:
- `template_default`: 15,164ms (15s) — small manifest, OK at 120s
- `template_fastapi_python`: 111,569ms (111s) — borderline at 120s
- `template_react_fastapi_monorepo`: TIMEOUT at 120,000ms
- `template_nextjs_fullstack`: TIMEOUT at 120,000ms
- `template_react_typescript`: TIMEOUT at 120,000ms

With 180s tier, these should complete (init_6 had template at 98.3s; the 120s timeouts suggest 120-150s actual processing).

## Regression Risk

**None** — additive condition, only changes timeout for `"templates"` group_id. No logic change. All other tiers unaffected.

## Acceptance Criteria

- [ ] `elif group_id == "templates": episode_timeout = 180.0` added before the `else` clause
- [ ] Comment updated to remove "templates" from the "safe" list in the else clause
- [ ] Existing tests pass (timeout tier tests in `test_graphiti_client.py`)
- [ ] New test: verify `"templates"` gets 180s timeout
