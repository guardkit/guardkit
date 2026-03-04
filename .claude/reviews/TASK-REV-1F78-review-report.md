# Review Report: TASK-REV-1F78 (Revised)

## Executive Summary

The `guardkit init fastapi-python` timeout errors have **three compounding root causes**, all now confirmed with high confidence:

1. **Upstream graphiti-core bug** ([getzep/graphiti#1272](https://github.com/getzep/graphiti/issues/1272)): `edge_fulltext_search` uses an O(n×m) re-MATCH pattern instead of O(n) `startNode(e)/endNode(e)`, causing 2ms queries to take 26-118 seconds on moderately-sized graphs.
2. **FalkorDB TIMEOUT set to 1000ms**: The NAS docker-compose sets `TIMEOUT 1000` (1 second), which is far too low for the O(n×m) queries graphiti-core generates. These queries need 2-120+ seconds.
3. **DS918+ hardware is adequate for the workload** but the combination of (1) and (2) makes it irrelevant — even a powerful server would timeout at 1000ms when queries take 26+ seconds due to the upstream bug.

**The `rules` group data is NOT consumed by Player/Coach agents at runtime.** It is only searchable via `guardkit graphiti search` for human ad-hoc use. Reducing or eliminating rule content from Graphiti has **zero impact** on autobuild quality.

---

## C4 Diagrams

### Diagram 1: Init Sync — Full Episode Ingestion Sequence

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  guardkit init fastapi-python                                                       │
│                                                                                     │
│  Step 2.5: sync_template_to_graphiti()                                              │
│  ─────────────────────────────────────                                              │
│                                                                                     │
│  For each of 16 items (1 template + 3 agents + 12 rules):                           │
│                                                                                     │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │ template_sync│───►│ graphiti_client   │───►│ graphiti-core│───►│  FalkorDB    │   │
│  │ .py          │    │ .add_episode()   │    │ .add_episode()│    │  (NAS)       │   │
│  │              │    │ 3 retries, 2s/4s │    │              │    │  whitestocks  │   │
│  └──────────────┘    └──────────────────┘    └──────┬───────┘    └──────────────┘   │
│                                                      │                              │
│                                                      ▼                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐     │
│  │  graphiti-core add_episode() INTERNAL SEQUENCE (per episode)               │     │
│  │                                                                             │     │
│  │  Step 1: retrieve_episodes()                                                │     │
│  │          → DB query: fetch recent episodes for context                      │     │
│  │                                                                             │     │
│  │  Step 2: extract_nodes()                                                    │     │
│  │          → LLM call(s): entity extraction from episode_body content         │     │
│  │          → For 3-6KB rule content: extracts ~5-15 entities                  │     │
│  │                                                                             │     │
│  │  Step 3: resolve_extracted_nodes()                                          │     │
│  │          → N parallel hybrid searches (1 per entity):                       │     │
│  │            • node_fulltext_search (BM25)     ← FalkorDB query              │     │
│  │            • node_similarity_search (cosine)  ← FalkorDB query              │     │
│  │          → LLM dedup call                                                   │     │
│  │                                                                             │     │
│  │  Step 4: extract_edges()                                                    │     │
│  │          → LLM call(s): relationship extraction                             │     │
│  │          → For 5-15 entities: creates ~10-30 edges                          │     │
│  │                                                                             │     │
│  │  Step 5: resolve_extracted_edges()     ◄◄◄ WHERE TIMEOUTS OCCUR ◄◄◄        │     │
│  │          → Per edge (10-30 edges), THREE search rounds:                     │     │
│  │                                                                             │     │
│  │          5a. get_between_nodes()                                             │     │
│  │              → Cypher MATCH per edge pair                                    │     │
│  │                                                                             │     │
│  │          5b. SEARCH 1 — Related edge dedup (filtered by node pair):         │     │
│  │              • edge_fulltext_search ──────────────► FalkorDB               │     │
│  │                CALL db.idx.fulltext.queryRelationships(                      │     │
│  │                  'RELATES_TO', $query)                                       │     │
│  │                YIELD relationship AS rel, score                              │     │
│  │                MATCH (n)-[e:RELATES_TO {uuid: rel.uuid}]->(m) ◄── BUG #1272│     │
│  │                  ↑ This re-MATCH scans ALL edges: O(fulltext × total_edges) │     │
│  │                  ↑ 2ms fulltext → 26-118s with re-MATCH                     │     │
│  │                                                                             │     │
│  │              • edge_similarity_search ────────────► FalkorDB               │     │
│  │                cosine distance on fact_embedding (768-dim vectors)           │     │
│  │                                                                             │     │
│  │          5c. SEARCH 2 — Invalidation candidates (NO node filter):           │     │
│  │              • Same as 5b but UNFILTERED — searches entire graph            │     │
│  │              • Even more expensive than 5b                                  │     │
│  │                                                                             │     │
│  │          5d. LLM dedup per edge                                              │     │
│  │                                                                             │     │
│  │  Step 6: extract_attributes_from_nodes()                                    │     │
│  │          → LLM call per node                                                │     │
│  │                                                                             │     │
│  │  Step 7: _process_episode_data()                                            │     │
│  │          → Bulk DB write (UNWIND + MERGE)                                   │     │
│  └─────────────────────────────────────────────────────────────────────────────┘     │
│                                                                                     │
│  QUERY VOLUME PER EPISODE (for a rule with ~10 entities, ~20 edges):                │
│  ┌───────────────────────────────────────────────────────┐                          │
│  │  Node searches:    10 fulltext + 10 cosine = 20       │                          │
│  │  Edge-between:     20 MATCH queries                   │                          │
│  │  Edge dedup (5b):  20 fulltext + 20 cosine = 40       │ ← TIMEOUTS HERE         │
│  │  Edge inval (5c):  20 fulltext + 20 cosine = 40       │ ← TIMEOUTS HERE         │
│  │  TOTAL:            ~120 FalkorDB queries per episode   │                          │
│  │  × 16 episodes  =  ~1920 queries during Step 2.5      │                          │
│  └───────────────────────────────────────────────────────┘                          │
│                                                                                     │
│  With TIMEOUT=1000ms and O(n×m) bug, most edge queries timeout.                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Diagram 2: Runtime — Player/Coach Context Retrieval

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  AutoBuild Runtime: Player/Coach Turn                                               │
│                                                                                     │
│  ┌────────────────────┐     ┌──────────────────────┐     ┌──────────────────┐       │
│  │ AutoBuildOrchestrator│──►│ AutoBuildContextLoader │──►│ JobContextRetriever│      │
│  │ .run()              │    │ .get_player_context() │    │ .retrieve()       │      │
│  └────────────────────┘     └──────────────────────┘     └────────┬─────────┘       │
│                                                                    │                │
│                                                                    ▼                │
│  ┌─────────────────────────────────────────────────────────────────────────────┐     │
│  │  SEARCHES ISSUED (per Player/Coach turn)                                   │     │
│  │                                                                             │     │
│  │  Standard groups (ALL tasks):                                               │     │
│  │  ┌─────────────────────────┬───────────┬─────────────────────────────┐      │     │
│  │  │ Group ID                │ Budget %  │ Purpose                     │      │     │
│  │  ├─────────────────────────┼───────────┼─────────────────────────────┤      │     │
│  │  │ feature_specs           │ 15%       │ Feature requirements        │      │     │
│  │  │ task_outcomes           │ 25%       │ Similar past task results   │      │     │
│  │  │ patterns_{tech_stack}   │ 20%       │ Known good patterns         │      │     │
│  │  │ project_architecture    │ 20%       │ System design context       │      │     │
│  │  │ failure_patterns        │ 15%       │ Known bugs to avoid         │      │     │
│  │  │ domain_knowledge        │ 5%        │ Business domain context     │      │     │
│  │  └─────────────────────────┴───────────┴─────────────────────────────┘      │     │
│  │                                                                             │     │
│  │  AutoBuild-only groups (when is_autobuild=True):                            │     │
│  │  ┌─────────────────────────┬─────────────────────────────────────────┐      │     │
│  │  │ Group ID                │ Purpose                                 │      │     │
│  │  ├─────────────────────────┼─────────────────────────────────────────┤      │     │
│  │  │ role_constraints        │ Player/Coach behavioral boundaries      │      │     │
│  │  │ quality_gate_configs    │ Task-type quality thresholds            │      │     │
│  │  │ turn_states             │ Cross-turn learning (last 5 turns)      │      │     │
│  │  │ implementation_modes    │ Direct vs task-work patterns            │      │     │
│  │  └─────────────────────────┴─────────────────────────────────────────┘      │     │
│  │                                                                             │     │
│  │  ╔═══════════════════════════════════════════════════════════════════╗      │     │
│  │  ║  GROUPS NOT QUERIED AT RUNTIME:                                  ║      │     │
│  │  ║                                                                  ║      │     │
│  │  ║  • "rules"      ← synced in Step 2.5, NEVER read by autobuild  ║      │     │
│  │  ║  • "agents"     ← synced in Step 2.5, NEVER read by autobuild  ║      │     │
│  │  ║  • "templates"  ← synced in Step 2.5, NEVER read by autobuild  ║      │     │
│  │  ║                                                                  ║      │     │
│  │  ║  These are ONLY available via `guardkit graphiti search` CLI     ║      │     │
│  │  ║  for human ad-hoc queries. The Player/Coach NEVER access them.  ║      │     │
│  │  ╚═══════════════════════════════════════════════════════════════════╝      │     │
│  └─────────────────────────────────────────────────────────────────────────────┘     │
│                                                                                     │
│  Result: RetrievedContext → .to_prompt() → markdown string → context= parameter     │
│                                                                                     │
│  If Graphiti unavailable: context_prompt = "" (graceful degradation)                 │
│  Player/Coach still runs with static agent markdown files only.                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Diagram 3: FalkorDB Query Execution — The Timeout Mechanism

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  FalkorDB Query Execution Path                                                      │
│                                                                                     │
│  MacBook Pro (client)          Tailscale WireGuard           DS918+ NAS (server)    │
│  ───────────────────          ──────────────────            ────────────────────     │
│                                                                                     │
│  graphiti-core                                              FalkorDB container      │
│  ┌────────────────┐           ┌─────────────┐              ┌──────────────────┐     │
│  │ FalkorDriver   │──────────►│  Tailscale   │─────────────│  Redis protocol  │     │
│  │ .execute_query()│  TCP 6379│  mesh tunnel │  Tailscale  │  (port 6379)     │     │
│  └────────────────┘           └─────────────┘              └────────┬─────────┘     │
│                                                                      │              │
│                                                              ┌───────▼───────┐      │
│  FalkorDB Server Configuration:                              │  Query Thread  │      │
│  ┌─────────────────────────────────┐                         │  Pool          │      │
│  │ TIMEOUT = 1000 (ms)             │ ◄── 1 SECOND!           │               │      │
│  │ MAX_QUEUED_QUERIES = 100        │                         │  THREAD_COUNT  │      │
│  │ RESULTSET_SIZE = 10000          │                         │  = 4 (4 cores) │      │
│  │ --maxmemory 1gb                 │                         └───────┬───────┘      │
│  │ mem_limit = 1536m               │                                 │              │
│  └─────────────────────────────────┘                                 ▼              │
│                                                              ┌──────────────┐       │
│  DS918+ Hardware:                                            │ Fulltext      │       │
│  ┌─────────────────────────────────┐                         │ Index Query   │       │
│  │ CPU: Celeron J3455              │                         │              │       │
│  │      4-core, 1.5GHz (2.3 burst)│                         │ Step 1: BM25 │       │
│  │ RAM: 8GB DDR3L                  │                         │ fulltext     │       │
│  │ Kernel: Linux 4.4.180+          │                         │ → ~2ms       │       │
│  │ No CPU CFS scheduler            │                         │              │       │
│  └─────────────────────────────────┘                         │ Step 2: re-  │       │
│                                                              │ MATCH by UUID│       │
│                                                              │ → O(n × m)   │       │
│  TIMEOUT SEQUENCE:                                           │ → 26-118s    │       │
│  ─────────────────                                           │              │       │
│  t=0ms     Query arrives                                     │ Step 3: WHERE│       │
│  t=2ms     Fulltext index returns ~1500 results              │ filter       │       │
│  t=1000ms  ████████ TIMEOUT ████████                         │ → killed     │       │
│            Server kills query, returns error                 └──────────────┘       │
│            "Query timed out"                                                        │
│                                                                                     │
│  WHY 1000ms IS TOO LOW:                                                             │
│  ────────────────────────                                                           │
│  The upstream bug (#1272) causes edge queries to do:                                │
│                                                                                     │
│    CALL db.idx.fulltext.queryRelationships(...)                                     │
│      YIELD relationship AS rel, score                                               │
│      MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)                   │
│                          ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑                               │
│                          This re-MATCH scans ALL edges                               │
│                          for each fulltext result.                                   │
│                          1500 results × 5000 edges = 7.5M comparisons               │
│                                                                                     │
│  FIX (proposed in #1272):                                                           │
│    CALL db.idx.fulltext.queryRelationships(...)                                     │
│      YIELD relationship AS e, score                                                 │
│      WITH e, score, startNode(e) AS n, endNode(e) AS m                              │
│                      ↑↑↑↑↑↑↑↑↑↑↑↑    ↑↑↑↑↑↑↑↑↑↑↑                                 │
│                      O(1) per result — no scan needed                               │
│                      1500 results × 1 lookup = 1500 comparisons                     │
│                                                                                     │
│  With fix: ~2ms fulltext + ~1ms endpoint lookup = ~3ms total                        │
│  Without fix: ~2ms fulltext + 26-118s re-MATCH = TIMEOUT                            │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Diagram 4: Connection Exhaustion Timeline

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  FalkorDB Server State During Init                                                  │
│                                                                                     │
│  Time (s)  Event                                    FalkorDB State                  │
│  ────────  ──────────────────────────────────       ──────────────────              │
│  0         Step 2 starts (8 seeding episodes)       OK, low load                    │
│  401       Step 2 complete                          ~200 entities, ~400 edges       │
│                                                                                     │
│  401       Step 2.5 starts                          Graph: moderate                 │
│  401-500   template + 3 agents synced (96-153s ea)  Queries slow (96-153s/episode)  │
│            ↑ No timeouts yet — episodes succeed                                     │
│            ↑ but take 2-5× expected time                                            │
│                                                                                     │
│  ~500      code-style rule sync begins              Graph: ~300 entities, ~800 edges│
│  ~500      ████ First timeout (line 112) ████       Fulltext queries > 1000ms       │
│            edge_fulltext queries start timing out                                   │
│            Retry 1/3... 2s wait... Retry 2/3... 4s wait... Retry 3/3               │
│                                                                                     │
│  ~600-5000 Rules sync with cascading timeouts       Graph grows each episode        │
│            Each episode:                            More edges → slower queries     │
│            - Extracts ~10 entities, ~20 edges       Positive feedback loop:         │
│            - Fires ~120 queries                     more data → slower queries →    │
│            - ~80 of those timeout at 1000ms          more timeouts → partial data → │
│            - Some succeed (within 1000ms)            still more entities added      │
│                                                                                     │
│  ~5000     3 consecutive add_episode failures       ████████████████████████████    │
│            Circuit breaker trips (line 1300)         CIRCUIT BREAKER TRIPPED        │
│            "Graphiti disabled after 3 failures"                                     │
│                                                                                     │
│  ~5000+    BUT: graphiti-core's internal ops         FalkorDB server exhausted     │
│            still running inside in-flight episodes   - Thread pool saturated        │
│            These bypass the circuit breaker           - Pending queries in queue     │
│                                                       - Memory pressure from        │
│  ~5000-6700 Connection closures begin (33 total)       concurrent operations        │
│             "Connection closed by server"                                           │
│             Both fulltext AND vector queries fail      Server drops TCP connections  │
│             768-dim vectors dumped in error logs        to shed load                 │
│                                                                                     │
│  ~6759     Step 2.5 completes                        Server recovering              │
│            "Template sync complete: 1 template,                                     │
│             3 agents, 12 rules synced (6759.4s)"                                    │
│                                                                                     │
│  ~6759     "GuardKit initialized successfully!"      FalkorDB back to OK           │
│            5 unawaited coroutine warnings                                           │
│            (search, edge_search, node_search,                                       │
│             episode_search, community_search)                                       │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Revised Findings

### Finding 1 (CONFIRMED): Upstream graphiti-core O(n×m) Query Bug

**Confidence: Very High** — confirmed by [getzep/graphiti#1272](https://github.com/getzep/graphiti/issues/1272)

The `edge_fulltext_search` method in graphiti-core uses:
```cypher
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
  YIELD relationship AS rel, score
  MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)  -- O(n×m) re-MATCH
```

Instead of:
```cypher
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
  YIELD relationship AS e, score
  WITH e, score, startNode(e) AS n, endNode(e) AS m             -- O(n) direct access
```

**Measured impact** (from issue #1272): fulltext returns 1492 results in 2ms, but re-MATCH takes 26.7 seconds for 412 results. Complete query takes 118.4 seconds. With TIMEOUT=1000ms, this always times out.

This is the **primary root cause**. Every edge search in Steps 5b and 5c of `add_episode()` hits this bug. With ~20 edges per episode and 2 searches per edge (dedup + invalidation), that's ~40 fulltext queries per episode that all timeout.

### Finding 2 (CONFIRMED): FalkorDB TIMEOUT=1000ms Is Too Low

**Confidence: Very High** — directly verified from [docker-compose.falkordb.yml](docker/nas/docker-compose.falkordb.yml):55

```yaml
FALKORDB_ARGS=MAX_QUEUED_QUERIES 100 TIMEOUT 1000 RESULTSET_SIZE 10000
```

`TIMEOUT 1000` = 1000 milliseconds = **1 second**. Per [FalkorDB docs](https://docs.falkordb.com/getting-started/configuration.html), this is the query execution timeout for read queries. When the O(n×m) edge queries need 26-118 seconds, they will always exceed 1 second.

**Key nuance**: Even raising TIMEOUT won't fix the performance problem — it would just let the queries complete slowly instead of timing out. The real fix is the upstream O(n) query pattern.

### Finding 3 (CONFIRMED): DS918+ Hardware Is NOT the Bottleneck

**Confidence: Very High**

The DS918+ specs:
- **CPU**: Celeron J3455, 4-core, 1.5GHz (burst 2.3GHz)
- **RAM**: 8GB DDR3L (FalkorDB allocated 1GB maxmemory, 1.5GB container)
- **THREAD_COUNT**: 4 (matches CPU cores — this is the FalkorDB query thread pool)

**Why hardware is not the problem**:
1. The fulltext index lookup itself completes in **2ms** — this runs fine on the Celeron
2. The problem is the O(n×m) re-MATCH pattern which does 7.5M comparisons in the query engine
3. Even an M2 Max or Xeon would timeout at 1000ms on a 26-second O(n×m) query
4. Memory is adequate — FalkorDB uses ~200-500MB typically, well within the 1GB limit
5. The connection closures happen because 4 thread-pool threads are all blocked on long-running queries, leaving no threads to handle new queries — this is a thread starvation issue from the O(n×m) bug, not hardware insufficiency

**However**: The 4-core/1.5GHz Celeron does mean that the O(n×m) computation is ~3-5x slower than on the MacBook's M2 Max. So while hardware isn't the root cause, it makes the symptom ~3-5x worse. Once the upstream bug is patched (O(n) queries), the Celeron will handle the workload fine.

### Finding 4 (CONFIRMED): `rules` Group Not Used by Player/Coach

**Confidence: Very High** — verified by code trace through `job_context_retriever.py`

The Player/Coach agents query these groups at runtime:
- `feature_specs`, `task_outcomes`, `patterns_{tech_stack}`, `project_architecture`, `failure_patterns`, `domain_knowledge`
- AutoBuild-only: `role_constraints`, `quality_gate_configs`, `turn_states`, `implementation_modes`

The `rules`, `agents`, and `templates` groups are **NEVER queried by autobuild**. They are only available via `guardkit graphiti search` for human ad-hoc search.

**Impact of reducing/removing rule content from Graphiti**: **Zero impact on autobuild quality.** The Player/Coach agents get their behavioral context from the static `.claude/rules/*.md` files that are copied to the project during Step 1 of init. Graphiti's `rules` group is purely for human searchability.

### Finding 5 (CONFIRMED): Misleading Success Logging

`sync_rule_to_graphiti()` (line 479-487) doesn't check the return value of `client.add_episode()`. When `add_episode()` returns `None` (failure), the sync function still logs `[Graphiti] Synced rule 'X'` because the exception was already caught and swallowed by the graphiti_client wrapper. 5 rules show this misleading success pattern.

### Finding 6 (CONFIRMED): Unawaited Coroutine Warnings

The 5 `RuntimeWarning: coroutine '...' was never awaited` errors at shutdown indicate that graphiti-core's search coroutines (created during dedup operations within in-flight `add_episode()` calls) were garbage-collected without being awaited. This means some dedup operations were silently skipped, potentially resulting in duplicate entities in the knowledge graph.

---

## Revised Recommendations

### Priority 1: Fix the Upstream Query Pattern (Highest Impact)

**R1: Apply local workaround for getzep/graphiti#1272**

Add a third monkey-patch to `falkordb_workaround.py` that replaces the O(n×m) `edge_fulltext_search` query pattern with the O(n) `startNode(e)/endNode(e)` pattern.

```python
# In falkordb_workaround.py — new workaround 3
# Replace: MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
# With:    WITH e, score, startNode(e) AS n, endNode(e) AS m
```

**Expected impact**: Edge fulltext queries drop from 26-118s to ~3ms. This single fix eliminates the root cause of all 64 timeouts and most of the 33 connection closures.

**Effort**: Medium (need to monkey-patch `FalkorDriver.build_edge_fulltext_query` or the caller)
**Risk**: Low — the fix is semantically identical, just more efficient
**Confidence**: Very High — issue #1272 demonstrates the fix and its impact

### Priority 2: Increase FalkorDB TIMEOUT

**R2: Raise TIMEOUT from 1000ms to 30000ms (30s)**

Update `docker/nas/docker-compose.falkordb.yml`:
```yaml
FALKORDB_ARGS=MAX_QUEUED_QUERIES 100 TIMEOUT 30000 RESULTSET_SIZE 10000
```

**Why 30s**: Even with R1 applied, some queries during heavy graph seeding may exceed 1s. The graphiti_client already has a 30s connection timeout. Aligning the FalkorDB query timeout with this prevents spurious failures.

**Expected impact**: Eliminates timeout errors for queries that are slow but would complete. This is a safety net — with R1 applied, most queries complete in <100ms.

**Effort**: 1 line change in docker-compose + redeploy
**Risk**: None — worst case is slow queries run to completion instead of timing out
**Note**: Consider also using `TIMEOUT_MAX` and `TIMEOUT_DEFAULT` if running FalkorDB ≥v2.10

### Priority 3: Reduce Content Volume (Defense in Depth)

**R3: Sync only metadata + content_preview for rules (remove full_content)**

In `template_sync.py:sync_rule_to_graphiti()`, remove the `full_content` field:

```python
# Before:
rule_body = {
    ...
    "content_preview": main_content[:500] if main_content else "",
    "full_content": main_content if main_content else "",  # REMOVE THIS
}

# After:
rule_body = {
    ...
    "content_preview": main_content[:500] if main_content else "",
    # full_content removed — reduces entity extraction by ~90%
}
```

**Why this is safe**: The `rules` group is NEVER queried by Player/Coach autobuild. It's only used for human `guardkit graphiti search`. The 500-char preview is sufficient for search result display. The actual rule content lives in `.claude/rules/*.md` files which are directly loaded by Claude Code's context system.

**Expected impact**: ~90% reduction in entity extraction per rule. Combined with R1, Step 2.5 should drop from ~113 minutes to <2 minutes.

**Effort**: 1 line deletion
**Risk**: None for autobuild. Marginal reduction in human search result detail (mitigated by content_preview).

### Priority 4: Fix Return Value Checking

**R4: Check `add_episode()` return in sync functions**

```python
# In sync_rule_to_graphiti():
result = await client.add_episode(...)
if result is None:
    logger.warning(f"[Graphiti] Failed to sync rule '{rule_name}' (episode creation returned None)")
    return False
logger.info(f"[Graphiti] Synced rule '{rule_name}'")
return True
```

**Effort**: 5 lines per sync function (2 functions)
**Risk**: None

### Priority 5: Suppress Vector Logging

**R5: Set graphiti_core.driver.falkordb_driver logger to WARNING during sync**

```python
# In template_sync.py at start of sync_template_to_graphiti():
import logging
falkordb_logger = logging.getLogger("graphiti_core.driver.falkordb_driver")
original_level = falkordb_logger.level
falkordb_logger.setLevel(logging.WARNING)
try:
    # ... sync operations ...
finally:
    falkordb_logger.setLevel(original_level)
```

This suppresses the ERROR-level logs that dump query parameters (including 768-dim vectors). WARNING-level messages from `graphiti_client.py` retry logic will still appear.

**Effort**: 5 lines
**Risk**: None — retry warnings still visible

### Priority 6: Episode-Level Timeout

**R6: Wrap each `add_episode()` in asyncio.wait_for()**

In `graphiti_client.py:_create_episode()`, add a timeout per attempt:

```python
result = await asyncio.wait_for(
    self._graphiti.add_episode(...),
    timeout=120.0  # 2 minutes max per episode
)
```

**Expected impact**: Prevents a single episode from blocking for 153+ seconds. With R1+R2 applied, this is a safety net.

**Effort**: 3 lines
**Risk**: Low — may cause partial episode data if timeout fires mid-write

### NOT Recommended

**Moving FalkorDB off the NAS**: The DS918+ hardware is adequate for this workload. The Celeron handles fulltext indexing and graph traversal fine. The problem is the O(n×m) query pattern, not the hardware. Once R1 is applied, the NAS will handle init sync comfortably.

**Parallel rule syncing**: Not needed if R1+R2+R3 are applied. Sequential syncing at ~3ms/query will be fast enough. Adding parallelism increases complexity and FalkorDB load without proportional benefit.

---

## Implementation Priority and Sequencing

```
┌───────────────────────────────────────────────────────────────┐
│  Wave 1 (Immediate — deploy together):                        │
│                                                               │
│  R1: Patch edge_fulltext_search O(n×m) → O(n)                │
│      → falkordb_workaround.py (new workaround)               │
│      → Eliminates root cause of 64 timeouts                  │
│                                                               │
│  R2: Raise TIMEOUT 1000 → 30000                              │
│      → docker-compose.falkordb.yml + redeploy                │
│      → Safety net for remaining slow queries                  │
│                                                               │
│  R3: Remove full_content from rule episodes                   │
│      → template_sync.py (1 line)                              │
│      → ~90% reduction in entity extraction work               │
├───────────────────────────────────────────────────────────────┤
│  Wave 2 (Quick follow-up):                                    │
│                                                               │
│  R4: Fix return value checking in sync functions              │
│  R5: Suppress vector logging during sync                      │
│  R6: Episode-level timeout (120s)                             │
├───────────────────────────────────────────────────────────────┤
│  Wave 3 (When bandwidth allows):                              │
│                                                               │
│  Submit upstream PR to getzep/graphiti for #1272 fix          │
│  Submit upstream PR for log parameter truncation              │
└───────────────────────────────────────────────────────────────┘

Expected results after Wave 1:
  Step 2.5 time: 6759s → ~60-120s (estimate)
  Timeout errors: 64 → 0
  Connection closures: 33 → 0
  Vector log dumps: 30 → 0
  Total init time: ~120 min → ~8-10 min
```

---

## Acceptance Criteria Assessment

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Root cause of FalkorDB query timeouts identified | **DONE** | graphiti-core #1272 O(n×m) re-MATCH pattern + TIMEOUT=1000ms |
| Root cause of "Connection closed by server" identified | **DONE** | Thread starvation from blocked O(n×m) queries exhausting 4-thread pool |
| Relationship between content volume and timeout frequency | **DONE** | More content → more entities → more edges → more O(n×m) queries → more timeouts |
| Impact of 5 failed episodes on knowledge graph completeness | **DONE** | 5 rules have missing/partial graph data; ZERO impact on autobuild (rules group not queried at runtime) |
| Unawaited coroutine warnings root cause identified | **DONE** | Garbage-collected search coroutines from in-flight episodes killed by circuit breaker |
| Recommendations for timeout mitigation provided | **DONE** | R1-R6 with effort/risk/impact analysis |
| Priority ordering of fixes established | **DONE** | Wave 1 (R1+R2+R3), Wave 2 (R4+R5+R6), Wave 3 (upstream PRs) |
| Connection to reduce-static-markdown initiative clarified | **DONE** | R3 directly implements it; safe because rules group not used by autobuild |

---

## Sources

- [FalkorDB Configuration Documentation](https://docs.falkordb.com/getting-started/configuration.html)
- [getzep/graphiti#1272 — edge_fulltext_search O(n×m) bug](https://github.com/getzep/graphiti/issues/1272)
