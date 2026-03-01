---
id: TASK-EVAL-006
title: "Implement EvalJudge with deterministic and LLM comparison scoring"
task_type: feature
parent_review: TASK-REV-EAE8
feature_id: FEAT-GKVV
status: pending
created: 2026-03-01T00:00:00Z
priority: high
tags: [eval-runner, judge, llm, scoring]
complexity: 6
wave: 2
implementation_mode: task-work
dependencies:
  - TASK-EVAL-001
  - TASK-EVAL-005
---

# Task: Implement EvalJudge with Deterministic and LLM Comparison Scoring

## Description

Implement the two-phase judging pipeline: deterministic checks (filesystem-based) followed by LLM-as-judge scoring. The comparison mode scores criteria as deltas between arms (1.0 = GuardKit wins, 0.5 = tie, 0.0 = vanilla wins).

## Acceptance Criteria

- [ ] `EvalJudge.evaluate_comparison(brief, guardkit_traj, vanilla_traj, metrics) -> EvalResult`
- [ ] Deterministic criteria (c2, c3, c5) use `ComparisonMetrics` deltas for scoring
- [ ] LLM judge criteria (c1, c4) receive both SUMMARY.md files, run logs, and quantitative metrics
- [ ] LLM judge always uses Anthropic API (not local vLLM) for consistent scoring quality
- [ ] Judge prompt instructs delta scoring: 1.0 = GuardKit clearly better, 0.5 = tie, 0.0 = vanilla wins
- [ ] Each criterion scored between 0.0 and 1.0
- [ ] Weighted score = sum of (criterion score * criterion weight)
- [ ] Result classification: PASSED (>= pass_threshold), FAILED (>= escalate_threshold), ESCALATED (< escalate_threshold)
- [ ] LLM judge retries up to 5 times with exponential backoff on rate limit (ASSUM-004)
- [ ] Both arms failing still produces a comparison result (not silently discarded)
- [ ] Judge assesses partial pipeline completion — does not penalize incomplete runs
- [ ] `EvalResult` includes per-criterion scores with reasoning
- [ ] Unit tests for deterministic scoring, classification thresholds, retry logic, partial completion

## Technical Context

- Location: `guardkit/eval/judge.py` (new module)
- Design reference: `docs/research/eval-runner/eval-runner-architecture.md` (Section 5)
- Judge prompt: `docs/research/eval-runner/eval-runner-guardkit-vs-vanilla.md` (Section 8)
- Escalation logic: `docs/research/eval-runner/eval-runner-architecture.md` (Section 5.3)
- Uses Anthropic API directly (like `coach_verification.py`), not via Agent SDK

## BDD Scenario Coverage

- Key example: Judge scores criteria as deltas between arms
- Boundary: Weighted score exactly at pass_threshold 0.65 → PASSED
- Boundary: Weighted score 0.64 → FAILED
- Boundary: Weighted score exactly at escalate_threshold 0.40 → FAILED (not escalated)
- Boundary: Weighted score 0.39 → ESCALATED
- Boundary: Perfect tie → 0.5
- Edge case: LLM judge retries on rate limit (5x exponential backoff)
- Edge case: Partial GuardKit pipeline still provides comparison data
- Negative: Both arms failing still produces comparison result

## Implementation Notes

[Space for implementation details]

## Test Execution Log

[Automatically populated by /task-work]
