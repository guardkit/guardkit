# AutoBuild FEAT-5606 Fixes

## Problem Statement

AutoBuild feature FEAT-5606 ("GOAL.md Parser and Strict Validation") failed after 57m 34s, completing only 2/5 tasks. Root cause analysis (TASK-REV-8BC0) identified five issues across the orchestration stack:

1. **40% CancelledError rate** on direct-mode Player invocations due to async generator cleanup race condition
2. **Zero diagnostic visibility** when parallel tasks time out
3. **Implementation mode routing** defaults to direct mode for tasks that would benefit from task-work mode
4. **Instrumentation data loss** from asyncio.Lock bound to wrong event loop in parallel execution
5. **Synthetic report false negatives** preventing Coach from verifying semantic acceptance criteria

## Solution Approach

Five targeted fixes, organized in 3 waves with dependency tracking:

| Wave | Tasks | Focus |
|------|-------|-------|
| 1 | GEN1 + OBS2 | Fix generator lifecycle + add parallel diagnostics |
| 2 | MODE3 + EMIT4 | Improve routing defaults + fix instrumentation |
| 3 | SYNTH5 | Enhance synthetic report verification |

## Subtask Summary

| ID | Priority | Title | Complexity |
|----|----------|-------|------------|
| TASK-FIX-GEN1 | P0 | Fix direct-mode generator lifecycle | 4 |
| TASK-FIX-OBS2 | P1 | Add per-task progress logs | 5 |
| TASK-FIX-MODE3 | P1 | Default to task-work mode for complexity >= 2 | 3 |
| TASK-FIX-EMIT4 | P2 | Fix JSONLFileBackend cross-loop lock | 2 |
| TASK-FIX-SYNTH5 | P3 | Improve synthetic report semantic verification | 5 |

## References

- Review report: `.claude/reviews/TASK-REV-8BC0-review-report.md`
- Deep dive with sequence diagrams: `.claude/reviews/TASK-REV-8BC0-deep-dive.md`
- Parent review task: `tasks/backlog/TASK-REV-8BC0-analyse-autobuild-feat-5606-failure.md`
