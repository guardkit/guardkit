---
autobuild_state:
  base_branch: main
  current_turn: 1
  last_updated: '2026-02-09T12:21:21.543237'
  max_turns: 25
  started_at: '2026-02-09T12:10:32.865958'
  turns:
  - coach_success: true
    decision: approve
    feedback: null
    player_success: true
    player_summary: Implementation via task-work delegation
    timestamp: '2026-02-09T12:10:32.865958'
    turn: 1
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-6EDD
complexity: 6
dependencies:
- TASK-SP-001
feature_id: FEAT-SP-001
id: TASK-SP-003
implementation_mode: task-work
parent_review: TASK-REV-DBBC
status: design_approved
tags:
- system-plan
- graphiti
- persistence
task_type: feature
title: Implement SystemPlanGraphiti read/write operations
wave: 2
---

# Task: Implement SystemPlanGraphiti Read/Write Operations

## Description

Create the `SystemPlanGraphiti` class that encapsulates all Graphiti read/write operations for `/system-plan`. This is the persistence layer that bridges entity definitions (Wave 1) with the interactive command (Wave 3).

## Acceptance Criteria

- [ ] `SystemPlanGraphiti` class with `client` and `project_id` constructor params
- [ ] `_available` property checks `client is not None and client.enabled`
- [ ] `upsert_component(component: ComponentDef) -> Optional[str]` — upserts with stable entity_id
- [ ] `upsert_adr(adr: ArchitectureDecision) -> Optional[str]` — upserts with ADR-SP-NNN entity_id
- [ ] `upsert_system_context(system: SystemContextDef) -> Optional[str]` — upserts system context
- [ ] `upsert_crosscutting(concern: CrosscuttingConcernDef) -> Optional[str]` — upserts concern
- [ ] `has_architecture_context() -> bool` — quick check for mode detection
- [ ] `get_architecture_summary() -> Optional[dict]` — retrieves architecture + decision facts
- [ ] `get_relevant_context_for_topic(topic: str, num_results: int) -> List[Dict]` — semantic search
- [ ] All write operations use `client.get_group_id()` for correct group prefixing
- [ ] All write operations use `upsert_episode()` (NOT `add_episode()`)
- [ ] All operations have graceful degradation (return None/[]/False on failure or disabled client)
- [ ] `[Graphiti]` prefix on all log messages
- [ ] Unit tests: mock GraphitiClient, verify correct API calls and params
- [ ] >=85% coverage

## Files to Create

- `guardkit/planning/graphiti_arch.py` — SystemPlanGraphiti class
- `tests/unit/planning/test_graphiti_arch.py` — Unit tests

## Implementation Notes

- Follow pattern from `guardkit/knowledge/adr_service.py` for Graphiti write operations
- Use `json.dumps(entity.to_episode_body())` for episode_body parameter
- Group IDs: `"project_architecture"` for components/system/crosscutting, `"project_decisions"` for ADRs
- Both groups already in `GraphitiClient.PROJECT_GROUP_NAMES` — no registration needed
- `search()` returns `List[Dict[str, Any]]` with `{"uuid", "fact", "name", "score"}` shape
- Use `num_results` parameter (not `limit`) for search calls

## Seam Test Points

- `entity.to_episode_body()` → `json.dumps()` → `upsert_episode()` pipeline
- `client.get_group_id("project_architecture")` returns `{project_id}__project_architecture`
- `client.search()` called with `num_results` (not `limit`)
- All methods return None/[]/False when `client.enabled == False`
- All methods handle exceptions with warning log and graceful return