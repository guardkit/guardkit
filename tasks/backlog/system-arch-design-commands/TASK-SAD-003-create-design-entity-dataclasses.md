---
id: TASK-SAD-003
title: "Create DesignDecision, ApiContract, and DataModel entity dataclasses"
task_type: feature
parent_review: TASK-REV-AEE1
feature_id: FEAT-SAD
wave: 1
implementation_mode: task-work
complexity: 5
dependencies: []
---

# Task: Create DesignDecision, ApiContract, and DataModel entity dataclasses

## Description

Create three new entity dataclasses for `/system-design` artefacts. These follow the existing pattern established by `ArchitectureDecision`, `ComponentDef`, `SystemContextDef`, and `CrosscuttingConcernDef` in `guardkit/knowledge/entities/`.

## Acceptance Criteria

- [ ] Create `guardkit/knowledge/entities/design_decision.py` with `DesignDecision` dataclass
  - Fields: number, title, context, decision, rationale, alternatives_considered, consequences, related_components, status, superseded_by, supersedes
  - `entity_id` property: `DDR-{NNN:03d}`
  - `to_episode_body()` method
- [ ] Create `guardkit/knowledge/entities/api_contract.py` with `ApiContract` dataclass
  - Fields: bounded_context, consumer_types (list), endpoints (list of dicts), protocol (REST/GraphQL/MCP/A2A/ACP), version
  - `entity_id` property: `API-{bounded_context_slug}`
  - `to_episode_body()` method
- [ ] Create `guardkit/knowledge/entities/data_model.py` with `DataModel` dataclass
  - Fields: entities (list of dicts with name, attributes, relationships), invariants, bounded_context
  - `entity_id` property: `DM-{bounded_context_slug}`
  - `to_episode_body()` method
- [ ] All three entities follow the established pattern (frozen dataclass, entity_id property, to_episode_body)
- [ ] Unit tests for each entity class (creation, entity_id, serialisation)
- [ ] Register entities in `guardkit/knowledge/entities/__init__.py`

## Implementation Notes

- Follow the pattern in `guardkit/knowledge/entities/architecture_context.py`
- Use `@dataclass` (not Pydantic) — consistent with existing entities
- DDR numbering: scanner function `scan_next_ddr_number()` needed (parallel to ADR scanner)
- API contracts support multiple protocols per bounded context (web + agent consumers)
