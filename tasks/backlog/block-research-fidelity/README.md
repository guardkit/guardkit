# Block Research Fidelity Improvements

**Feature ID**: FEAT-BRF
**Status**: Backlog
**Parent Review**: [TASK-REV-BLOC](.claude/reviews/TASK-REV-BLOC-review-report.md)

## Problem Statement

The TASK-REV-BLOC architectural review identified that GuardKit's AutoBuild implementation, while faithful to Block AI's "Adversarial Cooperation in Code Synthesis" research in its core design, has gaps in two key principles:

1. **Anchoring Prevention** (65/100): Implementation plan and cumulative history can anchor Player behavior to early assumptions
2. **Context Pollution** (70/100): Worktree state accumulates across turns without isolation mechanisms

## Solution Approach

This feature implements 5 improvements to address the identified gaps:

### Critical (Wave 1)
1. **Fresh Perspective Reset** - Periodically reset Player context to prevent anchoring
2. **Worktree Checkpoints** - Add checkpoint/rollback mechanism for context isolation

### Important (Wave 2)
3. **Raise Arch Threshold** - Increase quality gate from 60 to 75
4. **Document Honesty Context** - Improve Coach agent documentation

### Nice to Have (Wave 3)
5. **Ablation Mode** - Testing mode to validate Block research findings

## Subtask Summary

| ID | Title | Priority | Mode | Wave |
|----|-------|----------|------|------|
| [TASK-BRF-001](TASK-BRF-001-fresh-perspective-reset.md) | Fresh Perspective Reset | High | task-work | 1 |
| [TASK-BRF-002](TASK-BRF-002-worktree-checkpoint-rollback.md) | Worktree Checkpoint/Rollback | High | task-work | 1 |
| [TASK-BRF-003](TASK-BRF-003-raise-arch-threshold.md) | Raise Arch Threshold | Medium | direct | 2 |
| [TASK-BRF-004](TASK-BRF-004-document-honesty-context.md) | Document Honesty Context | Medium | direct | 2 |
| [TASK-BRF-005](TASK-BRF-005-ablation-mode.md) | Ablation Mode | Low | task-work | 3 |

## Expected Outcomes

After implementation:

| Principle | Before | After |
|-----------|--------|-------|
| Anchoring Prevention | 65/100 | ≥85/100 |
| Context Pollution | 70/100 | ≥85/100 |
| Completion Criteria | 85/100 | ≥90/100 |
| **Overall Fidelity** | 78/100 | ≥85/100 |

## Quick Start

```bash
# Wave 1 - Critical fixes (parallel with Conductor)
conductor spawn block-research-fidelity-wave1-1
conductor spawn block-research-fidelity-wave1-2

# In each workspace:
/task-work TASK-BRF-001 --mode=tdd
/task-work TASK-BRF-002 --mode=tdd

# Wave 2 - Configuration changes
# Can be done directly or via task-work
/task-work TASK-BRF-003
/task-work TASK-BRF-004

# Wave 3 - Optional enhancement
/task-work TASK-BRF-005
```

## Related Documents

- [Implementation Guide](IMPLEMENTATION-GUIDE.md) - Detailed execution strategy
- [Review Report](.claude/reviews/TASK-REV-BLOC-review-report.md) - Original gap analysis
- [AutoBuild Architecture](docs/deep-dives/autobuild-architecture.md) - System documentation

## References

- Block AI Research: "Adversarial Cooperation in Code Synthesis"
- Hegelion: Open-source reference implementation
