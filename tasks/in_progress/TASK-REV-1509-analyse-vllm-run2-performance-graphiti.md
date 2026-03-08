---
id: TASK-REV-1509
title: Analyse vLLM run 2 performance and Graphiti integration failure
status: review_complete
task_type: review
review_mode: decision
review_depth: standard
priority: high
tags: [vllm, performance, graphiti, autobuild, gb10, review]
complexity: 6
created: 2026-03-07T12:00:00Z
updated: 2026-03-07T14:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: decision
  depth: standard
  findings_count: 8
  recommendations_count: 4
  decision: implement
  report_path: .claude/reviews/TASK-REV-1509-review-report.md
  completed_at: 2026-03-07T14:00:00Z
---

# Task: Analyse vLLM Run 2 Performance and Graphiti Integration Failure

## Description

Analyse the second vLLM autobuild run on Dell ProMax GB10 to understand:

1. **Performance regression**: Did the TASK-VPT-001 changes (max_parallel=1, sdk_max_turns=75, timeout_multiplier=3.0) cause a regression or improvement? Compare total run time and per-task throughput against run 1.
2. **Graphiti still not working**: Despite TASK-FIX-GCW6 being completed (factory singleton init), Graphiti context retrieval appears to still be failing. Root cause this — is it the same `get_factory()` issue or a different failure mode?
3. **Comparative analysis with Anthropic run 2**: The Anthropic API run succeeded. Compare task completion rates, timing, and Graphiti status between the two runs.
4. **Graphiti integration gap analysis**: Review all completed Graphiti-related tasks and reviews to identify if there's additional context or fixes that have been missed. We've done extensive work on Graphiti integration — is there a pattern of recurring failures?

## Review Objectives

### Objective 1: Performance Impact of VPT-001 Changes
- Compare run 2 vs run 1 per-turn throughput (run 1 baseline: ~20s/turn sequential, ~87s/turn parallel)
- Verify max_parallel=1 eliminated the parallel throughput penalty
- Assess whether sdk_max_turns=75 provided sufficient headroom
- Check timeout_multiplier=3.0 adequacy

### Objective 2: Graphiti Failure Root Cause
- Identify the exact failure point in run 2 logs
- Compare against TASK-FIX-GCW6 completion report — was the fix deployed?
- Check if `get_factory()` now returns a valid factory or if a different failure occurs
- Determine if FalkorDB connectivity is the issue vs code-level bug

### Objective 3: Anthropic Run 2 Comparison
- Task completion rates (vLLM vs Anthropic)
- Per-task timing comparison
- Graphiti status in Anthropic run (does it work there?)
- Quality of generated code (retry rates, turns needed)

### Objective 4: Graphiti Integration History Review
- Review all Graphiti-related completed tasks for gaps
- Check reviews: TASK-REV-5E93, TASK-REV-5610, TASK-REV-C960, TASK-REV-0E58
- Check completed fixes: TASK-FIX-GCW3, GCW4, GCW6, GTP1, GCI0, GLF-001
- Identify any remaining wiring issues or configuration gaps
- Determine if the autobuild entry path fully exercises the Graphiti init chain

## Reference Files

| File | Description |
|------|-------------|
| `docs/reviews/vllm-profiling/vllm_run_2.md` | vLLM autobuild run 2 log (primary input) |
| `docs/reviews/vllm-profiling/anthropic_run_2_success.md` | Anthropic API run 2 log (comparison) |
| `docs/reviews/vllm-profiling/vllm_run_1.md` | vLLM run 1 log (baseline for regression check) |
| `.claude/reviews/TASK-REV-5E93-review-report.md` | Run 1 review report with profiling data |
| `tasks/completed/TASK-FIX-GCW6/completion-report.md` | GCW6 fix details |
| `tasks/backlog/vllm-perf-tuning/TASK-VPT-001-tune-local-backend-defaults.md` | VPT-001 changes |

## Acceptance Criteria

- [x] Per-turn throughput comparison: run 2 vs run 1 (with VPT-001 changes)
- [x] Root cause identified for Graphiti failure in run 2
- [x] Clear determination: is this the same GCW6 issue or a new failure?
- [x] Anthropic vs vLLM comparison table for run 2
- [x] Graphiti integration gap analysis with specific next-fix recommendation
- [x] Updated pre-run checklist for run 3
