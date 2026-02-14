---
id: TASK-FKDB-008
title: Cleanup, documentation updates, and ADR-003
status: completed
created: 2026-02-11T17:00:00Z
completed: 2026-02-12T10:00:00Z
completed_location: tasks/completed/TASK-FKDB-008/
priority: medium
tags: [falkordb, documentation, adr, migration]
parent_review: TASK-REV-38BC
feature_id: FEAT-FKDB-001
implementation_mode: direct
wave: 3
complexity: 3
depends_on:
  - TASK-FKDB-007
organized_files:
  - TASK-FKDB-008-cleanup-docs-adr.md
---

# Task: Cleanup, documentation updates, and ADR-003

## Description

Final cleanup: update documentation to reflect FalkorDB as the default backend, remove APOC references, update backup scripts, and write ADR-003 documenting the migration decision.

## Acceptance Criteria

- [x] AC-001: `guardkit/cli/graphiti.py` cosmetic messages updated (no "Neo4j" in user-facing output)
- [x] AC-002: `docs/guides/graphiti-integration-guide.md` updated for FalkorDB
- [x] AC-003: `docs/research/knowledge-graph-mcp/graphiti-shared-infrastructure-guide.md` updated
- [x] AC-004: Backup scripts updated for FalkorDB (Redis BGSAVE instead of Neo4j dump)
- [x] AC-005: ADR-003 written documenting the Neo4j → FalkorDB migration decision and rationale
- [x] AC-006: `.guardkit/graphiti.yaml` example in docs shows FalkorDB defaults

## Files Modified

- `guardkit/cli/graphiti.py` — Added `_format_connection_target()` helper, replaced 5 hardcoded "Neo4j" messages
- `docs/guides/graphiti-integration-guide.md` — Config examples, env vars, FAQ, troubleshooting updated
- `docs/research/knowledge-graph-mcp/graphiti-shared-infrastructure-guide.md` — Step 5 constructor pattern fixed
- `scripts/graphiti-backup.sh` — Complete rewrite: Neo4j dump/load → Redis BGSAVE + volume tar
- `docs/adr/ADR-003-falkordb-migration.md` — New file documenting migration decision

## Implementation Notes

ADR-003 should document:
- **Context**: Neo4j as current backend, FalkorDB as lighter alternative
- **Decision**: Migrate to FalkorDB via graphiti-core's native FalkorDriver
- **Consequences**: Simpler infrastructure (Redis-based), no APOC dependency, same graphiti-core API
- **Risks accepted**: Early adopter of graphiti-core FalkorDB support (no upstream tests)

## Completion Notes

- All 6 acceptance criteria satisfied
- 85 tests passing, 0 regressions (1 pre-existing failure in `test_list_handles_disabled_graphiti` unrelated to changes)
- `_format_connection_target()` helper dynamically shows "FalkorDB at host:port" or "Neo4j at uri" based on `graph_store` config
- Backup script redesigned for Redis BGSAVE workflow; `list` command still detects legacy Neo4j backups
