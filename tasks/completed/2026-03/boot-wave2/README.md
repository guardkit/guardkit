# FEAT-BOOT Wave 2: Bootstrap Fixes from TASK-REV-C9E5

## Problem

After implementing all 7 BOOT Wave 1 tasks (TASK-BOOT-{E3C0, 3CAF, 43DE, 214B, 6D85, F9C4, 7369}), the FEAT-BA28 re-run still fails with UNRECOVERABLE_STALL on TASK-DB-003. Two root causes were identified:

1. **Propagation gap**: `requires_infrastructure` defined in feature YAML never reaches the Coach because `orchestrate()` loads it from task `.md` frontmatter (which lacks the field)
2. **Install-before-ready**: Bootstrap runs editable install before the project source tree is complete

These combine to produce: no dependencies installed + no Docker infrastructure + no conditional approval = identical feedback loop = stall.

## Solution

Five targeted fixes addressing root causes, diagnostics, cache correctness, and regression prevention.

## Source Review

All tasks derive from: `.claude/reviews/TASK-REV-C9E5-review-report.md` (Revision 3)

Parent review: TASK-REV-C9E5

## Subtasks

| ID | Title | Priority | Wave | Complexity | Mode | Dependencies |
|----|-------|----------|------|------------|------|--------------|
| TASK-BOOT-B032 | Fix requires_infrastructure propagation | P0 | 1 | 3 | task-work | — |
| TASK-BOOT-F632 | Dependency-only install for incomplete projects | P0 | 1 | 5 | task-work | — |
| TASK-BOOT-754A | Structured diagnostic logging | P1 | 1 | 2 | task-work | — |
| TASK-BOOT-0F53 | State-aware hash persistence | P2 | 2 | 3 | task-work | — |
| TASK-BOOT-99A5 | Integration test for propagation | P1 | 2 | 4 | task-work | B032 |

## Co-dependency Analysis

```
For TASK-DB-003 to resolve stall (conditional approval, test skipped):
  TASK-BOOT-B032 alone is sufficient

For TASK-DB-003 tests to ACTUALLY PASS:
  TASK-BOOT-B032 + TASK-BOOT-F632 are both required
  B032 provides: requires_infrastructure=[postgresql] → Docker → DATABASE_URL
  F632 provides: sqlalchemy, asyncpg, fastapi installed → import succeeds

For diagnostic visibility:
  TASK-BOOT-754A alone is sufficient

For cache correctness:
  TASK-BOOT-0F53 alone is sufficient
```

## Open Design Decisions

- **Time-based vs structure-hash retry** (R3): Using time-based cooldown for simplicity. Could switch to `source_tree_hash` if needed later.
- **Dependency parser depth** (R2): v1 uses simple PEP 508 string parsing for Python. Complex specifiers (extras, markers) passed through to pip as-is.
