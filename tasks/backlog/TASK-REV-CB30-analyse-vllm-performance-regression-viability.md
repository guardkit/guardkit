---
id: TASK-REV-CB30
title: Analyse vLLM performance regression and viability
status: review_complete
created: 2026-03-07T10:00:00Z
updated: 2026-03-07T10:00:00Z
priority: high
tags: [vllm, performance, regression, qwen3, gb10, review]
task_type: review
complexity: 6
review_mode: decision
review_depth: comprehensive
related_tasks: [TASK-REV-1509, TASK-VPT-001]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Analyse vLLM Performance Regression and Viability

## Description

Review the performance regression introduced by TASK-VPT-001 (`max_parallel=1`) which caused Run 2 duration to increase from 2h 58m (Run 1) to 4h 42m — a 60% regression. The current 10x differential vs Anthropic API makes vLLM on GB10 unviable for production use. Target is 2.5-3x differential, not 10x.

## Context

### Source Review Report
- `.claude/reviews/TASK-REV-1509-review-report.md` — comprehensive Run 2 analysis

### The Core Problem
TASK-VPT-001 set `max_parallel=1` to eliminate GPU contention (the 4.3x parallel throughput penalty). This succeeded in its goal but made everything sequential, massively increasing wall-clock time. The net result was **worse** than Run 1 despite eliminating contention.

### Current Performance Gap (Run 2 vs Anthropic)

| Task | vLLM Duration | Anthropic Duration | Ratio |
|------|--------------|-------------------|-------|
| FBP-001 | 16m 18s | 4m 21s | 3.7x |
| FBP-002 | 8m | 3m 16s | 2.4x |
| FBP-004 | 30m | 4m 3s | 7.4x |
| FBP-003 | 11m 40s | 4m 53s | 2.4x |
| FBP-005 | 77m 23s | 5m 21s | 14.4x |
| FBP-006 | 26m 32s | 6m 7s | 4.3x |
| FBP-007 | FAILED | 8m 31s | N/A |
| **Total** | **4h 42m** | **28m** | **10x** |

### Key Observations
- Per-turn throughput: ~20s/turn (vLLM) vs ~5-7s/turn (Anthropic) = **3-4x at the turn level**
- SDK turn consumption: Qwen3 uses **2-3x more turns** than Claude for equivalent tasks
- Two bottlenecks compound: slower turns × more turns = 6-10x+ total
- FBP-005 is the worst outlier at 14.4x (hit SDK ceiling, needed 2 AutoBuild turns)
- Some tasks (FBP-002, FBP-003) are only 2.4x — suggesting the 2.5-3x target is achievable for simpler tasks

### ChatGPT's Assessment
Context reduction with further tuning could yield 1.5-3x improvements. This needs validation against actual data.

## Review Objectives

### Objective 1: Decompose the 10x Gap
- What portion is per-turn latency (hardware-bound)?
- What portion is turn inefficiency (Qwen3 needing more turns)?
- What portion is SDK ceiling hits and AutoBuild retries?
- What portion is sequential execution (max_parallel=1)?
- What is the theoretical minimum with perfect tuning on GB10?

### Objective 2: Evaluate Context Reduction Impact
- Review the context-reduction task in backlog
- What reduction in prompt tokens is achievable?
- How does this translate to per-turn latency improvement?
- Is ChatGPT's 1.5-3x improvement estimate realistic?

### Objective 3: Parallelism Strategy
- Can we restore `max_parallel=2` with smarter scheduling?
- Would staggered starts (delay second task by N seconds) avoid GPU contention?
- Is there a GPU memory threshold that triggers contention?
- What about `max_parallel=2` but only for simple tasks?

### Objective 4: SDK Turn Efficiency
- Why does Qwen3 use 2-3x more SDK turns than Claude?
- Can prompt engineering reduce turn count?
- Would system prompt optimisation help?
- Is this a fundamental model capability gap?

### Objective 5: Viability Assessment
- At what ratio (vLLM/Anthropic) does vLLM become viable? (User target: 2.5-3x)
- What is the realistic best-case scenario with all optimisations?
- Cost comparison: vLLM GB10 operational cost vs Anthropic API cost
- Break-even analysis: at what usage volume does local vLLM pay for itself?
- Is there a point where "doing it manually" is genuinely better?

## Acceptance Criteria

- [ ] 10x gap decomposed into contributing factors with percentages
- [ ] Context reduction impact estimated with evidence
- [ ] Parallelism alternatives evaluated with risk assessment
- [ ] SDK turn efficiency analysis completed
- [ ] Viability decision matrix produced with clear recommendation
- [ ] Actionable Run 3 parameter recommendations (beyond what TASK-REV-1509 already covers)

## Data Sources

- `.claude/reviews/TASK-REV-1509-review-report.md` — Run 2 comprehensive review
- `docs/reviews/vllm-profiling/vllm_run_2.md` — Run 2 raw data
- `tasks/backlog/context-reduction/` — context reduction task details
- `tasks/backlog/vllm-perf-tuning/` — existing perf tuning task
- `tasks/completed/TASK-VPT-002-run3/` — Run 3 fixes (if applicable)

## Implementation Notes

This is a review/analysis task. Use `/task-review TASK-REV-CB30` to execute.
