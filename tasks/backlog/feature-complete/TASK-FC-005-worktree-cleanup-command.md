---
id: TASK-FC-005
title: Add guardkit worktree cleanup command
status: backlog
created: 2026-01-24T12:00:00Z
updated: 2026-01-24T12:00:00Z
priority: medium
tags: [feature-complete, worktree, cleanup, cli]
complexity: 2
parent_review: TASK-REV-FC01
feature_id: FEAT-FC-001
implementation_mode: task-work
wave: 1
dependencies: []
estimated_minutes: 40
---

# Task: Add guardkit worktree cleanup command

## Description

Implement the `guardkit worktree cleanup FEAT-XXX` command that users run after completing their merge/PR. This command removes the worktree directory and deletes the branch.

## Requirements

1. Add CLI command `guardkit worktree cleanup <ID>`:
   - Accept task ID (`TASK-XXX`) or feature ID (`FEAT-XXX`)
   - Remove worktree directory from `.guardkit/worktrees/`
   - Delete the branch `autobuild/<ID>`
   - Update feature YAML: set `worktree_cleaned: true`
   - Confirmation prompt unless `--force` flag

2. Safety checks:
   - Warn if there are uncommitted changes in worktree
   - Warn if branch hasn't been merged yet
   - `--force` flag bypasses warnings

3. Handle edge cases:
   - Worktree already removed
   - Branch already deleted
   - Git not available

## Acceptance Criteria

- [ ] `guardkit worktree cleanup FEAT-XXX` command works
- [ ] `guardkit worktree cleanup TASK-XXX` command works
- [ ] Worktree directory removed
- [ ] Branch deleted
- [ ] Feature YAML updated with `worktree_cleaned: true`
- [ ] Confirmation prompt shown (unless `--force`)
- [ ] Warning if uncommitted changes
- [ ] Warning if branch not merged
- [ ] `--force` flag bypasses warnings
- [ ] Handles already-cleaned worktrees gracefully
- [ ] Unit tests for cleanup logic

## Technical Notes

```python
@worktree.command()
@click.argument("id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation and warnings")
def cleanup(id: str, force: bool) -> None:
    """Clean up worktree after merge is complete."""
    repo_root = Path.cwd()
    manager = WorktreeManager(repo_root)

    worktree_path = repo_root / ".guardkit" / "worktrees" / id
    branch_name = f"autobuild/{id}"

    # Safety checks (unless --force)
    if not force:
        # Check for uncommitted changes
        if _has_uncommitted_changes(worktree_path):
            console.print("[yellow]⚠ Worktree has uncommitted changes[/yellow]")
            if not click.confirm("Continue anyway?"):
                raise click.Abort()

        # Check if branch is merged
        if not _is_branch_merged(branch_name, repo_root):
            console.print("[yellow]⚠ Branch may not be merged yet[/yellow]")
            if not click.confirm("Continue anyway?"):
                raise click.Abort()

    # Perform cleanup
    try:
        if worktree_path.exists():
            manager._run_git(["worktree", "remove", str(worktree_path), "--force"])
            console.print(f"  ✓ Removed worktree: {worktree_path}")
        else:
            console.print(f"  [dim]⏭ Worktree already removed[/dim]")

        # Delete branch
        try:
            manager._run_git(["branch", "-D", branch_name])
            console.print(f"  ✓ Deleted branch: {branch_name}")
        except:
            console.print(f"  [dim]⏭ Branch already deleted[/dim]")

        # Update feature YAML if it's a feature
        if id.startswith("FEAT-"):
            _update_feature_yaml(id, repo_root)

        console.print(f"\n[green]✓ Cleanup complete for {id}[/green]")

    except Exception as e:
        console.print(f"[red]✗ Cleanup failed: {e}[/red]")
        raise click.Abort()
```

## Files to Modify

- **Modify**: `guardkit/cli/autobuild.py` (or create `guardkit/cli/worktree.py`)
- **Modify**: `guardkit/worktrees/manager.py` (if needed)
- **Create**: `tests/cli/test_worktree_cleanup.py`
