# Feature: /system-plan Command (FEAT-SP-001)

**Parent Review**: TASK-REV-DBBC
**Feature Spec**: `docs/research/system-level-understanding/specs/FEAT-SP-001-system-plan-command.md`
**Priority**: P0
**Total Tasks**: 8
**Estimated Complexity**: 8/10

## Overview

Interactive architecture planning command that establishes and maintains system-level context in Graphiti. Completes the command hierarchy:

```
/task-review    → Code/test level
/feature-plan   → Feature/task level
/system-plan    → System/architecture level  ← NEW
```

## Task Summary

| ID | Title | Complexity | Wave | Dependencies |
|----|-------|-----------|------|-------------|
| TASK-SP-001 | Architecture entity definitions | 4 | 1 | — |
| TASK-SP-002 | Complexity gating | 3 | 1 | — |
| TASK-SP-003 | SystemPlanGraphiti operations | 6 | 2 | SP-001 |
| TASK-SP-004 | Adaptive question flow engine | 5 | 2 | SP-001 |
| TASK-SP-005 | Architecture markdown writer | 5 | 2 | SP-001 |
| TASK-SP-006 | CLI command | 6 | 3 | SP-003, SP-004, SP-005 |
| TASK-SP-007 | Slash command specification | 5 | 3 | SP-003, SP-004, SP-005 |
| TASK-SP-008 | Integration & seam tests | 7 | 4 | SP-003, SP-005, SP-006 |

## Execution Waves

```
Wave 1: [TASK-SP-001, TASK-SP-002]           ← Parallel: entities + gating
Wave 2: [TASK-SP-003, TASK-SP-004, TASK-SP-005] ← Parallel: persistence + questions + writer
Wave 3: [TASK-SP-006, TASK-SP-007]           ← Parallel: CLI + slash command
Wave 4: [TASK-SP-008]                        ← Seam tests (validates all integration points)
```

## Key Architecture Decisions

1. **Entities use dataclasses** (not Pydantic) — internal state containers
2. **Graphiti groups reuse existing** `project_architecture` and `project_decisions` — no registration needed
3. **Upsert with stable entity_id** — prevents duplicates on re-run
4. **Jinja2 templates** — consistent with existing template in `installer/core/`
5. **Methodology-gated questions** — DDD fields only when DDD selected
6. **Seam tests as dedicated task** — catches integration errors before they ship
