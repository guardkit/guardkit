# FEAT-AQG: AutoBuild Quality Gaps — Implementation Guide

## Overview

Fixes systemic AutoBuild quality gaps identified across TASK-REV-6F11, TASK-REV-422A, and TASK-REV-7972.

## Wave Breakdown

### Wave 1: Core Quality Gate Fixes (2 tasks, parallel)

| Task | Title | Complexity | Mode | Dependencies |
|------|-------|-----------|------|-------------|
| AQG-001 | Coach criteria verification | 6 | task-work | None |
| AQG-002 | Zero-test anomaly blocking | 4 | task-work | None |

These are independent — AQG-001 adds structured criteria output to Coach, AQG-002 makes zero-test detection configurable. No file conflicts.

### Wave 2: Low-Priority Fixes (2 tasks, parallel)

| Task | Title | Complexity | Mode | Dependencies |
|------|-------|-----------|------|-------------|
| AQG-003 | Feature ID turn state | 2 | task-work | None |
| AQG-004 | Event loop cleanup | 3 | task-work | None |

Independent tasks touching different files. AQG-003 modifies autobuild.py + feature_orchestrator.py. AQG-004 modifies graphiti_client.py.

## Key Files

| File | Tasks | Notes |
|------|-------|-------|
| `guardkit/orchestrator/quality_gates/coach_validator.py` | AQG-001, AQG-002 | Main validation logic |
| `guardkit/orchestrator/autobuild.py` | AQG-001 (verify), AQG-003 | Criteria display + feature ID |
| `guardkit/orchestrator/feature_orchestrator.py` | AQG-003 | Pass feature ID |
| `guardkit/knowledge/graphiti_client.py` | AQG-004 | Event loop cleanup |

## Execution Strategy

```
Wave 1: AQG-001 + AQG-002 (parallel, Conductor recommended)
Wave 2: AQG-003 + AQG-004 (parallel, Conductor recommended)
```

Total estimated: 4 tasks, 2 waves.
