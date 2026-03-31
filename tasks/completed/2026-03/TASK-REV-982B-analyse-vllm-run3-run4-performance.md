---
id: TASK-REV-982B
title: Analyse vLLM Run 3 and Run 4 performance on Dell GB10
status: review_complete
task_type: review
review_mode: decision
review_depth: comprehensive
priority: high
tags: [vllm, performance, graphiti, autobuild, gb10, review, qwen3]
complexity: 6
created: 2026-03-08T10:00:00Z
updated: 2026-03-08T10:00:00Z
related_tasks: [TASK-REV-1509, TASK-REV-CB30, TASK-VOPT-001, TASK-VOPT-002, TASK-VOPT-003, TASK-VOPT-004]
review_results:
  mode: decision
  depth: comprehensive
  score: 72
  findings_count: 12
  recommendations_count: 7
  decision: accept_with_selective_optimisation
  report_path: .claude/reviews/TASK-REV-982B-review-report.md
  completed_at: 2026-03-08T14:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Analyse vLLM Run 3 and Run 4 Performance on Dell GB10

## Description

Analyse the vLLM autobuild Run 3 (resume) and Run 4 (fresh) results on Dell ProMax GB10 to:

1. **Assess Run 3 impact**: Run 3 was a resume run where only FBP-007 executed fresh (all others skipped). FBP-007 went from FAILED (Run 2, 4 turns, 138m) to SUCCESS (Run 3, 1 turn, ~64m) — a dramatic improvement attributed to Graphiti context loading. Quantify the improvement and confirm root cause.

2. **Full Run 4 analysis**: Run 4 was a complete fresh run (--fresh flag) with all 7 tasks. Total duration: 227m 24s (3h 47m). All 7/7 tasks succeeded. One SDK ceiling hit (FBP-005, 26 turns HIT, needed 2 AutoBuild turns). Compare against Run 2 (4h 42m) and Anthropic baseline (28m).

3. **VOPT task status assessment**: Evaluate whether the TASK-VOPT-001 through TASK-VOPT-004 optimisation tasks from TASK-REV-CB30 are still relevant given Run 4 results, and reprioritise accordingly.

4. **Per-task timing extraction**: Extract per-task and per-wave timing from Run 4 logs to build a comparison table against Run 2 and Anthropic Run 2.

5. **Viability reassessment**: Run 4 at 227m vs Run 2 at 282m is an 19% improvement. The ratio to Anthropic (28m) is now ~8x (down from 10x). Assess whether the VOPT optimisations can realistically close the gap further toward the 2.5-3x target.

## Context

### Previous Reviews
- **TASK-REV-1509**: Run 2 analysis — identified Graphiti failure, 10x gap vs Anthropic, recommended P0 fixes
- **TASK-REV-CB30**: Viability analysis — decomposed 10x gap, created VOPT subtasks, set 2.5-3x target

### Run History

| Run | Mode | Duration | Tasks | FBP-007 | Graphiti | Key Change |
|-----|------|----------|-------|---------|----------|------------|
| Run 1 | Fresh | 2h 58m | 6/7 | FAILED | Broken | Baseline |
| Run 2 | Fresh | 4h 42m | 6/7 | FAILED | Broken | VPT-001 (max_parallel=1) |
| Run 3 | Resume | 63m 35s | 7/7 | SUCCESS (1 turn) | Working | Graphiti fix + cancelled-error-fix |
| Run 4 | Fresh | 3h 47m | 7/7 | SUCCESS (1 turn) | Working | Fresh run with Run 3 fixes |

### Run 4 Task Details

| Task | Status | AutoBuild Turns | SDK Turns | Notes |
|------|--------|----------------|-----------|-------|
| FBP-001 | SUCCESS | 1 | 37 | Scaffolding |
| FBP-002 | SUCCESS | 1 | 32 | Pydantic settings |
| FBP-004 | SUCCESS | 1 | 41 | Correlation ID middleware |
| FBP-003 | SUCCESS | 1 | 82 | Structured logging (high SDK turns) |
| FBP-005 | SUCCESS | 2 | 26 HIT | Health endpoints (SDK ceiling hit) |
| FBP-006 | SUCCESS | 1 | 43 | Integration tests |
| FBP-007 | SUCCESS | 1 | - | Quality gates (scaffolding) |

### Pending VOPT Tasks (from TASK-REV-CB30)

| Task | Description | Status |
|------|-------------|--------|
| TASK-VOPT-001 | Context reduction (~19KB → ~10-12KB) | Backlog |
| TASK-VOPT-002 | Per-SDK-turn timing instrumentation | Backlog |
| TASK-VOPT-003 | Suppress FalkorDB index log noise | Backlog |
| TASK-VOPT-004 | Full Run 4 benchmark (now completed as this run) | Backlog (done?) |

## Review Objectives

### Objective 1: Run 3 Validation
- Confirm FBP-007 improvement is attributable to Graphiti context loading
- Validate that the cancelled-error-fix contributed to stability
- Assess whether the resume-mode results are representative

### Objective 2: Run 4 Performance Decomposition
- Extract per-task wall-clock times from Run 4 logs (timestamps available)
- Build comparison table: Run 4 vs Run 2 vs Anthropic
- Identify which tasks improved most and which remain problematic
- Analyse FBP-003's high SDK turn count (82 turns) — is this a concern?
- Analyse FBP-005's SDK ceiling hit — what caused it?

### Objective 3: Gap Analysis Update
- Run 4 ratio to Anthropic: ~8x overall (down from 10x)
- Per-task ratios: which are within 2.5-3x target, which are not?
- Updated decomposition: hardware-bound vs turn-inefficiency vs context overhead

### Objective 4: VOPT Task Reassessment
- TASK-VOPT-004 appears to be satisfied by Run 4 — recommend closing
- TASK-VOPT-001 (context reduction): still the biggest addressable factor?
- TASK-VOPT-002 (timing instrumentation): still needed given Run 4 has SDK turn counts?
- TASK-VOPT-003 (FalkorDB log noise): still present in Run 4 logs?
- Any new optimisation tasks identified from Run 4 data?

### Objective 5: Viability Decision Update
- Updated viability assessment given 8x ratio (was 10x)
- Realistic best-case with remaining VOPT optimisations
- Cost-benefit: is further optimisation effort justified?
- Recommendation: continue optimising, accept current performance, or pivot?

## Reference Files

| File | Description |
|------|-------------|
| `docs/reviews/vllm-profiling/vllm_run_3.md` | Run 3 log (resume, FBP-007 only fresh) |
| `docs/reviews/vllm-profiling/vllm_run_4.md` | Run 4 log (full fresh run) |
| `docs/reviews/vllm-profiling/vllm_run_2.md` | Run 2 log (baseline comparison) |
| `.claude/reviews/TASK-REV-1509-review-report.md` | Run 2 review report |
| `.claude/reviews/TASK-REV-CB30-vllm-viability-review-report.md` | Viability review report |
| `tasks/backlog/vllm-optimisation/` | VOPT subtask definitions |

## Acceptance Criteria

- [ ] Per-task timing table for Run 4 extracted from logs
- [ ] Comparison table: Run 4 vs Run 2 vs Anthropic (per-task and total)
- [ ] FBP-003 high SDK turn count (82) root cause analysed
- [ ] FBP-005 SDK ceiling hit root cause analysed
- [ ] VOPT task status recommendations (close/modify/keep)
- [ ] Updated viability assessment with 8x ratio context
- [ ] Clear recommendation on next steps (optimise further vs accept vs pivot)

## Implementation Notes

This is a review/analysis task. Use `/task-review TASK-REV-982B` to execute.
