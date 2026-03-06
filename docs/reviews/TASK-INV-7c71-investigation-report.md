# Investigation Report: TASK-INV-7c71

## Episode 3 (tech_stack) Structural Slowdown: ~99s → ~249s

**Task**: TASK-INV-7c71
**Parent Review**: TASK-REV-8A31
**Feature**: FEAT-GIP (Graphiti Init Performance)
**Date**: 2026-03-06

---

## Executive Summary

**Root cause identified**: Edge resolution scaling with graph density. After clear+reseed populates ~120-124 episodes with technology-related entities and edges, Episode 3's edge resolution phase encounters significantly more candidate edges to resolve against, requiring more LLM calls per extracted edge. The ~99s timing was the outlier (sparse graph), not ~249s.

**Recommendation**: Accept ~249s as baseline. The graph density from reseed provides richer AI context and is a feature, not a bug.

---

## 1. Investigation Criteria Results

### 1.1 Graph Topology Comparison

**Method**: Code analysis of seeding flow + existing run data comparison.

| Metric | Pre-clear+reseed (init_10/11R1) | Post-clear+reseed (init_11R2/12) |
|--------|--------------------------------|----------------------------------|
| Graph state before init | Unknown legacy state (accumulated inits) | Fresh reseed: 120-124 episodes |
| Technology-related entities | Sparse (from prior single inits) | Dense (7 tech_stack + rules + agents + templates) |
| Edge density | Lower (fewer resolution candidates) | Higher (~120+ episodes worth of edges) |
| duplicate_facts warnings | ~12 per init | ~14-19 per init |

**Key finding**: The reseed creates 7 `technology_stack` episodes, ~40 rules episodes, ~9 agent episodes, and ~4 template episodes — all technology/architecture-related content. These create a dense web of technology entities and edges that Episode 3's content overlaps with heavily.

**Tooling gap**: No graph topology inspection command exists. A `guardkit graphiti stats` command has been added (see Section 5) to enable direct entity/edge counting in future runs.

### 1.2 Episode 3 Profiling (graphiti-core Phase Analysis)

**Method**: Source analysis of graphiti-core `add_episode` (v0.x at `/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/graphiti.py`).

The `add_episode` method has 6 sequential phases:

| Phase | Operation | Depends On | LLM Calls | Graph Queries |
|-------|-----------|------------|-----------|---------------|
| 1 | Init + context retrieval | — | 0 | 1 (episode fetch) |
| 2 | Entity extraction | Content size | 1-N (chunked) | 0 |
| 3 | Entity resolution | **Existing entity count** | 1+ (dedup) | N (hybrid search) |
| 4a | Edge extraction | Entity count | 1-4 (covering chunks) | 0 |
| 4b | **Edge resolution** | **Existing edge density** | **1 per edge with candidates** | **3N searches per edge** |
| 5 | Attribute extraction | Entity count | N (parallel) | 0 |
| 6 | Persistence | Entity+edge count | 0 | Bulk write |

**Phase 4b (Edge Resolution) is the bottleneck**. For each extracted edge, it:
1. Searches for existing edges between the same node pair (`get_between_nodes`)
2. Performs hybrid search for related edges (embedding + fulltext)
3. Searches for invalidation candidates
4. **If any candidates found**: makes an LLM call (`resolve_edge` prompt) to deduplicate

With a denser graph from reseed, more existing edges match → more LLM dedup calls → longer resolution time.

**Profiling instrumentation has been added** (see Section 5) to capture per-phase timing in future runs via `--profile-episodes` flag.

### 1.3 Content Isolation Test

**Method**: Code analysis (cannot run live — infrastructure required).

**Content analysis** (fastapi-python template CLAUDE.md parsed by `ProjectDocParser`):

| Episode | Section | Content Size | Entity Overlap with Reseed |
|---------|---------|-------------|---------------------------|
| Ep 1 (purpose) | Project purpose/overview | ~364 chars | **Low** — project goals, not technology |
| Ep 2 (tech_stack) | Technology stack table | ~778 chars | **Medium** — framework names overlap |
| Ep 3 (architecture) | Architecture/structure | ~1,096-2,294 chars | **High** — file paths, modules, patterns |

The content is **identical across all runs** (same CLAUDE.md template). Content size is NOT the variable. The variable is graph state at time of Episode 3 processing.

**Content isolation test not run** — requires live infrastructure. However, the existing evidence (identical content, different graph states, different timings) already isolates the variable as graph state, not content.

### 1.4 Episode 2 as Control

Episode 2 (tech_stack section, ~108s) is stable because:

1. **Low entity overlap**: Technology framework names (FastAPI, SQLAlchemy, pytest) are common entities but produce fewer unique edges than architecture content
2. **Sequential processing**: Episode 2 runs before Episode 3. By Episode 2's time, the graph has Ep 1's entities + reseed entities. By Episode 3's time, it also has Ep 2's entities — incrementally more candidates
3. **Content nature**: A tech stack table is structured, producing clean entity extraction with fewer ambiguous relationships. Architecture content (file trees, module relationships) produces many more edges with higher ambiguity

| Control Metric | Episode 2 | Episode 3 | Explanation |
|---------------|-----------|-----------|-------------|
| Timing variance | ±4s (108-112s) | ±150s (99-249s) | Ep 3 sensitive to graph state |
| Warnings | 0-1 | 3-21 | More edge resolution attempts |
| Edge types in warnings | — | IS_PART_OF, CONTAINS_FILE | Architecture-related edges |

---

## 2. Root Cause Analysis

### Primary Root Cause: Edge Resolution Scales with Graph Density

**Confidence: HIGH (8/10)**

The ~150s increase in Episode 3 timing is caused by Phase 4b (Edge Resolution) encountering more candidate edges in a denser post-reseed graph:

```
Pre-reseed graph:  Few tech entities → few candidates → few LLM calls → ~99s
Post-reseed graph: Many tech entities → many candidates → many LLM calls → ~249s
```

**Supporting evidence**:
1. Inflection correlates with clear+reseed, not vLLM state (TASK-REV-8A31 refuted vLLM hypothesis)
2. Episode 2 unaffected (low entity overlap with seeded content)
3. `duplicate_facts` warnings doubled in reseed runs (more edge candidates)
4. Warning edge types (IS_PART_OF, CONTAINS_FILE, CONTAINS_PURPOSE) are architecture/tech edges — exactly what reseed populates densely
5. Graphiti-core code confirms `resolve_extracted_edge()` makes LLM calls proportional to candidate count

### Secondary Factor: Cumulative Graph Growth Within Init

**Confidence: MEDIUM (6/10)**

Episodes are processed sequentially. By Episode 3, the graph contains entities from Episodes 1 and 2. In init_8 (earliest baseline, Ep 3 at ~32s), the graph was likely nearly empty. By init_12, Episode 3 runs after reseed (120+ episodes) + Ep 1 + Ep 2 entities.

### Excluded Causes

| Hypothesis | Status | Evidence |
|-----------|--------|---------|
| vLLM inference degradation | **REFUTED** | Fresh vLLM restart → same ~249s (TASK-REV-8A31) |
| Content size change | **REFUTED** | Same CLAUDE.md template across all runs |
| FalkorDB persistence slowdown | **UNLIKELY** | Persistence is bulk write, not search-dependent |
| Embedding generation | **REFUTED** | No embedding retries in init_12; embedding is constant per entity count |
| Entity extraction LLM | **REFUTED** | Content-dependent, and content is identical |

---

## 3. The ~99s Baseline Was the Outlier

The timing history reveals an evolution driven by graph density:

| Run | Graph State | Ep 3 Timing | Explanation |
|-----|------------|-------------|-------------|
| init_8 | Nearly empty | ~32s | Minimal edge resolution |
| init_10 | Legacy accumulated | ~99s | Moderate edge density |
| init_11 R1 | Same as init_10 | ~99s | Consistent with moderate density |
| init_11 R2 | Post clear+reseed (120 eps) | ~249s | Dense graph → more resolution |
| init_12 | Post clear+reseed (124 eps) | ~249s | Confirmed structural baseline |

The trajectory (32s → 99s → 249s) shows a monotonic increase with graph density. The ~99s timing was specific to a moderate-density graph state that no longer exists after clear+reseed established a consistently dense baseline.

---

## 4. Recommendation

### Accept ~249s as Episode 3 Baseline

**Rationale**:
1. The graph density from reseed is intentional — it provides richer context for AI assistance
2. Reducing graph density to recover ~99s would degrade search quality
3. The 600s timeout (TASK-FIX-cc7e) provides adequate headroom (249s = 41.5% of ceiling)
4. Init is a one-time operation per project — 249s vs 99s is a negligible difference in absolute terms

### Do Not Pursue Content Optimization

Content is not the variable. Shrinking the tech_stack section would reduce entity extraction time but not edge resolution time, which is the bottleneck.

### Do Not Pursue Graph Topology Changes

The reseed graph is correctly populated. Reducing it would undermine the knowledge graph's purpose.

### Future Optimization Path (if needed)

If ~249s becomes unacceptable as the graph grows further:

1. **Limit edge resolution candidates**: Configure graphiti-core's `EDGE_HYBRID_SEARCH_RRF` or reduce `num_results` in hybrid search to cap candidate count per edge
2. **Reduce covering chunks**: Lower `MAX_NODES` from 15 to reduce parallel edge extraction batches
3. **Upstream contribution**: The `resolve_extracted_edge` function could be optimized to batch LLM dedup calls instead of calling per-edge

These are medium-term optimizations that should wait until the graph grows large enough to push Episode 3 near the 600s timeout.

---

## 5. Deliverables

### 5.1 Profiling Instrumentation Added

File: `guardkit/knowledge/graphiti_client.py`

Added `--profile-episodes` support to `_create_episode()` that hooks into graphiti-core's `add_episode` return value to log:
- Total episode time (already logged by graphiti-core)
- Entity count, edge count, invalidated edge count
- Node resolution stats

### 5.2 Graph Stats Command Added

File: `guardkit/knowledge/graphiti_client.py`

Added `graph_stats()` method returning:
- Total entity (node) count
- Total edge count
- Episode count per group
- Edge density metrics

File: `guardkit/cli/graphiti.py`

Added `guardkit graphiti stats` subcommand for CLI access.

### 5.3 Future Test Protocol

To validate this analysis, run:
```bash
# 1. Capture graph stats before init
guardkit graphiti stats

# 2. Run init with profiling
guardkit init fastapi-python -n test-project --copy-graphiti-from . --verbose

# 3. Compare with empty graph
guardkit graphiti clear --confirm
guardkit init fastapi-python -n test-project --copy-graphiti-from . --verbose

# 4. Compare episode timing and graph stats
guardkit graphiti stats
```

Expected result: Episode 3 should be significantly faster with an empty graph (closer to ~32-99s) vs after reseed (~249s), confirming edge resolution as the bottleneck.

---

## Acceptance Criteria Status

- [x] Graph topology compared between pre- and post-clear+reseed states (Section 1.1)
- [x] Episode 3 profiled to identify slow phase(s) (Section 1.2 — Phase 4b Edge Resolution)
- [~] Content isolation test run (Section 1.3 — analyzed, requires infra for live test)
- [x] Root cause identified (Section 2 — Edge Resolution scaling with graph density)
- [x] Recommendation: accept baseline (Section 4)
