---
id: TASK-SP-001
title: Create architecture entity definitions
status: in_review
task_type: scaffolding
parent_review: TASK-REV-DBBC
feature_id: FEAT-SP-001
wave: 1
implementation_mode: task-work
complexity: 4
dependencies: []
tags:
- system-plan
- entities
- graphiti
autobuild_state:
  current_turn: 1
  max_turns: 25
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-6EDD
  base_branch: main
  started_at: '2026-02-09T08:03:41.777815'
  last_updated: '2026-02-09T08:16:46.565562'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-09T08:03:41.777815'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Create Architecture Entity Definitions

## Description

Create the data model layer for `/system-plan` — the entity dataclasses that represent architecture knowledge. These are pure data structures with `to_episode_body()` methods following the ADR-GBF-001 convention (domain data only, no `_metadata`).

## Acceptance Criteria

- [ ] `ComponentDef` dataclass with methodology-aware `to_episode_body()` (DDD fields only when methodology=="ddd")
- [ ] `SystemContextDef` dataclass with stable `entity_id` property (format: `SYS-{slug}`)
- [ ] `CrosscuttingConcernDef` dataclass with stable `entity_id` property (format: `XC-{slug}`)
- [ ] `ArchitectureDecision` dataclass with stable `entity_id` property (format: `ADR-SP-{NNN}`)
- [ ] `ArchitectureContext` dataclass with `format_for_prompt()` for coach/feature-plan integration
- [ ] All `entity_id` properties are deterministic (same input → same ID)
- [ ] No `_metadata` in any `to_episode_body()` output
- [ ] DDD fields (`aggregate_roots`, `domain_events`, `context_mapping`) omitted from body when methodology != "ddd"
- [ ] `entity_type` property returns `"bounded_context"` for DDD, `"component"` for others
- [ ] Unit tests: >=85% coverage on all entity definitions

## Files to Create

- `guardkit/knowledge/entities/component.py` — ComponentDef
- `guardkit/knowledge/entities/system_context.py` — SystemContextDef
- `guardkit/knowledge/entities/crosscutting.py` — CrosscuttingConcernDef
- `guardkit/knowledge/entities/architecture_context.py` — ArchitectureContext + ArchitectureDecision
- `guardkit/knowledge/entities/__init__.py` — Update exports
- `tests/unit/knowledge/test_architecture_entities.py` — Unit tests

## Implementation Notes

- Follow existing pattern in `guardkit/knowledge/entities/feature_overview.py`
- Use `@dataclass` (not Pydantic) — these are internal state containers
- Use `field(default_factory=list)` for mutable defaults
- `ArchitectureContext.format_for_prompt()` should filter facts by score > 0.5 and respect token budget
- `ArchitectureContext.empty()` classmethod for graceful degradation
- Entity ID slugification: `name.lower().replace(" ", "-")[:30]`

## Seam Test Points

- `to_episode_body()` output is JSON-serializable via `json.dumps()`
- `entity_id` is stable across multiple instantiations with same name
- DDD vs non-DDD body content conditional on methodology field
