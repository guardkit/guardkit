# ADR-003: Migrate from Neo4j to FalkorDB for Knowledge Graph Backend

**Status**: Accepted
**Date**: 2026-02-11
**Decision Makers**: Rich Woollcott
**Context**: FalkorDB migration as part of FEAT-FKDB-001, informed by TASK-REV-38BC deep architectural review

---

## Context

### Current State

GuardKit uses Neo4j as the graph database backend for Graphiti knowledge graph integration. The Graphiti library (`graphiti-core`) connects to Neo4j via the `neo4j` Python driver, using Bolt protocol on port 7687. This requires:

- Neo4j Docker container (~2-4GB JVM heap)
- APOC plugin for extended Cypher operations
- Neo4j-specific configuration (`bolt://localhost:7687`, user/password auth)

### Why Change

1. **Resource efficiency**: Neo4j's JVM footprint is heavy for a development-machine knowledge graph. FalkorDB runs on Redis with ~500MB RAM (7x more efficient).

2. **Deployment simplicity**: Neo4j requires JVM tuning and APOC plugin management. FalkorDB is a single container with zero configuration.

3. **graphiti-core alignment**: As of `graphiti-core` v0.26.3, FalkorDB is the default recommended backend. The library ships with `FalkorDriver` alongside `Neo4jDriver`, and all 20+ internal query sites use the driver-agnostic `execute_query()` pattern.

4. **NAS deployment target**: The Synology DS918+ (8GB) is the target shared infrastructure host. Neo4j's memory requirements make it a tight fit; FalkorDB is comfortable.

5. **Performance**: FalkorDB benchmarks show sub-140ms p99 latency vs Neo4j's 46.9s for aggregate expansion queries (per graphiti-core team benchmarks).

### Deep-Dive Validation (TASK-REV-38BC)

A comprehensive architectural review verified:

- **DD-1**: `execute_query()` returns compatible tuples from both drivers. Neo4j's `EagerResult` is a named tuple; FalkorDB returns `(records, header, None)`. Both support `records, _, _ = result` unpacking.
- **DD-2**: `Graphiti(graph_driver=FalkorDriver(...))` constructor injection is clean — no hidden Neo4j assumptions in initialization.
- **DD-3**: FalkorDB client is NOT thread-safe by default, but `GraphitiClientFactory` already creates per-thread clients.
- **DD-4**: `FalkorDriverSession.run()` returns `None` — the 3 raw Cypher queries in `graphiti_client.py` are the only crash-risk code.
- **DD-5**: graphiti-core has zero Neo4j imports outside `driver/neo4j_driver.py`.
- **DD-6**: graphiti-core has NO FalkorDB tests — GuardKit is an early adopter.

---

## Decision

Migrate from Neo4j to FalkorDB as the default knowledge graph backend, using graphiti-core's native `FalkorDriver`.

### Implementation Approach

1. **Backwards compatible**: Add `graph_store` config field (`neo4j` | `falkordb`). Keep `neo4j_*` field names as aliases.
2. **Conditional driver creation**: `GraphitiClient.initialize()` creates `FalkorDriver` or `Neo4jDriver` based on config.
3. **Refactor 3 raw Cypher queries**: Replace `driver.session().run()` with `driver.execute_query()` in `_list_groups()`, `_clear_group()`, `get_clear_preview()`.
4. **Docker Compose update**: Replace Neo4j service with FalkorDB (same compose file name for compatibility).
5. **Re-seed knowledge**: Fresh `guardkit graphiti seed --force` after migration (no data migration from Neo4j).

### Migration Waves

| Wave | Tasks | Risk |
|------|-------|------|
| 0 (Gate) | Validate FalkorDB + graphiti-core E2E | Blocks all other waves |
| 1 | Config, dependency, Docker | Low |
| 2 | Driver creation, raw query refactor | **Critical** (TASK-FKDB-006) |
| 3 | Tests, docs, cleanup | Low |

---

## Consequences

### Positive

1. **7x lower RAM**: ~500MB vs 2-4GB for Neo4j JVM heap
2. **Simpler deployment**: Single container, no APOC plugin, no JVM tuning
3. **Aligned with upstream**: FalkorDB is graphiti-core's recommended backend
4. **NAS-friendly**: Comfortable on 8GB Synology DS918+ for shared infrastructure
5. **Redis protocol**: Uses standard Redis port 6379, familiar tooling (`redis-cli`)
6. **Sub-140ms queries**: Significant latency improvement for graph operations

### Negative

1. **Early adopter risk**: graphiti-core has no FalkorDB tests — we rely on Wave 0 validation
2. **No data migration**: Knowledge graph must be re-seeded from scratch (system context is scripted, project-specific episodes are lost)
3. **Browser UI change**: FalkorDB Browser (port 3000) is less polished than Neo4j Browser (port 7474)

### Risks Accepted

1. **No upstream FalkorDB test coverage**: Mitigated by Wave 0 validation gate and our own test suite
2. **FalkorDB `execute_query()` returns `None` on index errors**: Mitigated by None guards in refactored code
3. **`FalkorDriverSession.run()` returns `None`**: The 3 raw queries MUST be refactored before migration (TASK-FKDB-006 is critical path)

---

## Alternatives Considered

### Alternative 1: Stay on Neo4j

Keep the existing Neo4j backend. No migration effort.

**Rejected because**: Too resource-heavy for NAS deployment, increasing divergence from graphiti-core's recommended path.

### Alternative 2: Use KuzuDB

graphiti-core also supports KuzuDB (embedded graph database, no Docker needed).

**Rejected because**: KuzuDB is file-based and doesn't support the shared multi-machine architecture needed for Tailscale + NAS deployment. Good for single-machine use but doesn't fit our target architecture.

### Alternative 3: Use Neptune (AWS)

graphiti-core supports Amazon Neptune for cloud deployment.

**Rejected because**: Ongoing cloud costs (~$25-30/month) vs zero incremental cost for FalkorDB on existing NAS hardware.

---

## References

- TASK-REV-38BC review report: `.claude/reviews/TASK-REV-38BC-review-report.md`
- Implementation tasks: `tasks/backlog/falkordb-migration/`
- Shared infrastructure guide: `docs/research/knowledge-graph-mcp/graphiti-shared-infrastructure-guide.md`
- ADR-001: `docs/adr/ADR-001-graphiti-integration-scope.md` (original Graphiti scope decision)

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-02-11 | Initial decision based on TASK-REV-38BC deep review | Rich Woollcott |
