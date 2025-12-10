---
id: TASK-UX-0BBB
title: Update task-refine for design context awareness
status: backlog
created: 2025-11-11T11:30:00Z
updated: 2025-11-11T11:30:00Z
priority: medium
tags: [ux-integration, task-refine, constraint-validation]
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Update task-refine for design context awareness

## Description

Update the `/task-refine` command to detect when a task was generated from a design context (Figma/Zeplin) and enforce constraint boundaries during refinements. This prevents scope creep beyond what was specified in the original design.

This is part of Phase 4 of the Design URL Integration project (see [design-url-integration-implementation-guide.md](../../docs/proposals/design-url-integration-implementation-guide.md)).

## Acceptance Criteria

- [ ] Command detects design context from task frontmatter
- [ ] Design-aware refinement mode activated when design context present
- [ ] Constraint validation enforced during refinements
- [ ] Warning displayed about staying within design boundaries
- [ ] Prohibition checklist re-validated after refinements
- [ ] Graceful standard refinement when no design context
- [ ] Clear error messages when refinement violates constraints
- [ ] Command updated in global commands directory
- [ ] Tests updated to cover design-aware refinements

## Implementation Notes

### Source File
- **File**: `installer/core/commands/task-refine.md`

### Key Changes Required

**1. Add Design Context Detection**

Add detection logic at the beginning of task-refine:

```python
# /task-refine command
def task_refine(task_id: str, refinement_description: str) -> None:
    """
    Refine a completed task with minor improvements.

    If task has design context, enforce constraint boundaries.
    """

    # Load task
    task = load_task(task_id)

    # Check if task has design context
    design_url = task.frontmatter.get('design_url')
    has_design_context = design_url is not None

    if has_design_context:
        # Design-aware refinement mode
        console.print("[blue]📐 Design-driven task detected[/blue]")
        console.print("[yellow]⚠️  Refinements must stay within design boundaries[/yellow]")

        # Load original design context
        design_context = DesignContext.from_dict(task.state.get('design_context', {}))

        # Execute design-aware refinement
        execute_design_aware_refinement(
            task=task,
            refinement_description=refinement_description,
            design_context=design_context
        )
    else:
        # Standard refinement mode
        console.print("[dim]Standard refinement workflow[/dim]")

        # Execute standard refinement (existing behavior)
        execute_standard_refinement(
            task=task,
            refinement_description=refinement_description
        )
```

**2. Add Design-Aware Refinement Mode**

```python
def execute_design_aware_refinement(
    task: Task,
    refinement_description: str,
    design_context: DesignContext
) -> None:
    """
    Execute refinement while enforcing design constraint boundaries.

    Flow:
    1. Display constraint warnings
    2. Analyze refinement request for scope violations
    3. Execute refinement if within boundaries
    4. Re-validate against prohibition checklist
    5. Update task files
    """

    # Step 1: Display design boundaries
    console.print("\n[bold]Design Constraint Boundaries[/bold]")
    console.print(f"  [blue]Design Source:[/blue] {design_context.design_source}")
    console.print(f"  [blue]Design URL:[/blue] {design_context.design_url}")
    console.print("\n[yellow]Prohibited Changes:[/yellow]")
    console.print("  ✗ No business logic beyond what's visible")
    console.print("  ✗ No API integration")
    console.print("  ✗ No state management beyond UI state")
    console.print("  ✗ No routing logic")
    console.print("  ✗ No error handling beyond UI feedback")
    console.print("  ✗ No loading states")

    # Step 2: Analyze refinement request
    console.print(f"\n[bold]Analyzing refinement request...[/bold]")

    scope_analysis = analyze_refinement_scope(
        refinement_description=refinement_description,
        design_context=design_context
    )

    if scope_analysis.has_violations:
        # Refinement violates design constraints
        console.print("[red]✗ Refinement violates design constraints[/red]")

        for violation in scope_analysis.violations:
            console.print(f"  [red]✗[/red] {violation}")

        console.print("\n[yellow]Suggested Actions:[/yellow]")
        console.print("  1. Modify refinement to stay within design boundaries")
        console.print("  2. Create a new task for additional functionality")
        console.print("  3. Update the design in Figma/Zeplin first, then re-run task")

        raise RefinementViolatesConstraintsError(
            "Refinement violates design constraints. Aborting."
        )

    # Step 3: Execute refinement
    console.print("[green]✓[/green] Refinement is within design boundaries")
    console.print(f"\n[bold]Executing refinement...[/bold]")

    refinement_result = apply_refinement(
        task=task,
        refinement_description=refinement_description
    )

    # Step 4: Re-validate constraints
    console.print(f"\n[bold]Re-validating constraints...[/bold]")

    validation_result = validate_constraints_after_refinement(
        task=task,
        design_context=design_context,
        modified_files=refinement_result.modified_files
    )

    if validation_result.has_violations:
        # Refinement introduced constraint violations
        console.print("[red]✗ Refinement introduced constraint violations[/red]")

        for violation in validation_result.violations:
            console.print(f"  [red]✗[/red] {violation}")

        # Rollback refinement
        console.print("\n[yellow]Rolling back refinement...[/yellow]")
        rollback_refinement(task, refinement_result)

        raise RefinementIntroducedViolationsError(
            "Refinement introduced constraint violations. Rolled back."
        )

    # Step 5: Update task
    console.print("[green]✓[/green] All constraints validated")
    console.print(f"\n[bold green]Refinement completed successfully[/bold green]")

    # Update task metadata
    task.frontmatter['updated'] = datetime.now().isoformat()
    task.frontmatter['refinement_count'] = task.frontmatter.get('refinement_count', 0) + 1
    task.save()
```

**3. Add Refinement Scope Analysis**

```python
def analyze_refinement_scope(
    refinement_description: str,
    design_context: DesignContext
) -> ScopeAnalysis:
    """
    Analyze refinement request to detect constraint violations.

    Uses AI to analyze the refinement description and detect if it
    introduces functionality beyond the design boundaries.
    """

    # Define prohibited patterns
    prohibited_patterns = {
        'business_logic': ['business logic', 'calculation', 'algorithm', 'validation rule'],
        'api_integration': ['api', 'fetch', 'axios', 'http request', 'endpoint'],
        'database': ['database', 'query', 'save to db', 'persist'],
        'authentication': ['auth', 'login logic', 'session', 'token'],
        'state_management': ['redux', 'context api', 'global state', 'store'],
        'routing': ['navigation', 'route', 'redirect', 'url change'],
        'error_handling': ['try-catch', 'error boundary', 'error handling'],
        'loading_states': ['loading state', 'spinner logic', 'isLoading'],
    }

    violations = []

    refinement_lower = refinement_description.lower()

    # Check for prohibited patterns
    for category, patterns in prohibited_patterns.items():
        for pattern in patterns:
            if pattern in refinement_lower:
                violations.append(
                    f"Detected {category.replace('_', ' ')}: '{pattern}' "
                    f"(prohibited for design-driven tasks)"
                )

    # Additional AI-based analysis could be added here
    # to detect more subtle violations

    return ScopeAnalysis(
        has_violations=len(violations) > 0,
        violations=violations
    )
```

**4. Add Constraint Validation After Refinement**

```python
def validate_constraints_after_refinement(
    task: Task,
    design_context: DesignContext,
    modified_files: List[str]
) -> ValidationResult:
    """
    Re-validate constraints after refinement is applied.

    Scans modified files for prohibited patterns.
    """

    violations = []

    for file_path in modified_files:
        file_violations = scan_file_for_violations(file_path)
        violations.extend(file_violations)

    return ValidationResult(
        has_violations=len(violations) > 0,
        violations=violations
    )


def scan_file_for_violations(file_path: str) -> List[str]:
    """
    Scan a file for prohibited patterns.

    Returns list of constraint violations found.
    """
    violations = []

    with open(file_path) as f:
        content = f.read()

    # Check for prohibited patterns
    if 'fetch(' in content or 'axios.' in content:
        violations.append(f"{file_path}: API integration detected (prohibited)")

    if 'useState(' in content or 'useReducer(' in content:
        # Check if state management is beyond UI state
        # This is a simplified check - actual implementation should be more sophisticated
        state_count = content.count('useState(')
        if state_count > 3:  # Arbitrary threshold
            violations.append(
                f"{file_path}: Complex state management detected (may exceed design boundaries)"
            )

    if 'useRouter' in content or 'redirect(' in content:
        violations.append(f"{file_path}: Routing logic detected (prohibited)")

    if 'try {' in content and 'catch' in content:
        # Check if error handling is beyond UI feedback
        violations.append(f"{file_path}: Complex error handling detected (may exceed design boundaries)")

    # Add more checks...

    return violations
```

**5. Add Rollback Mechanism**

```python
def rollback_refinement(task: Task, refinement_result: RefinementResult) -> None:
    """
    Rollback refinement changes if constraint violations detected.

    Uses git to revert changes.
    """
    console.print("[yellow]Rolling back changes...[/yellow]")

    # Use git to revert changes
    for file_path in refinement_result.modified_files:
        subprocess.run(['git', 'checkout', 'HEAD', file_path], check=True)

    console.print("[green]✓[/green] Changes rolled back successfully")
```

**6. Add Result Data Classes**

```python
from dataclasses import dataclass
from typing import List

@dataclass
class ScopeAnalysis:
    """Analysis of refinement scope relative to design boundaries."""
    has_violations: bool
    violations: List[str]


@dataclass
class ValidationResult:
    """Result of constraint validation."""
    has_violations: bool
    violations: List[str]


@dataclass
class RefinementResult:
    """Result of refinement application."""
    success: bool
    modified_files: List[str]
```

**7. Add Error Classes**

```python
class RefinementViolatesConstraintsError(Exception):
    """Raised when refinement violates design constraints."""
    pass


class RefinementIntroducedViolationsError(Exception):
    """Raised when refinement introduces constraint violations."""
    pass
```

**8. Update Standard Refinement (Existing Behavior)**

Ensure standard refinement workflow remains unchanged:

```python
def execute_standard_refinement(
    task: Task,
    refinement_description: str
) -> None:
    """
    Execute standard refinement workflow (no design context).

    This is the existing behavior - no changes needed.
    """
    console.print(f"\n[bold]Executing refinement...[/bold]")

    # Existing refinement logic
    refinement_result = apply_refinement(
        task=task,
        refinement_description=refinement_description
    )

    # Update task metadata
    task.frontmatter['updated'] = datetime.now().isoformat()
    task.frontmatter['refinement_count'] = task.frontmatter.get('refinement_count', 0) + 1
    task.save()

    console.print(f"\n[bold green]Refinement completed successfully[/bold green]")
```

**9. Update Help Text**

Add design-aware refinement guidance to command help:

```markdown
## Usage

/task-refine TASK-XXX "Refinement description"

## Design-Driven Tasks

For tasks created from designs (Figma/Zeplin):
- Refinements must stay within design boundaries
- No business logic beyond what's visible
- No API integration, routing, or complex state management
- Constraint violations will cause refinement to abort

If you need functionality beyond the design:
1. Update the design in Figma/Zeplin first
2. Create a new task for additional functionality
3. Or use /task-work for a new implementation
```

### Testing Strategy

**Unit Tests**:
- Test design context detection (with/without design_url)
- Test `analyze_refinement_scope()` with various descriptions
- Test `scan_file_for_violations()` with prohibited patterns
- Test `validate_constraints_after_refinement()`
- Test rollback mechanism

**Integration Tests**:
- Full refinement with design context (valid refinement)
- Full refinement with design context (violates constraints)
- Full refinement without design context (standard workflow)
- Rollback on constraint violation
- Re-validation after refinement

**Manual Testing**:
- Test with real design-driven task (e.g., from /figma-to-react)
- Attempt refinement that violates constraints (should abort)
- Attempt valid refinement (should succeed)
- Test with task without design URL (standard refinement)

## Test Requirements

- [ ] Unit test: Design context detection (present)
- [ ] Unit test: Design context detection (absent)
- [ ] Unit test: analyze_refinement_scope() with valid refinement
- [ ] Unit test: analyze_refinement_scope() with violating refinement
- [ ] Unit test: scan_file_for_violations() detects API integration
- [ ] Unit test: scan_file_for_violations() detects routing logic
- [ ] Unit test: scan_file_for_violations() detects complex state management
- [ ] Unit test: validate_constraints_after_refinement()
- [ ] Unit test: rollback_refinement() reverts changes
- [ ] Integration test: Full refinement with design context (valid)
- [ ] Integration test: Full refinement with design context (violates)
- [ ] Integration test: Full refinement without design context
- [ ] Integration test: Rollback on constraint violation
- [ ] Edge case test: Refinement description ambiguous
- [ ] Edge case test: Multiple violations detected

## Dependencies

**Blockers** (must be completed first):
- TASK-UX-7F1E: Add design URL parameter to task-create (design_url field must exist)
- TASK-UX-6D04: Update task-work Phase 1 (design context must be stored in task state)

**Related** (provides context):
- TASK-UX-7E5E: Update task-work Phase 3 (orchestrator routing logic)

## Next Steps

After completing this task:
1. TASK-UX-010: Deprecate old commands (figma-to-react, zeplin-to-maui)
2. TASK-UX-011: Create design-to-code user guide
3. TASK-UX-012: Update CLAUDE.md

## References

- [Design URL Integration Proposal](../../docs/proposals/design-url-integration-proposal.md)
- [Implementation Guide - Phase 4](../../docs/proposals/design-url-integration-implementation-guide.md#phase-4-update-task-work)
- [Existing task-refine Command](../../installer/core/commands/task-refine.md)
- [Constraint Validation Logic](../../installer/core/agents/figma-orchestrator.md) (Phase 5)

## Implementation Estimate

**Duration**: 4-5 hours

**Complexity**: 6/10 (Medium-High)
- Add design context awareness to task-refine
- Implement scope analysis for refinements
- Add constraint validation after refinement
- Implement rollback mechanism
- Maintain backward compatibility (standard refinement)
- Comprehensive error handling

## Test Execution Log

_Automatically populated by /task-work_
