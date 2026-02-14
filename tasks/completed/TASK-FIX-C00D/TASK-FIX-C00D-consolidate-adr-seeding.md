---
id: TASK-FIX-C00D
title: Consolidate ADR seeding and integrate into main seed
status: completed
created: 2026-02-12T00:00:00Z
updated: 2026-02-12T00:00:00Z
completed: 2026-02-12T00:00:00Z
priority: high
tags: [graphiti, seeding, adr, falkordb]
parent_review: TASK-REV-3ECA
complexity: 3
---

# Task: Consolidate ADR seeding and integrate into main seed

## Description

Currently ADR seeding is fragmented:
- `seed_architecture_decisions.py` (in main seed) has 3 **condensed** feature-build lessons
- `seed_feature_build_adrs.py` (separate `seed-adrs` CLI only) has 3 **full** feature-build ADRs
- 9 project ADRs on disk are not seeded at all

Consolidate by replacing the condensed duplicates with the full versions, integrating into the main seed, and adding guidance for project ADR seeding.

## Context

- Parent review: TASK-REV-3ECA (FINDING-4 + FINDING-5)
- `seed_architecture_decisions.py` and `seed_feature_build_adrs.py` both seed the same 3 decisions (SDK invocation, FEAT-XXX paths, pre-loop design phase) but with different detail levels
- The full ADRs in `seed_feature_build_adrs.py` include context, rejected alternatives, and violation symptoms that the condensed versions lack

## Changes Required

### 1. Replace condensed episodes with full ADR seeding

In `seed_architecture_decisions.py`, replace the 3 inline episodes with a delegation to `seed_feature_build_adrs()`:

```python
async def seed_architecture_decisions(client) -> None:
    """Seed architecture decisions including feature-build ADRs."""
    if not client or not client.enabled:
        return
    from guardkit.knowledge.seed_feature_build_adrs import seed_feature_build_adrs
    await seed_feature_build_adrs(client)
```

### 2. Add post-seed hint for project ADRs

In `_cmd_seed()` success output (graphiti.py), after the category list, add:

```
To seed project ADRs:
  guardkit graphiti add-context docs/adr/ --type adr
```

### 3. Update tests

- Update test that asserts `seed_architecture_decisions` creates 3 episodes (it will now create 3 via delegation)
- The episode count stays the same (3) but episode names change from `issue_*` to `adr_fb_*`

## Project ADRs (for reference, seeded via add-context)

| ADR | File | Status | Priority |
|-----|------|--------|----------|
| Adopt GuardKit | `0001-adopt-agentic-flow.md` | Accepted | HIGH |
| Graphiti Integration Scope | `ADR-001-graphiti-integration-scope.md` | Accepted | HIGH |
| FalkorDB Migration | `ADR-003-falkordb-migration.md` | Accepted | HIGH |
| Episode Upsert Strategy | `ADR-GR-001-upsert-strategy.md` | Accepted | HIGH |
| Unified Episode Serialization | `ADR-GBF-001-unified-episode-serialization.md` | Accepted | MEDIUM |
| Upfront Complexity | `ADR-005-upfront-complexity-refactored-architecture.md` | Proposed | MEDIUM |
| Figma-React | `ADR-002-figma-react-architecture.md` | Proposed | LOW |
| Remove guardkit-python | `0003-remove-taskwright-python-template.md` | Accepted | LOW |
| Agent Discovery | `docs/adrs/ADR-002-agent-discovery-strategy.md` | Proposed | LOW |

## Acceptance Criteria

- [x] AC-001: `seed_architecture_decisions()` delegates to `seed_feature_build_adrs()` (no duplicate condensed episodes)
- [x] AC-002: `guardkit graphiti seed --force` seeds full ADR-FB-001/002/003 via `architecture_decisions` category
- [x] AC-003: Post-seed output includes hint about `add-context` for project ADRs
- [x] AC-004: Existing tests updated and passing
- [x] AC-005: No regressions in `test_seeding.py`

## Files to Change

- `guardkit/knowledge/seed_architecture_decisions.py` - Replace with delegation
- `guardkit/cli/graphiti.py` - Add post-seed hint
- `tests/knowledge/test_seeding.py` - Update architecture decisions test assertions
