---
complexity: 7
dependencies:
- TASK-SP-003
- TASK-SP-005
- TASK-SP-006
feature_id: FEAT-SP-001
id: TASK-SP-008
implementation_mode: task-work
parent_review: TASK-REV-DBBC
status: design_approved
tags:
- system-plan
- testing
- integration
- e2e
- seams
task_type: testing
title: Create integration and end-to-end seam tests
wave: 4
---

# Task: Create Integration and End-to-End Seam Tests

## Description

Create comprehensive integration and end-to-end tests specifically targeting the technology seams in the `/system-plan` feature. These tests validate the boundaries between components where errors historically occur in GuardKit features: entity serialization, async boundaries, Graphiti API correctness, template rendering, and CLI wiring.

## Acceptance Criteria

### Seam 1: Entity Serialization Pipeline
- [ ] Test: `ComponentDef.to_episode_body()` → `json.dumps()` → valid JSON string
- [ ] Test: `ArchitectureDecision.to_episode_body()` → `json.dumps()` → valid JSON string
- [ ] Test: All entity types produce JSON that `json.loads()` can round-trip
- [ ] Test: DDD entity body contains `aggregate_roots`; modular entity body does NOT

### Seam 2: Async/Sync Boundary
- [ ] Test: `asyncio.run()` wrapping of `detect_mode()` works in sync context
- [ ] Test: `asyncio.run()` wrapping of `SystemPlanGraphiti.upsert_component()` works in sync context
- [ ] Test: No nested event loop errors when called from CLI layer

### Seam 3: Group ID Prefixing
- [ ] Test: `upsert_component()` calls `client.get_group_id("project_architecture")` (not hardcoded)
- [ ] Test: `upsert_adr()` calls `client.get_group_id("project_decisions")` (not hardcoded)
- [ ] Test: Group ID includes project prefix: `{project_id}__project_architecture`

### Seam 4: Upsert Idempotency
- [ ] Test: Calling `upsert_component()` twice with same ComponentDef → `upsert_episode()` called twice with same `entity_id`
- [ ] Test: Same `entity_id` passed both times (verifies deduplication intent)

### Seam 5: Graceful Degradation
- [ ] Test: All `SystemPlanGraphiti` methods return None/[]/False when `client is None`
- [ ] Test: All `SystemPlanGraphiti` methods return None/[]/False when `client.enabled == False`
- [ ] Test: `detect_mode()` returns "setup" when Graphiti unavailable
- [ ] Test: `ArchitectureContext.empty()` returns usable empty context
- [ ] Test: CLI command completes without error when Graphiti is None

### Seam 6: Template Rendering
- [ ] Test: `ArchitectureWriter.write_all()` produces all expected files for modular methodology
- [ ] Test: `ArchitectureWriter.write_all()` produces `bounded-contexts.md` (not `components.md`) for DDD
- [ ] Test: Generated system-context.md contains valid mermaid diagram syntax
- [ ] Test: Generated ADR files follow Michael Nygard format
- [ ] Test: Empty component list → no crash, still produces index file

### Seam 7: CLI Registration
- [ ] Test: `guardkit system-plan --help` returns valid help text (Click integration)
- [ ] Test: `--mode` flag accepts only `setup|refine|review`
- [ ] Test: `--focus` flag accepts only `domains|services|decisions|crosscutting|all`
- [ ] Test: Unknown flags are rejected

### Seam 8: Context Assembly (format_for_prompt)
- [ ] Test: `ArchitectureContext.format_for_prompt()` produces non-empty string when facts present
- [ ] Test: `ArchitectureContext.format_for_prompt()` filters facts by score > 0.5
- [ ] Test: `ArchitectureContext.format_for_prompt()` returns empty string when no high-score facts
- [ ] Test: Token budget is respected (output doesn't exceed max_tokens worth of content)

### Seam 9: Feature-Plan Integration
- [ ] Test: `load_architecture_context()` returns `ArchitectureContext` with populated facts from mock Graphiti
- [ ] Test: `load_architecture_context()` returns `ArchitectureContext.empty()` when no architecture exists
- [ ] Test: `ArchitectureContext.has_context` is True when component_facts or decision_facts present
- [ ] Test: `ArchitectureContext.has_context` is False when all fact lists empty

### Search API Shape
- [ ] Test: `get_architecture_summary()` uses `num_results` parameter (not `limit`)
- [ ] Test: `get_relevant_context_for_topic()` searches both architecture and decisions groups

## Files to Create

- `tests/integration/test_system_plan_seams.py` — Integration tests for all 9 seams
- `tests/integration/test_system_plan_e2e.py` — End-to-end flow tests (setup mode with mock Graphiti)

## Implementation Notes

- Use `AsyncMock` for all Graphiti client mocking (no real Neo4j dependency)
- Use `tmp_path` fixture for file system tests (template rendering)
- Use Click's `CliRunner` for CLI integration tests
- Group tests by seam for clarity: `class TestSeam1_EntitySerialization`, etc.
- E2E test: exercise full setup flow with mocked Graphiti and verify both file output AND Graphiti calls
- Follow test pattern from `tests/unit/knowledge/test_feature_plan_context_builder.py`

## Why This Task Exists

Historical GuardKit features have had errors at technology seams:
- Entity serialization mismatches (TASK-FIX-CKPT: JSON path mismatch)
- Async/sync confusion (TASK-FIX-GCI0: `await` on sync function)
- Null handling at boundaries (TASK-FIX-64EE: null quality gates)
- Group ID mistakes (hardcoded vs `get_group_id()`)
- Search API misuse (`limit` vs `num_results`)

These seam tests are designed to catch exactly these error patterns before they reach production.