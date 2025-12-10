---
id: TASK-REV-A4AB
title: Implement /task-review core command and orchestrator (Phase 1)
status: in_review
created: 2025-01-20T15:00:00Z
updated: 2025-11-20T12:36:00Z
completed_at: 2025-11-20T12:36:00Z
priority: high
tags: [task-review, command, phase-1, architecture]
complexity: 6
estimated_effort: 4-8 hours
actual_effort: 2 hours
related_proposal: docs/proposals/task-review-command-proposal.md
parent_initiative: task-review-command-implementation
phase: 1
dependencies: []
test_results:
  status: passing
  unit_tests: 20
  integration_tests: 9
  total_tests: 29
  all_passing: true
---

# Task: Implement /task-review Core Command and Orchestrator (Phase 1)

## Context

This is **Phase 1 of 5** for implementing the `/task-review` command based on the proposal in `docs/proposals/task-review-command-proposal.md`.

**Goal**: Create the foundation for the `/task-review` command - the command specification, orchestrator, and core workflow phases.

**Parent Initiative**: Complete `/task-review` command implementation (5 phases total)

## Description

Implement the core infrastructure for the `/task-review` command, which provides structured analysis and decision-making workflows separate from `/task-work` implementation workflows.

### Deliverables

1. **Command Specification** (`installer/core/commands/task-review.md`)
   - Command syntax documentation
   - Workflow phases (1-5) specification
   - Flag documentation (--mode, --depth, --output)
   - Execution protocol
   - Integration with task states

2. **Core Orchestrator** (`installer/core/commands/lib/task_review_orchestrator.py`)
   - `execute_task_review()` - Main entry point
   - `load_review_context()` - Phase 1 implementation
   - `execute_review_analysis()` - Phase 2 skeleton
   - `synthesize_recommendations()` - Phase 3 skeleton
   - `generate_review_report()` - Phase 4 skeleton
   - `present_decision_checkpoint()` - Phase 5 skeleton
   - `handle_review_decision()` - Decision routing

3. **State Management**
   - Add `REVIEW_COMPLETE` state support
   - Implement state transitions (BACKLOG → IN_PROGRESS → REVIEW_COMPLETE → IN_REVIEW)
   - Update task state manager

4. **Task Metadata Schema**
   - Add `task_type` field (review, implementation, research, docs)
   - Add `review_mode` field (architectural, code-quality, decision, technical-debt, security)
   - Add `review_depth` field (quick, standard, comprehensive)
   - Add `review_results` section for completed reviews

## Acceptance Criteria

### Command Specification
- [ ] `task-review.md` exists with complete command documentation
- [ ] All flags documented (--mode, --depth, --output)
- [ ] All 5 workflow phases specified
- [ ] Execution protocol defined (similar to task-work)
- [ ] Integration points with task-work documented

### Core Orchestrator
- [ ] `task_review_orchestrator.py` exists
- [ ] `execute_task_review()` function implemented with proper argument parsing
- [ ] Phase 1 (load_review_context) fully implemented
- [ ] Phases 2-5 have skeleton implementations (minimal but callable)
- [ ] All functions have docstrings and type hints
- [ ] Error handling for missing task files
- [ ] Validation for review_mode and review_depth values

### State Management
- [ ] `REVIEW_COMPLETE` state added to valid states enum
- [ ] State transition logic updated to handle review workflow
- [ ] Task files can be moved to/from review_complete directory
- [ ] Metadata updated correctly during state transitions

### Task Metadata
- [ ] `task_type` field recognized in task frontmatter
- [ ] `review_mode`, `review_depth` fields recognized
- [ ] `review_results` section schema defined
- [ ] Backward compatibility with existing tasks (no task_type field)

### Basic Workflow
- [ ] Can invoke `/task-review TASK-XXX` and command is recognized
- [ ] Command loads task context correctly
- [ ] Command accepts --mode flag (validates against allowed values)
- [ ] Command accepts --depth flag (validates against allowed values)
- [ ] Command accepts --output flag (validates against allowed values)
- [ ] Invalid flags show helpful error messages
- [ ] Task metadata is updated with review_type and review_depth

## Implementation Notes

### Architecture Decisions

1. **Separation from task-work**: Create entirely separate orchestrator (do NOT modify task-work)
2. **Reuse existing infrastructure**: Use same task loading, state management as task-work
3. **Skeleton for Phases 2-5**: Implement minimal versions that can be enhanced in later phases
4. **Flag validation**: Strict validation of mode/depth/output values

### File Structure

```
installer/core/commands/
├── task-review.md                              # Command spec (NEW)
└── lib/
    ├── task_review_orchestrator.py             # Core orchestrator (NEW)
    ├── review_context_loader.py                # Phase 1 helper (NEW)
    └── review_state_manager.py                 # State transitions (NEW)
```

### Key Functions

```python
# installer/core/commands/lib/task_review_orchestrator.py

def execute_task_review(
    task_id: str,
    mode: str = "architectural",
    depth: str = "standard",
    output: str = "detailed"
) -> Dict[str, Any]:
    """
    Main orchestrator for task-review command.

    Args:
        task_id: Task ID (e.g., TASK-XXX)
        mode: Review mode (architectural, code-quality, decision, etc.)
        depth: Review depth (quick, standard, comprehensive)
        output: Output format (summary, detailed, presentation)

    Returns:
        Review results dictionary
    """
    # Validate inputs
    validate_review_mode(mode)
    validate_review_depth(depth)
    validate_output_format(output)

    # Phase 1: Load review context
    task_context = load_review_context(task_id)

    # Phase 2: Execute review analysis (skeleton)
    review_results = execute_review_analysis(task_context, mode, depth)

    # Phase 3: Synthesize recommendations (skeleton)
    recommendations = synthesize_recommendations(review_results)

    # Phase 4: Generate review report (skeleton)
    report = generate_review_report(review_results, recommendations, output)

    # Phase 5: Human decision checkpoint (skeleton)
    decision = present_decision_checkpoint(report, recommendations)

    # Handle decision
    handle_review_decision(task_id, decision, recommendations)

    return {
        "status": "success",
        "review_mode": mode,
        "review_depth": depth,
        "task_id": task_id
    }
```

### Skeleton Implementation Pattern

For Phases 2-5 (will be enhanced in later tasks):

```python
def execute_review_analysis(task_context, mode, depth):
    """Skeleton: Will be enhanced in Phase 2 task."""
    print(f"Phase 2: Review Analysis (mode={mode}, depth={depth})")
    return {"findings": [], "mode": mode, "depth": depth}

def synthesize_recommendations(review_results):
    """Skeleton: Will be enhanced in Phase 3 task."""
    print("Phase 3: Synthesize Recommendations")
    return {"recommendations": [], "confidence": "medium"}

def generate_review_report(review_results, recommendations, output):
    """Skeleton: Will be enhanced in Phase 3 task."""
    print(f"Phase 4: Generate Report (output={output})")
    return f"# Review Report\n\n(Placeholder for {output} format)"

def present_decision_checkpoint(report, recommendations):
    """Skeleton: Will be enhanced in Phase 4 task."""
    print("Phase 5: Human Decision Checkpoint")
    print("[A]ccept / [R]evise / [I]mplement / [C]ancel")
    return "accept"  # Default for skeleton
```

### Testing Strategy

1. **Unit Tests**: Test orchestrator functions independently
2. **Integration Test**: Test end-to-end workflow with skeleton phases
3. **State Transition Test**: Verify REVIEW_COMPLETE state handling
4. **Flag Validation Test**: Test all combinations of mode/depth/output

### Dependencies

- Existing task loading infrastructure
- Existing state management code
- No new external dependencies

## Test Requirements

### Unit Tests

File: `tests/unit/commands/test_task_review_orchestrator.py`

```python
def test_execute_task_review_basic():
    """Test basic task-review execution with defaults."""
    result = execute_task_review("TASK-001")
    assert result["status"] == "success"
    assert result["review_mode"] == "architectural"  # default
    assert result["review_depth"] == "standard"  # default

def test_execute_task_review_with_flags():
    """Test task-review with custom flags."""
    result = execute_task_review(
        "TASK-001",
        mode="code-quality",
        depth="comprehensive",
        output="summary"
    )
    assert result["review_mode"] == "code-quality"
    assert result["review_depth"] == "comprehensive"

def test_invalid_review_mode():
    """Test validation of review mode."""
    with pytest.raises(ValueError, match="Invalid review mode"):
        execute_task_review("TASK-001", mode="invalid")

def test_load_review_context():
    """Test Phase 1 context loading."""
    context = load_review_context("TASK-001")
    assert "task_id" in context
    assert "title" in context
    assert "description" in context
    assert "review_scope" in context
```

### Integration Tests

File: `tests/integration/test_task_review_workflow.py`

```python
def test_review_workflow_end_to_end():
    """Test complete review workflow with skeleton phases."""
    # Create review task
    task_id = create_test_task(task_type="review", review_mode="architectural")

    # Execute review
    result = execute_task_review(task_id)

    # Verify workflow completed
    assert result["status"] == "success"

    # Verify state transition
    task = load_task(task_id)
    assert task["status"] == "review_complete"
    assert "review_results" in task
```

## Related Tasks

- **TASK-REV-XXXX**: Implement review modes (Phase 2) - Depends on this task
- **TASK-REV-YYYY**: Implement report generation (Phase 3) - Depends on this task
- **TASK-REV-ZZZZ**: Implement integration with task-create (Phase 4) - Depends on this task
- **TASK-REV-AAAA**: Implement comprehensive testing (Phase 5) - Depends on this task

## Success Criteria

- [ ] Command can be invoked: `/task-review TASK-XXX`
- [ ] All flags work correctly
- [ ] Task context loads successfully
- [ ] Skeleton workflow executes without errors
- [ ] State transitions work correctly
- [ ] All unit tests pass
- [ ] Integration test passes
- [ ] Documentation is complete and clear

## Implementation Checklist

- [ ] Create `task-review.md` command specification
- [ ] Create `task_review_orchestrator.py` with main function
- [ ] Implement `load_review_context()` (Phase 1)
- [ ] Create skeleton functions for Phases 2-5
- [ ] Add `REVIEW_COMPLETE` state to state manager
- [ ] Add review metadata fields to task schema
- [ ] Write unit tests for orchestrator
- [ ] Write integration test for workflow
- [ ] Update CLAUDE.md with task-review reference
- [ ] Test manually with real review task

---

**Note**: This task focuses on **infrastructure and skeleton**. The actual review logic (agents, analysis, reports) will be implemented in subsequent phases.
