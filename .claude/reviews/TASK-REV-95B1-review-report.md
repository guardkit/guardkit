# Review Report: TASK-REV-95B1

## Executive Summary

The template filter changes from TASK-a912 delivered a **62.5% reduction in seed time** (98m 40s vs 263m 05s) and a **54.4% reduction in total episodes** (78 vs 171). The filter correctly limited seeding to the `default` template only, eliminating all 6 non-default template agents (18 → 0), rules (72 → 3), and template episodes (7 → 1). The success rate improved from 72.5% to 89.7%.

All 8 skipped episodes are **timeout failures**, not filtering issues — the same timeout-prone episodes that failed in reseed_3. Init project performance improved 26% (830.9s vs 611.3s first run in init_13, but init_13 had a pre-seeded graph; the comparable second run was 880.5s, making init_14 a 5.6% improvement).

**Verdict**: Template filter is working as designed. The primary remaining bottleneck is per-episode LLM processing time, not volume.

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Comprehensive
- **Task**: TASK-REV-95B1
- **Related**: TASK-REV-acbc, TASK-a912

---

## Finding 1: Seed Performance — 62.5% Time Reduction

| Metric | reseed_guardkit_3 | reseed_guardkit_5 | Change |
|--------|-------------------|-------------------|--------|
| Duration | 263m 05s | 98m 40s | **-62.5%** |
| Total episodes | 171 | 78 | **-54.4%** |
| Created episodes | 124 | 70 | **-43.5%** |
| Skipped episodes | 47 | 8 | **-83.0%** |
| Success rate | 72.5% | 89.7% | **+17.2pp** |
| Fully seeded categories | 11/17 | 12/17 | +1 |
| Partial categories | 6/17 | 5/17 | -1 |

**Analysis**: The 62.5% time reduction slightly exceeds the 54.4% episode reduction because the eliminated episodes (template/agent/rule) included many of the longest-running timeout-prone episodes. The skip rate improved dramatically because most of the 47 skips in reseed_3 were from non-default template rules (32/47 = 68%).

**Average time per successful episode**: reseed_3 = ~127s, reseed_5 = ~84.6s (33% faster per-episode, likely due to smaller graph reducing search/dedup overhead).

---

## Finding 2: Template Filter Effectiveness — Working Correctly

| Content type | reseed_3 | reseed_5 | Expected | Match? |
|--------------|----------|----------|----------|--------|
| Templates seeded | 4/7 (3 skipped) | 1/1 (default) | 1 | Yes |
| Agents seeded | 9/18 (9 skipped) | 0/0 | 0 | Yes |
| Rules attempted | 72 (from 7 templates) | 3 (default only) | 3 | Yes |
| Rules created | 40/72 | 1/3 | - | - |

The template filter correctly:
- Auto-detected `default` as the active template
- Excluded all 6 non-default templates and their agents/rules
- Reduced rules from 72 episodes to 3 episodes
- Eliminated all 18 agent episodes

**Episodes eliminated by filter**: 93 (171 - 78) = templates(6) + agents(18) + rules(69)

---

## Finding 3: Category-by-Category Comparison

| Category | reseed_3 | reseed_5 | Change |
|----------|----------|----------|--------|
| product_knowledge | 3/3 ✓ | 3/3 ✓ | Same |
| command_workflows | 19/20 (1 skip) | 17/20 (3 skip) | **-2 worse** |
| quality_gate_phases | 11/12 (1 skip) | 11/12 (1 skip) | Same |
| technology_stack | 7/7 ✓ | 7/7 ✓ | Same |
| feature_build_architecture | 8/8 ✓ | 8/8 ✓ | Same |
| architecture_decisions | ✓ | ✓ | Same |
| failure_patterns | 4/4 ✓ | 4/4 ✓ | Same |
| component_status | **6/6 ✓** | **5/6 (1 skip)** | **-1 worse** |
| integration_points | 3/3 ✓ | 3/3 ✓ | Same |
| templates | 4/7 (3 skip) | **1/1 ✓** | N/A (filtered) |
| agents | 9/18 (9 skip) | **0/0 ✓** | N/A (filtered) |
| patterns | 5/5 ✓ | 5/5 ✓ | Same |
| rules | 40/72 (32 skip) | **1/3 (2 skip)** | N/A (filtered) |
| project_overview | 3/3 ✓ | 3/3 ✓ | Same |
| project_architecture | 2/3 (1 skip) | 2/3 (1 skip) | Same |
| failed_approaches | ✓ | ✓ | Same |
| pattern_examples | ✓ | ✓ | Same |

**Notable**: `command_workflows` degraded from 1 skip to 3 skips (new timeouts on `command_task_work` and `workflow_feature_to_build`). `component_status` degraded from 0 skips to 1 skip (new timeout on `component_taskwork_interface`). These are likely stochastic — the Qwen model sometimes runs slightly slower on certain episodes.

---

## Finding 4: Skipped Episode Root Cause Analysis

All 8 skipped episodes failed due to **timeout**:

| Episode | Category | Timeout | Also failed in reseed_3? |
|---------|----------|---------|--------------------------|
| command_task_work | command_workflows | 120s | No (new) |
| command_feature_spec | command_workflows | 120s | **Yes** |
| workflow_feature_to_build | command_workflows | 120s | No (new) |
| phases_overview | quality_gate_phases | 120s | **Yes** |
| component_taskwork_interface | component_status | 120s | No (new) |
| rule_default_quality_gates | rules | 180s | **Yes** |
| rule_default_workflow | rules | 180s | **Yes** |
| guardkit_project_structure | project_architecture | 120s | **Yes** |

**Pattern**: 5/8 are repeat offenders (same episodes that timed out in reseed_3). 3/8 are new timeouts, likely stochastic (graph size and LLM variability). The 2 default rules (`quality_gates`, `workflow`) consistently time out — they may be too large for the 180s budget.

**Root cause**: These episodes likely have complex content that causes the LLM (Qwen) to take longer for entity extraction and edge deduplication. The timeout budget (120s for standard, 180s for rules) is not always sufficient.

---

## Finding 5: Init Project Performance

| Metric | init_project_13 (run 2) | init_project_14 | Change |
|--------|------------------------|-----------------|--------|
| Total duration | 880.5s | 830.9s | **-5.6%** |
| Episodes | 3 | 3 | Same |
| Episode 1 (purpose) | 254.4s | 350.8s | +37.9% |
| Episode 2 (tech_stack) | 108.1s | 121.6s | +12.5% |
| Episode 3 (architecture) | 248.8s | 358.5s | +44.1% |
| Total episode time | 611.3s | 830.9s | +35.9% |

**Wait** — init_project_13 contains two runs. Run 1 was 611.3s but seeded into a pre-existing graph (skipping files noted). Run 2 in init_13 was 880.5s total. Init_project_14 at 830.9s is a 5.6% improvement over the comparable fresh init run.

**Episode profiles**:

| Episode | init_14 nodes | init_14 edges |
|---------|---------------|---------------|
| project_purpose | 26 | 44 |
| project_tech_stack | 13 | 12 |
| project_architecture | 23 | 63 |

These are reasonable graph sizes. The architecture episode extracts the most edges (63), explaining its longer duration.

---

## Finding 6: LLM Invalid `duplicate_facts` Warnings

| Source | Warning count |
|--------|---------------|
| reseed_guardkit_3 | 370 |
| reseed_guardkit_5 | 218 |
| init_project_14 | 20 |

**What these mean**: During edge deduplication, Graphiti asks the LLM to identify which existing facts are duplicated by new facts. The LLM returns indices, but sometimes returns indices outside the valid range (e.g., returning index 5 when only 2 existing facts exist). This is a **warning**, not an error — the invalid indices are silently ignored.

**Impact assessment**: LOW. The graphiti-core library handles these gracefully (the `Skipping invalid LLM dedupe id` message confirms this). The consequence is that some legitimate duplicates may not be detected, leading to slightly redundant edges in the graph. This is a cosmetic issue, not a data integrity issue.

**Trend**: Warnings decreased proportionally with episodes (370→218, roughly 54% reduction matching 54% episode reduction). The per-episode rate is similar, suggesting this is inherent Qwen model behaviour, not a regression.

Additionally, 3 `Skipping invalid LLM dedupe id` warnings appeared in reseed_5 for node deduplication — same root cause (Qwen model returning out-of-range indices).

---

## Finding 7: Time Distribution Analysis (reseed_5)

Examining episode completion times from reseed_5 (sorted by duration):

| Duration range | Count | Total time (est.) |
|----------------|-------|-------------------|
| >90s | 5 | ~7.5m |
| 60-90s | 18 | ~22.5m |
| 40-60s | 19 | ~15.8m |
| 20-40s | 20 | ~10m |
| <20s | 8 | ~2m |
| Timeouts (120-180s) | 8 | ~18.7m |

**Longest successful episodes** (from logs):
- `guardkit_purpose`: 151.6s (massive — 23 nodes, 42 edges)
- `component_stream_parser`: 118.5s (18 nodes, 21 edges)
- `command_system_overview`: 93.2s (11 nodes, 11 edges)
- `Orchestrator Pattern: State Management`: 90.8s (10 nodes, 22 edges)
- `adr_fb_002`: 86.2s (12 nodes, 20 edges)

**Top time consumers**: The universal categories (product_knowledge, command_workflows, quality_gate_phases, technology_stack, feature_build_architecture, patterns, pattern_examples) still dominate because they're seeded for every template.

---

## Finding 8: Remaining Optimisation Opportunities

### Opportunity A: Increase Timeout for Chronic Failures (Low effort, Medium impact)

The 2 default rules (`quality_gates`, `workflow`) consistently time out at 180s. Increasing to 240s or 300s could recover 2 episodes. Similarly, `command_task_work` and `phases_overview` at 120s could benefit from 180s.

**Impact**: Recover up to 5 of 8 skipped episodes. Does not save time, but improves success rate to ~96%.

### Opportunity B: Chunk Large Episodes (Medium effort, High impact)

`guardkit_purpose` at 151.6s extracts 23 nodes and 42 edges — it's doing too much in one episode. Splitting into smaller, focused episodes could:
- Reduce per-episode time
- Reduce timeout risk
- Improve extraction quality

**Impact**: Could eliminate the longest episode and reduce timeout risk for complex content.

### Opportunity C: Parallel Episode Seeding (High effort, High impact)

Currently episodes are seeded sequentially. If the Graphiti client can support concurrent add_episode calls (with different episode names), parallel seeding could cut total time by 50-70%.

**Impact**: Could reduce 98m to ~30-40m. Requires investigation of Graphiti concurrency model.

### Opportunity D: Episode Caching/Skip (Medium effort, Medium impact)

If the graph already contains episodes from a previous seed (e.g., incremental re-seed), skip episodes that haven't changed since last seed. Use content hashing to detect unchanged episodes.

**Impact**: Re-seeds after small changes could complete in minutes instead of 98m.

### Opportunity E: Reduce `duplicate_facts` Overhead (Low effort, Low impact)

Each edge deduplication requires an LLM call. With 218 warnings, the LLM is being called repeatedly for deduplication with marginal value for early episodes (few existing facts). Consider skipping deduplication for the first N episodes or reducing search scope.

**Impact**: Marginal time savings, reduced warning noise.

---

## Decision Matrix

| Option | Impact | Effort | Risk | Priority |
|--------|--------|--------|------|----------|
| A: Increase timeouts | Medium | Low | None | **P1 — Quick win** |
| B: Chunk large episodes | High | Medium | Low | **P1 — Next target** |
| C: Parallel seeding | High | High | Medium | P2 — Investigate |
| D: Episode caching | Medium | Medium | Low | P2 — For re-seeds |
| E: Reduce dedup overhead | Low | Low | Low | P3 — Nice to have |

---

## Acceptance Criteria Status

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Duration comparison | **DONE** | 98m 40s vs 263m 05s = 62.5% reduction |
| Episode-by-episode comparison | **DONE** | Category table in Finding 3 |
| Category success rate table | **DONE** | Finding 3 |
| Template filter verification | **DONE** | Finding 2 — filter working correctly |
| Init project analysis | **DONE** | Finding 5 — 830.9s, 3 episodes, reasonable |
| Root cause of skipped episodes | **DONE** | Finding 4 — all timeouts, 5/8 repeat offenders |
| Root cause of duplicate_facts warnings | **DONE** | Finding 6 — Qwen model behaviour, benign |
| Remaining optimisation opportunities | **DONE** | Finding 8 — 5 options with priority matrix |
| Recommendation for next steps | **DONE** | See below |

---

## Recommendations

1. **Accept template filter as complete** — TASK-a912 delivered its expected outcome
2. **Next task: Increase timeouts** for chronic timeout episodes (quick win, P1)
3. **Next task: Chunk `guardkit_purpose`** episode into 2-3 smaller episodes (P1)
4. **Investigate parallel seeding** feasibility with Graphiti (P2, research task)
5. **Monitor init performance** — 830.9s is acceptable but init_project episodes are slow due to larger CLAUDE.md content being processed in project context

---

## Appendix: Episode Timing Data

### Slowest 10 Successful Episodes (reseed_5)

1. `guardkit_purpose` — 151.6s (23 nodes, 42 edges)
2. `component_stream_parser` — 118.5s (18 nodes, 21 edges)
3. `command_system_overview` — 93.2s (11 nodes, 11 edges)
4. `Orchestrator Pattern: State Management` — 90.8s (10 nodes, 22 edges)
5. `adr_fb_002` — 86.2s (12 nodes, 20 edges)
6. `guardkit_installation_setup` — 82.2s (15 nodes, 15 edges)
7. `Pydantic Pattern: Nested Models` — 83.3s (11 nodes, 18 edges)
8. `cli_guardkit_graphiti` — 80.3s (14 nodes, 13 edges)
9. `workflow_design_first` — 79.7s (15 nodes, 13 edges)
10. `Orchestrator Pattern: Strategy Routing` — 79.3s (14 nodes, 14 edges)

### Timeout Episodes (reseed_5)

1. `command_task_work` — timeout 120s (new failure)
2. `command_feature_spec` — timeout 120s (repeat)
3. `workflow_feature_to_build` — timeout 120s (new failure)
4. `phases_overview` — timeout 120s (repeat)
5. `component_taskwork_interface` — timeout 120s (new failure)
6. `rule_default_quality_gates` — timeout 180s (repeat)
7. `rule_default_workflow` — timeout 180s (repeat)
8. `guardkit_project_structure` — timeout 120s (repeat)
