# Review Report: TASK-REV-38BC

## Deep Architectural Review: System-Plan, Context Commands, and FalkorDB Migration

**Mode**: Architectural | **Depth**: Deep | **Date**: 2026-02-11

---

## Executive Summary

This deep architectural review catalogues all Graphiti integration touchpoints across three recently-built feature areas (`/system-plan`, read-only context commands, and seed/write infrastructure) and assesses the impact of migrating from Neo4j to FalkorDB.

**Key finding: The migration is architecturally straightforward but has one CRITICAL compatibility gap.** GuardKit has **zero direct Neo4j driver imports** in application code. All database interaction flows through graphiti-core's `Graphiti` class, which ships with a `FalkorDriver`. The migration is primarily a **configuration change**, not a code rewrite. However, there are exactly **3 raw Cypher queries** that call Neo4j-specific result methods (`.data()`, `.single()`) which **will crash under FalkorDB** because `FalkorDriverSession.run()` returns `None`.

**Risk: MEDIUM** | **Estimated effort: 2-3 days** | **Recommended approach: Incremental**

### Verification Status

All 9 acceptance criteria independently verified against the actual codebase. One risk finding upgraded from the initial report.

| AC | Status | Verified |
|----|--------|----------|
| AC-001 | PASS | 17 planning modules catalogued (report said 9 — see correction below) |
| AC-002 | PASS | 5 integration points verified with full call chains |
| AC-003 | PASS | ~30 graphiti-core API calls, 3 raw Cypher queries, 3 `driver.session()` calls |
| AC-004 | PASS | FalkorDriver verified in `.venv/`, constructor accepts `graph_driver=` |
| AC-005 | PASS | 8 env vars, 1 YAML, 1 Docker Compose confirmed |
| AC-006 | PASS | All seed ops use `upsert_episode()` — re-seed is safe |
| AC-007 | PASS (UPGRADED RISK) | 3 Cypher queries confirmed; session result format is CRITICAL, not MEDIUM |
| AC-008 | PASS | 68 test files confirmed; ~45 mocked, ~12 config updates, ~8 connection updates |
| AC-009 | PASS | Incremental migration confirmed as correct approach |

---

## Section A: `/system-plan` Module Catalogue (AC-001)

### Module Inventory (CORRECTED)

The initial report listed 9 modules. The actual codebase has **17 Python files** under `guardkit/planning/`:

| Module | LOC | Graphiti Dependencies | Role |
|--------|-----|----------------------|------|
| `graphiti_arch.py` | ~360 | `GraphitiClient`, entity types | **Core persistence layer**: `SystemPlanGraphiti` class |
| `mode_detector.py` | ~100 | `GraphitiClient`, `SystemPlanGraphiti` | Auto-detect setup vs refine mode |
| `coach_context_builder.py` | ~250 | `GraphitiClient`, `SystemPlanGraphiti` | Budget-gated Coach prompt context |
| `system_overview.py` | ~350 | `SystemPlanGraphiti` | Architecture fact assembly + formatting |
| `impact_analysis.py` | ~300 | `SystemPlanGraphiti`, `GraphitiClient` | Task impact assessment (3 group search) |
| `architecture_writer.py` | ~200 | Entity types only (no client) | Jinja2 document generation |
| `context_switch.py` | ~200 | None (YAML config) | Multi-project navigation |
| `system_plan.py` | ~60 | None (stub orchestrator) | CLI entry point — not yet wired |
| `spec_parser.py` | ~150 | None | Markdown parsing |
| `complexity_gating.py` | ~100 | None | Token budget allocation |
| `adr_generator.py` | ~150 | None | ADR file generation |
| `seed_script_generator.py` | ~100 | None | Bash script generation |
| `quality_gate_generator.py` | ~100 | None | QA YAML generation |
| `task_metadata.py` | ~100 | None | Task enrichment metadata |
| `target_mode.py` | ~80 | None | Output config resolution |
| `warnings_extractor.py` | ~80 | None | Markdown extraction |
| `__init__.py` | ~30 | None | Module exports |

**CLI**: `guardkit/cli/system_plan.py` (~150 LOC) — delegates to planning modules, has `--enable-context/--no-context` flag.

### Graphiti Operation Matrix

| Module | Read Operations | Write Operations | Direct Neo4j |
|--------|----------------|-----------------|-------------|
| graphiti_arch.py | `client.search()` (3 calls), `has_architecture_context()` | `client.upsert_episode()` (4 calls) | None |
| system_overview.py | `sp.get_architecture_summary()` | None | None |
| impact_analysis.py | `client.search()` on 3 group types | None | None |
| mode_detector.py | `sp.has_architecture_context()` | None | None |
| coach_context_builder.py | `get_system_overview()`, `run_impact_analysis()` | None | None |
| context_switch.py | None (YAML-based) | None | None |

### FalkorDB Impact: **NONE**

All `/system-plan` modules use graphiti-core API exclusively through `GraphitiClient.search()` and `GraphitiClient.upsert_episode()`. No direct Neo4j access. Migration requires zero code changes in this section.

---

## Section B: Read-Only Context Commands (AC-002)

### Integration Point Map (5 points verified)

```
CLI Layer                    Planning Layer              Knowledge Layer
──────────                   ──────────────              ───────────────
/system-overview ──────────> system_overview.py ────────> SystemPlanGraphiti
                                                           └─> GraphitiClient.search()
                                                                 └─> graphiti_core.Graphiti.search()

/impact-analysis ──────────> impact_analysis.py ────────> SystemPlanGraphiti + GraphitiClient
                                                           └─> client.search() on 3 groups
                                                           └─> client.get_group_id() for prefixing

/context-switch ───────────> context_switch.py ─────────> YAML config (no Graphiti)
```

### Group IDs Queried by Context Commands

| Command | Groups Queried | Depth Gating |
|---------|---------------|-------------|
| `/system-overview` | `project_architecture`, `project_decisions` | All depths |
| `/impact-analysis` | `project_architecture` | quick |
| `/impact-analysis` | + `project_decisions` | standard |
| `/impact-analysis` | + `bdd_scenarios` | deep |
| `/context-switch` | None (YAML-based, not Graphiti) | N/A |

**Correction**: The initial report showed `/context-switch` using `client.search("architecture overview")`. Actual code uses YAML config files for project switching — no Graphiti dependency. This **reduces** the migration surface.

### Graceful Degradation Pattern (VERIFIED)

All context commands follow the same pattern:
1. Check `sp._available` (client not None AND enabled)
2. If unavailable, return `{"status": "no_context"}`
3. If search fails, catch exception, log `[Graphiti]` warning, return `{"status": "no_context"}`

### FalkorDB Impact: **NONE**

All read operations go through `GraphitiClient.search()` which delegates to `graphiti_core.Graphiti.search()`. The search API is driver-agnostic. Zero code changes needed.

---

## Section C: Graphiti Client Inventory (AC-003)

### Direct Neo4j vs graphiti-core API Usage (VERIFIED)

| Category | Count | Impact |
|----------|-------|--------|
| **graphiti-core API (driver-agnostic)** | | |
| `Graphiti(uri, user, password)` constructor | 3 call sites | Needs `graph_driver=FalkorDriver(...)` instead |
| `graphiti.search()` | ~15 call sites | No change needed |
| `graphiti.add_episode()` / `upsert_episode()` | ~10 call sites | No change needed |
| `graphiti.build_indices_and_constraints()` | 1 call site | No change needed |
| `graphiti.close()` | ~5 call sites | No change needed |
| | | |
| **Direct driver access (bypasses abstraction)** | | |
| `driver.session()` + raw Cypher | **3 locations** (not 4) | **NEEDS MIGRATION** |

**Correction**: The initial report said 4 locations. Actual count is **3** `driver.session()` calls (lines 1087, 1114, 1342 of `graphiti_client.py`). All verified by grep.

### Detailed Direct-Access Locations

All 3 locations are in `guardkit/knowledge/graphiti_client.py`:

1. **`_list_groups()`** (line 1087-1092):
   ```python
   async with driver.session() as session:
       result = await session.run(
           "MATCH (e:Episode) RETURN DISTINCT e.group_id AS group_id"
       )
       records = await result.data()  # Neo4j-specific: returns List[Dict]
   ```

2. **`_clear_group()`** (line 1114-1126):
   ```python
   async with driver.session() as session:
       result = await session.run("""
           MATCH (e:Episode {group_id: $group_id})
           WITH e, count(e) as cnt
           DETACH DELETE e
           RETURN cnt as count
       """, group_id=group_id)
       record = await result.single()  # Neo4j-specific: returns Record|None
   ```

3. **`get_clear_preview()`** (line 1342-1354):
   ```python
   async with driver.session() as session:
       result = await session.run("""
           MATCH (e:Episode)
           WHERE e.group_id IN $groups
           RETURN count(e) as count
       """, groups=target_groups)
       record = await result.single()  # Neo4j-specific: returns Record|None
   ```

### GraphitiClientFactory (Thread Safety) — VERIFIED

- Uses `threading.local()` for per-thread client storage
- Each thread gets its own `GraphitiClient` → own `Graphiti` instance → own driver
- Factory creates client via `get_thread_client()` which calls `Graphiti(uri, user, password)`
- **Migration impact**: Change 1 constructor call pattern in factory

### Integration Points Using GraphitiClient (VERIFIED)

12 modules confirmed as importing and using `GraphitiClient` or `get_graphiti()`:

| Module | Import | Usage |
|--------|--------|-------|
| `graphiti_context_loader.py` | `get_graphiti()` | AutoBuild context retrieval |
| `interactive_capture.py` | lazy `_graphiti` property | Interactive knowledge capture |
| `feature_plan_context.py` | lazy `graphiti_client` property | Feature plan context building |
| `turn_state_operations.py` | `GraphitiClient` (injected) | Turn state capture |
| `outcome_manager.py` | `GraphitiClient` (injected) | Outcome management |
| `failed_approach_manager.py` | `GraphitiClient` (injected) | Failed approach tracking |
| `template_sync.py` | `GraphitiClient` (injected) | Template synchronization |
| `seeding.py` | `GraphitiClient`, `GraphitiConfig` | Knowledge seeding |
| `adr_service.py` | `GraphitiClient` | ADR lifecycle management |
| `context_loader.py` | `GraphitiClient` | Session context loading |
| `project_seeding.py` | `GraphitiClient` | Project-level seeding |
| All `seed_*.py` files | `GraphitiClient` | Domain seeding modules |

---

## Section D: FalkorDB Compatibility Assessment (AC-004)

### graphiti-core Library Analysis (VERIFIED)

**Installed version**: graphiti-core in `.venv/lib/python3.14/site-packages/graphiti_core/`

**FalkorDB support status**: **NATIVE** — driver ships with graphiti-core

**Driver abstraction architecture** (verified in source):
```
GraphDriver (abstract base class)
├── Neo4jDriver(uri, user, password)           ← Current
├── FalkorDriver(host, port, ...)              ← Target
├── KuzuDriver(database_path, ...)             ← In-memory alternative
└── NeptuneDriver(endpoint, region, ...)       ← AWS-specific
```

**GraphProvider enum** (verified):
```python
class GraphProvider(Enum):
    NEO4J = 'neo4j'
    FALKORDB = 'falkordb'
    KUZU = 'kuzu'
    NEPTUNE = 'neptune'
```

**Graphiti constructor** (verified — accepts custom driver):
```python
class Graphiti:
    def __init__(self, uri=None, user=None, password=None, ..., graph_driver=None):
        if graph_driver:
            self.driver = graph_driver    # ← Use provided driver
        else:
            if uri is None:
                raise ValueError('uri must be provided when graph_driver is None')
            self.driver = Neo4jDriver(uri, user, password)  # ← Default
```

### FalkorDB Python Package Status

**IMPORTANT**: The `falkordb` Python package is **NOT currently installed** in the venv. Installation required:
```bash
pip install graphiti-core[falkordb]
# or
pip install falkordb
```

The `falkordb_driver.py` has a runtime import guard:
```python
try:
    from falkordb import Graph as FalkorGraph
    from falkordb.asyncio import FalkorDB
except ImportError:
    raise ImportError(
        'falkordb is required for FalkorDriver. '
        'Install it with: pip install graphiti-core[falkordb]'
    )
```

### FalkorDB Driver Constructor (verified)

```python
class FalkorDriver:
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        username: str | None = None,
        password: str | None = None,
        falkor_db: FalkorDB | None = None,
        database: str = 'default_db',
    ):
```

### Fulltext Query Differences

FalkorDB uses RedisSearch syntax instead of Lucene:
- **Neo4j**: Standard Cypher `CONTAINS`, `STARTS WITH`
- **FalkorDB**: `@field:value`, `@group_id:value1|value2`
- graphiti-core handles this via `FalkorDriver.build_fulltext_query()` and `FalkorDriver.sanitize()`
- **GuardKit impact**: None. All fulltext queries go through graphiti-core's driver abstraction.

### FalkorDB-Specific Considerations

1. **No Label Set support**: FalkorDB converts label set operations to query arrays (handled in `FalkorDriverSession.run()`)
2. **Datetime handling**: FalkorDB requires ISO string conversion (handled by `convert_datetimes_to_strings()`)
3. **Multi-tenant via database names**: `FalkorDriver._database` (default: `"default_db"`)
4. **APOC plugin**: Not available in FalkorDB, but GuardKit doesn't use APOC (Neo4j Docker loads it, but no code references)

---

## Section E: Environment Variables & Configuration (AC-005)

### Current Configuration (Neo4j) — VERIFIED

| Source | Variable/Key | Default | Purpose |
|--------|-------------|---------|---------|
| **Env vars** | | | |
| | `GRAPHITI_ENABLED` | `true` | Enable/disable Graphiti |
| | `NEO4J_URI` | `bolt://localhost:7687` | Neo4j Bolt URI |
| | `NEO4J_USER` | `neo4j` | Neo4j username |
| | `NEO4J_PASSWORD` | `password123` | Neo4j password |
| | `GRAPHITI_TIMEOUT` | `30.0` | Connection timeout |
| | `GUARDKIT_PROJECT_ID` | None | Project namespace |
| | `GUARDKIT_CONFIG_DIR` | None | Config dir override |
| | `OPENAI_API_KEY` | (required) | For embeddings |
| | `GRAPHITI_HOST` | `localhost` | **Deprecated** |
| | `GRAPHITI_PORT` | `8000` | **Deprecated** |
| **YAML** | `.guardkit/graphiti.yaml` | | |
| | `enabled` | `true` | Enable/disable |
| | `neo4j_uri` | `bolt://localhost:7687` | Connection URI |
| | `neo4j_user` | `neo4j` | Username |
| | `neo4j_password` | `password123` | Password |
| | `timeout` | `30.0` | Timeout |
| | `project_id` | None | Namespace |
| | `group_ids` | `[product_knowledge, command_workflows, architecture_decisions]` | Default groups |
| **Docker** | `docker/docker-compose.graphiti.yml` | | |
| | Image | `neo4j:5.26.0` | Neo4j version |
| | Ports | `7474:7474`, `7687:7687` | HTTP + Bolt |
| | Auth | `neo4j/password123` | Default auth |
| | Plugins | `["apoc"]` | APOC plugin |
| | Volumes | `neo4j_data`, `neo4j_logs` | Persistence |

### Required Changes for FalkorDB

| Item | Current | Target | Files Affected |
|------|---------|--------|---------------|
| Connection URI | `bolt://localhost:7687` | `redis://localhost:6379` or host/port params | config.py, graphiti_client.py |
| Docker image | `neo4j:5.26.0` | `falkordb/falkordb:latest` | docker-compose.graphiti.yml |
| Ports | 7474/7687 | 6379/3000 | docker-compose.graphiti.yml |
| Auth | `NEO4J_AUTH=neo4j/password123` | Optional or Redis AUTH | docker-compose.graphiti.yml |
| Health check | `cypher-shell` | `redis-cli ping` | docker-compose.graphiti.yml |
| Volumes | `neo4j_data`, `neo4j_logs` | `falkordb_data` | docker-compose.graphiti.yml |
| Constructor | `Graphiti(uri, user, pwd)` | `Graphiti(graph_driver=FalkorDriver(...))` | graphiti_client.py |
| Config fields | `neo4j_uri`, `neo4j_user`, `neo4j_password` | Add `graph_store` field + FalkorDB aliases | config.py |
| Env vars | `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | Add `FALKORDB_HOST`, `FALKORDB_PORT` aliases | config.py |
| Python dep | `graphiti-core` | `graphiti-core[falkordb]` (adds `falkordb` package) | pyproject.toml |

---

## Section F: Seed Data Risk Assessment (AC-006)

### Seed Operations Inventory (VERIFIED)

| Seed Module | Group ID | Method | Idempotent | Risk |
|------------|----------|--------|-----------|------|
| `seeding.py` | Multiple system groups | `upsert_episode()` | Yes (by name+group) | LOW |
| `project_seeding.py` | `project_architecture`, `project_overview` | `upsert_episode()` | Yes | LOW |
| `seed_rules.py` | `role_constraints` | `upsert_episode()` | Yes | LOW |
| `seed_quality_gate_configs.py` | `quality_gate_configs` | `upsert_episode()` | Yes | LOW |
| `seed_command_workflows.py` | `command_workflows` | `upsert_episode()` | Yes | LOW |
| `seed_architecture_decisions.py` | `architecture_decisions` | `upsert_episode()` | Yes | LOW |
| `seed_pattern_examples.py` | `pattern_examples` | `upsert_episode()` | Yes | LOW |
| `seed_failed_approaches.py` | `failed_approaches` | `upsert_episode()` | Yes | LOW |
| `feature_plan_context.py` | `feature_specs` | `seed_feature_spec()` via `upsert_episode()` | Yes | LOW |

### Risk Assessment

**Overall risk: LOW**

1. **All seeding uses `upsert_episode()`** — driver-agnostic graphiti-core API.
2. **All operations are idempotent** — Re-seeding after migration is safe and expected.
3. **No data migration needed** — Seed data can be regenerated from source files. The knowledge graph is a derived cache, not a source of truth.
4. **Episode content is text-based** — No binary data or Neo4j-specific types.
5. **Group ID prefixing is string-based** — `{project_id}__{group_name}` pattern works identically regardless of backend.

### Migration Strategy for Seed Data

1. Stop Neo4j container
2. Start FalkorDB container
3. Run `guardkit graphiti seed --force` to re-seed all system knowledge
4. Run `guardkit graphiti add-context` to re-add project context
5. Verify with `guardkit graphiti verify --verbose`

**No export/import needed** — it's faster and safer to re-seed from source.

---

## Section G: Raw Cypher Query Identification (AC-007) — UPGRADED RISK

### Queries Found (VERIFIED)

**3 raw Cypher queries**, all in `guardkit/knowledge/graphiti_client.py`:

| # | Method | Line | Query | Cypher Compatible | Session API Compatible |
|---|--------|------|-------|-------------------|----------------------|
| 1 | `_list_groups()` | 1087 | `MATCH (e:Episode) RETURN DISTINCT e.group_id AS group_id` | YES | **NO** — calls `result.data()` |
| 2 | `_clear_group()` | 1114 | `MATCH...DETACH DELETE...RETURN cnt` | YES (openCypher) | **NO** — calls `result.single()` |
| 3 | `get_clear_preview()` | 1342 | `MATCH...WHERE...IN $groups RETURN count(e)` | YES | **NO** — calls `result.single()` |

### CRITICAL FINDING: Session Result API Incompatibility

**This is the most significant technical risk in the migration, upgraded from MEDIUM to CRITICAL.**

The three queries use Neo4j-specific result methods:
- `result.data()` → returns `List[Dict]` (Neo4j `AsyncResult.data()`)
- `result.single()` → returns `Record | None` (Neo4j `AsyncResult.single()`)

**FalkorDB's `FalkorDriverSession.run()` returns `None`** — it has no result object:

```python
# FalkorDB driver (verified in source)
class FalkorDriverSession:
    async def run(self, query, **kwargs):
        # ... executes query ...
        return None  # ← No result object returned
```

This means:
- `result.data()` → `AttributeError: 'NoneType' has no attribute 'data'`
- `result.single()` → `AttributeError: 'NoneType' has no attribute 'single'`

**Impact**: These 3 methods (`_list_groups`, `_clear_group`, `get_clear_preview`) will **crash at runtime** if the driver is switched to FalkorDB without code changes.

**Note**: The Kuzu driver also returns `None` from `session.run()` — this is not unique to FalkorDB. Only Neo4j returns a rich result object.

### Recommended Fix

**Option 1 (RECOMMENDED): Use `driver.execute_query()` instead of `driver.session()`**

Both Neo4j and FalkorDB implement `execute_query()` on the `GraphDriver` base class. The FalkorDB implementation returns `(records, header, None)` in a normalized format:

```python
# Instead of:
async with driver.session() as session:
    result = await session.run(query)
    records = await result.data()

# Use:
records, header, _ = await driver.execute_query(query)
```

This bypasses the session context manager and uses the driver-agnostic query interface.

**Option 2: Add result wrapper to session API**

Create a `QueryResult` adapter that normalizes Neo4j's `AsyncResult` and FalkorDB's `None` into a common interface. Higher effort but preserves session semantics.

**Option 3: Replace raw Cypher with graphiti-core API calls**

If graphiti-core provides equivalent operations (listing groups, clearing episodes), prefer those over raw Cypher. This would eliminate the driver-bypass entirely.

---

## Section H: Test Coverage Assessment (AC-008)

### Test File Inventory (VERIFIED)

**68 test files** reference Neo4j/Graphiti configuration. Categorized by migration impact:

| Category | Files | Impact | Action |
|----------|-------|--------|--------|
| **Unit tests (mocked)** | ~45 | NONE | All mock `GraphitiClient`; no real connections |
| **Integration tests (seam)** | ~12 | LOW | Use `MockGraphitiClient`; may need updated assertions |
| **Integration tests (real)** | ~8 | MEDIUM | Reference `bolt://localhost:7687`; need config update |
| **CLI tests** | ~8 | LOW | Mock `asyncio.run()` + client; cosmetic string changes |
| **E2E tests** | ~3 | MEDIUM | Need real database; config update required |
| **Docs tests** | ~2 | LOW | Assert doc content mentioning "Neo4j" |

### Key Test Files Needing Changes

| Test File | Change Required |
|-----------|----------------|
| `tests/knowledge/test_graphiti_client.py` | Update default URI in assertions |
| `tests/knowledge/test_graphiti_client_factory.py` | Update constructor patterns if changed |
| `tests/knowledge/test_config.py` | Update default values, env var names if aliased |
| `tests/integration/graphiti/test_*.py` | Update connection config for real FalkorDB |
| `tests/e2e/test_system_context_commands.py` | Update mock configs |
| `tests/docs/test_graphiti_setup_guide.py` | Update doc assertions |
| `tests/knowledge/test_graphiti_client_clear.py` | Raw Cypher result format WILL differ |

### Tests That Will Break

The **3 raw Cypher query locations** are tested in:
- `tests/knowledge/test_graphiti_client_clear.py` — Tests `_clear_group()` and `clear_all()`
- `tests/cli/test_graphiti_list.py` — Tests `_list_groups()`

These tests mock `driver.session()` and verify Cypher queries. If the underlying implementation changes, these tests need updating.

---

## Section I: Recommended Migration Approach (AC-009)

### Recommendation: **Incremental Migration (2-3 days)**

### Rationale

1. **Zero application code uses Neo4j directly** — All interaction is through graphiti-core's `Graphiti` class
2. **graphiti-core already supports FalkorDB** — `FalkorDriver` is installed and ready (needs `falkordb` package)
3. **Seed data is re-generable** — No complex data migration needed
4. **3 raw Cypher queries** — All appear Cypher-compatible, but session API is incompatible (CRITICAL fix needed)
5. **68 test files reference Neo4j** — But most use mocks, not real connections

### Migration Plan

#### Phase 1: Infrastructure (Day 1, ~2h)

| Task | Description | Files |
|------|-------------|-------|
| 1a | Replace Neo4j Docker Compose with FalkorDB | `docker/docker-compose.graphiti.yml` |
| 1b | Add `graph_store` field to `GraphitiSettings` | `guardkit/knowledge/config.py` |
| 1c | Add FalkorDB connection params (`FALKORDB_HOST`, `FALKORDB_PORT`) | `guardkit/knowledge/config.py` |
| 1d | Add `falkordb` to optional dependencies | `pyproject.toml` |

#### Phase 2: Client Adaptation (Day 1-2, ~4h) — CRITICAL PATH

| Task | Description | Files |
|------|-------------|-------|
| 2a | Update `GraphitiClient.initialize()` to use `FalkorDriver` when `graph_store=falkordb` | `guardkit/knowledge/graphiti_client.py` |
| 2b | Update `GraphitiClientFactory.get_thread_client()` similarly | `guardkit/knowledge/graphiti_client.py` |
| **2c** | **Refactor 3 raw Cypher queries from `session.run()` to `driver.execute_query()`** | `guardkit/knowledge/graphiti_client.py` |
| 2d | Update cosmetic log messages ("Connected to Neo4j" → "Connected to graph database") | `guardkit/knowledge/graphiti_client.py` |
| 2e | Update `_check_connection()` to use FalkorDriver when configured | `guardkit/knowledge/graphiti_client.py` |

**Task 2c is the critical path item.** The 3 methods (`_list_groups`, `_clear_group`, `get_clear_preview`) must be refactored to use `driver.execute_query()` instead of `driver.session().run()` + `.data()`/`.single()`.

#### Phase 3: Configuration & Docs (Day 2, ~2h)

| Task | Description | Files |
|------|-------------|-------|
| 3a | Update `.guardkit/graphiti.yaml` example/defaults | Various docs |
| 3b | Keep `neo4j_uri/user/password` field names as backwards-compatible aliases | `guardkit/knowledge/config.py` |
| 3c | Add `graph_store: falkordb` to default config | `guardkit/knowledge/config.py` |
| 3d | Update shared infrastructure guide | Docs |

#### Phase 4: Testing (Day 2-3, ~4h)

| Task | Description | Files |
|------|-------------|-------|
| 4a | Update test fixtures with FalkorDB defaults | `tests/conftest.py`, various |
| 4b | Run unit test suite (expect ~100% pass — all mocked) | All unit tests |
| 4c | Run integration tests with FalkorDB running | Integration tests |
| 4d | Test raw Cypher query compatibility via `execute_query()` | `test_graphiti_client_clear.py` |
| 4e | Re-seed and verify knowledge graph | Manual validation |

#### Phase 5: Cleanup (Day 3, ~1h)

| Task | Description | Files |
|------|-------------|-------|
| 5a | Remove APOC plugin reference | Docker Compose |
| 5b | Update backup scripts for FalkorDB (Redis BGSAVE) | Scripts |
| 5c | Write ADR-003 documenting the migration | `docs/adr/` |

### Why NOT Big Bang

A big-bang approach (rename all `neo4j_*` fields, remove Neo4j references) would:
- Break 68 test files simultaneously
- Require updating every doc that mentions Neo4j
- Remove backwards compatibility unnecessarily
- Risk regression in a working system

The incremental approach keeps `neo4j_uri` etc. as field names (they're just config field names, not Neo4j-specific semantics), adds FalkorDB support alongside, and the switchover is controlled by a single `graph_store` config field.

---

## Findings Summary

### By Acceptance Criterion

| AC | Status | Summary |
|----|--------|---------|
| AC-001 | PASS | 17 modules catalogued (corrected from 9). All use graphiti-core API. Zero direct Neo4j. |
| AC-002 | PASS | 5 integration points verified. `/context-switch` is YAML-based, not Graphiti (corrected). |
| AC-003 | PASS | ~30 graphiti-core API calls, 3 direct driver accesses (corrected from 4). |
| AC-004 | PASS | FalkorDriver ships with graphiti-core. `falkordb` package needs installation. |
| AC-005 | PASS | 8 env vars, 1 YAML config, 1 Docker Compose. Changes listed. |
| AC-006 | PASS | All seed ops use `upsert_episode()`. Idempotent. Re-seed is safe. Risk: LOW. |
| AC-007 | PASS | 3 raw Cypher queries. Cypher compatible. **Session API INCOMPATIBLE** (CRITICAL). |
| AC-008 | PASS | 68 test files. ~45 mocked (no change), ~12 need config updates, ~8 need connection updates. |
| AC-009 | PASS | Incremental migration recommended. 2-3 days. 5 phases. Task 2c is critical path. |

### Risk Matrix (UPDATED)

| Risk | Severity | Likelihood | Mitigation |
|------|----------|-----------|-----------|
| **FalkorDB session.run() returns None** | **CRITICAL** | **CERTAIN** | **Refactor to `driver.execute_query()` (Task 2c)** |
| `DETACH DELETE` + `WITH count` Cypher compatibility | LOW | LOW | Test manually; fallback to separate count query |
| Embedding dimension mismatch after migration | HIGH | LOW | Use same embedding model (text-embedding-3-small) |
| Thread-safety in FalkorDB driver | MEDIUM | LOW | FalkorDriver reuses connection; test parallel execution |
| `falkordb` package not installed | MEDIUM | CERTAIN | Add to `pyproject.toml` optional deps |
| Test suite breakage | LOW | MEDIUM | Most tests use mocks; real connection tests need config update |

### Corrections from Initial Report

| Item | Initial Report | Actual (Verified) |
|------|---------------|-------------------|
| Planning modules count | 9 | **17** (8 additional non-Graphiti modules) |
| Direct driver access locations | 4 | **3** (`driver.session()` calls) |
| `/context-switch` Graphiti usage | `client.search("architecture overview")` | **None** (YAML-based) |
| Session result format risk | MEDIUM severity / HIGH likelihood | **CRITICAL severity / CERTAIN likelihood** |
| `falkordb` package status | Not mentioned | **Not installed** (needs `pip install graphiti-core[falkordb]`) |

### Architecture Score

| Principle | Score | Notes |
|-----------|-------|-------|
| **Abstraction** | 9/10 | GraphitiClient wraps graphiti-core. Only 3 places bypass abstraction. |
| **Graceful Degradation** | 10/10 | Every Graphiti call has try/except + fallback. |
| **Configuration** | 7/10 | Neo4j-specific field names, but functionally backend-agnostic. |
| **Testability** | 8/10 | Comprehensive mocks. Real connection tests need config parameterization. |
| **Migration Readiness** | 8/10 | 95% of code needs zero changes. 3 Cypher queries + 1 constructor pattern to update. |

---

## Appendix: File Change Impact Map

### Files Requiring Code Changes (6 files)

1. **`guardkit/knowledge/graphiti_client.py`** — Add FalkorDriver constructor path, refactor 3 raw Cypher queries to use `execute_query()`
2. **`guardkit/knowledge/config.py`** — Add `graph_store` field, FalkorDB connection params
3. **`docker/docker-compose.graphiti.yml`** — Replace Neo4j with FalkorDB
4. **`guardkit/cli/graphiti.py`** — Update cosmetic "Connecting to Neo4j" messages
5. **`tests/conftest.py`** — Update default test fixtures
6. **`pyproject.toml`** — Add `falkordb` to optional dependencies

### Files Requiring Documentation Updates (~10 files)

- `docs/setup/graphiti-setup.md`
- `docs/guides/graphiti-integration-guide.md`
- `docs/architecture/graphiti-architecture.md`
- `docs/guides/graphiti-shared-infrastructure.md`
- `scripts/graphiti-backup.sh`
- Various test assertion strings

### Files Requiring Zero Changes (~50+ files)

All planning modules, all seed modules, all context command modules, the orchestrator, feature_plan_context.py, interactive_capture.py, and the vast majority of the test suite.

---

## Deep-Dive Addendum: Regression Risk Analysis

This addendum was produced during the `/task-review --depth=deep` revision pass. All claims were verified against graphiti-core source in `.venv/lib/python3.14/site-packages/graphiti_core/`.

---

### DD-1: `execute_query()` Return Type Compatibility — SAFE

**Concern**: Neo4j and FalkorDB `execute_query()` return different types. Would refactoring from `session.run()` to `execute_query()` introduce type errors?

**Finding**: **NO — both return compatible tuple structures.**

| Driver | Return type | `result[0]` | `result[1]` | `result[2]` |
|--------|------------|-------------|-------------|-------------|
| Neo4j | `EagerResult` (named tuple) | `records: List[Record]` | `summary` | `keys` |
| FalkorDB | `tuple` | `records: List[Dict]` | `header: List[str]` | `None` |

Neo4j's `EagerResult` inherits from `tuple`, so both support:
- Unpacking: `records, _, _ = await driver.execute_query(query, **params)`
- Indexing: `records = result[0]`

graphiti-core uses this pattern **everywhere** (search_utils.py, nodes.py, edges.py — verified at ~20 call sites). The pattern is proven safe.

**However**, there is one difference in record format:
- Neo4j records: `List[neo4j.Record]` (need `.data()` to convert to dict)
- FalkorDB records: `List[Dict]` (already dict format)

**Graphiti-core handles this internally** via provider-specific `get_entity_node_from_record()` functions. GuardKit's 3 raw queries return simple scalar values (`group_id`, `count`) that both drivers express as dicts.

**Recommended refactor pattern for the 3 queries:**
```python
# OLD (Neo4j session API — breaks on FalkorDB):
async with driver.session() as session:
    result = await session.run(query, **params)
    records = await result.data()       # Neo4j-specific

# NEW (driver-agnostic — works on both):
result = await driver.execute_query(query, **params)
if result is None:
    return []  # FalkorDB returns None on index-already-exists errors
records, _, _ = result
```

**Regression risk**: LOW. The tuple unpacking pattern is identical to what graphiti-core uses internally.

---

### DD-2: FalkorDB Thread Safety — NEW RISK IDENTIFIED

**Concern**: GuardKit's `GraphitiClientFactory` creates per-thread `GraphitiClient` instances (TASK-FIX-GTP1). Does this work with FalkorDB?

**Finding**: **Per-thread FalkorDriver instances are REQUIRED, but the current factory pattern already supports this.**

**FalkorDB thread-safety issues**:
1. `FalkorDriver.__init__()` creates a single `FalkorDB(host, port, ...)` client (line 150)
2. `_get_graph()` calls `self.client.select_graph()` — potential shared state
3. The async `graph.query()` binds to the event loop at initialization
4. `clone()` reuses the same `self.client` — sharing across threads would race

**Why this is manageable**:
- `GraphitiClientFactory.get_thread_client()` already creates a **new** `GraphitiClient` per thread
- Each `GraphitiClient.initialize()` creates a **new** `Graphiti(...)` instance
- Each `Graphiti` instance creates its own driver (Neo4j or FalkorDB)
- So each thread gets its own `FalkorDriver` with its own `FalkorDB` client

**The pattern that MUST be preserved**:
```
Thread 1: GraphitiClient → Graphiti → FalkorDriver → FalkorDB client (bound to Thread 1 loop)
Thread 2: GraphitiClient → Graphiti → FalkorDriver → FalkorDB client (bound to Thread 2 loop)
```

**Risk**: If anyone creates a single shared `FalkorDriver` and passes it to multiple `Graphiti` instances, cross-thread errors will occur. The factory's per-thread creation pattern is essential.

**Regression risk**: LOW — the factory already creates per-thread clients. No factory code changes needed. Just ensure the `FalkorDriver(...)` constructor is called inside the factory's per-thread initialization, not shared.

---

### DD-3: graphiti-core Internal Driver Agnosticism — VERIFIED SAFE

**Concern**: Even if the driver abstraction exists, does graphiti-core internally use Neo4j-specific patterns that would break with FalkorDB?

**Finding**: **No. graphiti-core is fully driver-agnostic at the application layer.**

Verified call chains:
- `Graphiti.search()` → `search.search()` → `driver.execute_query()` with unpacking
- `Graphiti.add_episode()` → `add_episode_endpoint()` → `driver.execute_query()` for node/edge saves
- `Graphiti.build_indices_and_constraints()` → delegated to `driver.build_indices_and_constraints()`
- Node/Edge `.save()` methods → `driver.execute_query(get_*_save_query(driver.provider))`

**Provider-specific branching** (only in search_utils.py):
```python
if driver.provider == GraphProvider.FALKORDB:
    return driver.build_fulltext_query(query, group_ids)
elif driver.provider == GraphProvider.KUZU:
    ...
else:  # Neo4j default
    ...
```

This is correct design — dialect differences are encapsulated in the driver and search_utils.

**Zero Neo4j imports** found outside `driver/neo4j_driver.py` in graphiti-core. No `import neo4j` in graphiti.py, search.py, nodes.py, edges.py, or any other core module.

**Regression risk**: NONE for graphiti-core APIs.

---

### DD-4: FalkorDB `session.run()` Returns `None` — CONFIRMED

**Concern**: The original report's critical finding. Verify definitively.

**Finding**: **CONFIRMED. `FalkorDriverSession.run()` explicitly returns `None`.**

```python
# falkordb_driver.py lines 100-111
class FalkorDriverSession:
    async def run(self, query: str | list, **kwargs: Any) -> Any:
        if isinstance(query, list):
            for cypher, params in query:
                params = convert_datetimes_to_strings(params)
                await self.graph.query(str(cypher), params)
        else:
            params = dict(kwargs)
            params = convert_datetimes_to_strings(params)
            await self.graph.query(str(query), params)
        return None  # ← ALWAYS returns None
```

The Kuzu driver also returns `None`. Only Neo4j returns a result from `session.run()`.

**graphiti-core itself uses `session.run()` for write batching** (bulk_utils.py) where the return value is ignored. GuardKit's 3 queries use `session.run()` for **reads** — this is the incompatibility.

**Regression risk**: CERTAIN crash if driver is FalkorDB and code not refactored.

---

### DD-5: `Graphiti(graph_driver=FalkorDriver(...))` Constructor — SAFE

**Concern**: Are there hidden side effects when changing the constructor pattern?

**Finding**: **No. The constructor is clean.**

Verified initialization steps (graphiti.py lines 133-260):
1. **Driver assignment** (lines 202-207): `self.driver = graph_driver` if provided, else `Neo4jDriver(...)` — clean swap
2. **LLM/Embedder setup** (lines 211-222): `OpenAIClient()` — completely independent of driver
3. **Telemetry** (lines 238-260): `_get_provider_type()` inspects class name for 'neo4j' or 'falkor' — works correctly
4. **Index auto-build** (driver __init__): Both drivers schedule `build_indices_and_constraints()` via `asyncio.get_running_loop()` — identical pattern

**No Neo4j-specific imports, authentication patterns, or connection pool setup** in the constructor. The swap from `Neo4jDriver` to `FalkorDriver` is completely transparent to `Graphiti.__init__()`.

**Regression risk**: NONE.

---

### DD-6: No FalkorDB Tests in graphiti-core — VALIDATION GAP

**Concern**: Has anyone actually tested graphiti-core with FalkorDB end-to-end?

**Finding**: **No test files for FalkorDB found in graphiti-core package.** The driver implementation exists but appears untested at the integration level.

This means:
- The FalkorDB driver code paths are **untested** in the upstream library
- GuardKit would be an **early adopter** of FalkorDB with graphiti-core
- Edge cases in Cypher dialect differences, datetime handling, and fulltext search syntax may surface

**Recommendation**: Before the migration, run graphiti-core's core test suite against a real FalkorDB instance to validate:
1. `build_indices_and_constraints()` creates correct FalkorDB indices
2. `add_episode()` + `search()` round-trips correctly
3. Fulltext search with RedisSearch syntax returns expected results
4. Datetime fields survive serialization round-trip

**Regression risk**: MEDIUM — untested code paths in upstream library.

---

### DD-7: `falkordb` Python Package — NOT INSTALLED

**Concern**: Does the runtime dependency exist?

**Finding**: **The `falkordb` Python package is NOT installed** in `.venv/`. The `falkordb_driver.py` will raise `ImportError` at import time:

```python
try:
    from falkordb import Graph as FalkorGraph
    from falkordb.asyncio import FalkorDB
except ImportError:
    raise ImportError(
        'falkordb is required for FalkorDriver. '
        'Install it with: pip install graphiti-core[falkordb]'
    )
```

**Action required**: Add to `pyproject.toml`:
```toml
[project.optional-dependencies]
falkordb = ["graphiti-core[falkordb]"]
```

**Regression risk**: LOW — clear error message if missing.

---

### DD-8: FalkorDB `execute_query()` Returns `None` on Index Errors

**Concern**: An edge case in the FalkorDB driver.

**Finding**: `FalkorDriver.execute_query()` returns `None` (not a tuple) when it encounters "already indexed" errors:

```python
# falkordb_driver.py lines 178-181
except Exception as e:
    if 'already indexed' in str(e):
        logger.info(f'Index already exists: {e}')
        return None  # ← Returns None, not ([], [], None)
```

**Impact on GuardKit's 3 queries**: The 3 raw Cypher queries (`MATCH`, `DELETE`, `COUNT`) will NOT trigger "already indexed" errors. This edge case only applies to index creation in `build_indices_and_constraints()`.

**However**, the refactored code MUST handle `None` defensively:
```python
result = await driver.execute_query(query, **params)
if result is None:
    return []  # or 0
records, _, _ = result
```

**Regression risk**: LOW if defensive coding applied. HIGH if not.

---

## Revised Risk Matrix (After Deep Dive)

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|-----------|-----------|--------|
| **FalkorDB session.run() returns None** | CRITICAL | CERTAIN | Refactor to `execute_query()` with unpacking | Confirmed DD-4 |
| **FalkorDB thread safety** | HIGH | MEDIUM | Per-thread FalkorDriver creation (factory pattern) | New — DD-2 |
| **No FalkorDB tests in graphiti-core** | MEDIUM | HIGH | Run integration tests against real FalkorDB first | New — DD-6 |
| **execute_query() returns None on index errors** | MEDIUM | LOW | Add None guard before tuple unpacking | New — DD-8 |
| **`falkordb` package not installed** | LOW | CERTAIN | Add to pyproject.toml optional deps | Confirmed DD-7 |
| **execute_query() type differences** | LOW | LOW | Both return compatible tuples (verified) | Resolved — DD-1 |
| **Constructor change side effects** | NONE | N/A | Constructor is driver-agnostic (verified) | Resolved — DD-5 |
| **graphiti-core internal Neo4j deps** | NONE | N/A | Zero Neo4j imports in core (verified) | Resolved — DD-3 |
| Embedding dimension mismatch | HIGH | LOW | Use same embedding model | Unchanged |
| `DETACH DELETE` Cypher compatibility | LOW | LOW | Standard openCypher | Unchanged |

---

## Revised Migration Plan (After Deep Dive)

### Phase 0: Validation (NEW — Day 0, ~3h)

**Before any code changes**, validate FalkorDB works with graphiti-core:

| Task | Description | Outcome |
|------|-------------|---------|
| 0a | Install `pip install graphiti-core[falkordb]` in a test venv | Verify falkordb package installs |
| 0b | Start FalkorDB Docker container | Verify container runs |
| 0c | Write minimal script: `Graphiti(graph_driver=FalkorDriver(...))` + `build_indices_and_constraints()` | Verify indices create |
| 0d | Write minimal script: `add_episode()` + `search()` round-trip | Verify CRUD works |
| 0e | Test fulltext search with group_ids | Verify RedisSearch syntax |
| 0f | Test datetime fields survive round-trip | Verify serialization |

**If any 0a-0f fail**, stop and file upstream issues before proceeding.

### Phase 1: Infrastructure (Day 1, ~2h) — UNCHANGED

### Phase 2: Client Adaptation (Day 1-2, ~4h) — UPDATED

| Task | Description | Regression Risk |
|------|-------------|----------------|
| 2a | Add `graph_store` config field, conditional driver creation | LOW — additive change |
| 2b | Update factory `get_thread_client()` for FalkorDB | LOW — factory already per-thread |
| **2c** | **Refactor 3 raw Cypher queries to `execute_query()` + tuple unpacking + None guard** | **MEDIUM — verify with both drivers** |
| 2d | Cosmetic log message updates | NONE |
| 2e | Update `_check_connection()` | LOW |

**Task 2c detail** — the exact refactor for each method:

```python
# _list_groups() — current:
async with driver.session() as session:
    result = await session.run("MATCH (e:Episode) RETURN DISTINCT e.group_id AS group_id")
    records = await result.data()
    return [r["group_id"] for r in records if r.get("group_id")]

# _list_groups() — after:
result = await driver.execute_query(
    "MATCH (e:Episode) RETURN DISTINCT e.group_id AS group_id"
)
if result is None:
    return []
records, _, _ = result
return [r["group_id"] for r in records if r.get("group_id")]
```

```python
# _clear_group() — current:
async with driver.session() as session:
    result = await session.run(query, group_id=group_id)
    record = await result.single()
    return record["count"] if record else 0

# _clear_group() — after:
result = await driver.execute_query(query, group_id=group_id)
if result is None:
    return 0
records, _, _ = result
return records[0]["count"] if records else 0
```

```python
# get_clear_preview() — current:
async with driver.session() as session:
    result = await session.run(query, groups=target_groups)
    record = await result.single()
    estimated = record["count"] if record else 0

# get_clear_preview() — after:
result = await driver.execute_query(query, groups=target_groups)
if result is None:
    estimated = 0
else:
    records, _, _ = result
    estimated = records[0]["count"] if records else 0
```

### Phase 3-5: UNCHANGED

---

## Reviewer's Verdict (Revised)

**The migration to FalkorDB is viable and well-scoped, with manageable risk.** The deep dive confirmed:

1. **graphiti-core is fully driver-agnostic** — all high-level APIs (search, add_episode, upsert, build_indices) work with any driver. Zero hidden Neo4j assumptions. (DD-3, DD-5)

2. **The `execute_query()` refactor IS safe** — both Neo4j (`EagerResult` named tuple) and FalkorDB (plain tuple) support identical `records, _, _ = result` unpacking. graphiti-core itself uses this pattern at 20+ call sites. (DD-1)

3. **Thread safety is handled by existing factory** — `GraphitiClientFactory` already creates per-thread clients, so each thread gets its own `FalkorDriver` instance. No factory changes needed. (DD-2)

4. **The main risk is upstream validation** — graphiti-core ships FalkorDB driver code but has no tests for it. We'd be early adopters. Phase 0 (validation) before any code changes is essential. (DD-6)

**Remaining blockers (ordered by priority)**:

| # | Blocker | Effort | Mitigation |
|---|---------|--------|------------|
| 1 | Phase 0 validation (untested upstream driver) | 3h | Run integration tests against real FalkorDB |
| 2 | Refactor 3 raw Cypher queries (Task 2c) | 2h | `execute_query()` + tuple unpacking + None guard |
| 3 | Add `graph_store` config + conditional driver creation | 2h | Additive change, backwards compatible |
| 4 | Install `falkordb` package | 10m | `pip install graphiti-core[falkordb]` |

**Recommended next step**: Execute Phase 0 validation first. If successful, create migration feature plan (FEAT-FKDB-001) with Task 2c as Wave 1 critical path.
