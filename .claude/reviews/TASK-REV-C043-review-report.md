# Review Report: TASK-REV-C043 (Revised v4 — Strategic Alignment)

## The Real Goal

Context reduction for the Player/Coach on local GB10 hardware has **two complementary tracks**:

1. **FEAT-CR01** (static trimming): Reduce ~18K tokens of always-loaded context through path-gating, trimming, and deduplication. Target: ~13,400 token reduction. **Does NOT depend on Graphiti.** Status: backlog, Waves 1-5 ready.

2. **Graphiti seeding** (this review): Seed template metadata into Graphiti so the AutoBuildContextLoader can provide semantic search, role constraints, turn states, and cross-session memory. **Does NOT replace static rules** — Graphiti extracts facts, not verbatim content (proven by fidelity assessment Feb 5).

| Content | Size | Context reduction approach |
|---------|------|--------------------------|
| 12 rule files | ~44K chars (~11K tokens) | **FEAT-CR01**: trim + path-gate (NOT Graphiti) |
| CLAUDE.md files | ~20K chars (~5K tokens) | **FEAT-CR01**: trim |
| Agent files | ~10K chars (~2.4K tokens) | Already on-demand (subagent invocation) |
| Rule/agent metadata | N/A | **Graphiti**: semantic search for AutoBuild |
| Role constraints, turn states | N/A | **Graphiti** + FEAT-GE: cross-session memory |

`guardkit init` seeds content into Graphiti (track 2). This review assesses whether init seeding works — it doesn't, and the problems go deeper than the TASK-FIX-b7a7 changes.

## Executive Summary

| Change | Verdict | Action |
|--------|---------|--------|
| 1. Tiered timeouts (5-tier) | Partially working — correctly applied but insufficient headroom | **KEEP** |
| 2. `upsert_episode` migration | Neutral — useful infrastructure for seed-once pattern | **KEEP** |
| 3. Parallel sync (`_sync_items_parallel`) | **HARMFUL** — circuit breaker cascade, 0/12 rules | **REVERT** |
| 4. Full rule content (`main_content`) | **HARMFUL** — slower episodes, more edges | **REVERT to content_preview** |
| 5. Rate-limit-aware retry | Not exercised — neutral | **KEEP** |
| **ARCHITECTURAL** | System content re-seeded every init; should be seed-once | **REDESIGN** |

**Bottom line**: The init seeding needs to be redesigned around seed-once for system/template content, with project init only seeding project-specific content. Short-term: revert parallel sync and rule content to restore reliability.

---

## Review Details

- **Mode**: Technical Assessment (verification review, REVISED with code tracing)
- **Depth**: Comprehensive
- **Task**: TASK-REV-C043
- **Parent Review**: TASK-REV-BAC1
- **Feature**: FEAT-init-graphiti-remaining-fixes

---

## CORRECTED Step 2 Analysis (Project Knowledge Seeding)

My initial report had a critical error: I incorrectly stated coach timed out at 120.0s. The actual init_project_7 log shows:

| Episode | init_project_6 | init_project_7 | Change | Status |
|---------|---------------|----------------|--------|--------|
| 1. project_purpose | 189.6s OK | 241.2s OK | +51.6s (+27%) | Slower (graph growth) |
| 2. project_scope | 76.9s OK | 96.5s OK | +19.6s (+25%) | Slower (graph growth) |
| 3. project_architecture | 240.0s TIMEOUT (240s) | **300.4s TIMEOUT (300s)** | +60.4s | STILL FAILS (300s headroom insufficient) |
| 4. role_constraint_player | 26.8s OK | 28.2s OK | +1.4s | Stable |
| 5. role_constraint_coach | **120.0s TIMEOUT** | **26.6s OK** | **-93.4s** | **Recovered** (LLM variance) |
| 6. implementation_mode_1 | 65.8s OK | 75.1s OK | +9.3s | Stable |
| 7. implementation_mode_2 | 62.5s OK | 83.6s OK | +21.1s | Stable |
| 8. implementation_mode_3 | 59.2s OK | 30.8s OK | -28.4s | Improved |
| **Step 2 Total** | **840.9s** | **882.2s** | **+41.3s (+4.9%)** | Slightly slower |
| **Step 2 Successes** | **6/8** | **7/8** | **+1** | **IMPROVED** |

### Why coach completed at 26.6s (NOT an upsert skip)

**Important correction**: `seed_role_constraints.py` still uses `add_episode()`, NOT `upsert_episode()`. The full graphiti-core pipeline ran — confirmed by the `graphiti_core.graphiti:Completed add_episode in 26571ms` log line.

Additionally, `guardkit graphiti clear --project-only` only clears groups matching `{project}__*`. The `role_constraints` group is a **system group** (not prefixed), so it is **NOT cleared** between runs. This means coach data from prior runs persists, but the 26.6s completion time is the full `add_episode` pipeline, not a skip.

The 26.6s is likely **LLM variance** or a favourable graph state:
- init_project_5: 116.2s OK
- init_project_6: 120.0s TIMEOUT
- init_project_7: 26.6s OK

The extreme variance (116s → 120s → 26.6s) suggests graphiti-core's edge resolution is sensitive to graph state and LLM response times. The coach could easily timeout again on the next run.

**Note on `--project-only` clear scope**:
- **Cleared**: `vllm-profiling__project_overview`, `vllm-profiling__project_architecture`, etc.
- **NOT cleared**: `role_constraints`, `implementation_modes`, `templates`, `agents`, `rules` (all system groups)

This means system group data accumulates across runs unless a full clear or `--system-only` clear is performed.

### Why project_architecture still fails

At 300.4s it overshot the 300s timeout by just 0.4s — the timeout **is** being applied correctly, but the graph has grown enough that even 300s isn't enough.

---

## Step 2.5 Analysis (Template Sync) — ROOT CAUSE OF REGRESSION

### Observed Sequence

```
Line 92:  template_fastapi-python          → TIMEOUT at 120s  (failure #1)
Line 94:  agent_fastapi-specialist         → OK at 72.0s      (resets counter to 0)
Line 96:  agent_fastapi-database-specialist → TIMEOUT at 150s  (failure #1)  ← parallel
Line 98:  agent_fastapi-testing-specialist  → TIMEOUT at 150s  (failure #2)  ← parallel
Line 100: rule_migrations_chunk1           → TIMEOUT at 180s  (failure #3)  ← CIRCUIT BREAKER TRIPS
Line 101: "Graphiti disabled after 3 consecutive failures"
Lines 102-110: All remaining rules → immediate fail (circuit breaker active)
Line 111: rule_code-style_chunk1           → TIMEOUT at 180s  (failure #4, circuit half-open reset)
Line 112: "Graphiti disabled after 4 consecutive failures"
Lines 113-114: More rules → immediate fail
Line 115: rule_testing_chunk1              → TIMEOUT at 180s  (failure #5, another half-open reset)
Line 116: "Graphiti disabled after 5 consecutive failures"
Line 117: Remaining rules → immediate fail
```

### Two Independent Problems Compound

**Problem A: Parallel sync + circuit breaker interaction**

With sequential sync (init_project_6), successes between failures reset the counter:
```
code-style (132s OK) → counter=0
testing (73s OK)     → counter=0
migrations (106s OK) → counter=0
crud (180s TIMEOUT)  → counter=1
models (58s OK)      → counter=0    ← success resets!
...
```

With parallel sync (init_project_7), 3 agents run concurrently. The semaphore limits concurrency to 3, but if 2 out of 3 timeout, both `_record_failure()` calls fire close together. Then rules also run 3 at a time — one timeout pushes the count to 3, tripping the breaker.

**This alone would justify reverting to sequential sync.** The parallelism saves wall-clock time but destroys reliability.

**Problem B: Rules now send full content instead of content_preview**

The diff shows a critical change in `sync_rule_to_graphiti()`:

```python
# BEFORE (init_project_6 — committed code):
rule_body = {
    "content_preview": body_text[:500] if body_text else "",  # 500 chars max
}

# AFTER (init_project_7 — working tree):
rule_body = {
    "main_content": chunk.content,  # FULL text, potentially 2000+ chars
}
```

Even though episode splitting limits each chunk to ~2000 chars, sending `main_content` with the full chunk text instead of a 500-char preview means graphiti-core extracts **far more entities and edges** per episode. This is why rules that succeeded at 120s in init_5 (with `content_preview`) worked at 60-130s in init_6 (still `content_preview`) but fail at 180s in init_7 (with `main_content`).

The `content_preview` approach was deliberate — the full content is already available in `.claude/rules/*.md` files. The Graphiti episode only needs enough text for semantic search and entity extraction. Sending the full content forces graphiti-core to process many more edges, making every rule slower.

### Step 2.5 Comparison

| Item | init_6 (sequential, content_preview) | init_7 (parallel, main_content) | Change |
|------|--------------------------------------|----------------------------------|--------|
| Template | 98.3s OK | **120.0s TIMEOUT** | +21.7s → timeout |
| Agents synced | 2/3 | 1/3 | -1 (db-specialist hit 150s) |
| Rules synced | **10/12** | **0/12** | **-10 (cascade + slower content)** |
| Total synced | 13 | 2 | **-85%** |
| Duration | 1,523.3s | 451.6s | -71% (fast fail, not improvement) |

---

## Change-by-Change Revert Analysis

### Change 1: Tiered Timeouts — KEEP

```python
# _create_episode() in graphiti_client.py
if group_id.endswith("project_overview"):
    episode_timeout = 300.0
elif group_id == "rules":
    episode_timeout = 180.0
elif group_id == "role_constraints":
    episode_timeout = 150.0
elif group_id == "agents":
    episode_timeout = 150.0
else:
    episode_timeout = 120.0
```

**Evidence it's working**:
- Agents show "timed out after 150s" → tier applied correctly
- project_architecture shows "timed out after 300s" → tier applied correctly
- Rules show "timed out after 180s" → tier applied correctly

**Not enough headroom**, but the tiering logic itself is correct. The 300.4s miss is a graph growth issue, not a code bug. **Keep this**.

### Change 2: upsert_episode migration (project_seeding.py) — KEEP

Changed `add_episode()` → `upsert_episode()` for project_overview and implementation_modes. **Note**: `seed_role_constraints.py` was NOT migrated — it still uses `add_episode()`.

**Behaviour with `--project-only` clear between runs**:
- Project groups (project_overview): cleared → upsert finds nothing → full `add_episode` runs → no skip benefit
- System groups (implementation_modes): NOT cleared → upsert MAY find existing episode and skip if hash matches

**Evidence**:
- Coach (26.6s): NOT an upsert skip — uses `add_episode()` directly, LLM variance
- Player (28.2s): NOT an upsert skip — uses `add_episode()` directly
- Implementation modes: 75.1s, 83.6s, 30.8s — mixed, would need to check for "Skipping unchanged" log messages

**Keep this** — the upsert infrastructure is correct and will provide skip-if-unchanged for system groups. Minimal overhead when it doesn't skip (one `episode_exists` search before the `add_episode`).

### Change 3: Parallel sync (`_sync_items_parallel`) — REVERT

```python
# template_sync.py — added _sync_items_parallel() using asyncio.Semaphore
a_count, a_warnings = await _sync_items_parallel(
    items=agent_files, sync_fn=sync_agent_to_graphiti, ...
)
r_count, r_warnings = await _sync_items_parallel(
    items=rule_files, sync_fn=sync_rule_to_graphiti, ...
)
```

**Evidence it's harmful**:
- Circuit breaker trips at 3 consecutive failures
- Parallel failures accumulate faster than sequential successes can reset
- 0/12 rules synced vs 10/12 in init_project_6

**Revert to sequential**: Restore the original for-loop pattern. This loses wall-clock optimization but restores reliability. Parallel sync can be re-attempted later with a circuit-breaker-aware implementation (e.g., per-batch reset, or passing `ignore_circuit_breaker=True` during seeding).

### Change 4: Rule content — PARTIAL REVERT

The rule sync changed from:
```python
"content_preview": main_content[:500] if main_content else "",
```
to:
```python
"main_content": chunk.content,  # full chunk text
```

**Evidence it's harmful**: Rules that completed in 60-130s now timeout at 180s. The full content generates more entities/edges → slower Phase 4 resolution.

**Revert the content field** back to `content_preview: main_content[:500]`. **Keep the episode splitting infrastructure** — it's well-designed and will be useful when TASK-FIX-8f75 is properly implemented with appropriate timeout budgets.

### Change 5: Rate-limit-aware retry — KEEP

```python
if "429" in error_str or "Rate limit" in error_str or "rate_limit" in error_str:
    delay = 2 ** (attempt + 2)  # 4s, 8s for rate limits
else:
    delay = 2 ** (attempt + 1)  # 2s, 4s for other transient errors
```

**Neutral** — not exercised in init_project_7. No harm keeping it.

### Change 6: `max_concurrent_episodes` config — KEEP (but unused after revert)

Added `max_concurrent_episodes: int = 3` to `GraphitiConfig` and `GraphitiSettings`. Clean addition with validation. After reverting parallel sync, this config isn't actively used but remains available for future parallel implementations.

### Change 7: `_is_transient_error` expansion — KEEP

Added rate-limit error patterns to the transient error classifier. Correct and harmless.

---

## Specific Revert Instructions

### Revert 1: template_sync.py — Sequential sync

Revert the `_sync_items_parallel()` usage back to sequential for-loops:

```python
# REVERT agents from parallel back to sequential:
for agents_dir in agent_dirs:
    for agent_file in agents_dir.glob("*.md"):
        if "-ext.md" in agent_file.name:
            continue
        try:
            result = await sync_agent_to_graphiti(agent_file, template_id, client=client)
            if result:
                agent_count += 1
        except Exception as e:
            logger.warning(f"[Graphiti] Failed to sync agent {agent_file.name}: {e}")
            warning_count += 1

# REVERT rules from parallel back to sequential:
if rules_dir.exists() and rules_dir.is_dir():
    for rule_file in rules_dir.rglob("*.md"):
        try:
            result = await sync_rule_to_graphiti(rule_file, template_id, client=client)
            if result:
                rule_count += 1
        except Exception as e:
            logger.warning(f"[Graphiti] Failed to sync rule {rule_file.name}: {e}")
            warning_count += 1
```

The `_sync_items_parallel()` function can remain in the file (it's well-implemented) but should not be called until the circuit breaker is made parallel-aware.

### Revert 2: sync_rule_to_graphiti — content_preview

Change `main_content` back to `content_preview` with 500-char limit:

```python
rule_body = {
    "entity_type": "rule",
    "id": chunk_rule_id,
    "name": rule_name,
    "template_id": template_id,
    "path_patterns": path_patterns,
    "topics": topics[:10],
    "content_preview": chunk.content[:500] if chunk.content else "",  # NOT full content
    "chunk_index": chunk.chunk_index,
    "total_chunks": chunk.total_chunks,
}
```

---

## Projected Impact of Reverts

After reverting parallel sync + rule content, init_project_8 should look approximately like:

| Metric | init_6 (baseline) | init_7 (current) | Projected init_8 |
|--------|-------------------|-------------------|-------------------|
| Step 2 successes | 6/8 | 7/8 | **7/8** (LLM variance; coach may regress) |
| Rule sync | 10/12 | 0/12 | **8-10/12** (sequential + content_preview) |
| Agent sync | 2/3 | 1/3 | **2/3** (sequential, 150s timeout) |
| Template sync | 1/1 | 0/1 | **0-1/1** (120s may be tight) |
| Total items synced | ~17 | ~10 | **~17-19** |
| Total time | 2,364s | 1,334s | **~2,200-2,500s** |
| Circuit breaker | 0 | 2 | **0** |

The graph has grown slightly since init_project_6, so some items may be marginally slower — but sequential sync with content_preview should restore reliability.

---

## Cumulative Progress: init_project_3 → 7

| Metric | init_3 | init_4 | init_5 | init_6 | init_7 | Trend |
|--------|--------|--------|--------|--------|--------|-------|
| Total init time | ~7,160s | ~2,009s | ~2,183s | ~2,364s | ~1,334s | ↓ (misleading) |
| Query timeouts | 64 | 0 | 0 | 0 | 0 | Eliminated |
| Connection closures | 33 | 0 | 0 | 0 | 0 | Eliminated |
| Agent sync | ? | 1/3 | 3/3 | 2/3 | **1/3** | Oscillating ↓ |
| Rule sync | ? | 10/12 | 6/12 | 10/12 | **0/12** | **Cascade failure** |
| Project overview | No | No | 2/2 | 1/2 | 1/2 | Plateau |
| Role constraints | ? | ? | 2/2 | 1/2 | **2/2** | **Recovered (LLM variance)** |
| Total items synced | ? | ~15 | ~18 | ~17 | **~10** | **Regression** |

---

---

## ARCHITECTURAL ANALYSIS: What Init Seeding Is Actually For

### Correction: Graphiti Cannot Replace Static Rules

My v3 report proposed "selective retrieval replaces static rules". **This is wrong.** The Graphiti fidelity assessment (Feb 5, `docs/reviews/graphiti_enhancement/graphiti_code_retrieval_fidelity.md`) proved:

> Graphiti is a knowledge graph that extracts semantic facts, not a document store that preserves verbatim content. Code examples cannot be reliably retrieved in copy-paste usable form.

FEAT-CR01 already pivoted away from Graphiti-dependent context reduction (TASK-REV-CROPT). The approach is now **Graphiti-independent**: path-gating, trimming, deduplication. That work is in `tasks/backlog/context-reduction/` with ~13,400 token reduction achievable through static file trimming alone.

### So What IS Init Seeding For?

Seeding template content into Graphiti serves the **AutoBuild context loader** (`AutoBuildContextLoader`), not static rule replacement. It provides:

1. **Semantic search for "which rule applies?"** — The Player/Coach can query Graphiti to understand which rules exist and what they cover, then load the relevant static file on-demand (Option C from TASK-REV-CROPT: hybrid approach)
2. **Role constraint enforcement** — Player/Coach boundaries retrieved from Graphiti and injected into prompts
3. **Cross-session memory** — Turn states, failed approaches, quality gate configs (FEAT-GE enhancements)
4. **Template capability discovery** — "Does this template support X?" queries

The content_preview (500 chars) is sufficient for these semantic use cases. Full rule text is NOT needed in Graphiti — it stays in the static `.claude/rules/` files.

### What's Broken and What Needs to Happen

| What | Status | Impact |
|------|--------|--------|
| 0/12 rules in Graphiti | **Broken** (parallel sync + main_content) | AutoBuildContextLoader can't find rule metadata |
| System content re-seeded every init | **Wrong** (adds duplicates, graph bloat) | Init takes 35 min, graph grows, episodes slow |
| FEAT-CR01 static trimming | **Backlog** (Waves 1-5 ready) | ~13,400 token reduction not yet implemented |
| FEAT-GE Graphiti enhancements | **Backlog** (7 tasks) | Turn states, North Star, failed approaches not yet seeded |

### What `guardkit init` Should Do

| Step | Current | Target |
|------|---------|--------|
| Step 1 | Copy template files | Same (correct) |
| Step 2 | Seed project overview + role constraints + impl modes | **Project overview ONLY** (2 episodes, ~5-8 min) |
| Step 2.5 | Seed template/agents/rules (18 episodes, ~25 min) | **Skip** — system content seeded once via separate command |

System/template content (role constraints, impl modes, template manifest, agents, rules) should be seeded **once** via `guardkit graphiti seed-system` — not on every project init. The upsert infrastructure already supports this pattern.

---

## Updated Recommendations

### Short-term: Unblock Init (do now)

| # | Action | Effort |
|---|--------|--------|
| 1 | Revert parallel sync → sequential in `template_sync.py` | 2/10 |
| 2 | Revert rule `main_content` → `content_preview` in `sync_rule_to_graphiti()` | 1/10 |

These restore ~10/12 rule sync and unblock the Graphiti seeding pipeline.

### Medium-term: Fix Architecture (next)

| # | Action | Effort | Aligns with |
|---|--------|--------|-------------|
| 3 | Create `guardkit graphiti seed-system` command | 4/10 | New |
| 4 | Remove system seeding from `guardkit init` (Step 2.5 → no-op) | 3/10 | New |

This reduces init from ~35 min to ~5-8 min and eliminates graph bloat.

### Strategic: Context Reduction (then)

| # | Action | Effort | Aligns with |
|---|--------|--------|-------------|
| 5 | Execute FEAT-CR01 Waves 1-5 (static trimming + path-gating) | Per task | FEAT-CR01 (backlog) |
| 6 | Execute FEAT-GE (Graphiti enhancements for AutoBuild) | Per task | FEAT-GE (backlog) |

FEAT-CR01 delivers ~13,400 token reduction through static file work. FEAT-GE makes Graphiti actually useful for AutoBuild (turn states, North Star, failed approaches).

### Keep (already working)

Tiered timeouts, upsert migration, rate-limit retry, episode splitting infrastructure.

### Deprioritise

TASK-FIX-8f75 (episode splitting with proper testing), TASK-FIX-77b2 (parallel sync — blocked until circuit breaker is parallel-aware).

---

## Production Readiness

**NOT production-ready as-is** (0/12 rules synced).

**After reverts #1 + #2**: Init restores ~10/12 rules. Semantic metadata available for AutoBuildContextLoader. Production-viable.

**After #3-4**: Init fast (~5-8 min) and reliable. System content seeded once, correctly.

**After #5-6**: Context reduction achieved through FEAT-CR01 static trimming (~13,400 tokens). Graphiti enhanced for AutoBuild cross-session memory via FEAT-GE.

---

## Decision: [I]mplement

**Chosen**: [I]mplement — Create implementation tasks for all recommendations.

**Feature created**: FEAT-ISF (Init Seeding Fixes)
**Location**: `tasks/backlog/init-seeding-fixes/`

### Implementation Tasks Created

| ID | Task | Wave | Status |
|----|------|------|--------|
| TASK-ISF-001 | Revert parallel sync to sequential | 1 | Pending |
| TASK-ISF-002 | Revert rule main_content to content_preview | 1 | Pending |
| TASK-ISF-003 | Fix -ext.md file copying in init | 2 | Pending |
| TASK-ISF-004 | Seed Graphiti fidelity knowledge | 2 | Pending |
| TASK-ISF-005 | Create guardkit graphiti seed-system command | 3 | Pending |
| TASK-ISF-006 | Slim init to project-only seeding | 3 | Pending |

**Additional user requests included**:
- TASK-ISF-004: Seed the Feb 5 finding "Graphiti is a knowledge graph that extracts semantic facts, not a document store that preserves verbatim content"
- TASK-ISF-003: Verify and fix that -ext.md files should be copied during init
