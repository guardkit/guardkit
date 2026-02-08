# Graphiti Integration Gap Closure

**Parent Review:** TASK-REV-DE4F (Gap Analysis: Graphiti Integration Completeness)
**Feature ID:** FEAT-GG-001
**Created:** 2026-02-08

## Problem Statement

After 14 fix tasks (GCW1-6 + GCI0-7) resolved the major Graphiti integration gaps, a comprehensive gap analysis (TASK-REV-DE4F) found 4 remaining issues:

1. `seed_feature_spec()` is fully implemented but never called by `/feature-plan`
2. Standard `/task-work` context loading (GCI1) may not be wired in production execution
3. `[Graphiti]` structured logging missing from 4 write-path files
4. Two docstrings show `await` on sync `get_graphiti()` function

## Tasks

| Task ID | Description | Wave | Complexity | Priority |
|---------|-------------|------|------------|----------|
| TASK-FIX-GG01 | Wire `seed_feature_spec()` into `/feature-plan` | 1 | 2 | Medium |
| TASK-FIX-GG02 | Clarify/complete GCI1 standard `/task-work` wiring | 1 | 4 | Medium |
| TASK-FIX-GG03 | Add `[Graphiti]` logging to 4 write-path files | 2 | 1 | Low |
| TASK-FIX-GG04 | Fix docstring `await` examples | 2 | 1 | Low |

## Execution Strategy

**Wave 1** (2 tasks, parallel):
- GG01: Wire seeding call — straightforward, low risk
- GG02: Clarify task-work wiring — investigation + potential implementation

**Wave 2** (2 tasks, parallel):
- GG03: Logging updates — mechanical, low risk
- GG04: Docstring fixes — trivial

## Impact

Closing these gaps completes the Graphiti integration lifecycle:
- **Before:** Feature specs planned with Graphiti context but not seeded back
- **After:** Full read/write cycle for `/feature-plan`
- **Before:** Standard `/task-work` runs without knowledge graph context
- **After:** Clarified whether spec-level wiring provides context in practice
