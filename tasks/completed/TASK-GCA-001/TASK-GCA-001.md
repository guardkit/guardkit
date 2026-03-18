---
id: TASK-GCA-001
title: Create shared Graphiti availability preamble for command specs
status: completed
created: '2026-03-18T00:00:00Z'
updated: '2026-03-18T12:00:00Z'
completed: '2026-03-18T12:00:00Z'
completed_location: tasks/completed/TASK-GCA-001/
priority: high
complexity: 3
tags: [graphiti, command-specs, DRY]
parent_review: REV-SD-001
feature_id: FEAT-CD64
implementation_mode: task-work
wave: 1
---

# Create shared Graphiti availability preamble for command specs

## Description

Create a reusable markdown include at `installer/core/commands/lib/graphiti-preamble.md` that provides a standard Graphiti availability check pattern all command specs can reference.

This replaces the broken Python pseudocode pattern (`get_graphiti()`) with tool-native instructions the LLM can execute using its Read and Bash tools.

## Acceptance Criteria

- [x] `installer/core/commands/lib/graphiti-preamble.md` exists with:
  - Tier 1: Read-based check (Read `.guardkit/graphiti.yaml`, check `enabled: true`)
  - Tier 2: CLI-based check (`/Users/richardwoollcott/.agentecflow/bin/graphiti-check --status --quiet` via Bash tool)
  - Clear instructions on when to use each tier
  - Template for the "Graphiti unavailable" warning message
  - Template for seeding commands using `guardkit graphiti add-context`
- [x] Instructions are written as natural language directives the LLM can follow (not Python pseudocode)
- [x] File includes a section on how to reference it from command specs (e.g., "See: lib/graphiti-preamble.md")

## Implementation Notes

The preamble should be structured so command specs can reference specific sections:
- Availability check (all commands need this)
- Seeding commands (only commands that write to Graphiti)
- Group ID reference (which groups each command type uses)

Key design decision: use absolute path for `graphiti-check` (`~/.agentecflow/bin/graphiti-check`) to avoid PATH issues, or use the Read-based approach as the primary method since it requires no external tooling.
