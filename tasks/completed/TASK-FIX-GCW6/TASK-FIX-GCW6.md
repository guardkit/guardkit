---
id: TASK-FIX-GCW6
title: Fix Graphiti client lifecycle - singleton never initialized in autobuild path
status: completed
task_type: fix
created: 2026-02-08T21:00:00Z
updated: 2026-02-08T22:30:00Z
completed: 2026-02-08T22:30:00Z
completed_location: tasks/completed/TASK-FIX-GCW6/
priority: high
tags: [graphiti, context-retrieval, autobuild, fix, singleton, client-lifecycle]
complexity: 4
parent_feature: graphiti-context-wiring
parent_review: TASK-REV-0E58
related_tasks: [TASK-FIX-GCW3, TASK-FIX-GCW4, TASK-REV-8BD8]
---

# Task: Fix Graphiti Client Lifecycle - Singleton Never Initialized in Autobuild Path

## Problem

The Graphiti singleton (`_graphiti` global in `graphiti_client.py`) is **never initialized** during autobuild runs. GCW3 added auto-init code that calls `get_graphiti()`, but `get_graphiti()` just reads the global which is `None` because `init_graphiti()` is never called by any autobuild code path. Context retrieval is fully wired but permanently dormant.

Additionally, there is an architectural inconsistency: the `guardkit graphiti` CLI commands (seed, status, verify, add-context) bypass the singleton entirely, creating their own `GraphitiClient` instances directly via `_get_client_and_config()`. This means the codebase has **two incompatible client initialization strategies** that don't share state.

### Evidence

**Singleton consumers (all get `None` during autobuild):**
- `autobuild.py:597` — `get_graphiti()` in auto-init block
- `autobuild.py:2409` — `get_graphiti()` in another path
- `integrations/graphiti/project.py` — 5 calls to `get_graphiti()`
- `knowledge/template_sync.py` — 3 calls
- `knowledge/feature_plan_context.py:301` — 1 call
- `knowledge/gap_analyzer.py:332` — 1 call
- `knowledge/quality_gate_queries.py:38` — 1 call
- `knowledge/context_loader.py` — 4 calls
- `knowledge/failed_approach_manager.py` — 3 calls
- `knowledge/outcome_manager.py`, `outcome_queries.py`, `turn_state_operations.py` — multiple calls
- `knowledge/seed_quality_gate_configs.py`, `seed_role_constraints.py`, `seed_feature_build_adrs.py` — seeding helpers
- `knowledge/interactive_capture.py:100` — interactive capture

**Direct-client creators (bypass singleton):**
- `cli/graphiti.py:63` — `_get_client_and_config()` → `GraphitiClient(config)`
- `cli/graphiti.py:550` — `GraphitiClient()` (default config)
- `cli/init.py:280` — `GraphitiClient(config)`
- `knowledge/seeding.py:11` — `GraphitiClient(GraphitiConfig())`
- `knowledge/project_seeding.py:391` — `GraphitiClient()`
- `knowledge/seed_pattern_examples.py:20` — `GraphitiClient(GraphitiConfig())`
- `knowledge/seed_failed_approaches.py:19` — `GraphitiClient(GraphitiConfig())`
- `knowledge/adr_service.py:15,55` — `GraphitiClient()`

### Root Cause

1. `init_graphiti()` is async and is defined at `graphiti_client.py:1401` but **never called from any production code path** — only from docstring examples
2. The `guardkit graphiti` CLI commands were built first and create their own clients directly
3. The singleton pattern was added later but no startup hook was created to call `init_graphiti()`
4. GCW3's auto-init correctly calls `get_graphiti()` but can't fix the upstream lifecycle gap

### Impact

- **All context retrieval in autobuild is silently disabled** despite `enable_context=True` being the default
- The GCW1-5 fixes are correct but cannot deliver value until this lifecycle gap is closed
- Operators see `"Graphiti not available, context retrieval disabled"` in logs, which is technically accurate but misleading — Graphiti may be fully available, it's just not initialized

## Proposed Solution

### Approach: Initialize Graphiti in AutoBuildOrchestrator Auto-Init

Modify the auto-init block in `autobuild.py:594-608` to **initialize** the Graphiti client rather than just **read** the uninitialized singleton. This keeps the fix localized and doesn't require changes to every CLI entry point.

Two sub-approaches to consider:

#### Option A: Call `init_graphiti()` from auto-init (singleton approach)
```python
# autobuild.py auto-init block
if self.enable_context and self._context_loader is None:
    try:
        from guardkit.knowledge import init_graphiti, get_graphiti, AutoBuildContextLoader
        import asyncio
        # Initialize the singleton if not already initialized
        graphiti = get_graphiti()
        if graphiti is None:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already in async context
                await init_graphiti()
            else:
                asyncio.run(init_graphiti())
            graphiti = get_graphiti()
        if graphiti and graphiti.enabled:
            self._context_loader = AutoBuildContextLoader(...)
```

**Concern**: `init_graphiti()` is async, `__init__` is sync. Requires asyncio bridging.

#### Option B: Create client directly like CLI commands do (direct approach)
```python
# autobuild.py auto-init block
if self.enable_context and self._context_loader is None:
    try:
        from guardkit.knowledge import AutoBuildContextLoader
        from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig
        from guardkit.knowledge.config import load_graphiti_config
        settings = load_graphiti_config()
        config = GraphitiConfig(
            enabled=settings.enabled,
            neo4j_uri=settings.neo4j_uri,
            ...
        )
        client = GraphitiClient(config)
        # client.initialize() is async — need to handle this
```

**Concern**: Same async problem. Also duplicates `_get_client_and_config()` logic.

#### Option C: Refactor to sync initialization (recommended)
Add a sync `initialize_sync()` method or a sync factory, and consolidate the two initialization paths. This also addresses the broader inconsistency.

### Broader Consideration: Unify Client Initialization

The codebase has ~30+ `get_graphiti()` consumers and ~10 direct `GraphitiClient()` creators. These should eventually converge on a single strategy. Options:

1. **Make `init_graphiti()` the standard** — call it early in CLI startup, all consumers use `get_graphiti()`
2. **Add lazy-init to `get_graphiti()`** — if singleton is None, auto-initialize from config
3. **Keep both patterns** — CLI commands use direct clients for one-shot operations, long-running processes use singleton

Option 2 (lazy-init) is the simplest and most backwards-compatible: modify `get_graphiti()` to auto-initialize from `load_graphiti_config()` when the singleton is None. This fixes autobuild and every other singleton consumer in one place.

## Files to Modify

### Core Fix
- `guardkit/knowledge/graphiti_client.py` — `get_graphiti()` lazy-init or `init_graphiti()` sync variant
- `guardkit/orchestrator/autobuild.py` — Update auto-init block if needed

### Optional Consolidation (scope decision needed)
- `guardkit/cli/graphiti.py` — Migrate `_get_client_and_config()` to use singleton
- `guardkit/cli/init.py` — Migrate direct client creation
- `guardkit/knowledge/seeding.py` — Migrate direct client creation
- `guardkit/knowledge/adr_service.py` — Migrate direct client creation
- Other direct-client creators listed in Evidence section

## Acceptance Criteria

- [ ] `get_graphiti()` returns a usable client during autobuild when Graphiti/Neo4j is available
- [ ] Auto-init block at `autobuild.py:594-608` successfully creates `AutoBuildContextLoader` when Graphiti is available
- [ ] Graceful degradation preserved — no crash when Neo4j unavailable
- [ ] Existing `guardkit graphiti` CLI commands continue to work
- [ ] Tests cover: lazy-init success, lazy-init when Neo4j unavailable, singleton reuse, config loading
- [ ] Init log correctly shows `context_loader=provided` when Graphiti is available

## Design Decisions Needed

1. **Scope**: Fix only the autobuild path, or also consolidate the direct-client creators?
2. **Approach**: Lazy-init in `get_graphiti()` vs sync `init_graphiti()` call vs direct client creation in auto-init?
3. **Async handling**: How to handle the async `client.initialize()` in sync context (`__init__`)?
4. **Config source**: Use `load_graphiti_config()` (reads config file) or `GraphitiConfig()` (env vars/defaults)?

## Risk Assessment

- **Core fix (lazy-init)**: Low risk — additive change, graceful degradation preserved
- **Consolidation (migrate direct clients)**: Medium risk — broader scope, may affect CLI commands
- Recommend: Fix autobuild path first, consolidation as separate task if desired

## Test Plan

- Unit test: `get_graphiti()` returns initialized client when config available
- Unit test: `get_graphiti()` returns None gracefully when Neo4j unavailable
- Unit test: auto-init block creates `AutoBuildContextLoader` with initialized client
- Unit test: lazy-init doesn't re-initialize if already initialized
- Integration test: full chain CLI flag → orchestrator → context_loader → initialized client
