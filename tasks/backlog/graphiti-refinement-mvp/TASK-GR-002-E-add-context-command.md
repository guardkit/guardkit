---
id: TASK-GR-002-E
title: Add guardkit graphiti add-context CLI command
status: backlog
created: 2026-01-30T00:00:00Z
updated: 2026-01-30T00:00:00Z
priority: high
tags: [graphiti, context-addition, cli, mvp-phase-2]
task_type: feature
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: task-work
wave: 8
conductor_workspace: gr-mvp-wave8-cli
complexity: 4
depends_on:
  - TASK-GR-002-B
  - TASK-GR-002-C
  - TASK-GR-002-D
---

# Task: Add guardkit graphiti add-context CLI command

## Description

Implement the `guardkit graphiti add-context` CLI command that allows users to explicitly add context to Graphiti from files or directories.

## Acceptance Criteria

- [ ] `guardkit graphiti add-context <file>` adds single file
- [ ] `guardkit graphiti add-context <dir>` adds directory (with patterns)
- [ ] Auto-detects file type and uses appropriate parser
- [ ] Shows summary of what was added
- [ ] Graceful error handling for unsupported files

## Implementation Notes

### CLI Structure

```bash
guardkit graphiti add-context [OPTIONS] <PATH>

Arguments:
  PATH                    File or directory to add

Options:
  --type TEXT            Force parser type (adr, feature-spec, project-overview)
  --force                Overwrite existing context
  --dry-run              Show what would be added
  --pattern TEXT         Glob pattern for directory (default: **/*.md)
```

### Command Implementation

```python
@click.command("add-context")
@click.argument("path", type=click.Path(exists=True))
@click.option("--type", "parser_type", help="Force parser type")
@click.option("--force", is_flag=True, help="Overwrite existing")
@click.option("--dry-run", is_flag=True, help="Preview only")
@click.option("--pattern", default="**/*.md", help="File pattern for directories")
async def add_context(
    path: str,
    parser_type: Optional[str],
    force: bool,
    dry_run: bool,
    pattern: str
):
    """Add context to Graphiti from file or directory."""
    console = Console()
    path_obj = Path(path)

    # Get files to process
    if path_obj.is_file():
        files = [path_obj]
    else:
        files = list(path_obj.glob(pattern))

    console.print(f"Found {len(files)} files to process")

    # Process each file
    registry = get_parser_registry()
    client = GraphitiClient()

    for file_path in files:
        content = file_path.read_text()

        # Get parser
        if parser_type:
            parser = registry.get_parser(parser_type)
        else:
            parser = registry.detect_parser(str(file_path), content)

        if not parser:
            console.print(f"[yellow]Skipping {file_path}: no parser found[/yellow]")
            continue

        # Parse content
        result = parser.parse(content, str(file_path))

        if not result.success:
            console.print(f"[red]Failed to parse {file_path}: {result.warnings}[/red]")
            continue

        # Add to Graphiti
        if dry_run:
            console.print(f"[dim]Would add {len(result.episodes)} episodes from {file_path}[/dim]")
        else:
            for episode in result.episodes:
                await client.upsert_episode(
                    episode.content,
                    episode.group_id,
                    entity_id=episode.entity_id,
                    entity_type=episode.entity_type,
                    metadata=episode.metadata
                )
            console.print(f"[green]Added {len(result.episodes)} episodes from {file_path}[/green]")
```

### Files to Create

- `src/guardkit/cli/commands/graphiti_add_context.py`

## Test Requirements

- [ ] Unit tests for command logic
- [ ] Integration test with real files
- [ ] Test --dry-run output
- [ ] Test unsupported file handling

## Notes

Core user-facing command for explicit context addition.

## References

- [FEAT-GR-002 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-002-context-addition-command.md)
