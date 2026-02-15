# RediSearch Fulltext Query Workarounds for FalkorDB + Graphiti

> **Date**: 15 February 2026  
> **Relates to**: FEAT-FKDB-001 — FalkorDB Migration  
> **Workaround file**: `guardkit/knowledge/falkordb_workaround.py`  
> **Status**: Both workarounds applied, verified working

---

## Summary

Two additional bugs were discovered in graphiti-core's FalkorDB driver after the initial migration (TASK-FKDB-001 through TASK-FKDB-008). Both relate to how RediSearch fulltext indexing interacts with FalkorDB's multi-graph architecture and graphiti-core's `group_id` filtering.

These are in addition to the original decorator bug (PR #1170) already documented in `falkordb-search-bug-resolution.md`.

---

## Bug 1: Single group_id Driver Cloning (Existing — PR #1170)

**Upstream**: [getzep/graphiti#1161](https://github.com/getzep/graphiti/issues/1161) / [PR #1170](https://github.com/getzep/graphiti/pull/1170)

The `@handle_multiple_group_ids` decorator in `graphiti_core/decorators.py` checks `len(group_ids) > 1` before cloning the FalkorDB driver for the target graph database. This means single group_id searches (the common case) skip driver cloning entirely, querying the wrong graph.

**Fix**: Monkey-patch to use `>= 1` instead of `> 1`.

---

## Bug 2: RediSearch @group_id Filter Breaks on Underscores

**Discovered**: 15 February 2026  
**Affects**: graphiti-core v0.26.3 with FalkorDB backend  
**Upstream issue**: Not yet filed

### Problem

graphiti-core's `FalkorDriver.build_fulltext_query()` constructs RediSearch queries with an `@group_id` field filter:

```
(@group_id:product_knowledge) (search terms here)
```

This fails because RediSearch treats underscores as **token separators**. The value `product_knowledge` is tokenized as two separate terms: `product` and `knowledge`. This happens both at index time (when edges are stored) and at query time.

RediSearch's separator characters include:
```
, . < > { } [ ] " ' : ; ! @ # $ % ^ & * ( ) - + = ~ _
```

### Symptoms

Every search that uses a `group_id` filter produces:

```
ERROR: RediSearch: Syntax error at offset 31 near product_knowledge
query: '(@group_id:product_knowledge) ()'
```

This affects **all** GuardKit group_ids because they use underscore naming:
- System groups: `product_knowledge`, `command_workflows`, `quality_gate_phases`, `technology_stack`
- Project groups: `guardkit__project_overview`, `guardkit__project_architecture`, `guardkit__feature_specs`

### Why It Was Hard to Diagnose

The bug only manifests on the **fulltext search path**. Other operations work fine:
- `add_episode()` — writes use Cypher, not RediSearch fulltext
- Vector-only searches — use cosine distance on embeddings, no fulltext
- Cypher `WHERE e.group_id IN $group_ids` — string comparison, not fulltext

The status command and `JobContextRetriever` both hit the fulltext path, making it appear that groups were empty when they actually contained data.

### Initial Wrong Fix: Escaping Underscores

First attempt: escape underscores with backslash (`product\_knowledge`) before query construction. This failed for two reasons:

1. **Index-time tokenization**: Even if the query escapes underscores, the stored values were already tokenized at index time. `@group_id:product\_knowledge` can't match because the index contains `product` and `knowledge` as separate tokens, not `product_knowledge`.

2. **Groups without underscores also fail**: `patterns` and `agents` (no underscores) also produced syntax errors when the search text was empty, producing `(@group_id:patterns) ()` — the `()` is invalid RediSearch syntax.

### Correct Fix: Remove @group_id Filter Entirely

The `@group_id` fulltext filter is **redundant** on FalkorDB because group isolation is already enforced by two other mechanisms:

1. **Driver cloning** (Workaround 1): The `@handle_multiple_group_ids` decorator clones the FalkorDB driver to point at the specific named graph for each group_id. Every edge in the `product_knowledge` graph already has `group_id = "product_knowledge"`.

2. **Cypher WHERE clause**: The search query includes `WHERE e.group_id IN $group_ids` which performs exact string comparison after fulltext results are returned.

The fix monkey-patches `build_fulltext_query` to always pass `group_ids=None`, skipping the broken `@group_id` filter.

---

## Bug 3: Empty Query Text Produces Invalid RediSearch Syntax

**Discovered**: 15 February 2026 (during Bug 2 fix)  
**Affects**: Any search where the query text is fully stripped by RediSearch stopword removal

### Problem

When `build_fulltext_query` receives a query that consists entirely of stopwords or produces no meaningful tokens, the result is:

```
' ()'
```

This is invalid RediSearch syntax — `()` is empty parentheses with no content.

### Context

The `guardkit graphiti status` command searches with a generic probe query to count edges per group. After stopword removal, nothing remains, producing the empty `()`.

### Fix

After calling the original `build_fulltext_query`, check if the result is `()` or empty. If so, return `*` (RediSearch wildcard for "match all"). This is safe because the Cypher WHERE clause still filters by group_id.

**Note**: The `*` wildcard can timeout on very large graphs (observed on `guardkit__project_decisions`). This only affects the status command's "count everything" approach; real searches with actual query terms won't hit this.

---

## Implementation

All three workarounds are in `guardkit/knowledge/falkordb_workaround.py`:

```python
# Called once at startup
apply_falkordb_workaround()

# Internally applies:
# 1. handle_multiple_group_ids: >= 1 instead of > 1
# 2. build_fulltext_query: group_ids=None (remove @group_id filter)
# 3. build_fulltext_query: empty result -> '*' wildcard
```

The module auto-detects if upstream fixes are applied and skips unnecessary patches.

---

## Verification Results

After all workarounds applied:

| Group | Facts | Status |
|-------|-------|--------|
| product_knowledge | 27 | ✅ |
| command_workflows | 100 | ✅ |
| patterns | 100 | ✅ |
| agents | 16 | ✅ |
| project_overview | 39 | ✅ |
| project_architecture | 35 | ✅ |
| architecture_decisions | 65 | ✅ |
| failure_patterns | 24 | ✅ |
| feature_specs | 0 | ✅ (not yet seeded) |
| task_outcomes | 0 | ✅ (not yet seeded) |
| successful_fixes | 0 | ✅ (not yet seeded) |
| project_decisions | 0 | ⚠️ Timeout on `*` wildcard |
| **Total Episodes** | **406** | |

---

## Upstream Actions

| Action | Status |
|--------|--------|
| PR #1170 (decorator fix) | Open, unreviewed 5+ weeks |
| RediSearch group_id filter bug | Not yet filed — needs upstream issue |
| Empty query fallback | Not yet filed — needs upstream issue |

### Recommended Upstream Fix

Rather than escaping, the upstream fix for `build_fulltext_query` should:

1. Skip the `@group_id` filter when `driver.provider == GraphProvider.FALKORDB` (it's redundant due to multi-graph isolation)
2. Handle the empty query case by returning `*` or skipping the fulltext search entirely
3. Consider using RediSearch TAG fields instead of fulltext for `group_id` filtering (TAG fields support exact matching without tokenization)
