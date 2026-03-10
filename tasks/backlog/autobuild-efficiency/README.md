# Autobuild Efficiency: Quality Gate Optimization

## Problem Statement

The youtube-transcript-mcp autobuild review (TASK-REV-7D5B, 82/100) revealed that quality gate verification tasks consume 41% of total orchestrator turns (15/37) while producing zero production code. This inefficiency is structural: implementation tasks don't include lint compliance in their acceptance criteria, so errors accumulate and get deferred to standalone verification tasks where the Coach repeatedly rejects.

Evidence: FEAT-6CE9 (no standalone quality gate task) achieved 1.25 turns/task vs 2.25+ for features with quality gate tasks.

## Solution Approach

Three complementary implementation tasks:

1. **TASK-ABE-001**: Integrate lint compliance into implementation task ACs via research template prompt modifications. Eliminate standalone quality gate verification tasks.

2. **TASK-ABE-002**: Add a stack-agnostic pre-Coach auto-fix step in the autobuild orchestrator. Runs the appropriate linter/formatter between Player completion and Coach invocation, using GuardKit's existing `detect_stack()` patterns.

3. **TASK-ABE-003**: Generate structured review summaries from raw autobuild logs. Replace the raw terminal output with human-readable review documents.

## Projected Impact

| Change | Turn Reduction | Time Savings |
|--------|---------------|--------------|
| Lint in ACs + eliminate QG tasks (#1) | 20-30% | ~30-45 min/build |
| Pre-Coach auto-fix (#2) | 10-15% | ~15-20 min/build |
| **Combined** | **30-40%** | **~45-60 min per 5-feature build** |

## Source

- Parent review: TASK-REV-8D32
- Source review: TASK-REV-7D5B (youtube-transcript-mcp autobuild review)
- Review report: `.claude/reviews/TASK-REV-8D32-review-report.md`

## Execution Strategy

```
Wave 1 (parallel):
  TASK-ABE-001: Lint compliance in ACs
  TASK-ABE-002: Pre-Coach auto-fix

Wave 2 (after Wave 1):
  TASK-ABE-003: Structured review summaries
```
