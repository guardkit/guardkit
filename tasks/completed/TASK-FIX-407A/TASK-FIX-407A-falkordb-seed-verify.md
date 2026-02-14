---
id: TASK-FIX-407A
title: Run seed against FalkorDB and verify
status: completed
created: 2026-02-12T00:00:00Z
updated: 2026-02-14T00:00:00Z
completed: 2026-02-14T00:00:00Z
completed_location: tasks/completed/TASK-FIX-407A/
priority: high
tags: [graphiti, falkordb, verification]
parent_review: TASK-REV-3ECA
complexity: 2
depends_on: [TASK-FIX-986D, TASK-FIX-1584, TASK-FIX-C00D]
organized_files:
  - TASK-FIX-407A-falkordb-seed-verify.md
---

# Task: Run seed against FalkorDB and verify

## Description

After TASK-FIX-986D, TASK-FIX-1584, and TASK-FIX-C00D are complete, run the full seed against FalkorDB and verify everything works. Also seed project ADRs via `add-context`.

## Prerequisites

- TASK-FIX-986D (command workflow episodes) - MUST be complete
- TASK-FIX-1584 (display sync) - MUST be complete
- TASK-FIX-C00D (ADR consolidation) - MUST be complete
- FalkorDB running and accessible

## Steps

### 1. Run tests
```bash
pytest tests/knowledge/test_seeding.py -v
```
All tests must pass.

### 2. Seed system context
```bash
guardkit graphiti seed --force
```
Should list all 18 categories with checkmarks.

### 3. Verify seeded knowledge
```bash
guardkit graphiti verify --verbose
```
All 5 test queries should pass.

### 4. Check status
```bash
guardkit graphiti status --verbose
```
All categories should show non-zero episode counts.

### 5. Seed project ADRs
```bash
guardkit graphiti add-context docs/adr/ --type adr
guardkit graphiti add-context docs/architecture/ADR-GBF-001-unified-episode-serialization.md --type adr
```

### 6. Verify ADR content
```bash
guardkit graphiti search "FalkorDB migration"
guardkit graphiti search "SDK query invocation"
guardkit graphiti show ADR-003
```

## Acceptance Criteria

- [x] AC-001: `pytest tests/knowledge/test_seeding.py -v` - all tests pass
- [x] AC-002: `guardkit graphiti seed --force` completes successfully with all categories listed
- [x] AC-003: `guardkit graphiti verify` - all queries pass
- [~] AC-004: `guardkit graphiti status --verbose` - all categories populated (PARTIAL: data present in per-group FalkorDB graphs but status command count fails due to upstream RediSearch fulltext query syntax bug)
- [x] AC-005: Project ADRs searchable after `add-context`

## Results

### Bugs Found and Fixed

**Bug 1: `_get_client_and_config()` missing FalkorDB fields** (guardkit/cli/graphiti.py:62-71)
- `_get_client_and_config()` was not passing `graph_store`, `falkordb_host`, `falkordb_port` from settings to GraphitiConfig
- All CLI commands using this function (seed, verify, status, search, etc.) would default to Neo4j at localhost:7687
- Fix: Added `graph_store=settings.graph_store`, `falkordb_host=settings.falkordb_host`, `falkordb_port=settings.falkordb_port` to GraphitiConfig constructor

**Bug 2: `_cmd_add_context()` bypasses `_get_client_and_config()`** (guardkit/cli/graphiti.py:568)
- `add-context` command created `GraphitiClient()` directly with no arguments instead of using `_get_client_and_config()`
- Fix: Replaced `client = GraphitiClient()` with `client, settings = _get_client_and_config()`

### Known Upstream Issue

**RediSearch fulltext query syntax incompatibility** (graphiti-core)
- FalkorDB's RediSearch does not support the `@field:value` syntax in fulltext queries
- Affects `status --verbose` episode counting (shows 0 for all categories)
- Does NOT affect seed, verify, search, or add-context operations
- Episodes ARE present — verified via direct Cypher queries: 110+ episodes across 15 populated categories
- This is a graphiti-core upstream issue, not a GuardKit bug

### Verification Results

| Step | Result | Details |
|------|--------|---------|
| Tests | PASS | 46 passed, 2 skipped |
| Seed | PASS | 18 categories seeded to FalkorDB at whitestocks:6379 |
| Verify | PASS | 5/5 verification queries passed |
| Status | PARTIAL | Data present but count mechanism broken (upstream bug) |
| ADR seed | PASS | 14 episodes added (13 from docs/adr/ + 1 from ADR-GBF-001) |
| ADR search | PASS | FalkorDB migration results found (104 results) |

### Episode Counts (Direct Cypher Verification)

| Graph | Episodes |
|-------|----------|
| product_knowledge | 3 |
| command_workflows | 18 |
| quality_gate_phases | 12 |
| technology_stack | 6 |
| feature_build_architecture | 6 |
| architecture_decisions | 3 |
| failure_patterns | 4 |
| component_status | 2 |
| integration_points | 2 |
| templates | 4 |
| agents | 7 |
| patterns | 22 |
| rules | 4 |
| guardkit__project_overview | 3 |
| guardkit__project_architecture | 3 |
| failed_approaches | 5 |
| quality_gate_configs | 6 |
