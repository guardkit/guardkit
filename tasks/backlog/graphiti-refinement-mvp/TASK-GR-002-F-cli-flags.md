---
id: TASK-GR-002-F
title: Add --type, --force, --dry-run flags
status: in_review
created: 2026-01-30 00:00:00+00:00
updated: 2026-01-30 00:00:00+00:00
priority: medium
tags:
- graphiti
- context-addition
- cli
- flags
- mvp-phase-2
task_type: feature
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: task-work
wave: 8
conductor_workspace: gr-mvp-wave8-cli
complexity: 3
depends_on:
- TASK-GR-002-E
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-GR-MVP
  base_branch: main
  started_at: '2026-02-01T07:55:27.992649'
  last_updated: '2026-02-01T08:03:32.195371'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-01T07:55:27.992649'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Add --type, --force, --dry-run flags

## Description

Implement the additional flags for the `guardkit graphiti add-context` command that provide fine-grained control over context addition.

## Acceptance Criteria

- [ ] `--type` forces specific parser type
- [ ] `--force` overwrites existing content
- [ ] `--dry-run` shows preview without changes
- [ ] `--verbose` shows detailed output
- [ ] `--quiet` suppresses non-error output
- [ ] Flags work correctly with file and directory input

## Implementation Notes

### Flag Behaviors

```python
# --type: Force parser selection
if parser_type:
    parser = registry.get_parser(parser_type)
    if not parser:
        raise click.ClickException(f"Unknown parser type: {parser_type}")
else:
    parser = registry.detect_parser(file_path, content)

# --force: Handle existing content
if not force:
    exists = await client.episode_exists(entity_id, group_id)
    if exists.exists:
        console.print(f"[yellow]Skipping {file_path}: already exists (use --force to overwrite)[/yellow]")
        continue

# --dry-run: Preview mode
if dry_run:
    console.print(f"[dim]Would add: {episode.entity_id} to {episode.group_id}[/dim]")
    continue

# --verbose: Detailed output
if verbose:
    console.print(f"Parsing {file_path} with {parser.parser_type}")
    console.print(f"  Found {len(result.episodes)} episodes")
    for ep in result.episodes:
        console.print(f"    - {ep.entity_id} ({ep.entity_type})")

# --quiet: Minimal output
if not quiet:
    console.print(f"Added {count} episodes")
```

### Available Parser Types

```
--type options:
  feature-spec       Feature specification documents
  adr                Architecture Decision Records
  project-overview   CLAUDE.md/README.md
```

### Files to Modify

- `src/guardkit/cli/commands/graphiti_add_context.py` - Add flag handling

## Test Requirements

- [ ] Unit tests for each flag
- [ ] Test flag combinations
- [ ] Test error cases

## Notes

Enhances TASK-GR-002-E with more control options.

## References

- [FEAT-GR-002 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-002-context-addition-command.md)
