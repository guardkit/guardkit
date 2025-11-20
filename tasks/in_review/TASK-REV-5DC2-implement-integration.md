---
id: TASK-REV-5DC2
title: Implement /task-review integration with task-create and documentation (Phase 4)
status: in_review
created: 2025-01-20T15:00:00Z
updated: 2025-01-20T16:00:00Z
priority: medium
tags: [task-review, integration, phase-4, documentation]
complexity: 4
estimated_effort: 2-4 hours
related_proposal: docs/proposals/task-review-command-proposal.md
parent_initiative: task-review-command-implementation
phase: 4
dependencies: [TASK-REV-A4AB, TASK-REV-3248, TASK-REV-2367]
---

# Task: Implement /task-review Integration and Documentation (Phase 4)

## Context

This is **Phase 4 of 5** for implementing the `/task-review` command.

**Prerequisites**:
- TASK-REV-A4AB (Phase 1 - Core Command) must be complete
- TASK-REV-3248 (Phase 2 - Review Modes) must be complete
- TASK-REV-2367 (Phase 3 - Report Generation) must be complete

**Goal**: Integrate `/task-review` with `/task-create` for automatic review task detection and update all documentation.

## Description

Connect the `/task-review` command to the existing workflow by enhancing `/task-create` to detect review tasks and updating all documentation to reflect the new command.

### Deliverables

1. **Task Creation Hints** - Enhance `/task-create` to suggest `/task-review` for review tasks
2. **Documentation Updates** - Update CLAUDE.md, workflow guides, and README
3. **State Management** - Ensure `REVIEW_COMPLETE` state is fully integrated
4. **Command Discovery** - Make `/task-review` discoverable via `/help`

## Acceptance Criteria

### Task Creation Integration
- [ ] `/task-create` detects review task indicators:
  - `task_type: review` in command args
  - `decision_required: true` flag
  - Tags: architecture-review, code-review, decision-point
  - Title contains: "Review", "Analyze", "Evaluate", "Assessment"
- [ ] When detected, displays suggestion:
  ```
  Detected task type: REVIEW (analysis/decision-making)
  Suggested command: /task-review (not /task-work)

  Create task? [Y/n]:
  ```
- [ ] Suggestion is informational only (doesn't block creation)
- [ ] Task metadata includes `task_type: review` when appropriate

### Documentation Updates
- [ ] CLAUDE.md updated with:
  - `/task-review` command reference
  - When to use task-review vs task-work
  - Review workflow phases explained
  - Example review task scenarios
- [ ] New workflow guide: `docs/workflows/task-review-workflow.md`
- [ ] Updated `docs/guides/taskwright-workflow.md` with review tasks
- [ ] README updated with task-review mention

### State Management
- [ ] `REVIEW_COMPLETE` state fully integrated in:
  - State manager
  - Task status command
  - Task completion workflows
- [ ] State transition diagram updated
- [ ] Directory structure includes `tasks/review_complete/`

### Command Discovery
- [ ] `/help` command lists `/task-review`
- [ ] Command description clearly differentiates from `/task-work`
- [ ] Examples provided for common review scenarios

## Implementation Notes

### Task Creation Detection Logic

Add to `installer/global/commands/lib/task_create_orchestrator.py`:

```python
def detect_review_task(title: str, args: Dict) -> bool:
    """
    Detect if task is likely a review/analysis task.

    Args:
        title: Task title
        args: Command arguments (task_type, tags, etc.)

    Returns:
        True if task appears to be review task
    """
    # Explicit task_type field
    if args.get("task_type") == "review":
        return True

    # decision_required flag
    if args.get("decision_required"):
        return True

    # Review-related tags
    review_tags = {"architecture-review", "code-review", "decision-point", "assessment"}
    task_tags = set(args.get("tags", []))
    if review_tags & task_tags:
        return True

    # Title keywords
    title_lower = title.lower()
    review_keywords = ["review", "analyze", "evaluate", "assess", "audit", "investigation"]
    if any(keyword in title_lower for keyword in review_keywords):
        return True

    return False

def suggest_review_command(title: str):
    """Display suggestion to use /task-review instead of /task-work."""
    print("\n" + "="*67)
    print("REVIEW TASK DETECTED")
    print("="*67)
    print(f"\nTask: {title}")
    print("\nThis appears to be a review/analysis task.")
    print("\nSuggested workflow:")
    print("  1. Create task: /task-create (current command)")
    print("  2. Execute review: /task-review TASK-XXX")
    print("  3. (Optional) Implement findings: /task-work TASK-YYY")
    print("\nNote: /task-work is for implementation, /task-review is for analysis.")
    print("="*67 + "\n")
```

### CLAUDE.md Updates

Add new section after "Core Workflow":

```markdown
## Review vs Implementation Workflows

Taskwright supports two distinct workflows:

### Implementation Workflow (/task-work)
Use when **building** features, fixing bugs, or creating code:
```bash
/task-create "Add user authentication"
/task-work TASK-001  # Implements, tests, reviews code
/task-complete TASK-001
```

### Review Workflow (/task-review)
Use when **analyzing** architecture, making decisions, or assessing quality:
```bash
/task-create "Architectural review of authentication system" task_type:review
/task-review TASK-002  # Analyzes code, generates report, recommends decision
# If implementing findings: /task-work TASK-003
/task-complete TASK-002
```

### When to Use Each

| Scenario | Command |
|----------|---------|
| "Implement feature X" | `/task-work` |
| "Should we implement X?" | `/task-review` |
| "Fix bug in X" | `/task-work` |
| "Review architecture of X" | `/task-review` |
| "Add tests for X" | `/task-work` |
| "Assess technical debt in X" | `/task-review` |
| "Refactor X" | `/task-work` |
| "Security audit of X" | `/task-review` |
```

### New Workflow Guide

Create `docs/workflows/task-review-workflow.md`:

```markdown
# Task Review Workflow

## Overview

The `/task-review` command provides structured analysis and decision-making workflows for review tasks.

## Workflow Steps

1. **Create Review Task**
   ```bash
   /task-create "Architectural review of authentication" task_type:review
   ```

2. **Execute Review**
   ```bash
   /task-review TASK-001 --mode=architectural --depth=comprehensive
   ```

3. **Review Phases** (automatic):
   - Phase 1: Load review context
   - Phase 2: Execute analysis (invoke specialized agents)
   - Phase 3: Synthesize recommendations
   - Phase 4: Generate report
   - Phase 5: Human decision checkpoint

4. **Make Decision** (interactive):
   - [A]ccept - Approve findings, move to IN_REVIEW
   - [R]evise - Request deeper analysis
   - [I]mplement - Create implementation task
   - [C]ancel - Discard review

5. **Optional Implementation** (if [I]mplement chosen):
   ```bash
   /task-work TASK-002  # Implement recommended changes
   ```

## Review Modes

... (document all 5 modes)
```

## Test Requirements

### Integration Tests

File: `tests/integration/test_task_review_integration.py`

```python
def test_task_create_detects_review_task():
    """Test that task-create suggests task-review for review tasks."""
    # Create review task
    output = run_command('/task-create "Review authentication architecture" decision_required:true')

    assert "REVIEW TASK DETECTED" in output
    assert "/task-review" in output

def test_complete_review_workflow():
    """Test end-to-end review workflow."""
    # Create review task
    task_id = create_task("Architectural review", task_type="review")

    # Execute review
    result = execute_review(task_id, mode="architectural")

    # Verify state
    task = load_task(task_id)
    assert task["status"] == "review_complete"

    # Accept review
    accept_review(task_id)

    # Verify final state
    task = load_task(task_id)
    assert task["status"] == "in_review"
```

## Related Tasks

- **TASK-REV-A4AB**: Core command (prerequisite)
- **TASK-REV-3248**: Review modes (prerequisite)
- **TASK-REV-2367**: Report generation (prerequisite)
- **TASK-REV-4DE8**: Testing (Phase 5) - Depends on this task

## Success Criteria

- [ ] `/task-create` suggests `/task-review` appropriately
- [ ] CLAUDE.md fully documents task-review
- [ ] Workflow guide created and comprehensive
- [ ] State management fully integrated
- [ ] `/help` includes task-review
- [ ] All documentation updated
- [ ] Integration tests pass

---

**Note**: This task focuses on integration and discoverability. Phase 5 (Testing) will add comprehensive test coverage.
