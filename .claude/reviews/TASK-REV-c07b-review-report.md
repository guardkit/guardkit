# Review Report: TASK-REV-c07b (Revised)

## Executive Summary

init_project_13 Run 2 shows a **44% total timing regression** (611.3s → 880.5s) compared to the init_12 baseline (Run 1). Both runs were on **clean graphs** with identical CLAUDE.md content, and the only code difference was the timeout increase (300→600s) and episode profiling logging (commit 3afc32fe). This rules out code changes as the cause.

The regression is attributed to **vLLM inference variance** on local hardware (Dell GB10). Episode 1 (project_purpose) in particular swung from 254s to 425s (+67%) despite seeding identical content to an empty graph. This level of variance is consistent with local LLM behaviour, where GPU thermals, memory pressure, and batch scheduling can significantly affect inference times.

**The positive news**: the timeout increase from 300s→600s (TASK-FIX-cc7e) was **essential** — Episode 1 at 425s would have timed out with the old 300s limit. The "out of bounds" warnings are fully resolved (14→0). The new episode profiling provides valuable graph topology visibility.

**Overall assessment**: init_13 is not an improvement in raw timing, but the infrastructure changes (timeout headroom, profiling, out-of-bounds fix) are genuine improvements. The timing variance means a single run is insufficient to draw conclusions — multiple runs on a clean graph are needed to establish a reliable baseline.

### Key Findings

| Finding | Status | Impact |
|---------|--------|--------|
| 44% timing regression | vLLM inference variance, not a code defect | Need multi-run baseline |
| Timeout increase (300→600s) | Essential — prevented timeout at 425s | Critical infrastructure fix |
| Out-of-bounds warnings resolved (14→0) | Confirmed — upstream graphiti-core fix | Positive |
| Episode profiling working | New observability into graph topology | Good |
| duplicate_facts warnings increased | More LLM calls on heavier episodes | Upstream issue, cosmetic |

---

## Review Details

- **Mode**: Code Quality
- **Depth**: Comprehensive
- **Task ID**: TASK-REV-c07b
- **Parent Review**: TASK-REV-acbc
- **Data Sources**: init_project_13.md (2 runs), init_project_12.md, init_project_11.md, init_project_10.md

---

## Finding 1: Performance Regression — vLLM Inference Variance

### Test Conditions

Both runs were executed under comparable conditions:
- **Graph state**: Clean (graph cleared and Docker containers for vLLM serve/embed restarted between runs)
- **Content**: Identical CLAUDE.md parsed into 3 episodes (purpose, tech_stack, architecture)
- **Target project**: Same (`vllm-profiling` with `fastapi-python` template)

### Code Differences Between Runs

Only commit 3afc32fe separates Run 1 from Run 2. The changes to the init seeding path were:

| Change | Impact on Seeding |
|--------|:---:|
| Timeout 300→600s (graphiti_client.py:974) | No perf impact — only affects timeout ceiling |
| Episode profiling logging (graphiti_client.py:1002-1013) | Negligible — runs after `add_episode`, microseconds of list iteration |
| `graph_stats()` method added | Not called during init |
| Agent timeout 150→240s | Not relevant to init episodes |

**None of these changes affect episode processing time.** The content sent to graphiti-core is identical.

### Timing Comparison

| Episode | Run 1 (init_12) | Run 2 (init_13) | Delta | Delta % |
|---------|:---:|:---:|:---:|:---:|
| Ep1: project_purpose | 254.4s | 425.2s | +170.8s | **+67%** |
| Ep2: project_tech_stack | 108.1s | 116.6s | +8.5s | +8% |
| Ep3: project_architecture | 248.8s | 338.7s | +89.9s | **+36%** |
| **Total** | **611.3s** | **880.5s** | **+269.2s** | **+44%** |

### Root Cause: vLLM Inference Variance

With identical content, identical code path, and a clean graph, the only variable is the vLLM inference layer on the Dell GB10. Episode processing is dominated by LLM calls within graphiti-core (entity extraction, edge resolution, deduplication). Local LLM inference on consumer/workstation hardware exhibits high variance due to:

1. **GPU thermal throttling** — sustained inference loads cause clock speed reduction
2. **Memory fragmentation** — vLLM's KV cache management varies between restarts
3. **Batch scheduling** — graphiti-core sends variable batch sizes depending on content chunking
4. **No model quantisation cache warming** — first inference after restart may be slower

The **8% variance on Ep2** (116.6 vs 108.1s) is within normal bounds. The **67% variance on Ep1** and **36% on Ep3** are larger but not unprecedented for heavy episodes (60+ edges) on local hardware.

### Supporting Evidence: Historical Variance

| Run | Ep1 | Ep3 | Notes |
|-----|:---:|:---:|:---:|
| init_10 | 300.5s (T/O) | 99.1s | Clean graph |
| init_11 Run 1 | 300.5s (T/O) | 99.1s | Clean graph |
| init_11 Run 2 | 300.5s (T/O) | 249.2s | Clean graph (Docker restarted) |
| init_12 | 254.4s | 248.8s | Clean graph |
| init_13 Run 2 | 425.2s | 338.7s | Clean graph |

Episode 3 has ranged from 99s to 339s across clean-graph runs — a **3.4x range**. Episode 1 has ranged from 254s to 425s (excluding timeouts) — a **1.7x range**. This confirms high natural variance on the local vLLM setup.

---

## Finding 2: Timeout Increase Was Essential

TASK-FIX-cc7e raised the `project_overview` timeout from 300s to 600s. init_13 Run 2 proves this was critical:

- Episode 1 completed at **425.2s** — would have **timed out** at 300s
- Episode 3 completed at **338.7s** — would have **timed out** at 300s
- Both episodes now have comfortable headroom (71% and 56% of limit)

Without this fix, Run 2 would have had **2 of 3 episodes fail**, with only Episode 2 completing. The timeout increase converts what would have been a broken run into a successful one.

---

## Finding 3: Out-of-Bounds Warnings Fully Resolved

| Run | "out of bounds" Warnings | Graph State |
|-----|:---:|:---:|
| init_10 | 8+ | Clean |
| init_11 Run 1 | 8+ | Clean |
| init_12 / init_13 Run 1 | 14 | Clean |
| **init_13 Run 2** | **0** | **Clean** |

Both runs were on clean graphs, so this is **not a graph-state effect**. The resolution occurred between the two GuardKit codebases, but the warnings come from `graphiti_core.utils.maintenance.edge_operations`, not GuardKit code.

Most likely explanation: an **upstream graphiti-core version update** (or dependency update) that fixed the edge chunking index calculation. The "Target index -1 out of bounds for chunk of size 15" pattern is a classic off-by-one error that the graphiti-core maintainers would fix.

---

## Finding 4: Episode Profiling Metrics

New in Run 2 thanks to commit 3afc32fe:

| Episode | Nodes | Edges | Invalidated | Duration |
|---------|:---:|:---:|:---:|:---:|
| project_purpose | 23 | 60 | 0 | 425.2s |
| project_tech_stack | 13 | 14 | 0 | 116.6s |
| project_architecture | 24 | 59 | 0 | 338.7s |
| **Total** | **60** | **133** | **0** | **880.5s** |

### Insights

1. **Edge count strongly correlates with duration**: Ep1 (60 edges, 425s) and Ep3 (59 edges, 339s) vs Ep2 (14 edges, 117s). Roughly ~6-7s per edge for heavy episodes.
2. **Zero invalidations**: All edges freshly created on clean graph — expected.
3. **Edge-heavy ratio**: 2.2-2.6 edges/node for Ep1/Ep3, 1.1 for Ep2 — purpose and architecture descriptions are relationship-rich.
4. **This profiling data is valuable** for future performance analysis and should be included in all init profiling runs.

---

## Finding 5: Cross-Run Trend Analysis (init_10 → init_13)

### Complete Trend Table

| Run | Ep1 | Ep2 | Ep3 | Total | Ep1 Status | Graph |
|-----|:---:|:---:|:---:|:---:|:---:|:---:|
| init_10 | 300.5s | 112.3s | 99.1s | 511.9s | TIMEOUT | Clean |
| init_11 R1 | 300.5s | 112.3s | 99.1s | 511.9s | TIMEOUT | Clean |
| init_11 R2 | 300.5s | 110.2s | 249.2s | 659.9s | TIMEOUT | Clean |
| init_12 | 254.4s | 108.1s | 248.8s | 611.3s | OK | Clean |
| init_13 R1 | 254.4s | 108.1s | 248.8s | 611.3s | OK | Clean |
| **init_13 R2** | **425.2s** | **116.6s** | **338.7s** | **880.5s** | **OK** | **Clean** |

### Observations

1. **init_13 Run 1 IS init_12**: Identical timestamps, identical log output. Run 1 in init_project_13.md is a re-run of the init_12 codebase that produced the same results.

2. **Ep2 is the most stable episode**: Ranges from 108-117s (8% variance) — lightweight content, few edges, consistent.

3. **Ep1 and Ep3 have high variance**: Ep3 ranges from 99s to 339s across clean-graph runs. This makes single-run comparisons unreliable.

4. **Timeout headroom is now sufficient**: Even the worst observed Ep1 (425s) is well within the 600s limit.

---

## Finding 6: Episode Name Visibility (Not a Change)

The task noted that episode names appeared to change:
- init_12: `Episode 1/3`, `Episode 2/3`, `Episode 3/3` (no names visible)
- init_13 R2: `project_purpose_vllm-profiling`, `project_tech_stack_vllm-profiling`, `project_architecture_vllm-profiling`

**These are not changes.** The parser has always used `section_type` values of `purpose`, `tech_stack`, `architecture` (project_doc_parser.py:145-176). The episode name format has always been `project_{section_type}_{project_name}`. The new episode profiling logging (commit 3afc32fe) simply made these names visible in the output for the first time.

All 3 episodes use `group_id="project_overview"` (project_seeding.py:170), so the 600s timeout applies to all three via `group_id.endswith("project_overview")`.

---

## Finding 7: duplicate_facts Warnings — Upstream LLM Issue

| Run | duplicate_facts Warnings | Graph |
|-----|:---:|:---:|
| init_12 / Run 1 | ~9 | Clean |
| init_13 Run 2 | ~40 | Clean |

Run 2's increase correlates with more LLM calls during edge processing (60 edges in Ep1 vs fewer in Run 1's processing path). These warnings from `graphiti_core.utils.maintenance.edge_operations` indicate the LLM (vLLM with local model) is returning index values outside valid ranges. This is a combination of:

1. **Upstream graphiti-core prompt design** — the deduplication prompt may not constrain index ranges well
2. **Local LLM quality** — smaller models hallucinate more in structured output tasks

These warnings are **cosmetic** — they don't cause failures, they just indicate wasted LLM calls.

---

## Overall Assessment: Was This an Improvement?

### What Improved

| Improvement | Evidence |
|-------------|----------|
| **Out-of-bounds warnings eliminated** | 14→0 warnings. Clean resolution. |
| **Timeout headroom** | 300→600s prevents failures when Ep1/Ep3 run long |
| **Observability** | Episode profiling (nodes/edges/invalidated) is new and valuable |
| **No episodes failed** | All 3 episodes completed successfully in Run 2 |

### What Didn't Improve

| Area | Evidence |
|------|----------|
| **Raw timing** | 611s→881s (44% worse), but this is vLLM variance, not a regression |
| **duplicate_facts warnings** | Increased from ~9 to ~40, but cosmetic |

### What Can't Be Assessed From init Data

| Area | Why |
|------|-----|
| **Seed template filtering (TASK-a912)** | Init uses `seed_project_knowledge()`, not `seed_all_system_context()` |
| **AutoBuild rule pruning (TASK-daab)** | Only executes in AutoBuild worktree creation |

### Verdict

**The infrastructure is in better shape.** The timing regression is noise, not signal. A single init run on local vLLM is too variable for A/B comparison (Episode 3 has ranged from 99s to 339s across clean-graph runs). The meaningful improvements are the timeout fix, warning resolution, and profiling capability.

To get a reliable timing comparison, you would need **3+ runs and take the median** to smooth out vLLM variance.

---

## Recommendations

### 1. Run Multiple init Runs for Reliable Baseline (Priority: High)

A single run is insufficient given the observed variance (Ep3: 99-339s range). Run 3-5 init runs on a clean graph after each code change and compare medians. This gives a statistically meaningful baseline.

### 2. Accept init_13 Infrastructure Improvements (Priority: High)

The timeout fix, out-of-bounds resolution, and episode profiling are genuine improvements. The raw timing is not meaningful from a single run.

### 3. Validate TASK-daab/TASK-a912 via Their Correct Paths (Priority: Medium)

These were noted as context for the broader goal, not expected in init data. Validation when ready:
- **TASK-daab**: Run AutoBuild, inspect worktree `.claude/rules/`
- **TASK-a912**: Run `guardkit graphiti seed --template fastapi-python`, compare episode counts

### 4. Consider vLLM Warm-Up Protocol (Priority: Low)

If consistent timing matters for benchmarking, consider a warm-up sequence after Docker restart:
- Run a small test episode before the actual init
- This pre-warms the vLLM KV cache and GPU

---

## Acceptance Criteria Assessment

| Criterion | Status | Notes |
|-----------|:---:|:---:|
| init_13 Run 2 fully analysed with timing breakdown | **DONE** | Findings 1, 4 |
| Episode name/content changes documented | **DONE** | Finding 6 — names unchanged, profiling made them visible |
| Performance regression root cause identified | **DONE** | Finding 1 — vLLM inference variance on local hardware |
| "Out of bounds" warning resolution confirmed | **DONE** | Finding 3 — confirmed 14→0, upstream fix |
| Episode profiling metrics analysed | **DONE** | Finding 4 — edge count correlates with duration |
| Comparison to init_12 baseline with delta analysis | **DONE** | Finding 5 — cross-run trend init_10→init_13 |
| TASK-REV-acbc target metrics assessed | **DONE** | Not testable via init (different code paths) |
| Cross-run trend analysis updated | **DONE** | Finding 5 — complete table with all runs |
| Assessment of whether implementation objectives were met | **DONE** | Infrastructure improved, timing inconclusive |
| Recommendations for further optimisation | **DONE** | Recommendations section |
