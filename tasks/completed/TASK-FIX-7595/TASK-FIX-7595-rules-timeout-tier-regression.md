---
id: TASK-FIX-7595
title: Fix rules timeout tier regression from TASK-SPR-18fc per-template batching
status: completed
task_type: implementation
created: 2026-03-05T18:30:00Z
completed: 2026-03-05T19:00:00Z
priority: high
complexity: 2
parent_review: TASK-REV-5C55
feature_id: FEAT-SPR
tags: [graphiti, timeout, rules, regression, circuit-breaker, seeding]
dependencies: []
---

# Task: Fix rules timeout tier regression from TASK-SPR-18fc

## Problem

TASK-SPR-18fc changed `seed_rules.py:267` to use per-template group_ids:

```python
group_id = f"rules_{template_id}"  # e.g., "rules_fastapi_python"
```

But the timeout tier selection in `graphiti_client.py:975` still uses an exact match:

```python
elif group_id == "rules":
    episode_timeout = 180.0
```

After `_apply_group_prefix()`, the group_id becomes `"guardkit__rules_fastapi_python"`, which does NOT match `== "rules"`. Rules fall through to the `else` branch and get 120s instead of the intended 180s.

### Evidence (from reseed_guardkit_1 — post FEAT-SPR)

```
rules/default: 0/3 episodes (3 skipped)
rules/fastapi-python: 1/12 episodes (11 skipped)
rules/fastmcp-python: 0/11 episodes (11 skipped)
rules/mcp-typescript: 2/4 episodes (2 skipped)
rules/nextjs-fullstack: 8/12 episodes (4 skipped)
rules/react-fastapi-monorepo: 9/21 episodes (12 skipped)
rules/react-typescript: 5/9 episodes (4 skipped)

Total rules: 25/72 (34.7%) — 47 skipped
```

Successful rule episodes complete in 41-118s. At 180s timeout, episodes in the 120-180s range would succeed instead of timing out.

### Root Cause Chain

1. `seed_rules.py:267` → `group_id = "rules_fastapi_python"`
2. `graphiti_client.py:1106` → `_apply_group_prefix()` → `"guardkit__rules_fastapi_python"` (not in SYSTEM_GROUP_IDS)
3. `graphiti_client.py:975` → `group_id == "rules"` → **NO MATCH**
4. Falls to `else` at line 984 → **120s** instead of 180s

## Solution

Change the timeout tier matching at `graphiti_client.py:975` from exact match to substring match:

```python
# Before:
elif group_id == "rules":
    episode_timeout = 180.0

# After:
elif "rules" in group_id:
    episode_timeout = 180.0
```

This matches both:
- `"rules"` (bare, if ever used)
- `"guardkit__rules_fastapi_python"` (prefixed per-template)
- `"rules_fastapi_python"` (unprefixed per-template)

## Files to Modify

1. **`guardkit/knowledge/graphiti_client.py:975`** — Change `group_id == "rules"` to `"rules" in group_id`
2. **`tests/knowledge/test_graphiti_client.py`** — Add test verifying timeout tier for prefixed per-template group_ids

## Acceptance Criteria

- [ ] `"rules" in group_id` used at line 975 (or equivalent substring match)
- [ ] Rules episodes get 180s timeout regardless of per-template group_id format
- [ ] New test: `test_timeout_tier_rules_per_template_group_id` verifies 180s for `"guardkit__rules_fastapi_python"`
- [ ] New test: `test_timeout_tier_rules_bare_group_id` verifies 180s for `"rules"` (regression guard)
- [ ] Existing tests pass
- [ ] No changes to agents/templates timeout tiers (they use exact match and work correctly)

## Expected Impact

Rules success rate should improve from 25/72 (34.7%) to an estimated 40-50/72 (55-70%) as episodes that would complete between 120-180s stop being killed prematurely.

## Verification

After fix, run `guardkit graphiti seed --force` and check:
- Rules success rate (target: >60%)
- Total seed success rate (target: >75%)
- Circuit breaker trip count (target: <=2)
