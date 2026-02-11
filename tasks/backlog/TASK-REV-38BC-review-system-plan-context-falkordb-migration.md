---
id: TASK-REV-38BC
title: Review system-plan, context commands, and FalkorDB migration impact
status: review_complete
created: 2026-02-11T15:00:00Z
updated: 2026-02-11T15:00:00Z
priority: high
tags: [architecture-review, graphiti, falkordb, system-plan, migration, context-commands]
task_type: review
complexity: 7
---

# Task: Review system-plan, context commands, and FalkorDB migration impact

## Description

Analyse the recent changes across three related areas and assess the impact of migrating from Neo4j/Graphiti to FalkorDB:

1. **`/system-plan` command** (FEAT-SP-001): New architecture planning command with entity definitions, complexity gating, Graphiti arch operations, architecture writer, CLI command, and integration seam tests (TASK-SP-001 through TASK-SP-008).

2. **Read-only context commands** (FEAT-SC-001): System overview, impact analysis, context switch, and coach context builder commands that read from Graphiti to provide project context (TASK-SC-001 through TASK-SC-012).

3. **Graphiti seed data updates**: The existing seeding infrastructure (`guardkit/knowledge/`) that populates the knowledge graph with project architecture, role constraints, quality gates, ADRs, and feature specs.

**Migration context**: Graphiti currently uses Neo4j as its graph database backend. We are evaluating/migrating to FalkorDB. This review should identify all Graphiti integration touchpoints that would be affected and assess the scope of changes needed.

## Scope of Analysis

### A. `/system-plan` Command Implementation
- `guardkit/planning/system_plan.py` — core planning logic
- `guardkit/planning/graphiti_arch.py` — Graphiti architecture operations
- `guardkit/planning/architecture_writer.py` — architecture document generation
- `guardkit/planning/mode_detector.py` — planning mode detection
- `guardkit/cli/system_plan.py` — CLI integration
- `guardkit/templates/*.j2` — Jinja2 templates for architecture docs
- Tests: `tests/unit/planning/`, `tests/unit/cli/test_system_plan_cli.py`, `tests/integration/test_system_plan_*.py`

### B. Read-Only Context Commands
- `guardkit/cli/system_context.py` — system overview, impact analysis, context switch CLI
- `installer/core/commands/system-overview.md` — command spec
- `installer/core/commands/impact-analysis.md` — command spec
- `installer/core/commands/context-switch.md` — command spec
- Tests: `tests/e2e/test_system_context_commands.py`, `tests/integration/test_*_graphiti.py`

### C. Graphiti Seed/Write Path (FalkorDB Impact)
- `guardkit/knowledge/graphiti_client.py` — client factory (Neo4j connection)
- `guardkit/knowledge/seeding/` — project seeding infrastructure
- `guardkit/knowledge/turn_state_operations.py` — turn state capture
- `guardkit/knowledge/outcome_manager.py` — outcome management
- `guardkit/knowledge/failed_approach_manager.py` — failed approach tracking
- `guardkit/knowledge/template_sync.py` — template synchronization
- `guardkit/knowledge/graphiti_context_loader.py` — context retrieval
- `guardkit/knowledge/interactive_capture.py` — interactive knowledge capture
- `guardkit/knowledge/feature_plan_context.py` — feature plan context builder

### D. FalkorDB Migration Touchpoints
- Neo4j driver usage (`neo4j` Python package)
- Graphiti-core library dependency (`graphiti-core`)
- Connection string patterns (`bolt://`, `neo4j://`)
- Cypher query compatibility (if any raw queries exist)
- Docker Compose / infrastructure configuration
- Environment variable patterns (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`)

## Acceptance Criteria

- [ ] AC-001: All `/system-plan` Python modules catalogued with their Graphiti dependencies
- [ ] AC-002: All read-only context command Graphiti integration points identified
- [ ] AC-003: Complete inventory of Graphiti client usage (direct Neo4j vs graphiti-core API)
- [ ] AC-004: FalkorDB compatibility assessment for graphiti-core library
- [ ] AC-005: List of environment variables, config files, and connection patterns that need updating
- [ ] AC-006: Risk assessment for seed data operations during migration
- [ ] AC-007: Identification of any raw Cypher queries that may need FalkorDB dialect changes
- [ ] AC-008: Test coverage assessment — which tests depend on Neo4j and need updating
- [ ] AC-009: Recommended migration approach (big bang vs incremental, with justification)

## Review Approach

Use `/task-review TASK-REV-38BC --mode=architectural --depth=deep` to execute this analysis.

## Context

- Feature specs: `docs/research/system-level-understanding/specs/FEAT-SP-001-system-plan-command.md`, `docs/research/system-level-understanding/FEAT-SC-001-system-context-read-commands.md`
- Prior DB choice review: `tasks/backlog/TASK-REV-graphiti-db-choice.md`
- Graphiti integration guide: `docs/guides/graphiti-integration-guide.md`
- Graphiti infrastructure guide: `docs/research/knowledge-graph-mcp/graphiti-shared-infrastructure-guide.md`
- ADR: `docs/adr/ADR-001-graphiti-integration-scope.md`

## Implementation Notes

This is a review-only task. Findings will inform:
1. A migration plan task for FalkorDB transition
2. Potential refactoring tasks for abstraction layers
3. Updated seeding scripts for FalkorDB compatibility
