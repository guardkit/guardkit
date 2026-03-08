---
id: TASK-VOPT-004
title: Full Run 4 - fresh execution with all optimisations
status: backlog
task_type: review
priority: high
tags: [vllm, performance, run4, benchmark]
complexity: 1
parent_review: TASK-REV-CB30
feature_id: FEAT-VOPT
wave: 2
implementation_mode: manual
dependencies: [TASK-VOPT-001, TASK-VOPT-002, TASK-VOPT-003]
created: 2026-03-08T00:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Full Run 4 — Fresh Execution Benchmark

## Problem

Run 3 was a resume run (only FBP-007 executed fresh). We need a full fresh run to:
1. Validate all optimisations end-to-end
2. Get comparable per-task timings vs Run 2
3. Measure Graphiti context impact across all tasks (not just FBP-007)
4. Collect per-SDK-turn timing data (from TASK-VOPT-002)

## Pre-Run Checklist

```
□ TASK-VOPT-001 merged (slim protocol)
□ TASK-VOPT-002 merged (timing instrumentation)
□ TASK-VOPT-003 merged (log noise suppression)
□ pip install -e . (reinstall guardkit)
□ FalkorDB running on whitestocks: redis-cli -h whitestocks -p 6379 ping
□ Verify: guardkit graphiti search "test"
□ vLLM server running with Qwen3-Coder-Next-FP8
```

## Run Command

```bash
ANTHROPIC_BASE_URL=http://localhost:8000 ANTHROPIC_API_KEY=vllm-local \
  guardkit autobuild feature FEAT-1637 --max-turns 30 --verbose --fresh
```

## Expected Metrics to Collect

| Metric | Run 2 | Run 3 (partial) | Run 4 Target |
|--------|-------|-----------------|-------------|
| Total duration | 4h 42m | 64m (FBP-007 only) | <3h |
| Tasks completed | 6/7 | 7/7 | 7/7 |
| SDK ceiling hits | 33% | 0% | 0% |
| Overall ratio vs Anthropic | 10x | N/A | <5x |

## Post-Run Analysis

After completion, create review task: `/task-review TASK-VR4-XXX` to compare Run 4 vs Run 2 vs Anthropic with the new timing instrumentation data.

## References

- Review: `.claude/reviews/TASK-REV-CB30-vllm-viability-review-report.md`
- Run 2 data: `docs/reviews/vllm-profiling/vllm_run_2.md`
- Run 3 data: `docs/reviews/vllm-profiling/vllm_run_3.md`
