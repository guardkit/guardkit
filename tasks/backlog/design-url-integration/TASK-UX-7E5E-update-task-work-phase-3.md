---
id: TASK-UX-7E5E
title: Update task-work Phase 3 to route to orchestrators
status: backlog
created: 2025-11-11T11:25:00Z
updated: 2025-11-11T11:25:00Z
priority: high
tags: [ux-integration, task-work, phase-3, orchestration]
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Update task-work Phase 3 to route to orchestrators

## Description

Update the `/task-work` command's Phase 3 (Implementation) to detect design context from Phase 1, route to appropriate orchestrators (figma-orchestrator, zeplin-orchestrator), and handle orchestrator delegation to UI specialists.

This is part of Phase 4 of the Design URL Integration project (see [design-url-integration-implementation-guide.md](../../docs/proposals/design-url-integration-implementation-guide.md)).

## Acceptance Criteria

- [ ] Phase 3 detects design context from task state
- [ ] Routes to appropriate orchestrator based on design source
- [ ] Detects project stack (react, nextjs, maui, etc.)
- [ ] Passes design context and stack to orchestrator
- [ ] Orchestrator delegates to appropriate UI specialist
- [ ] Graceful fallback to standard implementation when no design context
- [ ] Clear progress reporting during orchestration
- [ ] Command updated in global commands directory
- [ ] Tests updated to cover orchestration scenarios

## Implementation Notes

### Source File
- **File**: `installer/core/commands/task-work.md`

### Key Changes Required

**1. Update Phase 3: Implementation**

Add orchestration routing logic at the beginning of Phase 3:

```python
# Phase 3: Implementation
def phase_3_implementation(
    task: Task,
    config: Config,
    plan: ImplementationPlan,
    design_context: Optional[DesignContext] = None
) -> ImplementationResult:
    """
    Execute implementation using orchestrator (if design context present)
    or standard workflow (if no design context).
    """

    # Check if design context exists
    if design_context:
        # Design-driven workflow via orchestrator
        console.print("[blue]📐 Design-driven implementation via orchestrator[/blue]")

        return execute_orchestrated_implementation(
            task=task,
            config=config,
            plan=plan,
            design_context=design_context
        )
    else:
        # Standard workflow
        console.print("[dim]Standard implementation workflow[/dim]")

        return execute_standard_implementation(
            task=task,
            config=config,
            plan=plan
        )
```

**2. Add Orchestrated Implementation**

```python
def execute_orchestrated_implementation(
    task: Task,
    config: Config,
    plan: ImplementationPlan,
    design_context: DesignContext
) -> ImplementationResult:
    """
    Execute design-driven implementation via orchestrator.

    Flow:
    1. Detect project stack
    2. Get orchestrator for design source
    3. Invoke orchestrator with design context and target stack
    4. Orchestrator delegates to {stack}-ui-specialist
    5. UI specialist generates components matching design
    6. Return results
    """

    # Step 1: Detect project stack
    stack = detect_project_stack()
    console.print(f"[dim]Detected stack: {stack}[/dim]")

    # Step 2: Get orchestrator for design source
    orchestrator_name = design_context.get_orchestrator_name()
    console.print(f"[dim]Using orchestrator: {orchestrator_name}[/dim]")

    # Step 3: Verify orchestrator exists
    if not orchestrator_exists(orchestrator_name):
        raise OrchestratorNotFoundError(
            f"Orchestrator '{orchestrator_name}' not found.\n"
            f"Expected location: installer/core/agents/{orchestrator_name}.md\n"
            f"Please ensure UX-003 or UX-004 tasks are completed."
        )

    # Step 4: Verify UI specialist exists for stack
    ui_specialist_name = f"{stack}-ui-specialist"
    if not ui_specialist_exists(ui_specialist_name, stack):
        raise UISpecialistNotFoundError(
            f"UI specialist '{ui_specialist_name}' not found for stack '{stack}'.\n"
            f"Expected location: installer/core/templates/{stack}-*/agents/{ui_specialist_name}.md\n"
            f"Please ensure the template includes a UI specialist, or create one via /template-create."
        )

    # Step 5: Invoke orchestrator
    console.print(f"\n[bold blue]Invoking {orchestrator_name}...[/bold blue]")

    orchestrator_result = invoke_orchestrator(
        orchestrator_name=orchestrator_name,
        task=task,
        design_context=design_context,
        target_stack=stack,
        ui_specialist=ui_specialist_name
    )

    # Step 6: Process orchestrator results
    if orchestrator_result.success:
        console.print("[green]✓[/green] Orchestrator completed successfully")

        return ImplementationResult(
            success=True,
            generated_files=orchestrator_result.generated_files,
            visual_fidelity=orchestrator_result.visual_fidelity,
            constraint_violations=orchestrator_result.constraint_violations
        )
    else:
        console.print("[red]✗[/red] Orchestrator failed")
        raise OrchestratorError(orchestrator_result.error_message)
```

**3. Add Stack Detection**

```python
def detect_project_stack() -> str:
    """
    Detect project stack from package.json, requirements.txt, .csproj, etc.

    Returns:
        Stack identifier: "react" | "nextjs" | "vue" | "fastapi" | "maui" | "flutter" | etc.
    """
    cwd = Path.cwd()

    # Check for Next.js
    package_json = cwd / "package.json"
    if package_json.exists():
        with open(package_json) as f:
            package_data = json.load(f)
            dependencies = {**package_data.get('dependencies', {}), **package_data.get('devDependencies', {})}

            if 'next' in dependencies:
                return 'nextjs'
            elif 'react' in dependencies:
                return 'react'
            elif 'vue' in dependencies:
                return 'vue'

    # Check for FastAPI
    requirements_txt = cwd / "requirements.txt"
    if requirements_txt.exists():
        with open(requirements_txt) as f:
            requirements = f.read().lower()
            if 'fastapi' in requirements:
                return 'fastapi'
            elif 'django' in requirements:
                return 'django'
            elif 'flask' in requirements:
                return 'flask'

    # Check for .NET MAUI
    for csproj_file in cwd.rglob("*.csproj"):
        with open(csproj_file) as f:
            csproj_content = f.read()
            if '<UseMaui>true</UseMaui>' in csproj_content:
                return 'maui'

    # Check for Flutter
    pubspec_yaml = cwd / "pubspec.yaml"
    if pubspec_yaml.exists():
        return 'flutter'

    # Check for SwiftUI
    for swift_file in cwd.rglob("*.swift"):
        # Simplified check - actual implementation should be more sophisticated
        return 'swiftui'

    # Default to unknown
    return 'unknown'
```

**4. Add Orchestrator Invocation**

```python
def invoke_orchestrator(
    orchestrator_name: str,
    task: Task,
    design_context: DesignContext,
    target_stack: str,
    ui_specialist: str
) -> OrchestratorResult:
    """
    Invoke orchestrator agent via Task tool.

    The orchestrator will:
    1. Verify MCP availability
    2. Extract design from Figma/Zeplin via MCP
    3. Document boundaries (prohibition checklist)
    4. Delegate to UI specialist for component generation
    5. Run visual regression tests (via UI specialist)
    6. Validate constraints (no scope creep)
    """

    # Prepare orchestrator prompt
    orchestrator_prompt = f"""
Execute design-to-code workflow for task {task.id}.

**Task Details:**
- Title: {task.title}
- Description: {task.description}

**Design Context:**
- Design Source: {design_context.design_source}
- Design URL: {design_context.design_url}
- Design Metadata: {json.dumps(design_context.design_metadata, indent=2)}

**Target Stack:**
- Stack: {target_stack}
- UI Specialist: {ui_specialist}

**Instructions:**
1. Execute 6-phase Saga pattern
2. Delegate component generation to {ui_specialist}
3. Enforce zero scope creep (prohibition checklist)
4. Validate visual fidelity >95%
5. Return results in expected format

**Expected Output Format:**
```json
{{
  "success": true,
  "generated_files": ["path/to/file1.tsx", "path/to/file2.spec.ts"],
  "visual_fidelity": 0.97,
  "constraint_violations": []
}}
```
    """

    # Invoke orchestrator via Task tool (subagent)
    try:
        # Use Task tool to launch orchestrator agent
        result = task_tool.launch_agent(
            subagent_type=orchestrator_name,
            prompt=orchestrator_prompt,
            description=f"Execute {orchestrator_name} for {task.id}"
        )

        # Parse orchestrator result
        orchestrator_output = json.loads(result)

        return OrchestratorResult(
            success=orchestrator_output.get('success', False),
            generated_files=orchestrator_output.get('generated_files', []),
            visual_fidelity=orchestrator_output.get('visual_fidelity', 0.0),
            constraint_violations=orchestrator_output.get('constraint_violations', []),
            error_message=orchestrator_output.get('error_message', None)
        )

    except Exception as e:
        return OrchestratorResult(
            success=False,
            generated_files=[],
            visual_fidelity=0.0,
            constraint_violations=[],
            error_message=str(e)
        )
```

**5. Add Orchestrator/Specialist Validation**

```python
def orchestrator_exists(orchestrator_name: str) -> bool:
    """
    Check if orchestrator agent exists.

    Expected location: installer/core/agents/{orchestrator_name}.md
    """
    orchestrator_path = Path("installer/core/agents") / f"{orchestrator_name}.md"
    return orchestrator_path.exists()


def ui_specialist_exists(ui_specialist_name: str, stack: str) -> bool:
    """
    Check if UI specialist exists for stack.

    Expected locations:
    - installer/core/templates/{stack}-*/agents/{ui_specialist_name}.md
    - ~/.agentecflow/templates/{stack}-*/agents/{ui_specialist_name}.md
    """
    # Check in global templates
    global_templates = Path("installer/core/templates")
    for template_dir in global_templates.glob(f"{stack}-*"):
        specialist_path = template_dir / "agents" / f"{ui_specialist_name}.md"
        if specialist_path.exists():
            return True

    # Check in user templates
    user_templates = Path.home() / ".agentecflow" / "templates"
    if user_templates.exists():
        for template_dir in user_templates.glob(f"{stack}-*"):
            specialist_path = template_dir / "agents" / f"{ui_specialist_name}.md"
            if specialist_path.exists():
                return True

    return False
```

**6. Add Result Data Classes**

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class OrchestratorResult:
    """Result from orchestrator execution."""
    success: bool
    generated_files: List[str]
    visual_fidelity: float  # 0.0-1.0
    constraint_violations: List[str]
    error_message: Optional[str] = None


@dataclass
class ImplementationResult:
    """Result from Phase 3 implementation."""
    success: bool
    generated_files: List[str]
    visual_fidelity: Optional[float] = None  # Only for design-driven
    constraint_violations: Optional[List[str]] = None  # Only for design-driven
```

**7. Add Error Classes**

```python
class OrchestratorNotFoundError(Exception):
    """Raised when orchestrator agent is not found."""
    pass


class UISpecialistNotFoundError(Exception):
    """Raised when UI specialist is not found for stack."""
    pass


class OrchestratorError(Exception):
    """Raised when orchestrator execution fails."""
    pass
```

**8. Update Standard Implementation (Existing Behavior)**

Ensure standard implementation workflow remains unchanged:

```python
def execute_standard_implementation(
    task: Task,
    config: Config,
    plan: ImplementationPlan
) -> ImplementationResult:
    """
    Execute standard implementation workflow (no design context).

    This is the existing behavior - no changes needed.
    """
    # Existing implementation logic
    # ...

    return ImplementationResult(
        success=True,
        generated_files=generated_files,
        visual_fidelity=None,  # Not applicable for standard workflow
        constraint_violations=None  # Not applicable for standard workflow
    )
```

**9. Update Phase 3 Output**

Add design-driven workflow reporting:

```python
# Print Phase 3 summary
console.print("\n[bold]Phase 3 Complete: Implementation[/bold]")

if implementation_result.visual_fidelity is not None:
    # Design-driven workflow
    console.print(f"  [blue]Visual Fidelity:[/blue] {implementation_result.visual_fidelity * 100:.1f}%")

    if implementation_result.constraint_violations:
        console.print(f"  [red]Constraint Violations:[/red] {len(implementation_result.constraint_violations)}")
        for violation in implementation_result.constraint_violations:
            console.print(f"    - {violation}")
    else:
        console.print(f"  [green]Constraint Violations:[/green] 0")

console.print(f"  [blue]Generated Files:[/blue] {len(implementation_result.generated_files)}")
for file in implementation_result.generated_files:
    console.print(f"    - {file}")
```

### Testing Strategy

**Unit Tests**:
- Test `detect_project_stack()` for each stack
- Test `orchestrator_exists()` with mock file system
- Test `ui_specialist_exists()` with mock file system
- Test `invoke_orchestrator()` with mocked Task tool

**Integration Tests**:
- Full Phase 3 with design context (Figma)
- Full Phase 3 with design context (Zeplin)
- Full Phase 3 without design context (standard workflow)
- Orchestrator not found error handling
- UI specialist not found error handling
- Orchestrator execution failure handling

**Manual Testing**:
- Test with real Figma URL and react stack
- Test with real Zeplin URL and nextjs stack
- Test with task without design URL (standard workflow)
- Verify orchestrator delegates to UI specialist correctly
- Verify visual fidelity scoring
- Verify constraint validation

## Test Requirements

- [ ] Unit test: detect_project_stack() for Next.js
- [ ] Unit test: detect_project_stack() for React
- [ ] Unit test: detect_project_stack() for FastAPI
- [ ] Unit test: detect_project_stack() for .NET MAUI
- [ ] Unit test: detect_project_stack() for unknown stack
- [ ] Unit test: orchestrator_exists() returns true when present
- [ ] Unit test: orchestrator_exists() returns false when absent
- [ ] Unit test: ui_specialist_exists() returns true when present
- [ ] Unit test: ui_specialist_exists() returns false when absent
- [ ] Unit test: invoke_orchestrator() with mocked Task tool
- [ ] Integration test: Phase 3 with Figma design context
- [ ] Integration test: Phase 3 with Zeplin design context
- [ ] Integration test: Phase 3 without design context
- [ ] Integration test: Orchestrator not found error
- [ ] Integration test: UI specialist not found error
- [ ] Integration test: Orchestrator execution failure
- [ ] Edge case test: Unknown stack detection
- [ ] Edge case test: Multiple stacks detected (should pick primary)

## Dependencies

**Blockers** (must be completed first):
- TASK-UX-6D04: Update task-work Phase 1 (design context must be loaded)
- TASK-UX-2A61: Refactor figma-react-orchestrator to figma-orchestrator (orchestrator must exist)
- TASK-UX-EFC3: Refactor zeplin-maui-orchestrator to zeplin-orchestrator (orchestrator must exist)
- TASK-UX-71BD: Extend react-ui-specialist (UI specialist must handle design contexts)
- TASK-UX-92BF: Extend nextjs-ui-specialist (UI specialist must handle design contexts)

## Next Steps

After completing this task:
1. TASK-UX-009: Update task-refine for design context awareness
2. TASK-UX-010: Deprecate old commands (figma-to-react, zeplin-to-maui)
3. TASK-UX-011: Create design-to-code user guide

## References

- [Design URL Integration Proposal](../../docs/proposals/design-url-integration-proposal.md)
- [Implementation Guide - Phase 4](../../docs/proposals/design-url-integration-implementation-guide.md#phase-4-update-task-work)
- [Existing task-work Command](../../installer/core/commands/task-work.md)
- [Figma Orchestrator](../../installer/core/agents/figma-orchestrator.md) (after UX-003)
- [Zeplin Orchestrator](../../installer/core/agents/zeplin-orchestrator.md) (after UX-004)

## Implementation Estimate

**Duration**: 6-8 hours

**Complexity**: 8/10 (High)
- Modify critical command (task-work Phase 3)
- Add orchestration routing logic
- Implement stack detection
- Add orchestrator invocation via Task tool
- Handle orchestrator → UI specialist delegation
- Comprehensive error handling
- Maintain backward compatibility (standard workflow)
- Integration with multiple dependencies

## Test Execution Log

_Automatically populated by /task-work_
