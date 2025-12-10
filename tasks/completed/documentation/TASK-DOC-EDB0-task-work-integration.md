---
id: TASK-DOC-EDB0
title: Add task-work integration section to task-review.md
status: completed
created: 2025-11-27T02:00:00Z
updated: 2025-11-27T08:15:00Z
completed_at: 2025-11-27T08:15:00Z
priority: high
tags: [documentation, task-review, task-work, workflow]
complexity: 3
related_to: [TASK-DOC-F3BA]
completion_metrics:
  implementation_commit: 3b0f2a2a3b6b1f6af80dd608fc4d39aa428c30f0
  merge_commit: 17d9a545b2308e1eac740c9cdd9b971484e24774
  worktree_branch: RichWoollcott/task-work-integration
  lines_added: 158
  files_modified: 2
---

# Task: Add /task-work Integration Section to task-review.md

## Context

Review task TASK-DOC-F3BA identified that task-review.md doesn't explain how review tasks integrate with implementation tasks via `/task-work`, leaving users unclear on the complete review → implementation workflow.

The integration is critical because:
1. Review tasks identify what needs to be done
2. [I]mplement decision creates implementation tasks automatically
3. Implementation tasks are executed via `/task-work`
4. Verification reviews close the loop

## Objective

Add a comprehensive "Integration with /task-work" section to task-review.md showing the complete review → implementation → verification cycle.

## Scope

### Files to Update

1. **installer/core/commands/task-review.md**:
   - Add new section "Integration with /task-work"
   - Document review → implementation workflow with examples
   - Explain decision checkpoint behavior ([I]mplement creates new task)
   - Show complete workflow from review to verification
   - Cross-reference to CLAUDE.md Review Workflow section

2. **installer/core/commands/task-create.md** (optional):
   - Add cross-reference to task-review integration

## Acceptance Criteria

- [ ] New section "Integration with /task-work" added to task-review.md
- [ ] Review → Implementation workflow documented with step-by-step examples
- [ ] Decision checkpoint behavior explained ([I]mplement option)
- [ ] Complete workflow example showing review → implement → verify cycle
- [ ] Task state transitions documented (REVIEW_COMPLETE → backlog → IN_PROGRESS)
- [ ] Cross-reference to CLAUDE.md Review Workflow section added
- [ ] Code examples use realistic task IDs and scenarios
- [ ] Consistent formatting with existing sections

## Implementation Notes

**Suggested Content Structure**:

```markdown
## Integration with /task-work

The `/task-review` command integrates seamlessly with `/task-work` to support a complete review → implementation → verification workflow.

### Review → Implementation Workflow

**Step 1: Create Review Task**
```bash
/task-create "Review authentication architecture" task_type:review
# Output: Created TASK-REV-A3F2
```

**Step 2: Execute Review**
```bash
/task-review TASK-REV-A3F2 --mode=architectural --depth=standard
# Review runs, generates report at .claude/reviews/TASK-REV-A3F2-review-report.md
# Task status: BACKLOG → IN_PROGRESS → REVIEW_COMPLETE
```

**Step 3: Decision Checkpoint**

After review completion, you'll see:

```
=========================================================================
REVIEW COMPLETE: TASK-REV-A3F2
=========================================================================

Review Results:
  Architecture Score: 72/100
  Findings: 8
  Recommendations: 5

Key Findings:
  - Authentication uses outdated session management
  - Password hashing needs upgrade to Argon2
  - Missing rate limiting on login endpoint

Recommendations:
  1. Migrate to JWT-based authentication
  2. Implement Argon2 password hashing
  3. Add rate limiting middleware
  4. Update session management logic
  5. Add integration tests for auth flow

Decision Options:
  [A]ccept - Archive review (no implementation needed)
  [R]evise - Request deeper analysis
  [I]mplement - Create implementation task based on recommendations
  [C]ancel - Discard review

Your choice:
```

**Step 4a: Choose [I]mplement**

System automatically creates implementation task:

```bash
✅ Created implementation task: TASK-IMP-B4D1

Task Details:
  Title: Implement findings from TASK-REV-A3F2
  Status: backlog
  Priority: high (inherited from review)
  Related Tasks: [TASK-REV-A3F2]

Implementation Scope:
  - Migrate to JWT-based authentication
  - Implement Argon2 password hashing
  - Add rate limiting middleware
  - Update session management logic
  - Add integration tests for auth flow

Review Report: .claude/reviews/TASK-REV-A3F2-review-report.md

Next Steps:
  /task-work TASK-IMP-B4D1
```

**Step 5: Implement Changes**
```bash
/task-work TASK-IMP-B4D1
# Executes implementation with all quality gates:
# - Phase 2: Planning
# - Phase 2.5: Architectural Review
# - Phase 3: Implementation
# - Phase 4: Testing
# - Phase 4.5: Test Enforcement
# - Phase 5: Code Review
```

**Step 6: Verification Review (Optional)**

After implementation, create verification review:

```bash
/task-create "Verify authentication refactoring from TASK-IMP-B4D1" task_type:review
# Output: Created TASK-VER-C5E3

/task-review TASK-VER-C5E3 --mode=code-quality --depth=quick
# Quick verification that changes meet original recommendations
```

### Task State Flow

```
Review Task:
  BACKLOG → IN_PROGRESS → REVIEW_COMPLETE → COMPLETED

Implementation Task (created from [I]mplement):
  BACKLOG → IN_PROGRESS → IN_REVIEW → COMPLETED

Verification Task (optional):
  BACKLOG → IN_PROGRESS → REVIEW_COMPLETE → COMPLETED
```

### Real-World Example: Security Audit

```bash
# 1. Security audit review
/task-create "Security audit of payment processing" task_type:review
/task-review TASK-SEC-D7E2 --mode=security --depth=comprehensive

# 2. Review identifies 12 vulnerabilities
# Decision: [I]mplement

# 3. System creates implementation task
# TASK-IMP-E8F3: Fix security vulnerabilities from TASK-SEC-D7E2

# 4. Implement fixes
/task-work TASK-IMP-E8F3

# 5. Verification review
/task-create "Verify security fixes from TASK-IMP-E8F3" task_type:review
/task-review TASK-VER-F9G4 --mode=security --depth=standard

# 6. Verification passes, close all tasks
/task-complete TASK-VER-F9G4
/task-complete TASK-IMP-E8F3
/task-complete TASK-SEC-D7E2
```

### Benefits of Integration

1. **Traceability**: Implementation tasks linked to review findings
2. **Context Preservation**: Review report available during implementation
3. **Consistent Quality**: Implementation goes through all quality gates
4. **Verification Loop**: Optional verification review closes the cycle
5. **Automated Task Creation**: [I]mplement option eliminates manual task creation

### See Also

- [CLAUDE.md Review Workflow](../../CLAUDE.md#review-workflow-analysisdecision-tasks)
- [Task Review Workflow Guide](../../docs/workflows/task-review-workflow.md)
- [task-create.md](./task-create.md#review-task-detection)
```

**Placement**: Add this section after "Review Modes (Detailed)" and before "Task States and Transitions"

## Source

**Review Report**: [TASK-DOC-F3BA Review Report](../../../.claude/task-plans/TASK-DOC-F3BA-review-report.md)
**Priority**: P2 (High)
**Estimated Effort**: 2-3 hours

## Method

**Claude Code Direct** - Documentation update, no testing needed
