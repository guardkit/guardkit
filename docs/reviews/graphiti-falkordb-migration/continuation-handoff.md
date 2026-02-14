# FalkorDB Migration — Continuation Handoff

**Date**: 12 February 2026
**Feature**: FEAT-FKDB-001 — FalkorDB Migration
**Review**: TASK-REV-38BC
**Status**: Code migration COMPLETE — infrastructure migration NEXT

---

## What's Been Done

### All 8 Migration Tasks: COMPLETE

| Task | Title | Status | Wave |
|------|-------|--------|------|
| TASK-FKDB-001 | Validate FalkorDB + graphiti-core E2E | ✅ Completed | 0 (Gate) |
| TASK-FKDB-002 | Add `graph_store` config + FalkorDB connection params | ✅ Completed | 1 |
| TASK-FKDB-003 | Add `falkordb` optional dependency | ✅ Completed | 1 |
| TASK-FKDB-004 | FalkorDB Docker Compose | ✅ Completed | 1 |
| TASK-FKDB-005 | Conditional driver creation (GraphitiClient + Factory) | ✅ Completed (in_review) | 2 |
| TASK-FKDB-006 | Refactor 3 raw Cypher queries to `execute_query()` | ✅ Completed | 2 |
| TASK-FKDB-007 | Update tests for FalkorDB compatibility | ✅ Completed | 3 |
| TASK-FKDB-008 | Cleanup, docs, ADR-003 | ✅ Completed | 3 |

### Discovered Task: ALSO COMPLETE

| Task | Title | Status |
|------|-------|--------|
| TASK-FKDB-32D9 | Fix upstream decorator bug + workarounds | ✅ Completed |

**Upstream bug**: `@handle_multiple_group_ids` decorator in `graphiti_core/decorators.py` uses `> 1` instead of `>= 1`, causing single group_id FalkorDB searches to use the wrong database after `add_episode()` mutates the shared driver. GuardKit implements a monkey-patch workaround in `guardkit/knowledge/falkordb_workaround.py` that auto-detects upstream fix.

- Upstream issue: [getzep/graphiti#1161](https://github.com/getzep/graphiti/issues/1161) (filed by `himorishige`)
- Upstream PR: [getzep/graphiti#1170](https://github.com/getzep/graphiti/pull/1170) (open, unreviewed 3+ weeks)
- GuardKit bug report doc: `docs/reviews/graphiti-falkordb-migration/upstream-decorator-bug-report.md` — reviewed, edits applied, ready for upstream comment

### Key Files Created/Modified

- `guardkit/knowledge/config.py` — `graph_store`, `falkordb_host`, `falkordb_port` fields
- `guardkit/knowledge/graphiti_client.py` — Conditional `FalkorDriver`/`Neo4jDriver` creation, `execute_query()` refactor
- `guardkit/knowledge/falkordb_workaround.py` — Monkey-patch for upstream decorator bug
- `docker/docker-compose.graphiti.yml` — FalkorDB-only compose (replaced Neo4j)
- `docker/docker-compose.falkordb-test.yml` — Test container
- `docs/adr/ADR-003-*.md` — Migration decision record
- `docs/guides/graphiti-integration-guide.md` — Updated for FalkorDB
- `scripts/graphiti-validation/validate_falkordb.py` — 8/8 AC validation script
- `tests/knowledge/test_falkordb_workaround.py` — 18 tests for workaround

### Test Results

- 18 workaround tests: all passing
- 129 existing graphiti client tests: all passing (0 regressions)
- FalkorDB E2E validation: 8/8 PASS
- graphiti-core version: v0.26.3
- falkordb package version: 1.4.0

---

## Current State

### Docker on MacBook Pro (12 Feb 2026)

Both graph databases are running side by side:

| Container | Image | Status | Ports |
|-----------|-------|--------|-------|
| `guardkit-falkordb` | `falkordb/falkordb:latest` | 🟢 Running (b40d67afa4) | 6379, 3000 |
| `guardkit-neo4j` | `neo4j:5.26.0` (or similar) | 🟢 Running (4d6f55e94f) | 7474, 7687 |

GuardKit code now supports both backends via `graph_store` config. Setting `graph_store=falkordb` uses FalkorDB; `graph_store=neo4j` (default) uses Neo4j for backwards compatibility.

### Tailscale Network: OPERATIONAL

All four machines now on the Tailscale mesh:

| Machine | Role | Tailscale Status |
|---------|------|-----------------|
| MacBook Pro M2 Max | Daily development | ✅ Connected |
| Synology DS918+ NAS | Shared infrastructure target | ✅ Connected |
| Dell ProMax GB10 | Compute/embeddings | ✅ Connected |
| Pro Max (?) | Additional compute | ✅ Connected |

Tailscale provides stable hostnames and encrypted WireGuard tunnels between all machines, eliminating the need for `/etc/hosts` management or fixed IP configuration.

### GuardKit Config Currently Points At

```yaml
# .guardkit/graphiti.yaml (current — local MacBook)
graph_store: falkordb
falkordb_host: localhost
falkordb_port: 6379
```

---

## What Comes Next

### Phase 1: Move FalkorDB to NAS (Primary Goal)

The three-machine infrastructure guide defines the NAS as the home for shared stateful services. FalkorDB should move from the MacBook to the Synology DS918+.

**Steps:**

1. **Deploy FalkorDB on NAS** — SSH into NAS, create Docker Compose at `/volume1/docker/infrastructure/docker-compose.yml` using the config from the infrastructure guide (includes memory limits, RDB save schedule, resource budgets)

2. **Migrate existing data** (if any worth keeping) — FalkorDB uses Redis RDB snapshots. Export from MacBook container, import on NAS. Or start fresh if the data is just test/validation data.

3. **Update GuardKit config** to point at NAS via Tailscale:
   ```yaml
   graph_store: falkordb
   falkordb_host: <nas-tailscale-hostname>
   falkordb_port: 6379
   ```

4. **Validate connectivity** — Run `validate_falkordb.py` against the NAS-hosted instance

5. **Remove Neo4j container** from MacBook Docker — no longer needed for GuardKit

6. **Remove FalkorDB container** from MacBook Docker — now running on NAS

### Phase 2: NAS Infrastructure Stack (Optional — Broader)

The infrastructure guide also plans NATS + Dolt alongside FalkorDB on the NAS:

| Service | Purpose | Status |
|---------|---------|--------|
| FalkorDB | Knowledge graph (Graphiti) | **Ready to deploy** |
| NATS + JetStream | Message bus (agent orchestration) | Planned |
| Dolt | Task archive (Git-for-data) | Planned |

These are independent and can be deployed incrementally. FalkorDB is the immediate priority.

### Phase 3: GB10 Embedding Service (Future)

The GB10 provides local embedding generation via Ollama, replacing OpenAI API calls. This complements the knowledge graph on the NAS.

---

## NAS Resource Budget (from infrastructure guide)

| Service | Expected RAM | Max Configured | CPU |
|---------|-------------|----------------|-----|
| FalkorDB | ~200-500MB | 1.5GB | 1.5 cores |
| NATS + JetStream | ~50-100MB | 512MB | 1.0 core |
| Dolt | ~100-200MB | 512MB | 0.5 core |
| **Total containers** | **~350-800MB** | **2.5GB** | **3.0 cores** |
| DSM + file services | ~1-2GB | — | — |
| **Remaining** | **~4.5-6.5GB** | — | **1 core** |

DS918+ has 8GB RAM and 4-core Celeron J3455. Comfortable headroom.

---

## NAS Docker Compose (from infrastructure guide)

Ready-to-use FalkorDB config for NAS:

```yaml
falkordb:
  image: falkordb/falkordb:latest
  container_name: falkordb
  ports:
    - "6379:6379"
  volumes:
    - falkordb_data:/data
  command: >
    --maxmemory 1gb
    --save 900 1
    --save 300 10
    --save 60 10000
  restart: unless-stopped
  mem_limit: 1536m
  cpus: 1.5
```

Note: NAS version includes `--maxmemory 1gb` and RDB save schedule. The MacBook dev compose doesn't have these constraints.

---

## Decisions Needed in Next Session

1. **Start with FalkorDB-only on NAS, or full stack (FalkorDB + NATS + Dolt)?**
2. **Migrate existing FalkorDB data or start fresh?**
3. **Neo4j removal timing** — Remove now or keep briefly as fallback?
4. **FalkorDB Browser UI** — Expose port 3000 on NAS for web-based graph browsing?
5. **Upstream bug report** — Post reviewed document as comment on #1161?

---

## Key Reference Files

| File | Purpose |
|------|---------|
| `tasks/backlog/falkordb-migration/README.md` | Feature overview |
| `tasks/completed/TASK-FKDB-*` | All completed task specs |
| `tasks/in_review/TASK-FKDB-005-*.md` | Driver creation (in_review) |
| `tasks/in_review/TASK-FKDB-32D9-*.md` | Upstream bug workaround |
| `.claude/reviews/TASK-REV-38BC-review-report.md` | Original deep review |
| `docs/reviews/graphiti-falkordb-migration/upstream-decorator-bug-report.md` | Bug report for upstream |
| `docs/adr/ADR-003-*.md` | Migration decision record |
| `docs/guides/graphiti-integration-guide.md` | Updated integration guide |
| `guardkit/knowledge/falkordb_workaround.py` | Monkey-patch workaround |
| `scripts/graphiti-validation/validate_falkordb.py` | Validation script |
| Three-machine infrastructure guide (project knowledge) | NAS deployment plan |
| `docker/docker-compose.graphiti.yml` | Current FalkorDB compose (MacBook) |
