---
id: TASK-SPR-18fc
title: Split rules into logical batches to reduce circuit breaker exposure
status: completed
task_type: implementation
created: 2026-03-05T12:00:00Z
completed: 2026-03-05T14:00:00Z
priority: high
complexity: 5
parent_review: TASK-REV-F404
feature_id: FEAT-SPR
tags: [graphiti, seeding, rules, episode-splitting]
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Split rules into logical batches to reduce circuit breaker exposure

## Problem

The rules category has 72 individual episodes — the largest single category. With a 180s timeout per episode, 3 consecutive timeouts (540s total) trip the circuit breaker. The remaining 68+ rules then get instant-skipped. Result: **1/72 rules seeded** (98.6% failure rate).

### Evidence (from TASK-REV-F404 final seed)

```
INFO:guardkit.knowledge.seed_rules:Seeding 72 rule episodes from .../installer/core/templates
WARNING:guardkit.knowledge.seeding:  Seeded rules: 1/72 episodes (71 skipped)
```

## Solution

Group the 72 rules into logical batches of 5-10 by template, registering each batch as a separate seeding category in the orchestrator. This reduces circuit breaker exposure per batch and prevents a single slow template's rules from blocking all others.

### Approach

1. **Discover rules grouped by template** (already done in `seed_rules.py` — iterates `template_entry` in `sorted(templates_dir.iterdir())`)
2. **Register each template's rules as a separate category** in the orchestrator:
   ```python
   # Instead of one "rules" category:
   categories = [
       ...
       ("rules_default", "seed_rules_default"),
       ("rules_fastapi_python", "seed_rules_fastapi_python"),
       ("rules_nextjs_fullstack", "seed_rules_nextjs"),
       ("rules_react_typescript", "seed_rules_react"),
       ...
   ]
   ```
3. **Or batch within `seed_rules`** itself, yielding per-template results:
   ```python
   async def seed_rules(client) -> tuple[int, int]:
       total_created, total_skipped = 0, 0
       for template_id, episodes in episodes_by_template.items():
           created, skipped = await _add_episodes(
               client, episodes, f"rules_{template_id}", f"rules/{template_id}"
           )
           total_created += created
           total_skipped += skipped
       return (total_created, total_skipped)
   ```

### Key consideration

If combined with TASK-SPR-5399 (circuit breaker reset between categories), batching may be less critical. However, batching still improves:
- Per-template failure isolation
- More granular logging
- Better timeout management (different template rules may need different timeouts)

## Files Modified

- `guardkit/knowledge/seed_rules.py` — Batched by template with circuit breaker reset
- `tests/knowledge/test_seed_rules.py` — 25 new tests for batched behavior
- `tests/knowledge/test_seed_enrichment.py` — Updated group_id test for per-template convention

## Acceptance Criteria

- [x] Rules are seeded in per-template batches (not one monolithic batch)
- [x] Circuit breaker failures in one template's rules don't block other templates
- [x] Logging shows per-template results (e.g., "rules/fastapi-python: 8/10 episodes")
- [x] Total rules seeded significantly improves from 1/72
- [x] Existing tests pass
