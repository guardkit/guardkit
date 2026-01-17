# Pre-Loop Documentation Enhancement

## Problem Statement

The pre-loop architecture in AutoBuild has unclear documentation, leading to user confusion about:
- Why pre-loop is disabled by default for feature-build
- When to enable pre-loop manually
- How feature-plan tasks differ from standalone tasks

## Solution Approach

Enhance documentation to clarify the pre-loop behavior without code changes. The current implementation is architecturally sound; what's needed is better user guidance.

## Review Reference

- **Review Task**: TASK-REV-PL01
- **Review Report**: [.claude/reviews/TASK-REV-PL01-review-report.md](../../../.claude/reviews/TASK-REV-PL01-review-report.md)
- **Recommendation**: Option B (Accept Minimal Pre-Loop + Enhanced Documentation)

## Subtasks

| Task ID | Title | Method | Wave |
|---------|-------|--------|------|
| TASK-PLD-001 | Update CLAUDE.md Pre-Loop Section | direct | 1 |
| TASK-PLD-002 | Add Decision Tree to Workflow Docs | direct | 1 |
| TASK-PLD-003 | Update feature-build CLI Help Text | task-work | 2 |

## Execution Strategy

**Wave 1** (Parallel - Documentation):
- TASK-PLD-001: Update main CLAUDE.md
- TASK-PLD-002: Add decision tree to guardkit-workflow.md

**Wave 2** (Sequential - Depends on Wave 1):
- TASK-PLD-003: Update CLI help text to reference new docs

## Success Criteria

- [ ] CLAUDE.md Pre-Loop section clearly explains when pre-loop runs
- [ ] Decision tree helps users choose between pre-loop enabled/disabled
- [ ] CLI help text points to documentation for pre-loop behavior
- [ ] No code changes required (documentation only)
