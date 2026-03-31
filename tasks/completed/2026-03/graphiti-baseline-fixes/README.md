# FEAT-GBF: Graphiti Baseline Fixes

**Parent Review**: TASK-REV-C632 (Graphiti Usage Baseline Analysis)
**Score**: 82/100 (Good - minor improvements identified)

## Problem Statement

The TASK-REV-C632 baseline analysis identified 3 actionable improvements to the Graphiti integration:

1. **Dual serialization path** - Episodes get metadata from both entity-level `to_episode_body()` and client-level `_inject_metadata()`, risking divergence
2. **Large seeding module** - `seeding.py` at 1,446 lines, several categories not yet extracted to dedicated files
3. **Missing fidelity guidance** - Baseline docs don't reference the known retrieval fidelity limitations from the code retrieval assessment

## Solution

Three implementation tasks + one follow-up review to update the baseline documents.

## Subtasks

| Task | Title | Wave | Mode | Priority |
|------|-------|------|------|----------|
| TASK-GBF-001 | Unify episode serialization pattern | 1 | task-work | Medium |
| TASK-GBF-002 | Extract remaining seeding categories | 1 | task-work | Low |
| TASK-GBF-003 | Add retrieval fidelity guidance to docs | 1 | direct | Medium |
| TASK-GBF-REV | Update baseline docs post-implementation | 2 | task-review | Medium |

## Execution Strategy

**Wave 1** (3 tasks - all independent, can run in parallel):
- TASK-GBF-001: Code refactoring (serialization)
- TASK-GBF-002: Code refactoring (seeding extraction)
- TASK-GBF-003: Documentation update (fidelity guidance)

**Wave 2** (1 task - depends on all Wave 1):
- TASK-GBF-REV: Review and update baseline docs to reflect changes

## Key Files

- Review report: `.claude/reviews/TASK-REV-C632-review-report.md`
- Technical reference: `docs/reviews/graphiti_baseline/graphiti-technical-reference.md`
- Storage theory: `docs/reviews/graphiti_baseline/graphiti-storage-theory.md`
- Fidelity assessment: `docs/reviews/graphiti_enhancement/graphiti_code_retrieval_fidelity.md`
