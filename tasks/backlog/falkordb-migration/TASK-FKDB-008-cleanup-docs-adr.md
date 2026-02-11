---
id: TASK-FKDB-008
title: Cleanup, documentation updates, and ADR-003
status: backlog
created: 2026-02-11T17:00:00Z
priority: medium
tags: [falkordb, documentation, adr, migration]
parent_review: TASK-REV-38BC
feature_id: FEAT-FKDB-001
implementation_mode: direct
wave: 3
complexity: 3
depends_on:
  - TASK-FKDB-007
---

# Task: Cleanup, documentation updates, and ADR-003

## Description

Final cleanup: update documentation to reflect FalkorDB as the default backend, remove APOC references, update backup scripts, and write ADR-003 documenting the migration decision.

## Acceptance Criteria

- [ ] AC-001: `guardkit/cli/graphiti.py` cosmetic messages updated (no "Neo4j" in user-facing output)
- [ ] AC-002: `docs/guides/graphiti-integration-guide.md` updated for FalkorDB
- [ ] AC-003: `docs/research/knowledge-graph-mcp/graphiti-shared-infrastructure-guide.md` updated
- [ ] AC-004: Backup scripts updated for FalkorDB (Redis BGSAVE instead of Neo4j dump)
- [ ] AC-005: ADR-003 written documenting the Neo4j → FalkorDB migration decision and rationale
- [ ] AC-006: `.guardkit/graphiti.yaml` example in docs shows FalkorDB defaults

## Files to Modify

- `guardkit/cli/graphiti.py` — Cosmetic message updates
- `docs/guides/graphiti-integration-guide.md`
- `docs/research/knowledge-graph-mcp/graphiti-shared-infrastructure-guide.md`
- `scripts/graphiti-backup.sh` (if exists)
- `docs/adr/ADR-003-falkordb-migration.md` (new file)

## Implementation Notes

ADR-003 should document:
- **Context**: Neo4j as current backend, FalkorDB as lighter alternative
- **Decision**: Migrate to FalkorDB via graphiti-core's native FalkorDriver
- **Consequences**: Simpler infrastructure (Redis-based), no APOC dependency, same graphiti-core API
- **Risks accepted**: Early adopter of graphiti-core FalkorDB support (no upstream tests)
