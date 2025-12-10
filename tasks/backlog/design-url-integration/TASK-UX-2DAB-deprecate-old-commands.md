---
id: TASK-UX-2DAB
title: Deprecate old commands (figma-to-react, zeplin-to-maui)
status: backlog
created: 2025-11-11T11:35:00Z
updated: 2025-11-11T11:35:00Z
priority: medium
tags: [ux-integration, deprecation, migration]
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Deprecate old commands (figma-to-react, zeplin-to-maui)

## Description

Deprecate the stack-specific design-to-code commands (`/figma-to-react`, `/zeplin-to-maui`) in favor of the new unified workflow that uses `/task-create` with `design:` parameter and technology-agnostic orchestrators.

This is part of Phase 5 of the Design URL Integration project (see [design-url-integration-implementation-guide.md](../../docs/proposals/design-url-integration-implementation-guide.md)).

## Acceptance Criteria

- [ ] `/figma-to-react` marked as deprecated
- [ ] `/zeplin-to-maui` marked as deprecated
- [ ] Deprecation warnings display when commands used
- [ ] Commands still function (backward compatibility)
- [ ] Clear migration guide provided in warnings
- [ ] Documentation updated with deprecation notices
- [ ] Deprecation timeline communicated (removal in future version)
- [ ] Command files updated with deprecation metadata
- [ ] Tests updated to verify deprecation warnings

## Implementation Notes

### Files to Update
- **File 1**: `installer/core/commands/figma-to-react.md`
- **File 2**: `installer/core/commands/zeplin-to-maui.md`

### Key Changes Required

**1. Add Deprecation Metadata to Command Frontmatter**

Update both command files with deprecation metadata:

```markdown
---
name: figma-to-react
version: 1.0.0
deprecated: true
deprecated_since: 2025-11-11
deprecated_in_favor_of: task-create with design parameter
removal_planned: 2026-06-01  # 6 months deprecation period
description: |
  [DEPRECATED] Generate React components from Figma designs.

  This command is deprecated in favor of the unified design workflow.
  Use /task-create with design: parameter instead.
---
```

```markdown
---
name: zeplin-to-maui
version: 1.0.0
deprecated: true
deprecated_since: 2025-11-11
deprecated_in_favor_of: task-create with design parameter
removal_planned: 2026-06-01  # 6 months deprecation period
description: |
  [DEPRECATED] Generate .NET MAUI components from Zeplin designs.

  This command is deprecated in favor of the unified design workflow.
  Use /task-create with design: parameter instead.
---
```

**2. Add Deprecation Warning at Command Start**

Add prominent warning at the beginning of each command:

```python
# /figma-to-react command
def figma_to_react(file_key: str, node_id: str = None) -> None:
    """
    [DEPRECATED] Generate React components from Figma designs.

    This command is deprecated. Please use the new unified workflow:
    /task-create "Component name" design:https://figma.com/design/{file_key}/...
    """

    # Display deprecation warning
    console.print("\n" + "=" * 80)
    console.print("[bold yellow]⚠️  DEPRECATION WARNING[/bold yellow]")
    console.print("=" * 80)
    console.print()
    console.print("[yellow]/figma-to-react is deprecated and will be removed in a future version.[/yellow]")
    console.print()
    console.print("[bold]New Workflow:[/bold]")
    console.print("  1. Use /task-create with design: parameter:")
    console.print(f"     [cyan]/task-create \"Component name\" design:https://figma.com/design/{file_key}/...[/cyan]")
    console.print()
    console.print("  2. Run /task-work on the created task:")
    console.print("     [cyan]/task-work TASK-XXX[/cyan]")
    console.print()
    console.print("[bold]Benefits of New Workflow:[/bold]")
    console.print("  ✓ Technology-agnostic (works with React, Next.js, MAUI, Flutter, etc.)")
    console.print("  ✓ Integrated with task workflow (planning, review, testing)")
    console.print("  ✓ Better constraint validation")
    console.print("  ✓ Traceability and audit trail")
    console.print()
    console.print("[dim]This command will continue to work until: 2026-06-01[/dim]")
    console.print("=" * 80)
    console.print()

    # Prompt user to continue or migrate
    choice = Prompt.ask(
        "How would you like to proceed?",
        choices=["continue", "migrate", "cancel"],
        default="migrate"
    )

    if choice == "cancel":
        console.print("[yellow]Command cancelled.[/yellow]")
        return

    if choice == "migrate":
        # Help user migrate to new workflow
        migrate_to_new_workflow_figma(file_key, node_id)
        return

    # If user chose "continue", proceed with existing behavior
    console.print("[dim]Continuing with deprecated command...[/dim]\n")

    # Existing figma-to-react implementation
    # ...
```

```python
# /zeplin-to-maui command
def zeplin_to_maui(project_id: str, screen_id: str) -> None:
    """
    [DEPRECATED] Generate .NET MAUI components from Zeplin designs.

    This command is deprecated. Please use the new unified workflow:
    /task-create "Component name" design:https://app.zeplin.io/project/{project_id}/screen/{screen_id}
    """

    # Display deprecation warning
    console.print("\n" + "=" * 80)
    console.print("[bold yellow]⚠️  DEPRECATION WARNING[/bold yellow]")
    console.print("=" * 80)
    console.print()
    console.print("[yellow]/zeplin-to-maui is deprecated and will be removed in a future version.[/yellow]")
    console.print()
    console.print("[bold]New Workflow:[/bold]")
    console.print("  1. Use /task-create with design: parameter:")
    console.print(f"     [cyan]/task-create \"Component name\" design:https://app.zeplin.io/project/{project_id}/screen/{screen_id}[/cyan]")
    console.print()
    console.print("  2. Run /task-work on the created task:")
    console.print("     [cyan]/task-work TASK-XXX[/cyan]")
    console.print()
    console.print("[bold]Benefits of New Workflow:[/bold]")
    console.print("  ✓ Technology-agnostic (works with React, Next.js, MAUI, Flutter, etc.)")
    console.print("  ✓ Integrated with task workflow (planning, review, testing)")
    console.print("  ✓ Better constraint validation")
    console.print("  ✓ Traceability and audit trail")
    console.print()
    console.print("[dim]This command will continue to work until: 2026-06-01[/dim]")
    console.print("=" * 80)
    console.print()

    # Prompt user to continue or migrate
    choice = Prompt.ask(
        "How would you like to proceed?",
        choices=["continue", "migrate", "cancel"],
        default="migrate"
    )

    if choice == "cancel":
        console.print("[yellow]Command cancelled.[/yellow]")
        return

    if choice == "migrate":
        # Help user migrate to new workflow
        migrate_to_new_workflow_zeplin(project_id, screen_id)
        return

    # If user chose "continue", proceed with existing behavior
    console.print("[dim]Continuing with deprecated command...[/dim]\n")

    # Existing zeplin-to-maui implementation
    # ...
```

**3. Add Migration Helpers**

Add helper functions to guide users through migration:

```python
def migrate_to_new_workflow_figma(file_key: str, node_id: str = None) -> None:
    """
    Guide user through migration from /figma-to-react to new workflow.
    """
    console.print("\n[bold green]Let's migrate to the new workflow![/bold green]\n")

    # Construct Figma URL
    if node_id:
        # Convert node_id format if needed (colon to hyphen for URL)
        node_id_url = node_id.replace(':', '-')
        design_url = f"https://figma.com/design/{file_key}/?node-id={node_id_url}"
    else:
        design_url = f"https://figma.com/design/{file_key}/"

    # Prompt for component name
    component_name = Prompt.ask("What should we call this component?", default="FigmaComponent")

    # Generate task-create command
    task_create_cmd = f'/task-create "{component_name}" design:{design_url}'

    console.print("\n[bold]Step 1:[/bold] Create task with design URL")
    console.print(f"  [cyan]{task_create_cmd}[/cyan]")
    console.print()

    # Ask if user wants to create task now
    create_now = Confirm.ask("Would you like to create this task now?", default=True)

    if create_now:
        # Execute task-create
        from .task_create import task_create
        task_id = task_create(
            title=component_name,
            design_url=design_url
        )

        console.print(f"\n[green]✓[/green] Task created: {task_id}")
        console.print()
        console.print("[bold]Step 2:[/bold] Work on the task")
        console.print(f"  [cyan]/task-work {task_id}[/cyan]")
        console.print()

        # Ask if user wants to start work now
        work_now = Confirm.ask("Would you like to start work on this task now?", default=True)

        if work_now:
            from .task_work import task_work
            task_work(task_id)
    else:
        console.print("\n[dim]Task not created. Run the command above when ready.[/dim]")


def migrate_to_new_workflow_zeplin(project_id: str, screen_id: str) -> None:
    """
    Guide user through migration from /zeplin-to-maui to new workflow.
    """
    console.print("\n[bold green]Let's migrate to the new workflow![/bold green]\n")

    # Construct Zeplin URL
    design_url = f"https://app.zeplin.io/project/{project_id}/screen/{screen_id}"

    # Prompt for component name
    component_name = Prompt.ask("What should we call this component?", default="ZeplinComponent")

    # Generate task-create command
    task_create_cmd = f'/task-create "{component_name}" design:{design_url}'

    console.print("\n[bold]Step 1:[/bold] Create task with design URL")
    console.print(f"  [cyan]{task_create_cmd}[/cyan]")
    console.print()

    # Ask if user wants to create task now
    create_now = Confirm.ask("Would you like to create this task now?", default=True)

    if create_now:
        # Execute task-create
        from .task_create import task_create
        task_id = task_create(
            title=component_name,
            design_url=design_url
        )

        console.print(f"\n[green]✓[/green] Task created: {task_id}")
        console.print()
        console.print("[bold]Step 2:[/bold] Work on the task")
        console.print(f"  [cyan]/task-work {task_id}[/cyan]")
        console.print()

        # Ask if user wants to start work now
        work_now = Confirm.ask("Would you like to start work on this task now?", default=True)

        if work_now:
            from .task_work import task_work
            task_work(task_id)
    else:
        console.print("\n[dim]Task not created. Run the command above when ready.[/dim]")
```

**4. Update Command Help Text**

Update help text for both commands:

```markdown
# /figma-to-react

**[DEPRECATED - Use /task-create with design: parameter instead]**

This command is deprecated in favor of the unified design workflow.

## Migration Guide

### Old Way (Deprecated):
```bash
/figma-to-react abc123 2-2
```

### New Way (Recommended):
```bash
/task-create "Login Button" design:https://figma.com/design/abc123/?node-id=2-2
/task-work TASK-XXX
```

## Benefits of New Workflow

- ✓ Technology-agnostic (works with any stack)
- ✓ Integrated with task management
- ✓ Better planning and review
- ✓ Automatic testing and validation
- ✓ Full traceability

## Deprecation Timeline

- **Deprecated Since**: 2025-11-11
- **Planned Removal**: 2026-06-01 (6 months)
- **Alternative**: /task-create with design: parameter

See: [Design URL Integration User Guide](../../docs/guides/design-to-code-user-guide.md)
```

```markdown
# /zeplin-to-maui

**[DEPRECATED - Use /task-create with design: parameter instead]**

This command is deprecated in favor of the unified design workflow.

## Migration Guide

### Old Way (Deprecated):
```bash
/zeplin-to-maui proj123 screen456
```

### New Way (Recommended):
```bash
/task-create "Dashboard Screen" design:https://app.zeplin.io/project/proj123/screen/screen456
/task-work TASK-XXX
```

## Benefits of New Workflow

- ✓ Technology-agnostic (works with any stack)
- ✓ Integrated with task management
- ✓ Better planning and review
- ✓ Automatic testing and validation
- ✓ Full traceability

## Deprecation Timeline

- **Deprecated Since**: 2025-11-11
- **Planned Removal**: 2026-06-01 (6 months)
- **Alternative**: /task-create with design: parameter

See: [Design URL Integration User Guide](../../docs/guides/design-to-code-user-guide.md)
```

**5. Update CLAUDE.md**

Update project documentation to reflect deprecation:

```markdown
## UX Design Integration

~~**Commands** (DEPRECATED - use /task-create instead):~~
- ~~/figma-to-react~~ (Deprecated - use /task-create with design:)
- ~~/zeplin-to-maui~~ (Deprecated - use /task-create with design:)

**Recommended Workflow**:
```bash
# Create task with design URL
/task-create "Component name" design:<figma-or-zeplin-url>

# Work on task (orchestrator handles design extraction)
/task-work TASK-XXX
```

**Supported Design Sources:**
- Figma (via figma-dev-mode MCP)
- Zeplin (via zeplin MCP)

See: [Design-to-Code User Guide](docs/guides/design-to-code-user-guide.md)
```

### Testing Strategy

**Unit Tests**:
- Test deprecation warning display
- Test migration helper functions
- Test user choice handling (continue/migrate/cancel)

**Integration Tests**:
- Full command execution with deprecation warning
- Migration flow from old command to new workflow
- Verify commands still function (backward compatibility)

**Manual Testing**:
- Run /figma-to-react and verify deprecation warning
- Run /zeplin-to-maui and verify deprecation warning
- Test migration flow (choose "migrate" option)
- Test continue flow (choose "continue" option)
- Verify new workflow works as expected

## Test Requirements

- [ ] Unit test: Deprecation warning displays correctly
- [ ] Unit test: migrate_to_new_workflow_figma() generates correct command
- [ ] Unit test: migrate_to_new_workflow_zeplin() generates correct command
- [ ] Unit test: User choice handling (continue)
- [ ] Unit test: User choice handling (migrate)
- [ ] Unit test: User choice handling (cancel)
- [ ] Integration test: /figma-to-react with deprecation warning
- [ ] Integration test: /zeplin-to-maui with deprecation warning
- [ ] Integration test: Migration flow creates task correctly
- [ ] Integration test: Backward compatibility maintained
- [ ] Manual test: User experience with deprecation warning
- [ ] Manual test: Migration helper guides user correctly

## Dependencies

**Blockers** (must be completed first):
- TASK-UX-7F1E: Add design URL parameter to task-create (new workflow must work)
- TASK-UX-6D04: Update task-work Phase 1 (orchestration must work)
- TASK-UX-7E5E: Update task-work Phase 3 (routing must work)

**Related** (documentation):
- TASK-UX-011: Create design-to-code user guide (referenced in deprecation notices)

## Next Steps

After completing this task:
1. TASK-UX-011: Create design-to-code user guide
2. TASK-UX-012: Update CLAUDE.md
3. Monitor usage and gather feedback during deprecation period
4. Remove deprecated commands after 2026-06-01

## References

- [Design URL Integration Proposal](../../docs/proposals/design-url-integration-proposal.md)
- [Implementation Guide - Phase 5](../../docs/proposals/design-url-integration-implementation-guide.md#phase-5-deprecate-old-commands)
- [Existing figma-to-react Command](../../installer/core/commands/figma-to-react.md)
- [Existing zeplin-to-maui Command](../../installer/core/commands/zeplin-to-maui.md)

## Implementation Estimate

**Duration**: 3-4 hours

**Complexity**: 4/10 (Medium-Low)
- Add deprecation metadata to command files
- Implement deprecation warnings
- Create migration helper functions
- Update help text and documentation
- Maintain backward compatibility
- Test deprecation flow

## Test Execution Log

_Automatically populated by /task-work_
