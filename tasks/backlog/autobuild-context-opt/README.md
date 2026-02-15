# AutoBuild Context Payload Optimization

**Feature ID**: FEAT-ACO
**Parent Review**: TASK-REV-A781
**Priority**: High
**Total Tasks**: 6
**Estimated Complexity**: 7/10 (aggregate)

## Problem

AutoBuild SDK sessions load ~987KB of context per session (~1,974KB across 2 sessions per task), resulting in ~1,800s preamble before first meaningful code output. Only ~92KB is actually needed.

## Solution

Replace `/task-work` skill invocation with focused autobuild-specific prompts and switch to `setting_sources=["project"]` only.

## Tasks

| Task | Title | Complexity | Wave | Status |
|------|-------|-----------|------|--------|
| TASK-ACO-001 | Extract AutoBuild execution protocol | 4 | 1 | pending |
| TASK-ACO-002 | Build implementation prompt builder | 6 | 2 | pending |
| TASK-ACO-003 | Build design prompt builder | 6 | 2 | pending |
| TASK-ACO-004 | Expand direct mode auto-detection | 4 | 2 | pending |
| TASK-ACO-005 | Unit tests for prompt builders | 5 | 3 | pending |
| TASK-ACO-006 | Integration validation | 5 | 4 | pending |

## Execution Order

```
Wave 1: [TASK-ACO-001]                          ← Foundation
Wave 2: [TASK-ACO-002, TASK-ACO-003, TASK-ACO-004]  ← Parallel
Wave 3: [TASK-ACO-005]                          ← Tests
Wave 4: [TASK-ACO-006]                          ← Validation
```

## Quick Start

```bash
# Start with Wave 1
/task-work TASK-ACO-001

# After Wave 1 completes, Wave 2 tasks can run in parallel
/feature-build FEAT-ACO
```

## References

- [Feature Spec](../../../docs/features/FEAT-AUTOBUILD-CONTEXT-OPT-spec.md)
- [Review Report](../../../.claude/reviews/TASK-REV-A781-review-report.md)
- [Implementation Guide](IMPLEMENTATION-GUIDE.md)
