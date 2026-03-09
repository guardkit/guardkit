# Review Report: TASK-VR6-65A0

## Slim Protocol Turn Inflation on vLLM Backend

**Task**: Investigate slim protocol turn inflation on vLLM backend
**Mode**: Decision Analysis
**Depth**: Standard
**Date**: 2026-03-09

---

## Executive Summary

The slim protocol (5.5KB) causes **24-174% more SDK turns** than the full protocol (19KB) on the vLLM backend. The inflation is most severe on complex tasks (FBP-006: integration tests) and modest on simple tasks (FBP-002). The session resume feature (commit 821dfda5, present in Run 6) did **not** measurably reduce turn inflation. The recommendation is to create a **medium protocol (~10KB)** that restores the anti-stub rules and stack patterns while keeping the slim structure.

---

## Finding 1: SDK Turn Comparison (Quantified)

### Per-Task SDK Turns Across Runs

| Task | Run 4 (Full, 19KB) | Run 5 (Slim, 5.5KB) | Run 6 (Slim+Resume) | R5 vs R4 | R6 vs R4 |
|------|--------------------:|---------------------:|---------------------:|---------:|---------:|
| FBP-001 | 37 | 58 | 46 | +57% | +24% |
| FBP-002 | 32 | 29+37=66 | 25 | +106% | -22% |
| FBP-003 | 82 | 87+22=109 | 75 | +33% | -9% |
| FBP-004 | 41 | 69 | 72 | +68% | +76% |
| FBP-005 | 101+26=127 | 49 | 74 | -61% | -42% |
| FBP-006 | 43 | 110 | 118 | +156% | +174% |
| **Total** | **362** | **461** | **410** | **+27%** | **+13%** |

**Notes:**
- Run 4 used full protocol (19,259-19,780 bytes, variant not logged)
- Run 5 used slim protocol (5,536-5,640 bytes, variant=slim, multiplier=4.0x)
- Run 6 used slim protocol (5,536-5,596 bytes) + session resume feature (821dfda5)
- Multi-turn tasks show sum of SDK turns across AutoBuild turns (e.g., FBP-002 R5 = 29+37 over 2 AutoBuild turns)

### Key Observations

1. **FBP-006 (integration tests) is the outlier**: 43 turns (full) vs 110-118 turns (slim) = **156-174% inflation**. This task requires the most architectural context about project structure, test patterns, and error handling.

2. **FBP-005 anomaly**: Actually *improved* with slim (127→49/74). This was a multi-turn task on Run 4 that hit 101 SDK turns before needing a retry. The full protocol's verbosity may have caused context window pressure on this complex task.

3. **FBP-002 (simple task)**: Improved on Run 6 (25 vs 32), suggesting session resume helps simple tasks but not complex ones.

4. **Run 6 vs Run 5**: Mixed results. Session resume reduced total turns by 11% (461→410) but the effect is not consistent — FBP-006 actually got *worse* (110→118).

---

## Finding 2: Per-Turn Latency Savings (Cost Analysis)

### Prompt Size Delta

| Metric | Full Protocol | Slim Protocol | Delta |
|--------|-------------:|-------------:|------:|
| Protocol size | ~19,270 bytes | ~5,587 bytes | -13,683 bytes (-71%) |
| Estimated tokens | ~4,800 tokens | ~1,400 tokens | -3,400 tokens/turn |

### Cost Model

Using vLLM local pricing (effectively $0 per token for self-hosted), the per-turn token savings are **free in monetary terms** but have a **latency impact**:

| Metric | Full Protocol | Slim Protocol |
|--------|-------------:|-------------:|
| Est. prompt tokens/turn | ~4,800 more | baseline |
| Est. prefill time/turn (vLLM) | ~1.5-3s extra | baseline |
| Per-turn latency savings | baseline | -1.5-3s per turn |

### Total Duration Impact (Net Effect)

| Scenario | Turn Count | Per-Turn Savings | Extra Turns Cost | Net |
|----------|----------:|----------------:|----------------:|-----|
| FBP-001 (R4→R6) | +9 turns | -1.5s × 37 = -56s | +9 × ~20s = +180s | **+124s worse** |
| FBP-006 (R4→R6) | +75 turns | -1.5s × 43 = -65s | +75 × ~20s = +1,500s | **+1,435s worse** |
| FBP-005 (R4→R6) | -53 turns | n/a | -53 × ~20s = -1,060s | **-1,060s better** |

**Conclusion**: For complex tasks, the extra turns caused by slim protocol **far outweigh** the per-turn latency savings. Each extra turn costs ~20s of generation time, while the per-turn savings from removing 3,400 tokens is only ~1.5-3s.

---

## Finding 3: Which Removed Sections Correlate with Turn Inflation

### Content Removed by Slim Protocol

| Section | Lines Removed | Likely Impact on Turns |
|---------|-------------:|----------------------|
| Anti-stub rules + REJECTED/ACCEPTED examples | 88 lines | **HIGH** - Without examples, model produces stubs that fail Coach review, causing retries |
| Stack-specific patterns (Python, TS, .NET) | 47 lines | **HIGH** - Model generates non-idiomatic code, needing more iterations for quality gates |
| Fix loop pseudocode | 34 lines | **MEDIUM** - Model may not follow fix loop correctly, leading to extra turns |
| Report schema documentation | 80 lines | **LOW** - Mostly formatting, doesn't affect code generation |
| Docker setup details | 58 lines | **LOW** - Not relevant for most tasks (no infra in test feature) |
| SOLID/DRY/YAGNI explanations | 48 lines | **MEDIUM** - Affects code review phase, may cause rejection/retry |

### Correlation Evidence

**FBP-006 (highest inflation, +174%)**: Integration tests require:
- Understanding of project structure and patterns → **stack-specific patterns removed**
- Proper error handling → **error handling rules condensed to one sentence**
- Anti-stub compliance → **anti-stub examples removed**
- Correct test framework usage → **testing patterns removed**

**FBP-001 (low inflation, +24%)**: Scaffolding task is straightforward and doesn't rely heavily on protocol guidance.

### Most Impactful Removals (Ranked)

1. **Anti-stub rules with examples** (88 lines → 1 sentence) — Model can't distinguish stubs from real code without examples
2. **Stack-specific implementation patterns** (47 lines → 1 sentence) — Model defaults to generic patterns
3. **Error handling requirements** (detailed rules → brief mention) — Model omits edge cases
4. **SOLID/DRY/YAGNI with explanations** (48 lines → checklist) — Shallow compliance without understanding

---

## Finding 4: Confounding Factor - Session Resume (821dfda5)

Run 6 included the session resume feature (TASK-RFX-B20B). Results:

- **Total turns**: 461 (R5) → 410 (R6) = **11% reduction**
- **FBP-002**: 66 (R5, 2 AutoBuild turns) → 25 (R6, 1 turn) = **62% reduction** (resume clearly helped)
- **FBP-003**: 109 (R5, 2 turns) → 75 (R6, 1 turn) = **31% reduction** (resume clearly helped)
- **FBP-006**: 110 (R5) → 118 (R6) = **7% worse** (resume did NOT help)

**Conclusion**: Session resume helps reduce **AutoBuild retries** (tasks that previously needed 2 AutoBuild turns now complete in 1), but does NOT reduce **intra-turn SDK turn inflation** caused by missing protocol guidance. These are orthogonal problems.

---

## Finding 5: Feature Completion Status

| Run | Protocol | Tasks Completed | Status |
|-----|----------|---------------:|--------|
| Run 4 | Full (19KB) | 7/7 | COMPLETED |
| Run 5 | Slim (5.5KB) | 6/7 | FAILED (FBP-007 not completed) |
| Run 6 | Slim+Resume | 7/7 | COMPLETED |

Run 5 failed to complete the feature (6/7 tasks). Run 6 completed all 7 but at the cost of very high turn counts for FBP-006.

---

## Option Evaluation Matrix

| Option | Turn Reduction | Per-Turn Latency | Implementation Effort | Risk | Score |
|--------|:-------------:|:----------------:|:--------------------:|:----:|:-----:|
| A. Revert to full protocol | Best (baseline) | Worst (+3s/turn) | Zero | Low | 6/10 |
| B. Medium protocol (~10KB) | Good (-30-50% vs slim) | Good (-1.5s/turn) | Medium (2-4h) | Low | **9/10** |
| C. Keep slim + raise max turns | Poor (same inflation) | Best (-3s/turn) | Low (1-line) | Medium | 4/10 |
| D. Keep slim (no change) | Poor | Best (-3s/turn) | Zero | High (failures) | 3/10 |

---

## Recommendation: Create Medium Protocol (~10KB)

### What to Restore (from full → medium)

1. **Anti-stub rules with examples** (~88 lines) — Critical for quality
2. **Stack-specific implementation patterns** (~47 lines) — Reduces code iteration
3. **Error handling requirements** (~20 lines, abbreviated from full) — Prevents Coach rejections
4. **SOLID/DRY/YAGNI with brief explanations** (~25 lines, abbreviated) — Improves code review pass rate

**Estimated medium protocol size**: ~10-11KB (currently 5.5KB slim, 19KB full)

### What to Keep Removed

- Docker setup details (not needed unless `requires_infrastructure`)
- Verbose report schema documentation (slim version sufficient)
- Fix loop pseudocode (slim summary sufficient)

### Additional Configuration for Run 7

- Keep `sdk_max_turns = 100` for local backends (current setting)
- Keep session resume enabled (helps reduce AutoBuild retries)
- Consider raising `sdk_max_turns` to 120 as a safety margin for FBP-006-type tasks

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Medium protocol still causes inflation | Low | Medium | A/B test Run 7 with medium vs full on FBP-006 |
| Medium protocol too large for context | Very Low | Low | Still 47% smaller than full |
| Restored sections not the right ones | Low | Medium | Correlation analysis strongly implicates anti-stub + stack patterns |

---

## Decision Required

| Option | Recommendation |
|--------|---------------|
| **B. Create medium protocol** | **RECOMMENDED** — Best balance of turn efficiency and per-turn latency |
| A. Revert to full | Acceptable fallback if medium doesn't help |
| C. Raise max turns only | NOT recommended — treats symptom, not cause |
| D. No change | NOT recommended — Run 5 failed, FBP-006 inflation too high |

---

## Appendix: Raw Data Sources

- Run 4: `docs/reviews/vllm-profiling/vllm_run_4.md` (full protocol, 19KB)
- Run 5: `docs/reviews/vllm-profiling/vllm_run_5.md` (slim protocol, 5.5KB)
- Run 6: `docs/reviews/vllm-profiling/vllm_run_6.md` (slim + session resume)
- Protocol files: `guardkit/orchestrator/prompts/autobuild_execution_protocol.md` (full), `autobuild_execution_protocol_slim.md` (slim)
- Selection logic: `guardkit/orchestrator/agent_invoker.py:4094-4101`
