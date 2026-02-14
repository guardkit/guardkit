# FalkorDB Multi-Episode Search Bug: Resolution Research

> **Date**: February 2026  
> **Related Task**: TASK-FKDB-001 (AC-006 FAIL)  
> **Status**: HIGH CONFIDENCE — Likely resolved in current graphiti-core v0.24.3

---

## Summary

The multi-episode search destruction bug identified in TASK-FKDB-001 — where adding a second `add_episode()` call destroyed searchability of all previously-indexed data — is **very likely resolved** in the current graphiti-core release (v0.24.3). Between the version tested (~v0.17.x era) and v0.24.3, Zep shipped **three major FalkorDB-specific fixes** that directly address the failure modes we observed.

**Recommendation**: Upgrade to graphiti-core v0.24.3 and re-run TASK-FKDB-001 validation. If AC-006 passes, FalkorDB is unblocked for GuardKit integration.

---

## What Changed Since Our Test

### v0.23.0 — FalkorDB Enhancements (8 Nov 2025)

This was the **critical release** for FalkorDB. Key PRs:

| PR | Title | Relevance |
|----|-------|-----------|
| #835 | GraphID isolation support for FalkorDB multi-tenant architecture | Fixes group_id handling that was causing search failures |
| #1050 | Enable FalkorDB fulltext search tests | **All 4 FalkorDB fulltext search tests now pass** (edge, node, episode, community) — these were previously skipped |
| #910 | Integrate MCP for FalkorDB | Full MCP server support with FalkorDB as default backend |
| #911 | Add FalkorDB support for docker compose | Official Docker deployment |

The PR #1050 commit message is particularly telling: *"Testing revealed that all FalkorDB fulltext search tests pass successfully. The skip was added in PR #872 without explanation and appears to be unnecessary."* Tests were verified passing with FalkorDB 1.2.3.

### v0.23.1 — FalkorDB Entity Edge Save Fix (9 Nov 2025)

- **PR #1013**: Fixed the entity edge save bug (issue #1001) where `source_node_uuid` and `target_node_uuid` were stored as `None` in the FalkorDB Cypher SET statement
- This fix means edges now have proper UUID metadata, which is **critical for graph traversal search** — broken edges would explain why search returned 0 results after the second episode created new entity relationships

### v0.24.0–v0.24.3 (Nov–Dec 2025)

- Improved Anthropic model support (relevant for GuardKit)
- Property filters added
- Language prompt updates

---

## Root Cause Analysis (Updated)

Our original investigation identified four potential causes. Here's the updated status:

### 1. Index Rebuild Destroying Existing Data — LIKELY FIXED

The FalkorDB driver's `build_indices_and_constraints()` method uses RedisSearch commands that can DROP and recreate indices. The v0.23.0 release included significant FalkorDB driver improvements and the fulltext search tests now pass across multiple episodes, strongly suggesting this was addressed.

### 2. group_ids Filtering Bug (Issue #801) — STILL OPEN, WORKAROUND AVAILABLE

**Status**: Open, marked as "duplicate" (suggesting it's tracked elsewhere)

The `episode_fulltext_search` returns empty results when `group_ids` is `None` or `[]` because the WHERE clause `e.group_id IN $group_ids` always evaluates to false.

**Workaround**: Always pass explicit `group_ids` parameter. For FalkorDB, the default group_id is `"_"`, so use:

```python
results = await graphiti.search("query", group_ids=["_"])
```

This is the most likely remaining issue and is trivially worked around.

### 3. BFS Query Syntax Incompatibility (Issue #815) — STILL OPEN, AFFECTS search_() ONLY

**Status**: Open

FalkorDB doesn't support the `Entity|Episodic` label union syntax used in BFS queries. However, this **only affects `search_()`** (the underscore variant with graph traversal), not the standard `search()` method. The issue reporter confirmed: *"search() work normally"*.

**Impact for GuardKit**: Low — we use `search()`, not `search_()`.

### 4. Missing Edge UUID Properties (Issue #1001) — FIXED in v0.23.1

**Status**: Closed

The FalkorDB Cypher query's SET statement was missing `source_node_uuid` and `target_node_uuid`. Fixed by PR #1013 (contributed by @galshubeli from FalkorDB team).

---

## Additional Findings

### FalkorDB is Now the Default Backend

As of MCP Server v1.0.0 (Oct 2025), FalkorDB is the **default database backend** for the Graphiti MCP server. This represents a significant vote of confidence from Zep — they wouldn't default to a backend with known search destruction bugs.

### Active FalkorDB Development

The open PR list shows continued FalkorDB-specific work:
- PR #1118: Fix FalkorDB sanitize to handle forward slash character
- PR #1117: Add username support for FalkorDB authentication  
- PR #1105: Fix search returns empty results after container restart

### graphiti-core-falkordb Fork (v0.19.10)

FalkorDB maintains a separate PyPI package `graphiti-core-falkordb` which is their own fork. This appears to be older than the current upstream and should NOT be used — stick with the official `graphiti-core[falkordb]` package.

---

## Re-validation Plan

### Step 1: Upgrade

```bash
pip install --upgrade graphiti-core[falkordb]
# Expected: v0.24.3
```

### Step 2: Update FalkorDB Docker

```bash
docker pull falkordb/falkordb:latest
# Expected: v1.2.3+
```

### Step 3: Modify Validation Script

Key changes to `validate_falkordb.py`:

1. **Always pass explicit group_ids** — use `group_ids=["_"]` instead of `None`
2. **Use `search()` not `search_()`** — avoid the BFS syntax issue
3. **Add delay between episodes** — give index time to update (2-3 seconds)

```python
# AC-006 modified test
await graphiti.add_episode(
    name="ep1",
    episode_body="Alice works at Acme Corp as a software engineer",
    reference_time=datetime.now(timezone.utc),
    group_id="_"
)

await asyncio.sleep(3)  # Allow index propagation

await graphiti.add_episode(
    name="ep2", 
    episode_body="Bob manages the data science team at Beta Inc",
    reference_time=datetime.now(timezone.utc),
    group_id="_"
)

await asyncio.sleep(3)

# Search with explicit group_id
results = await graphiti.search("Alice", group_ids=["_"])
assert len(results) > 0, "EP1 data should still be searchable after EP2"

results = await graphiti.search("Bob", group_ids=["_"])
assert len(results) > 0, "EP2 data should be searchable"
```

### Step 4: Extended Multi-Episode Test

If AC-006 passes, run a more aggressive test with 5-10 episodes to confirm stability at scale.

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Bug still present in v0.24.3 | Low (20%) | Upstream tests pass; FalkorDB is now default backend |
| group_ids workaround insufficient | Low (15%) | Well-documented issue with clear fix path |
| New bugs introduced since v0.23.0 | Medium (30%) | PR #1105 suggests container restart issues exist |
| Performance regression | Low (10%) | FalkorDB benchmarks show 496x P99 improvement |

---

## Decision Framework

**If re-validation PASSES**: Proceed with FalkorDB as the production backend for GuardKit's knowledge graph. Benefits: Redis-based (simpler ops), faster performance, in-memory with persistence, lighter resource footprint than Neo4j.

**If re-validation FAILS**: Two options:

1. **Stay on Neo4j** (recommended) — Known working, full feature support, mature ecosystem. The operational overhead is higher but reliability is proven.

2. **Try KuzuDriver** — Embedded database shipped with graphiti-core. No network dependency, good for development. However, limited feature support (no dynamic fulltext indexing).

---

## Key Takeaway

The timing of our original validation was unfortunate — we tested right before v0.23.0 shipped the major FalkorDB fixes. The combination of GraphID isolation (#835), fulltext search enablement (#1050), and entity edge save fix (#1013) addresses the exact failure modes we observed. A re-test with v0.24.3 has a high probability of passing.
