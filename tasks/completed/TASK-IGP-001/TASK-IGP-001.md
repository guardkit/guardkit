---
id: TASK-IGP-001
title: Auto-offer system seeding after guardkit init
status: completed
created: 2026-03-15T12:30:00Z
updated: 2026-03-15T13:10:00Z
completed: 2026-03-15T13:10:00Z
completed_location: tasks/completed/TASK-IGP-001/
priority: medium
tags: [init, graphiti, ux, seeding]
task_type: implementation
parent_review: TASK-REV-A73F
feature_id: FEAT-IGP
implementation_mode: task-work
wave: 1
complexity: 3
depends_on: []
test_results:
  status: passed
  coverage: 100
  last_run: 2026-03-15T13:00:00Z
  tests_total: 100
  tests_passed: 100
  tests_failed: 0
---

# Task: Auto-offer system seeding after guardkit init

## Description

After `guardkit init` completes project-specific Graphiti seeding (Step 2), prompt the user to also run system-level seeding inline rather than requiring a separate `guardkit graphiti seed-system` command.

This closes the UX gap identified in TASK-REV-A73F Finding 4 where users must remember to run a separate command after init. AutoBuild depends on role constraints and implementation modes from system seeding, so new projects are in a degraded state until `seed-system` is run manually.

## Context

From TASK-REV-A73F review:
- `seed_project_knowledge()` only seeds project-specific content (project overview)
- System-scoped content (role constraints, impl modes, template sync) lives in `seed_system_content()`
- Currently only accessible via `guardkit graphiti seed-system` CLI command
- Init displays it as "Next steps: 1. Seed system knowledge" which is easy to miss

## Acceptance Criteria

- [x] After successful Graphiti project seeding, user is prompted: "Seed system knowledge now? (recommended) [Y/n]"
- [x] If user accepts (or non-interactive fallback), `seed_system_content()` runs inline with progress display
- [x] If user declines, existing "Next steps" message still shows `seed-system` command
- [x] `--skip-graphiti` flag skips both project AND system seeding (no prompt)
- [x] `--no-questions` flag auto-accepts system seeding (no prompt, just runs it)
- [x] Exception in system seeding does not fail the overall init (graceful degradation)
- [x] Existing tests continue to pass
- [x] New test covers the auto-offer flow (accept and decline paths)

## Key Files

- `guardkit/cli/init.py` - Add system seeding offer after Step 2 (around line 800)
- `guardkit/knowledge/system_seeding.py` - Already has `seed_system_content()`, no changes needed
- `tests/cli/test_init.py` - Add tests for new flow

## Implementation Notes

Insert after the project seeding success block at [init.py:777-789](guardkit/cli/init.py#L777-L789):

```python
# Step 2.5: Offer system seeding
if result.success and client and client.enabled:
    try:
        if no_questions:
            should_seed_system = True
        else:
            should_seed_system = Confirm.ask(
                "Seed system knowledge now? (recommended for AutoBuild)",
                default=True
            )
    except Exception:
        should_seed_system = True  # Non-interactive fallback

    if should_seed_system:
        console.print("\n[bold]Step 3: Seeding system knowledge...[/bold]")
        try:
            from guardkit.knowledge.system_seeding import seed_system_content
            sys_result = await seed_system_content(client, template_name=template)
            if sys_result.success:
                console.print("  [green]System knowledge seeded successfully[/green]")
            else:
                console.print("  [yellow]Warning: Some system seeding components failed[/yellow]")
        except Exception as e:
            console.print(f"  [yellow]Warning: System seeding error: {e}[/yellow]")
```

Update "Next steps" to conditionally omit `seed-system` if it was already run.
