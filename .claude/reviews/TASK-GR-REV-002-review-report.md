# Review Report: TASK-GR-REV-002

## Executive Summary

**Decision**: Remove `manual` implementation mode entirely.

The `manual` mode is redundant with GuardKit's complexity-based workflow adaptation. The `/task-work` command with complexity gating (0-10 scale) and `--micro`/`--intensity` flags provides sufficient workflow flexibility for all task types, including documentation and research tasks.

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Standard
- **Duration**: ~30 minutes
- **Reviewer**: Claude (architectural-reviewer)

---

## Analysis Summary

### Q1: What scenarios genuinely require human-only execution?

Very few:
- Third-party UI configuration (OAuth app registration)
- Physical actions (printing, hardware)
- Legal/compliance approvals

Most "manual" tasks (research, documentation, migrations, bulk operations) can be handled by AI with proper tooling.

### Q2: Can AI handle research/documentation tasks?

**Yes.** The failed TASK-GR-PRE-003-A ("Research graphiti-core upsert") could be handled by AI using `Read`, `WebFetch`, and `Write` tools.

### Q3: Should `/feature-build` skip manual tasks or fail on them?

**Neither** - remove `manual` mode entirely. The complexity system already handles variable-intensity workflows.

### Q4: Migration path?

Convert existing `manual` tasks to `task-work`. No deprecation warning needed (single user).

---

## Decision

**Remove `manual` implementation mode entirely.**

### Rationale

1. **Redundancy**: Complexity gating (0-10) already adapts workflow intensity
2. **Flags exist**: `--micro` and `--intensity=minimal` handle trivial tasks
3. **AutoBuild incompatibility**: `manual` cannot be executed autonomously
4. **No clear criteria**: Unclear what makes a task "manual" vs just complex

### Mode System After Change

| Mode | Use Case |
|------|----------|
| `task-work` | All tasks (default) - complexity gating adapts workflow |
| `direct` | Lightweight SDK, no plan needed (simple file changes) |

---

## Implementation Tasks Created

| Task ID | Title | Wave |
|---------|-------|------|
| TASK-RMM-001 | Remove manual mode from implementation_mode_analyzer | 1 |
| TASK-RMM-002 | Clean up manual references in agent_invoker | 1 |
| TASK-RMM-003 | Convert existing manual tasks to task-work | 2 |
| TASK-RMM-004 | Update documentation for two-mode system | 2 |

**Location**: `tasks/backlog/remove-manual-mode/`

---

## References

- TASK-GR-REV-001: AutoBuild failure analysis (parent review)
- FEAT-GR-MVP: Feature that exposed the issue
