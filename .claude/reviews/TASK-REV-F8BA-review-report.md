# Review Report: TASK-REV-F8BA — Graphiti Zero Categories Root Cause Analysis

## Executive Summary

**Root cause identified with high confidence**: Two independent bugs cause ALL search results to be silently discarded:

1. **RC6 (PRIMARY): Score attribution gap** — `Graphiti.search()` returns `list[EntityEdge]` without scores, but GuardKit's `_execute_search()` uses `getattr(edge, 'score', 0.0)` which defaults to `0.0` because `EntityEdge` has no `score` attribute. The `edge_reranker_scores` are stored separately in `SearchResults` and discarded by the public `search()` API. All results then fail the relevance threshold filter (`0.0 >= 0.5` → False).

2. **RC7 (SECONDARY): Circuit breaker cascade** — `JobContextRetriever` never calls `reset_circuit_breaker()` between category queries, so 3 consecutive failures (even transient) disable all remaining categories for 60s.

The `handle_multiple_group_ids` workaround (`>= 1`) is **correct and necessary** — reverting it would break 25+ call sites. `add_episode` DOES route data to group-specific FalkorDB databases.

**Fix**: Use `Graphiti.search_()` (which returns `SearchResults` with scores) or substitute `1.0` for missing scores. Add circuit breaker reset between categories.

---

## Review Details

- **Mode**: Decision Analysis (Comprehensive)
- **Depth**: Full code path trace through 6 layers + 4-area revision
- **Task**: TASK-REV-F8BA
- **Parent**: TASK-REV-982B

---

## Critical Correction from Revision

### Initial Hypothesis (OVERTURNED)

The initial analysis hypothesized that the `handle_multiple_group_ids` workaround caused searches to query empty databases. **This was wrong.** Deeper analysis of graphiti-core's `add_episode` method (line 881-890) revealed:

```python
# graphiti_core/graphiti.py:881-890
if group_id != self.driver._database:
    self.driver = self.driver.clone(database=group_id)
    self.clients.driver = self.driver
```

`add_episode` **does clone the driver** based on `group_id`, storing data in group-specific FalkorDB databases (e.g., "patterns" graph, "failure_patterns" graph). The workaround is correct — it ensures single-group searches also clone to the right database.

**Impact of reverting to `> 1`**: Would silently break **25+ production call sites** that pass single-element `group_ids` lists. This includes all `_query_category()` invocations, all CLI verify/list commands, turn state operations, ADR service, and more.

---

## Root Cause RC6: Score Attribution Gap (PRIMARY)

### The Bug

`EntityEdge` (graphiti-core) has **no `score` field**:

```python
# graphiti_core/edges.py:263-282
class EntityEdge(Edge):
    name: str
    fact: str
    fact_embedding: list[float] | None
    episodes: list[str]
    expired_at: datetime | None
    valid_at: datetime | None
    invalid_at: datetime | None
    attributes: dict[str, Any]
    # NO score field
```

Scores are stored separately in `SearchResults`:

```python
# graphiti_core/search/search_config.py:121-129
class SearchResults(BaseModel):
    edges: list[EntityEdge]
    edge_reranker_scores: list[float]   # ← scores here, parallel to edges
    nodes: list[EntityNode]
    node_reranker_scores: list[float]
    ...
```

But `Graphiti.search()` discards scores:

```python
# graphiti_core/graphiti.py:1379-1389
edges = (
    await search(self.clients, query, group_ids, search_config, ..., driver=driver)
).edges   # ← only edges, scores discarded
return edges
```

GuardKit's `_execute_search()` tries to get scores from edges:

```python
# graphiti_client.py:881
"score": getattr(edge, 'score', 0.0),   # ← always 0.0
```

Then `_query_category()` filters:

```python
# job_context_retriever.py:985-991
score = item.get("score", 1.0)  # gets 0.0 (key exists, value is 0.0)
if score >= threshold:           # 0.0 >= 0.5 → False
    filtered.append(item)        # never reached
```

**Result**: Every search result is silently filtered out. 0 categories, 0 tokens, always.

### Evidence

| Step | Code Location | Value |
|------|--------------|-------|
| EntityEdge has no `score` | graphiti_core/edges.py:263 | `score` not in class fields |
| SearchResults stores scores separately | graphiti_core/search/search_config.py:123 | `edge_reranker_scores: list[float]` |
| `Graphiti.search()` returns only edges | graphiti_core/graphiti.py:1389 | `.edges` extracts list without scores |
| `_execute_search` defaults to 0.0 | graphiti_client.py:881 | `getattr(edge, 'score', 0.0)` |
| `_query_category` threshold is 0.5-0.6 | job_context_retriever.py:351 | `STANDARD_THRESHOLD = 0.6` |
| 0.0 < 0.5, filtering removes all | job_context_retriever.py:991 | `score >= threshold` never true |

### Fix Options

**Option A: Use `search_()` instead of `search()` (Recommended)**

`Graphiti.search_()` returns `SearchResults` with both edges and scores. Change `_execute_search` to call `search_()` and zip edges with scores:

```python
# In _execute_search:
search_results = await self._graphiti.search_(
    query,
    config=EDGE_HYBRID_SEARCH_RRF,
    group_ids=group_ids,
)
result_list = [
    {
        "uuid": edge.uuid,
        "fact": edge.fact,
        "name": getattr(edge, 'name', edge.fact[:50]),
        "score": score,
    }
    for edge, score in zip(search_results.edges, search_results.edge_reranker_scores)
]
```

**Pros**: Proper scores, enables meaningful relevance filtering.
**Cons**: `search_()` also uses `@handle_multiple_group_ids`, so `SearchResults.merge()` is called for multi-group — need to verify score merging.

**Option B: Default score to 1.0 (Quick Fix)**

Change `_execute_search` to use `1.0` as default:

```python
"score": getattr(edge, 'score', 1.0),  # or getattr(edge, 'score', None) or 1.0
```

**Pros**: 1-character fix, immediately unblocks all context loading.
**Cons**: Loses relevance filtering entirely — all results pass threshold.

**Option C: Treat 0.0 scores as "no score" in filter**

Change `_query_category` to treat 0.0 as "no score provided":

```python
score = item.get("score") or 1.0  # falsy 0.0 becomes 1.0
```

**Pros**: Minimal change, consistent with intent of existing `1.0` default.
**Cons**: Can't distinguish genuine low-relevance from missing scores.

---

## Root Cause RC7: Circuit Breaker Cascade (SECONDARY)

### The Bug

The circuit breaker trips after 3 consecutive failures (`_max_failures = 3`). In `JobContextRetriever`, categories are queried sequentially (or in parallel via `asyncio.gather`). If any 3 queries fail, the circuit breaker trips and all subsequent queries return `[]` immediately.

**Critical**: `reset_circuit_breaker()` is called in seeding code (`seeding.py`, `seed_rules.py`) but **never** in `job_context_retriever.py` or `autobuild_context_loader.py`.

### Fix

Add `self.graphiti.reset_circuit_breaker()` between category queries in `retrieve()`, matching the pattern used in seeding.

---

## Previous Root Causes — Updated Status

| RC | Description | Status | Impact |
|----|-------------|--------|--------|
| RC2 | `patterns` vs `patterns_{tech_stack}` mismatch | **FIXED** (TASK-GCF-001) | Eliminated |
| RC3 | Dynamic groups empty on fresh runs | **FIXED** (TASK-GCF-003) | Eliminated |
| RC4 | Project namespace mismatch (`guardkit__` vs `vllm_profiling__`) | **Confirmed** | 65% of context budget affected for cross-project queries |
| RC5 | Silent exception handler | **FIXED** (TASK-GCF-002) | Diagnostic: will reveal exceptions |
| **RC6** | **Score attribution gap — EntityEdge has no score, defaults to 0.0, filtered by threshold** | **NEW — PRIMARY** | **ALL results silently discarded** |
| **RC7** | **Circuit breaker not reset between category queries** | **NEW — SECONDARY** | **3 failures disable remaining categories** |

---

## Additional Secondary Findings

### Embedding Model Consistency

- Config specifies `nomic-embed-text-v1.5` (768-dim) via vLLM at `promaxgb10-41b1:8001`
- Default fallback is `text-embedding-3-small` (1536-dim) — incompatible vector space
- If vLLM embedding endpoint was offline during seeding or search, cosine similarity would be meaningless
- **Risk**: Medium — verify vLLM serves same model consistently

### `handle_multiple_group_ids` Workaround — CONFIRMED CORRECT

The workaround changing `> 1` to `>= 1` is **necessary and correct**:

- `add_episode` routes writes to group-specific FalkorDB databases (graphiti_core/graphiti.py:881-890)
- Without the workaround, single-group searches fall through to `default_db` which contains NO data
- 25+ production call sites pass single-element `group_ids` lists
- Test `test_single_group_id_triggers_clone` explicitly validates this behavior

### FalkorDB Fulltext Index State

- `clone(database=gid)` creates a new `FalkorDriver` which schedules `build_indices_and_constraints()` in the event loop
- Indices are created per-group during seeding (74/79 episodes succeeded)
- During search, clone also creates indices — but they're already present from seeding
- **Risk**: Low for seeded groups, medium for unseeded groups (e.g., new project groups)

---

## Recommendations — Priority Order

### 1. Fix Score Attribution (RC6) — CRITICAL

**Recommended: Option A** (use `search_()` for proper scores) or **Option B** (default to 1.0) as immediate fix.

Option B is the fastest unblock:
```python
# graphiti_client.py:881 — change 0.0 to 1.0
"score": getattr(edge, 'score', 1.0),
```

### 2. Add Circuit Breaker Reset (RC7) — HIGH

Add reset between category batches in `job_context_retriever.py`:
```python
# After standard_queries gather, before autobuild_queries
if hasattr(self.graphiti, 'reset_circuit_breaker'):
    self.graphiti.reset_circuit_breaker()
```

### 3. Address RC4 Namespace Mismatch — MEDIUM

For cross-project AutoBuild (vllm-profiling querying guardkit-seeded data):
- Either re-seed from the target project
- Or implement cross-project search (query both `guardkit__*` and `{current}__*` groups)

### 4. Verify Embedding Consistency — LOW

Run diagnostic: embed a known string from both seeding and search contexts, compare cosine similarity.

---

## Decision Matrix

| Criteria | Option A (search_()) | Option B (score=1.0) | Option C (or 1.0) |
|----------|---------------------|---------------------|-------------------|
| Fix zero-categories | Yes | Yes | Yes |
| Preserves relevance filtering | Yes (proper scores) | No (all pass) | No (all pass) |
| Implementation effort | ~20 lines | 1 character | 1 character |
| Risk | Low-Medium | Very low | Very low |
| Time to deploy | Hours | Minutes | Minutes |
| **Recommendation** | **Best long-term** | **Best quick fix** | Acceptable |

---

## Verification Plan

### Step 1: Apply Score Fix (Option B — immediate)
```python
# graphiti_client.py:881
"score": getattr(edge, 'score', 1.0),
```

### Step 2: Add Circuit Breaker Reset
```python
# job_context_retriever.py — after standard queries gather
if hasattr(self.graphiti, 'reset_circuit_breaker'):
    self.graphiti.reset_circuit_breaker()
```

### Step 3: Run AutoBuild with Diagnostics
```bash
# Check logs for:
# - RC5 logging: category-level warnings (exceptions vs empty results)
# - TASK-VOPT-002: per-turn context loading timing
# - Category population: "[Graphiti] Player context: N categories, X/Y tokens"
```

### Step 4: Implement Option A (search_()) for Proper Scoring
```python
# Replace self._graphiti.search() with self._graphiti.search_()
# Map SearchResults.edge_reranker_scores to result dicts
```

---

## Appendix: Complete Code Path Trace (Corrected)

### Write Path (Seeding)
```
GraphitiClient.add_episode(group_id="patterns", scope=None)
  → _apply_group_prefix("patterns") → "patterns" (system group, no prefix)
  → _create_episode(group_id="patterns")
    → self._graphiti.add_episode(group_id="patterns")
      → "patterns" != self.driver._database ("default_db")
      → self.driver = self.driver.clone(database="patterns")     ← CLONES TO "patterns" DB
      → self.clients.driver = self.driver
      → writes nodes/edges to "patterns" FalkorDB graph          ← DATA HERE
```

### Read Path (Search) — with score bug
```
_query_category(group_ids=["patterns"])
  → GraphitiClient.search(group_ids=["patterns"])
    → _apply_group_prefix("patterns") → "patterns"
    → _execute_search(group_ids=["patterns"])
      → self._graphiti.search(group_ids=["patterns"])
        → @handle_multiple_group_ids (>= 1)
          → driver.clone(database="patterns")                     ← CORRECT DB
          → search runs against "patterns" graph                  ← DATA EXISTS
          → returns list[EntityEdge]                              ← NO .score ATTRIBUTE
      → getattr(edge, 'score', 0.0) → 0.0                       ← BUG: score lost
      → returns [{"score": 0.0, ...}, ...]
    → score = item.get("score", 1.0) → 0.0
    → 0.0 >= 0.5 → False                                         ← BUG: filtered out
    → returns ([], 0)
```

### Key Files Referenced

| File | Role |
|------|------|
| `graphiti_core/edges.py:263` | EntityEdge class — NO score field |
| `graphiti_core/search/search_config.py:121` | SearchResults — scores in separate list |
| `graphiti_core/graphiti.py:1331-1389` | search() discards scores, returns only edges |
| `graphiti_core/graphiti.py:881-890` | add_episode clones driver by group_id |
| `guardkit/knowledge/graphiti_client.py:881` | getattr(edge, 'score', 0.0) — bug |
| `guardkit/knowledge/job_context_retriever.py:985-991` | Threshold filter — 0.0 always fails |
| `guardkit/knowledge/falkordb_workaround.py` | Workaround is CORRECT (>= 1 needed) |
| `guardkit/_group_defs.py` | System/Project group definitions |

---

## Implementation Results

All four fixes applied and verified. Tests pass (100/100 in affected test files).

### Fix 1: Score Default (RC6 — CRITICAL) ✅
**File**: `guardkit/knowledge/graphiti_client.py:881`
- Changed `getattr(edge, 'score', 0.0)` → `getattr(edge, 'score', None) or 1.0`
- Ensures edges without score attribute pass threshold filters

### Fix 2: Circuit Breaker Reset (RC7 — HIGH) ✅
**File**: `guardkit/knowledge/job_context_retriever.py`
- Added `reset_circuit_breaker()` before standard queries gather
- Added `reset_circuit_breaker()` before AutoBuild queries
- Added `reset_circuit_breaker()` before sequential category loop
- Prevents cascade failures across category batches

### Fix 3: Switch to search_() API (RC6 — PROPER FIX) ✅
**File**: `guardkit/knowledge/graphiti_client.py:_execute_search()`
- Replaced `self._graphiti.search()` with `self._graphiti.search_()`
- Uses `EDGE_HYBRID_SEARCH_RRF` config (same as search() uses internally)
- Zips `SearchResults.edges` with `edge_reranker_scores` for proper scoring
- Updated 8 tests across `test_graphiti_client.py` and `test_graphiti_client_circuit_breaker.py`

### Fix 4: RC4 Namespace Diagnostic ✅
**File**: `guardkit/knowledge/graphiti_client.py` (constructor)
- Added info-level log when config `project_id` differs from cwd-derived name
- Confirms config value takes precedence (no actual mismatch in production)
- RC4 is a theoretical risk, not an active bug — config `project_id: guardkit` is used consistently
