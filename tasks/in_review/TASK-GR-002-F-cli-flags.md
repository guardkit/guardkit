---
complexity: 3
conductor_workspace: gr-mvp-wave8-cli
created: 2026-01-30 00:00:00+00:00
depends_on:
- TASK-GR-002-E
feature_id: FEAT-GR-MVP
id: TASK-GR-002-F
implementation_mode: task-work
parent_review: TASK-REV-1505
priority: medium
status: in_review
tags:
- graphiti
- context-addition
- cli
- flags
- mvp-phase-2
task_type: feature
title: Add --type, --force, --dry-run flags
updated: 2026-02-01 00:00:00+00:00
wave: 8
---

# Task: Add --type, --force, --dry-run flags

## Description

Implement the additional flags for the `guardkit graphiti add-context` command that provide fine-grained control over context addition.

## Acceptance Criteria

- [x] `--type` forces specific parser type
- [x] `--force` overwrites existing content
- [x] `--dry-run` shows preview without changes
- [x] `--verbose` shows detailed output
- [x] `--quiet` suppresses non-error output
- [x] Flags work correctly with file and directory input

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

### Files Modified

- `guardkit/cli/graphiti.py` - Added `--verbose` and `--quiet` flag handling
- `tests/unit/test_graphiti_add_context.py` - Added 6 tests for new flags

## Test Requirements

- [x] Unit tests for each flag
- [x] Test flag combinations
- [x] Test error cases

## Implementation Summary

### What Was Done

The `--type`, `--force`, and `--dry-run` flags were already implemented in TASK-GR-002-E. This task added:

1. **`--verbose` (`-v`) flag**: Shows detailed processing output including:
   - Parser type being used
   - Number of episodes found
   - Individual episode details (entity_id, entity_type)

2. **`--quiet` (`-q`) flag**: Suppresses non-error output while still showing:
   - Warnings (yellow)
   - Errors (red)

3. **Mutual exclusivity**: `--verbose` and `--quiet` cannot be used together

### Test Results

- 20/20 add-context tests pass
- 80/80 graphiti-related tests pass
- No regressions

### Code Review

- Rating: 9.5/10
- Status: APPROVED
- All acceptance criteria met

## Notes

Enhances TASK-GR-002-E with more control options.

## References

- [FEAT-GR-002 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-002-context-addition-command.md)
