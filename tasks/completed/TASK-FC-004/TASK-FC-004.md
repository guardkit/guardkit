---
id: TASK-FC-004
title: Add merge instruction display
status: completed
created: 2026-01-24T12:00:00Z
updated: 2026-01-24T21:40:00Z
completed: 2026-01-24T21:40:00Z
priority: medium
tags: [feature-complete, display, ux]
complexity: 1
parent_review: TASK-REV-FC01
feature_id: FEAT-FC-001
implementation_mode: direct
wave: 1
dependencies: []
estimated_minutes: 20
actual_minutes: 15
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria satisfied"
completed_location: tasks/completed/TASK-FC-004/
organized_files: ["TASK-FC-004.md"]
---

# Task: Add merge instruction display

## Description

Implement the Phase 4 logic in `FeatureCompleteOrchestrator` that displays clear instructions for users to complete the merge/PR using their preferred git tool (GitKraken, Fork, Tower, CLI, etc.).

## Requirements

1. Add `_display_handoff()` method to `FeatureCompleteOrchestrator`:
   - Display branch information (source → target)
   - Display worktree location
   - Show instructions for multiple tool options
   - Show cleanup command to run after merge

2. Use Rich library for formatted console output with Panel

3. Instructions should cover:
   - GUI tools (GitKraken, Fork, Tower, Sourcetree)
   - Command line (git merge)
   - CLI PR tools (gh, glab) as optional

## Acceptance Criteria

- [x] `_display_handoff()` method implemented
- [x] Clear panel showing branch and worktree info
- [x] Instructions for GUI tools
- [x] Instructions for CLI direct merge
- [x] Instructions for CLI PR creation (optional)
- [x] Cleanup command displayed
- [x] Visually appealing Rich console output

## Technical Notes

```python
def _display_handoff(self, feature: Feature, worktree: Worktree) -> None:
    """Display merge instructions for user."""
    console.print()
    console.print(Panel(
        f"[bold cyan]Branch:[/bold cyan] {worktree.branch_name} → {worktree.base_branch}\n"
        f"[bold cyan]Worktree:[/bold cyan] {worktree.path}\n\n"
        f"[bold]Use your preferred tool to complete the merge:[/bold]\n\n"
        f"  [dim]GitKraken/Fork/Tower:[/dim]\n"
        f"    1. Open the worktree folder\n"
        f"    2. Create PR or merge to {worktree.base_branch}\n\n"
        f"  [dim]Command Line (direct merge):[/dim]\n"
        f"    git checkout {worktree.base_branch}\n"
        f"    git merge --no-ff {worktree.branch_name}\n"
        f"    git push\n\n"
        f"  [dim]Command Line (GitHub PR):[/dim]\n"
        f"    gh pr create --base {worktree.base_branch} --head {worktree.branch_name}\n\n"
        f"[bold yellow]After merge:[/bold yellow]\n"
        f"  guardkit worktree cleanup {feature.id}",
        title="📋 READY FOR MERGE",
        border_style="green"
    ))
```

## Files to Modify

- **Modify**: `guardkit/orchestrator/feature_complete.py`
- **No new tests needed** (display-only, manual verification)
