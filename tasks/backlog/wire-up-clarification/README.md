# Feature: Wire Up Clarification Python Orchestrators

> **STATUS: SUPERSEDED**
>
> This feature folder has been superseded by `unified-clarification-subagent/`.
>
> **Reason**: TASK-REV-CLQ3 decided to use a unified subagent pattern instead of orchestrators. The subagent pattern eliminates handoff complexity and provides consistent architecture across all commands.
>
> See: [unified-clarification-subagent/](../unified-clarification-subagent/)

---

## Original Problem Statement (Superseded)

The clarifying questions feature has been fully implemented (~8,740 lines of code across 17 tasks) but is **dead code** because slash commands don't invoke the Python orchestrators.

**Root Cause**: Slash commands like `/feature-plan` and `/task-review` are markdown files that Claude reads as instructions. These instructions tell Claude to manually orchestrate the workflow, but they never instruct Claude to run the Python orchestrators that contain the clarification logic.

## Solution Approach

Modify the markdown command files to invoke Python orchestrators instead of describing a manual workflow. The Python code is ready; it just needs to be called.

**Key Changes**:
1. Update `/feature-plan.md` to call `python3 ~/.agentecflow/bin/feature-plan-orchestrator`
2. Update `/task-review.md` to call `python3 ~/.agentecflow/bin/task-review-orchestrator`
3. Create symlinks during installation
4. Add end-to-end smoke test

## Subtasks

| Task | Description | Mode | Priority |
|------|-------------|------|----------|
| TASK-WC-001 | Update feature-plan.md execution instructions | direct | high |
| TASK-WC-002 | Update task-review.md execution instructions | direct | high |
| TASK-WC-003 | Add orchestrator symlinks to installer | direct | high |
| TASK-WC-004 | Add end-to-end smoke test | task-work | medium |

## Execution Strategy

**Wave 1** (parallel - no dependencies):
- TASK-WC-001: Update feature-plan.md
- TASK-WC-002: Update task-review.md
- TASK-WC-003: Add installer symlinks

**Wave 2** (depends on Wave 1):
- TASK-WC-004: Smoke test (validates all Wave 1 changes work together)

## Expected Outcome

After implementation:
- Clarifying questions will be displayed for ambiguous inputs
- ~15% reduction in incorrect assumptions
- ~8,740 lines of existing code becomes functional
- 40-60 hours of previous work becomes valuable

## Related

- **Review Task**: TASK-REV-CLQ2
- **Review Report**: [.claude/reviews/TASK-REV-CLQ2-review-report.md](../../../.claude/reviews/TASK-REV-CLQ2-review-report.md)
- **Original Implementation**: TASK-CLQ-001 through TASK-CLQ-012, TASK-CLQ-FIX-001 through TASK-CLQ-FIX-006

## Generated

- Date: 2025-12-13
- Method: `/task-review TASK-REV-CLQ2` → [I]mplement
- Estimated Effort: 4-8 hours total
