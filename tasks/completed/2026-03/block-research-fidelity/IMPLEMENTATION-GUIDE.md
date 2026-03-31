# Implementation Guide: Block Research Fidelity Improvements

## Feature Overview

**Feature ID**: FEAT-BRF
**Parent Review**: TASK-REV-BLOC
**Created**: 2026-01-24

This feature addresses gaps identified in the Block Research Fidelity Review, improving GuardKit's adherence to Block AI's "Adversarial Cooperation in Code Synthesis" research principles.

## Gap Summary

| Gap | Principle | Current Score | Target |
|-----|-----------|--------------|--------|
| Anchoring Prevention | Fresh perspective each turn | 65/100 | 85/100 |
| Context Pollution | Isolated context windows | 70/100 | 85/100 |
| Quality Threshold | Objective completion criteria | 85/100 | 90/100 |

## Wave Breakdown

### Wave 1: Critical Gap Fixes (Parallel)

These tasks address the two **major** gaps and can be implemented in parallel:

| Task ID | Title | Mode | Workspace | Complexity |
|---------|-------|------|-----------|------------|
| TASK-BRF-001 | Fresh Perspective Reset | task-work | wave1-1 | 6 |
| TASK-BRF-002 | Worktree Checkpoint/Rollback | task-work | wave1-2 | 7 |

**Execution**:
```bash
# Using Conductor for parallel execution
conductor spawn block-research-fidelity-wave1-1
conductor spawn block-research-fidelity-wave1-2

# In wave1-1 workspace:
/task-work TASK-BRF-001 --mode=tdd

# In wave1-2 workspace:
/task-work TASK-BRF-002 --mode=tdd
```

**Dependencies**: None - these are independent implementations.

**Estimated Effort**: 8-12 hours combined (4-6 hours each)

---

### Wave 2: Configuration and Documentation (Parallel)

These tasks are simpler changes that can be done in parallel after Wave 1:

| Task ID | Title | Mode | Workspace | Complexity |
|---------|-------|------|-----------|------------|
| TASK-BRF-003 | Raise Arch Threshold | direct | wave2-1 | 2 |
| TASK-BRF-004 | Document Honesty Context | direct | wave2-2 | 2 |

**Execution**:
```bash
# Can be done directly (no task-work needed)
# Or using Conductor:
conductor spawn block-research-fidelity-wave2-1
conductor spawn block-research-fidelity-wave2-2
```

**Dependencies**: Wave 1 tasks should be complete first (configuration changes reference new features).

**Estimated Effort**: 2-3 hours combined

---

### Wave 3: Nice-to-Have (Sequential)

Lower priority enhancement:

| Task ID | Title | Mode | Workspace | Complexity |
|---------|-------|------|-----------|------------|
| TASK-BRF-005 | Ablation Mode | task-work | wave3-1 | 4 |

**Execution**:
```bash
/task-work TASK-BRF-005 --mode=standard
```

**Dependencies**: Waves 1-2 complete.

**Estimated Effort**: 3-4 hours

---

## Execution Strategy

### Recommended Order

```
Wave 1 (Parallel)     Wave 2 (Parallel)     Wave 3 (Sequential)
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│ TASK-BRF-001    │   │ TASK-BRF-003    │   │ TASK-BRF-005    │
│ (perspective)   │   │ (threshold)     │   │ (ablation)      │
├─────────────────┤   ├─────────────────┤   └─────────────────┘
│ TASK-BRF-002    │   │ TASK-BRF-004    │
│ (checkpoint)    │   │ (docs)          │
└────────┬────────┘   └────────┬────────┘
         │                     │
         └──────────┬──────────┘
                    ↓
              Wave 3 (after 1 & 2)
```

### Total Estimated Effort

- Wave 1: 8-12 hours
- Wave 2: 2-3 hours
- Wave 3: 3-4 hours
- **Total**: 13-19 hours

### Risk Assessment

| Task | Risk Level | Mitigation |
|------|-----------|------------|
| BRF-001 | Medium | Well-defined scope, clear implementation path |
| BRF-002 | Medium-High | Git operations need careful testing |
| BRF-003 | Low | Simple configuration change |
| BRF-004 | Low | Documentation only |
| BRF-005 | Low | Isolated feature, no production impact |

## Quality Gates

All tasks must pass standard quality gates:

- [ ] 100% tests passing
- [ ] ≥80% line coverage
- [ ] ≥75% branch coverage
- [ ] Architectural review ≥75 (per TASK-BRF-003)
- [ ] Plan audit: 0 violations

## Integration Points

### Modified Files

| Component | Files |
|-----------|-------|
| Orchestrator | `guardkit/orchestrator/autobuild.py` |
| CLI | `guardkit/cli/autobuild.py` |
| Quality Gates | `guardkit/orchestrator/quality_gates/coach_validator.py` |
| New Module | `guardkit/orchestrator/worktree_checkpoints.py` |
| Agent Defs | `.claude/agents/autobuild-coach.md` |
| Docs | `docs/guides/autobuild-workflow.md` |

### Testing Strategy

1. **Unit Tests**: Each task includes unit tests
2. **Integration Tests**: Wave 1 tasks need integration tests
3. **Ablation Comparison**: Wave 3 includes comparison tests

## Success Criteria

After implementation:

| Principle | Target Score |
|-----------|-------------|
| Anchoring Prevention | ≥85/100 |
| Context Pollution | ≥85/100 |
| Completion Criteria | ≥90/100 |
| **Overall Fidelity** | ≥85/100 |

## Notes

- Wave 1 tasks are the highest priority (address major gaps)
- Wave 2 tasks improve quality and documentation
- Wave 3 is optional but valuable for validating Block research findings
