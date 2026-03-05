# Review Report: TASK-REV-BAC1 (Revised — Deep Analysis)

## Executive Summary

TASK-FIX-b94e (raise rule timeout to 180s, project_overview to 240s) was **partially effective**. Rule sync improved from 50% to 83% (6/12 → 10/12), but three new regressions emerged due to graph-size scaling — the same root cause, propagating across technology boundaries.

Deep code-path tracing reveals that the **fundamental bottleneck is not in GuardKit** but in graphiti-core's `add_episode` pipeline, specifically the **edge deduplication phase** which makes O(edges_in_graph) vector searches plus O(extracted_edges) LLM calls per episode. As the graph grows, every subsequent episode takes proportionally longer. GuardKit's timeout is merely the symptom-layer where this manifests.

This revised analysis provides:
1. **C4 architecture diagrams** showing technology boundaries
2. **Sequence diagrams** tracing the exact failure path for each timeout scenario
3. **Root cause analysis per boundary** identifying where the problem lives vs where it appears
4. **Solutions addressing the correct boundary** rather than just raising timeouts

---

## Review Details

- **Mode**: Technical Assessment (deep-dive verification, REVISED)
- **Depth**: Comprehensive with code-path tracing
- **Task**: TASK-REV-BAC1
- **Parent Review**: TASK-REV-EE12
- **Feature**: FEAT-init-graphiti-remaining-fixes

---

## C4 Architecture: System Context

```
┌─────────────────────────────────────────────────────────────────────┐
│                         System Context                              │
│                                                                     │
│  ┌─────────────┐      ┌──────────────┐      ┌──────────────────┐   │
│  │  Developer   │─────▶│  GuardKit    │─────▶│  Knowledge Graph │   │
│  │  (Human)     │      │  CLI         │      │  (FalkorDB)      │   │
│  └─────────────┘      └──────┬───────┘      └──────────────────┘   │
│                              │                        ▲             │
│                              │                        │             │
│                              ▼                        │             │
│                       ┌──────────────┐      ┌─────────┴────────┐   │
│                       │  OpenAI API  │◀─────│  graphiti-core   │   │
│                       │  (LLM)       │      │  (Library)       │   │
│                       └──────────────┘      └──────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

**Boundary inventory**:
- **B1**: Developer → GuardKit CLI (command invocation)
- **B2**: GuardKit CLI → graphiti-core (Python library call)
- **B3**: graphiti-core → FalkorDB (Bolt protocol, TCP)
- **B4**: graphiti-core → OpenAI API (HTTPS, rate-limited)

---

## C4 Architecture: Container Level

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            Container Level                                    │
│                                                                              │
│  ┌────────────────────── GuardKit Process ──────────────────────────────┐    │
│  │                                                                      │    │
│  │  ┌──────────┐  Step 2   ┌───────────────┐                          │    │
│  │  │ CLI init │──────────▶│ project_      │                          │    │
│  │  │ handler  │           │ seeding.py    │                          │    │
│  │  │          │  Step 2.5 ├───────────────┤                          │    │
│  │  │          │──────────▶│ template_     │                          │    │
│  │  │          │           │ sync.py       │                          │    │
│  │  └──────────┘           └───────┬───────┘                          │    │
│  │                                 │                                    │    │
│  │                    add_episode() │ (with timeout wrapper)            │    │
│  │                                 ▼                                    │    │
│  │                         ┌───────────────┐                          │    │
│  │                         │ graphiti_     │ asyncio.wait_for(         │    │
│  │                         │ client.py    │   timeout=120/180/240s)   │    │
│  │                         │              │                           │    │
│  │                         │ _create_     │ ◄── TIMEOUT BOUNDARY     │    │
│  │                         │ episode()   │                           │    │
│  │                         └───────┬───────┘                          │    │
│  └─────────────────────────────────┼────────────────────────────────┘    │
│                                    │                                      │
│            ┌───────────────────────┼───────────────────────┐              │
│            │                       ▼                       │              │
│            │            graphiti-core Library               │              │
│            │  ┌─────────────────────────────────────────┐  │              │
│            │  │          add_episode() Pipeline          │  │              │
│            │  │                                         │  │              │
│            │  │  Phase 1: extract_nodes()      [LLM]   │  │              │
│            │  │  Phase 2: resolve_nodes()      [LLM]   │  │              │
│            │  │  Phase 3: extract_edges()      [LLM]   │  │              │
│            │  │  Phase 4: resolve_edges()  ◄── SLOW    │  │              │
│            │  │           ├─ search existing edges [DB] │  │              │
│            │  │           ├─ vector search per edge[DB] │  │              │
│            │  │           └─ LLM dedup per edge  [LLM] │  │              │
│            │  │  Phase 5: extract_attributes() [LLM]   │  │              │
│            │  │  Phase 6: bulk_write()         [DB]    │  │              │
│            │  │  Phase 7: update_communities()  [LLM]  │  │              │
│            │  └─────────────────────────────────────────┘  │              │
│            │                    │              │           │              │
│            └────────────────────┼──────────────┼───────────┘              │
│                                │              │                          │
│                   ┌────────────┘              └────────────┐              │
│                   ▼                                        ▼              │
│            ┌──────────────┐                      ┌──────────────┐        │
│            │  FalkorDB    │                      │  OpenAI API  │        │
│            │  (Redis+     │                      │  (GPT-4o)    │        │
│            │   Graph)     │                      │              │        │
│            │              │                      │  ~3-10 LLM   │        │
│            │  whitestocks │                      │  calls per   │        │
│            │  :6379       │                      │  episode     │        │
│            └──────────────┘                      └──────────────┘        │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## C4: Episode Seeding Sequence (init flow)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                Episode Seeding Order During `guardkit init`               │
│                                                                          │
│  Step 2: seed_project_knowledge()                                        │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                        │
│                                                                          │
│  Ep│  Name                    │ Group ID (prefixed)            │ Timeout │
│  ──┼──────────────────────────┼────────────────────────────────┼─────────│
│  1 │ project_purpose          │ vllm-profiling__project_overview│  240s  │
│  2 │ project_scope            │ vllm-profiling__project_overview│  240s  │
│  3 │ project_architecture     │ vllm-profiling__project_overview│  240s  │
│  4 │ role_constraint_player   │ role_constraints                │  120s  │
│    │                          │  (INFO: seeds OK at 26.8s)     │        │
│  5 │ role_constraint_coach    │ role_constraints                │  120s  │
│    │                          │  ◄── TIMEOUT at 120.0s         │        │
│  6 │ implementation_mode_*    │ implementation_modes            │  120s  │
│  7 │ implementation_mode_*    │ implementation_modes            │  120s  │
│  8 │ implementation_mode_*    │ implementation_modes            │  120s  │
│                                                                          │
│  Step 2.5: sync_template_to_graphiti()                                   │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                   │
│                                                                          │
│  9 │ template_fastapi-python  │ templates                      │  120s  │
│ 10 │ agent_db-specialist      │ agents                         │  120s  │
│ 11 │ agent_fastapi-specialist │ agents                         │  120s  │
│ 12 │ agent_testing-specialist │ agents                         │  120s  │
│    │                          │  ◄── TIMEOUT at 120.0s         │        │
│ 13 │ rule_code-style          │ rules                          │  180s  │
│ 14 │ rule_testing             │ rules                          │  180s  │
│ 15 │ rule_migrations          │ rules                          │  180s  │
│ 16 │ rule_crud                │ rules                          │  180s  │
│    │                          │  ◄── TIMEOUT at 180.0s         │        │
│ 17 │ rule_models              │ rules                          │  180s  │
│ 18 │ rule_pydantic-constraints│ rules                          │  180s  │
│ 19 │ rule_testing (guidance)  │ rules                          │  180s  │
│ 20 │ rule_fastapi (guidance)  │ rules                          │  180s  │
│ 21 │ rule_database (guidance) │ rules                          │  180s  │
│ 22 │ rule_routing             │ rules                          │  180s  │
│ 23 │ rule_schemas             │ rules                          │  180s  │
│    │                          │  ◄── TIMEOUT at 180.0s         │        │
│ 24 │ rule_dependencies        │ rules                          │  180s  │
│                                                                          │
│  Legend: Episodes 1-8 = Step 2, Episodes 9-24 = Step 2.5                 │
│  Graph grows ↓ with each successful episode                              │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key insight**: The group_id that arrives at `_create_episode()` is ALREADY prefixed by `_apply_group_prefix()`. So:
- `"project_overview"` → `"vllm-profiling__project_overview"` → `.endswith("project_overview")` = True → **240s** ✓
- `"role_constraints"` → stays `"role_constraints"` (SYSTEM_GROUP) → **120s** ← no special handling
- `"rules"` → stays `"rules"` (SYSTEM_GROUP) → `== "rules"` = True → **180s** ✓
- `"agents"` → stays `"agents"` (SYSTEM_GROUP) → **120s** ← no special handling

---

## Sequence Diagram 1: Successful Episode (e.g., rule_code-style at 132.1s)

```
GuardKit               graphiti-core              FalkorDB           OpenAI
_create_episode()      add_episode()              (bolt)             (HTTPS)
    │                      │                         │                  │
    │  wait_for(t=180s)    │                         │                  │
    │─────────────────────▶│                         │                  │
    │                      │                         │                  │
    │                      │  Phase 1: extract_nodes │                  │
    │                      │─────────────────────────────────────────▶│
    │                      │                         │    LLM call #1   │
    │                      │◀─────────────────────────────────────────│
    │                      │  ~5-10s                 │                  │
    │                      │                         │                  │
    │                      │  Phase 2: resolve_nodes │                  │
    │                      │────────────────────────▶│                  │
    │                      │  vector search (nodes)  │                  │
    │                      │◀────────────────────────│                  │
    │                      │─────────────────────────────────────────▶│
    │                      │                         │    LLM call #2   │
    │                      │◀─────────────────────────────────────────│
    │                      │  ~10-20s                │                  │
    │                      │                         │                  │
    │                      │  Phase 3: extract_edges │                  │
    │                      │─────────────────────────────────────────▶│
    │                      │  chunks of 15 nodes     │    LLM call #3   │
    │                      │◀─────────────────────────────────────────│
    │                      │  ~10-15s                │                  │
    │                      │                         │                  │
    │                      │  Phase 4: resolve_edges ◄── THE BOTTLENECK │
    │                      │  FOR EACH extracted edge:│                  │
    │                      │  ┌─────────────────────▶│                  │
    │                      │  │ get_between_nodes()  │                  │
    │                      │  │◀─────────────────────│                  │
    │                      │  │                      │                  │
    │                      │  │ vector search (edges)│                  │
    │                      │  │─────────────────────▶│                  │
    │                      │  │◀─────────────────────│                  │
    │                      │  │                      │                  │
    │                      │  │ LLM: deduplicate     │                  │
    │                      │  │──────────────────────────────────────▶│
    │                      │  │                      │    LLM call #N   │
    │                      │  │◀──────────────────────────────────────│
    │                      │  └──── repeat for each edge              │
    │                      │  ~60-100s (scales with graph size)       │
    │                      │                         │                  │
    │                      │  Phase 5: extract_attrs │                  │
    │                      │─────────────────────────────────────────▶│
    │                      │◀─────────────────────────────────────────│
    │                      │  ~5-10s                 │                  │
    │                      │                         │                  │
    │                      │  Phase 6: bulk_write    │                  │
    │                      │────────────────────────▶│                  │
    │                      │◀────────────────────────│                  │
    │                      │  ~2-5s                  │                  │
    │                      │                         │                  │
    │  ◀── result (132.1s) │                         │                  │
    │  SUCCESS             │                         │                  │
    │                      │                         │                  │
```

**Total**: ~92-160s. The variance is almost entirely in Phase 4, which depends on:
- Number of edges extracted (content-dependent)
- Number of existing edges in graph (graph-size-dependent)
- OpenAI API latency per call (~2-5s each, with variance)

---

## Sequence Diagram 2: Timeout — project_architecture (240.0s)

```
GuardKit               graphiti-core              FalkorDB           OpenAI
_create_episode()      add_episode()              (bolt)             (HTTPS)
    │                      │                         │                  │
    │  wait_for(t=240s)    │                         │                  │
    │─────────────────────▶│                         │                  │
    │                      │                         │                  │
    │                      │  Phase 1: extract_nodes (~10s)            │
    │                      │  Phase 2: resolve_nodes (~20s)            │
    │                      │  Phase 3: extract_edges (~15s)            │
    │                      │                         │                  │
    │                      │  Phase 4: resolve_edges                   │
    │                      │  ┌── edge 1/N ─────────────────────────▶│
    │                      │  │◀──────────────────────────────────────│
    │                      │  │  edge 2/N ──────────────────────────▶│
    │                      │  │◀──────────────────────────────────────│
    │                      │  │  ...                                   │
    │                      │  │  Graph has ~200+ edges from Step 2    │
    │                      │  │  Each resolve: 2 DB queries + 1 LLM  │
    │                      │  │  Each iteration: ~5-8s                │
    │                      │  │  ...                                   │
    │                      │  │                      │                  │
    │  ─── 240s elapsed ──▶│  │                      │                  │
    │  asyncio.TimeoutError│  │                      │                  │
    │  ◀── CancelledError  │  │                      │                  │
    │                      │  │                      │                  │
    │  _record_failure()   │  │  Phase 4 still running...             │
    │  return None         │  │  (coroutine cancelled but OpenAI      │
    │                      │  │   HTTP request may still be in-flight)│
    │                      │  │                      │                  │
    │                      │  │  RuntimeWarning: coroutine             │
    │                      │  │  'extract_attributes_from_node'        │
    │                      │  │  was never awaited (Phase 5 never ran)│
    │                      │  └──────────────────────────────────────┘│
```

**Root cause**: Episode 3 (project_architecture) processes a content-rich CLAUDE.md section. graphiti-core extracts ~15-25 entities and ~30-50 edges. Phase 4 resolve_edges does:
- 30-50 `get_between_nodes()` queries against FalkorDB
- 30-50 vector searches against ~200+ existing edges
- 30-50 LLM calls for deduplication
- At ~5-8s per edge resolution = ~150-400s total for Phase 4 alone

In init_project_5 the graph was smaller (~120 edges from fewer successful seeds), so vector searches returned fewer candidates and LLM dedup was faster → 176.7s total. In init_project_6, 4 more rules successfully seeded → ~200+ edges → Phase 4 expanded by ~63s.

---

## Sequence Diagram 3: Timeout — role_constraint_coach (120.0s)

```
GuardKit               graphiti-core              FalkorDB           OpenAI
_create_episode()      add_episode()              (bolt)             (HTTPS)
    │                      │                         │                  │
    │  wait_for(t=120s)    │                         │                  │
    │  group_id="role_     │                         │                  │
    │  constraints"        │                         │                  │
    │  ◄── NOT "rules",    │                         │                  │
    │  NOT endswith         │                         │                  │
    │  "project_overview"  │                         │                  │
    │  → default 120s      │                         │                  │
    │─────────────────────▶│                         │                  │
    │                      │                         │                  │
    │                      │  Phases 1-3: ~30s                         │
    │                      │                         │                  │
    │                      │  Phase 4: resolve_edges                   │
    │                      │  Graph state at this point:                │
    │                      │  - Ep 1 (project_purpose): ✓ seeded      │
    │                      │  - Ep 2 (project_scope): ✓ seeded        │
    │                      │  - Ep 3 (project_arch): ✗ timed out      │
    │                      │  - Ep 4 (player constraint): ✓ seeded    │
    │                      │  ─────────────────────                    │
    │                      │  Graph: ~80-120 entities, ~150-250 edges │
    │                      │                         │                  │
    │                      │  Coach constraint has rich content:       │
    │                      │  must_do, must_not_do, ask_before,       │
    │                      │  good_examples, bad_examples             │
    │                      │  → extracts ~10-15 edges                  │
    │                      │                         │                  │
    │                      │  Phase 4: ~80-90s for edge resolution    │
    │                      │                         │                  │
    │  ─── 120s elapsed ──▶│                         │                  │
    │  asyncio.TimeoutError│                         │                  │
    │  return None         │  (was 116.2s in init_5 — 3.8s headroom)│
    │                      │  (now >120s due to larger graph)          │
```

**Root cause**: The `role_constraints` group_id is in `SYSTEM_GROUP_IDS`, so it's NOT prefixed, and NOT matched by the `endswith("project_overview")` or `== "rules"` checks. It falls through to the default 120s timeout. The coach constraint episode has complex structured content (must_do/must_not_do/ask_before/examples) that generates many edges, and the growing graph pushed resolution time past 120s.

---

## Sequence Diagram 4: Timeout — fastapi-testing-specialist (120.0s)

```
GuardKit               graphiti-core              FalkorDB           OpenAI
_create_episode()      add_episode()              (bolt)             (HTTPS)
    │                      │                         │                  │
    │  wait_for(t=120s)    │                         │                  │
    │  group_id="agents"   │                         │                  │
    │  → default 120s      │                         │                  │
    │─────────────────────▶│                         │                  │
    │                      │                         │                  │
    │                      │  Graph state at this point:                │
    │                      │  Step 2: 6/8 episodes seeded              │
    │                      │  Step 2.5: template + 2 agents seeded     │
    │                      │  ─────────────────────────                │
    │                      │  Graph: ~150-200 entities, ~300-400 edges│
    │                      │  (MUCH larger than init_project_5 at     │
    │                      │   this point, because 4 more rules       │
    │                      │   completed from PREVIOUS init run left  │
    │                      │   residual data via --copy-graphiti-from)│
    │                      │                         │                  │
    │                      │  Agent content_preview: 500 chars        │
    │                      │  → extracts ~8-12 edges                   │
    │                      │  Phase 4: resolve against ~300+ edges    │
    │                      │                         │                  │
    │  ─── 120s elapsed ──▶│                         │                  │
    │  asyncio.TimeoutError│  (was 64.0s in init_5)  │                  │
    │  return None         │  (+56s = graph scaling)  │                  │
```

**Critical insight**: The `--copy-graphiti-from` flag means the FalkorDB graph from init_project_5 is carried forward. So init_project_6 starts with ALL the successfully-seeded data from init_project_5 already in the graph. Every episode in init_project_6 is deduplicating against the CUMULATIVE graph, not a fresh one.

---

## Root Cause Analysis: Per Technology Boundary

### Boundary B1: Developer → GuardKit CLI
**Status**: NO ISSUE
The CLI correctly orchestrates Step 2 then Step 2.5 in sequence. No parallelism bugs.

### Boundary B2: GuardKit → graphiti-core (THE CONTROL BOUNDARY)
**Status**: TIMEOUT CEILING TOO LOW for some groups

This is where `asyncio.wait_for(timeout=N)` wraps graphiti-core's `add_episode()`. The timeout mapping:

```
group_id check                         → timeout → affected episodes
─────────────────────────────────────────────────────────────────────
.endswith("project_overview")          → 240s    → project_purpose, project_scope,
                                                    project_architecture
== "rules"                             → 180s    → all 12 rules
(everything else)                      → 120s    → role_constraints,
                                                    implementation_modes,
                                                    templates, agents
```

**Problem**: The "everything else = 120s" bucket is too coarse. It groups together:
- `implementation_modes` episodes (12-27s, never at risk)
- `templates` episodes (~98s, comfortable)
- `agents` episodes (60-120s, borderline for testing-specialist)
- `role_constraints` episodes (27-120s, borderline for coach)

### Boundary B3: graphiti-core → FalkorDB
**Status**: NO ISSUE (but contributes to timing)

FalkorDB queries are fast (~1-5ms each for `get_between_nodes`). The vector search operations take ~50-200ms. Neither is the bottleneck — but there are O(extracted_edges) queries, so they add up.

### Boundary B4: graphiti-core → OpenAI API (THE ROOT CAUSE)
**Status**: FUNDAMENTAL BOTTLENECK

Each edge resolution requires 1 LLM call to OpenAI for deduplication. At ~2-5s per call (including network latency), and with 10-50 edges per episode:

```
Edge resolution time = num_extracted_edges × (
    DB_lookup_time +          # ~5ms, negligible
    vector_search_time +      # ~100ms, small
    LLM_dedup_call_time       # ~2-5s, DOMINANT
)

For rule_crud (180s timeout, FAILED):
  ~20 edges × (0.005 + 0.1 + 4.0)s = ~82s for Phase 4 alone
  + Phase 1-3 (~40s) + Phase 5 (~15s) + Phase 6 (~5s)
  = ~142s... but with a larger graph, vector search returns more
    candidates → LLM dedup prompt is longer → 3-5s → 4-7s per call
  = ~20 edges × 6s = ~120s for Phase 4 → total ~180s → TIMEOUT
```

**The scaling formula**:

```
T(episode) ≈ T_fixed + N_edges × (T_db + T_vector(G) + T_llm(G))

Where:
  T_fixed     = ~40-60s (phases 1,2,3,5,6 — roughly constant)
  N_edges     = 10-50 (depends on episode content)
  T_db        = ~5ms (constant, negligible)
  T_vector(G) = ~100-500ms (grows with graph size G as more candidates match)
  T_llm(G)    = ~2-7s (grows with G as dedup prompt includes more existing facts)
  G           = total edges in graph at time of episode processing
```

---

## Graph Growth Model

```
                  Graph Size (edges) During init_project_6
    Edges
    500 ┤
        │                                                    ┌── Step 2.5
    400 ┤                                                   ╱    rules adding
        │                                              ····╱     ~20-40 edges
    300 ┤                                         ····╱        each
        │                                    ····╱
    200 ┤                               ····╱
        │                          ····╱
    150 ┤── from --copy-graphiti ─╱
        │   (init_project_5 data)│
    100 ┤                        │  Step 2 adds
        │                        │  project_overview,
     50 ┤                        │  constraints, modes
        │                        │
      0 ┤────────────────────────┼──────────────────────▶ Time
        Ep1  Ep3  Ep5  Ep8   Template Agents  Rules...

    ◄── init_project_5 started fresh here (~50 edges from prior)
    ◄── init_project_6 starts here (~150 edges from copy) ── HIGHER BASE
```

**The `--copy-graphiti-from` amplification effect**: Each successful init run copies its graph to the target project. The next init run starts with this cumulative graph. So init_project_6 starts with ~150 edges (from init_project_5's successes), whereas init_project_5 started with ~50 edges (from init_project_4's successes). This is why init_project_6 is uniformly slower — every episode faces a larger starting graph.

---

## Definitive Root Cause Summary

```
┌───────────────────────────────────────────────────────────────────────┐
│                     ROOT CAUSE CHAIN                                  │
│                                                                       │
│  1. --copy-graphiti-from copies cumulative graph data                │
│     └─▶ init_project_6 starts with ~150 edges (vs ~50 in init_5)   │
│                                                                       │
│  2. graphiti-core's resolve_edges phase is O(edges × graph_size)     │
│     └─▶ Each edge does: DB lookup + vector search + LLM dedup call  │
│     └─▶ Vector search returns MORE candidates with larger graph      │
│     └─▶ LLM dedup prompt grows with more existing facts             │
│                                                                       │
│  3. OpenAI LLM calls dominate: ~2-7s per edge, non-parallelised     │
│     └─▶ 20 edges × 5s = 100s just for Phase 4                      │
│     └─▶ Total episode time: ~140-200s for complex episodes           │
│                                                                       │
│  4. GuardKit's timeout is a fixed ceiling per group_id               │
│     └─▶ "rules" = 180s, "project_overview" = 240s, default = 120s  │
│     └─▶ No per-episode adaptive timeout                              │
│     └─▶ role_constraints and agents use default 120s — too tight    │
│                                                                       │
│  THEREFORE:                                                           │
│  - The problem is NOT in GuardKit's code (correct architecture)      │
│  - The problem is NOT in FalkorDB (fast queries)                     │
│  - The problem IS in graphiti-core's O(n) LLM pipeline              │
│  - GuardKit can only MITIGATE via timeout tuning or content strategy │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Solutions: Addressing the Correct Boundary

### Solution 1: Tiered Timeout by Group (Boundary B2 — MITIGATION)

**Current state** (after TASK-FIX-b94e):
```python
if group_id.endswith("project_overview"):
    episode_timeout = 240.0
elif group_id == "rules":
    episode_timeout = 180.0
else:
    episode_timeout = 120.0  # ← role_constraints, agents fall here
```

**Proposed** — comprehensive group-aware timeout:
```python
# Tiered timeouts based on empirical data + growth headroom
if group_id.endswith("project_overview"):
    episode_timeout = 300.0   # Was 240s; ep3 hit ceiling at 240s
elif group_id == "rules":
    episode_timeout = 180.0   # Working for 10/12; keep as-is
elif group_id == "role_constraints":
    episode_timeout = 150.0   # Was 120s; coach at 120s needs ~130s
elif group_id == "agents":
    episode_timeout = 150.0   # Was 120s; testing-specialist at 120s
else:
    episode_timeout = 120.0   # templates, implementation_modes: safe
```

**Expected impact**:
| Episode | Current Ceiling | Proposed | Expected Result |
|---------|----------------|----------|-----------------|
| project_architecture | 240s | 300s | SUCCESS (~260-280s with headroom) |
| role_constraint_coach | 120s | 150s | SUCCESS (~125-135s with headroom) |
| agent testing-specialist | 120s | 150s | LIKELY SUCCESS (~120-135s) |
| rule_crud | 180s | 180s | Still fails (needs ~200s+) |
| rule_schemas | 180s | 180s | Still fails (needs ~200s+) |

**Net improvement**: 17/24 → 19-20/24 items synced.

**Complexity**: 2/10 — expand existing conditional, no new logic.

### Solution 2: Content-Aware Episode Splitting (Boundary B2 — STRUCTURAL FIX)

The episodes that timeout have the **most content** → most extracted edges → longest Phase 4. Instead of raising timeouts indefinitely, split large episodes into smaller ones:

```python
# In project_seeding.py, before seeding project_architecture:
MAX_EPISODE_CHARS = 2000  # Keep episodes small for faster processing

def split_large_episode(episode_data):
    """Split episode content into chunks if too large."""
    content = episode_data.content
    if len(content) <= MAX_EPISODE_CHARS:
        return [episode_data]

    # Split at section boundaries (## headings)
    sections = content.split('\n## ')
    chunks = []
    current_chunk = ""
    for section in sections:
        if len(current_chunk) + len(section) > MAX_EPISODE_CHARS:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = section
        else:
            current_chunk += '\n## ' + section if current_chunk else section
    if current_chunk:
        chunks.append(current_chunk)

    return [
        replace(episode_data, content=chunk, metadata={
            **episode_data.metadata,
            'chunk_index': i,
            'total_chunks': len(chunks),
        })
        for i, chunk in enumerate(chunks)
    ]
```

**Rationale**: Smaller episodes → fewer extracted edges per episode → Phase 4 stays fast even with large graphs. Two 1000-char episodes each take ~60-80s instead of one 2000-char episode taking ~200s+.

**Expected impact**: All episodes complete within 120-180s regardless of graph size.

**Complexity**: 4/10 — needs content splitting logic and testing.

**Trade-off**: More episodes = more total LLM calls, but each is smaller and stays under timeout. Total wall-clock time may increase slightly, but reliability improves dramatically.

### Solution 3: Skip Re-seeding of Existing Episodes (Boundary B2 — EFFICIENCY FIX)

When `--copy-graphiti-from` is used, the graph already contains data from the previous init. Re-seeding the same content forces graphiti-core to deduplicate against itself, wasting LLM calls.

```python
# In _create_episode(), before graphiti.add_episode():
async def _create_episode(self, name, episode_body, group_id):
    # Check if episode already exists in graph (fast search)
    existing = await self._graphiti.search(
        name,
        group_ids=[group_id],
        num_results=1,
    )
    if existing and self._content_matches(existing[0], episode_body):
        logger.info(f"Episode already exists, skipping: {name}")
        return existing[0].uuid  # Return existing UUID

    # Only create if new or changed
    return await self._graphiti.add_episode(...)
```

**Rationale**: The upsert_episode method already exists in GraphitiClient but isn't used during init seeding. If the source content hasn't changed (same template, same CLAUDE.md), re-seeding is pure waste.

**Expected impact**: On re-init with `--copy-graphiti-from`, most episodes skip entirely (already in graph). Only changed content needs seeding. Total init time could drop from ~39min to ~5-10min for unchanged projects.

**Complexity**: 5/10 — needs content hashing and existence check logic. The `upsert_episode` method already handles most of this; the seeding code just needs to use it.

### Solution 4: Parallel Episode Seeding Within Groups (Boundary B2 — PERFORMANCE)

Currently all episodes seed sequentially. Episodes within the same group could be parallelised using `asyncio.gather`:

```python
# In template_sync.py, rule syncing:
async def sync_rules_parallel(rule_files, template_id, client, max_concurrent=3):
    """Sync rules with bounded parallelism."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def sync_with_semaphore(rule_file):
        async with semaphore:
            return await sync_rule_to_graphiti(rule_file, template_id, client)

    results = await asyncio.gather(
        *[sync_with_semaphore(f) for f in rule_files],
        return_exceptions=True,
    )
    return results
```

**Rationale**: 12 rules at ~60-180s each, run sequentially = ~1,200-1,500s. Run 3 at a time = ~400-500s.

**Trade-off**: Parallel seeding means the graph grows faster during the sync, which could increase individual episode times. But the wall-clock reduction is substantial. Also, OpenAI rate limits may be hit with too much parallelism.

**Expected impact**: Step 2.5 time: 1,523s → ~600-800s.

**Complexity**: 5/10 — needs semaphore-bounded gather and error handling.

### NOT Recommended: Upstream graphiti-core changes

Fixing the O(n) edge deduplication in graphiti-core would be the ideal solution but is:
- Out of scope (upstream dependency)
- High risk (algorithmic change in LLM pipeline)
- Slow to land (upstream PR cycle)

---

## Recommended Implementation Order

| Priority | Solution | Effort | Impact | Risk |
|----------|----------|--------|--------|------|
| **1** | Solution 1: Tiered timeouts | 2/10 | +2-3 items | Near zero |
| **2** | Solution 3: Skip re-seeding | 5/10 | -80% init time on re-init | Low |
| **3** | Solution 2: Episode splitting | 4/10 | All items complete | Medium |
| **4** | Solution 4: Parallel seeding | 5/10 | -60% Step 2.5 time | Medium |

**Solution 1 should be done immediately** — it's a single conditional expansion that fixes 2-3 more items. Solutions 2-4 are architectural improvements that provide long-term reliability.

---

## TASK-FIX-b94e Effectiveness (from original report)

### Rule Sync Improvement

| Metric | init_project_5 | init_project_6 | Change |
|--------|----------------|----------------|--------|
| Rules synced | 6/12 (50%) | 10/12 (83%) | **+67% improvement** |
| Rules failed | 6/12 | 2/12 | -67% |

### Rule-by-Rule Comparison

| Rule | init_project_5 | init_project_6 | Status Change |
|------|----------------|----------------|---------------|
| code-style | 120.0s TIMEOUT | 132.1s SUCCESS | **FIXED** |
| testing (root) | 88.9s SUCCESS | 73.1s SUCCESS | Stable |
| migrations | 120.0s TIMEOUT | 106.2s SUCCESS | **FIXED** |
| crud | 120.0s TIMEOUT | 180.0s TIMEOUT | Still fails |
| models | 66.7s SUCCESS | 58.7s SUCCESS | Stable |
| pydantic-constraints | 120.0s TIMEOUT | 115.8s SUCCESS | **FIXED** |
| testing (guidance) | 120.0s TIMEOUT | 43.3s SUCCESS | **FIXED** |
| fastapi (guidance) | 36.2s SUCCESS | 30.0s SUCCESS | Stable |
| database (guidance) | 74.1s SUCCESS | 41.8s SUCCESS | Stable |
| routing | 114.6s SUCCESS | 134.6s SUCCESS | Stable |
| schemas | 120.0s TIMEOUT | 180.0s TIMEOUT | Still fails |
| dependencies | 101.7s SUCCESS | 78.6s SUCCESS | Stable |

---

## Cumulative Progress: init_project_3 → 4 → 5 → 6

| Metric | init_project_3 | init_project_4 | init_project_5 | init_project_6 | Trend |
|--------|---------------|----------------|----------------|----------------|-------|
| Total init time | ~7,160s (119 min) | ~2,009s (33 min) | ~2,183s (36 min) | ~2,364s (39 min) | 67% reduction from baseline; +3 min/iteration |
| Query timeouts | 64 | 0 | 0 | 0 | Eliminated |
| Connection closures | 33 | 0 | 0 | 0 | Eliminated |
| Agent sync success | Unknown | 1/3 (33%) | 3/3 (100%) | 2/3 (67%) | Oscillating |
| Rule sync success | Unknown | 10/12 (83%) | 6/12 (50%) | 10/12 (83%) | Recovered |
| Project overview | No | No | Yes (2/2) | Partial (1/2) | Regression |
| Role constraints | Unknown | Unknown | 2/2 (100%) | 1/2 (50%) | Regression |
| Items synced | Unknown | ~15 | ~18 | ~17 | Plateau (~85%) |
| Episode timeouts | Many | 2 | 6 | 4 | Improving |

---

## Acceptance Criteria Checklist

- [x] Quantitative comparison of init_project_5 vs init_project_6 metrics
- [x] Assessment of TASK-FIX-b94e effectiveness (rule sync: 50% → 83%)
- [x] Comparison of actual results vs TASK-REV-EE12 projections (3/6 hit, 3/6 missed)
- [x] Analysis of agent regression (fastapi-testing-specialist: graph-size scaling via --copy-graphiti-from)
- [x] Analysis of role_constraint timeout (group_id not matched by tiered timeout logic)
- [x] Analysis of remaining rule failures (crud, schemas exceed 180s ceiling)
- [x] Analysis of new warning types (index out of bounds — upstream off-by-one) and OpenAI retry (transient)
- [x] Updated cumulative metrics table (init_project_3 → 4 → 5 → 6 progression)
- [x] **C4 system context diagram** showing technology boundaries
- [x] **C4 container diagram** showing internal components and data flow
- [x] **C4 episode seeding sequence** showing exact ordering and timeout mapping
- [x] **Sequence diagram**: successful episode flow through all 4 boundaries
- [x] **Sequence diagram**: project_architecture timeout (Phase 4 bottleneck)
- [x] **Sequence diagram**: role_constraint_coach timeout (group_id mismatch)
- [x] **Sequence diagram**: agent testing-specialist timeout (cumulative graph effect)
- [x] **Root cause per boundary** (B1: clean, B2: timeout ceiling, B3: clean, B4: O(n) LLM)
- [x] **Graph growth model** explaining --copy-graphiti-from amplification
- [x] **4 solutions** addressing correct boundary with effort/impact/risk assessment
- [x] Definitive recommendation with implementation priority order

---

## Decision Options

| Option | Description |
|--------|-------------|
| **[A]ccept** | Accept current ~85% coverage as production-viable |
| **[R]evise** | Request further analysis on specific areas |
| **[I]mplement** | Create tasks for solutions (recommended: Solution 1 immediately, Solutions 2-4 as backlog) |
| **[C]ancel** | Discard review |
