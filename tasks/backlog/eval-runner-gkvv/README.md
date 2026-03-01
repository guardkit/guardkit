# Feature: Eval Runner GuardKit vs Vanilla Pipeline

**Feature ID:** FEAT-GKVV
**Parent Review:** TASK-REV-EAE8
**Status:** Planned
**Tasks:** 10
**Aggregate Complexity:** 7/10

## Problem Statement

GuardKit's core value proposition is that running `feature-spec → system-plan → feature-plan → autobuild` produces measurably better results than giving the same input to plain vanilla Claude Code. This claim needs empirical validation.

Currently, testing this requires manually briefing agents, monitoring dual runs, and comparing outputs — a process that takes hours per comparison and is too slow to run systematically.

## Solution

Build a standalone comparison pipeline (`guardkit eval run BRIEF.yaml`) that:

1. **Provisions forked workspaces** — GuardKit arm (with CLAUDE.md + .guardkit/) and Vanilla arm (same codebase, no GuardKit config)
2. **Resolves shared input** — text, file, or Linear ticket, distributed identically to both arms
3. **Runs arms sequentially** — GuardKit pipeline first, then vanilla Claude Code
4. **Extracts quantitative metrics** — test coverage, lint violations, assumptions surfaced
5. **Judges via delta scoring** — LLM + deterministic scoring (1.0 = GK wins, 0.5 = tie, 0.0 = vanilla wins)
6. **Classifies results** — PASSED (≥0.65), FAILED, or ESCALATED (<0.40)
7. **Stores in Graphiti** — comparison episodes with per-arm metrics and deltas for trend analysis

## Approach

**Option 3: Phased Hybrid** — Standalone CLI first (this feature), NATS JetStream integration later.

This de-risks the comparison methodology before investing in queue infrastructure. The runner interface (`run(brief) → EvalResult`) is identical whether called from CLI or NATS subscriber.

## Subtask Summary

| Wave | Task | Name | Complexity |
|------|------|------|-----------|
| 1 | TASK-EVAL-001 | Eval Schemas | 3 |
| 1 | TASK-EVAL-002 | Workspace Fork | 4 |
| 1 | TASK-EVAL-003 | InputResolver | 3 |
| 2 | TASK-EVAL-004 | EvalAgentInvoker | 5 |
| 2 | TASK-EVAL-005 | MetricsExtractor | 3 |
| 2 | TASK-EVAL-006 | EvalJudge | 6 |
| 3 | TASK-EVAL-007 | GKVVRunner | 6 |
| 4 | TASK-EVAL-008 | CLI + Templates + Brief | 4 |
| 4 | TASK-EVAL-009 | Graphiti Storage | 4 |
| 4 | TASK-EVAL-010 | Integration Tests | 5 |

## BDD Coverage

32 BDD scenarios in `features/eval-runner-gkvv/eval-runner-gkvv.feature`:
- 6 key examples (3 @smoke)
- 8 boundary conditions
- 6 negative cases
- 12 edge cases

## Next Steps

1. Review this implementation guide: [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md)
2. Start with Wave 1 tasks (TASK-EVAL-001, TASK-EVAL-002 in parallel)
3. Use `/task-work TASK-EVAL-001 --mode=tdd` for test-first implementation
