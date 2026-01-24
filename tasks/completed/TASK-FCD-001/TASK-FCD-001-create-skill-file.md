---
id: TASK-FCD-001
title: Create feature-complete.md skill file
status: completed
created: 2026-01-24T16:35:00Z
updated: 2026-01-24T17:15:00Z
completed: 2026-01-24T21:55:00Z
priority: high
tags: [skill-registration, feature-complete, documentation]
complexity: 2
parent_review: TASK-REV-FCD
feature_id: FEAT-FCD
implementation_mode: direct
wave: 1
estimated_minutes: 30
previous_state: in_review
state_transition_reason: "Completed via /task-complete - all acceptance criteria met"
completed_location: tasks/completed/TASK-FCD-001/
---

# Task: Create feature-complete.md skill file

## Problem Statement

The `/feature-complete` command is not recognized in Claude Code because no skill file exists at `installer/core/commands/feature-complete.md`.

## Requirements

Create a skill file that:
1. Documents the `/feature-complete FEAT-XXX` syntax
2. Documents `--dry-run` and `--force` flags
3. Explains when to use (manual completion, failed features, archival)
4. Shows CLI equivalent: `guardkit autobuild complete FEAT-XXX`
5. Includes "CRITICAL EXECUTION INSTRUCTIONS FOR CLAUDE" section

## Acceptance Criteria

- [x] File created at `installer/core/commands/feature-complete.md`
- [x] Follows structure of `installer/core/commands/feature-build.md`
- [x] Includes command syntax section
- [x] Includes available flags table
- [x] Includes usage examples
- [x] Includes CRITICAL EXECUTION INSTRUCTIONS section
- [x] Skill symlinked to `~/.agentecflow/commands/` after install

## Implementation Notes

**Template to follow**: [installer/core/commands/feature-build.md](../../../installer/core/commands/feature-build.md)

**Key sections to include**:
1. Command Syntax
2. Available Flags (`--dry-run`, `--force`)
3. Examples
4. When to Use (vs auto-completion)
5. CLI Reference
6. CRITICAL EXECUTION INSTRUCTIONS FOR CLAUDE

**CLI Command to delegate to**:
```bash
guardkit autobuild complete FEAT-XXX [--dry-run] [--force]
```

## Files to Create/Modify

- **Create**: `installer/core/commands/feature-complete.md` ✅ COMPLETED

## Testing

After creation, verify:
```bash
# Check file exists
ls installer/core/commands/feature-complete.md

# Re-run install to symlink
./installer/scripts/install.sh

# Verify symlink created
ls -la ~/.agentecflow/commands/feature-complete.md
```

## Implementation Summary

**File created**: `installer/core/commands/feature-complete.md` (732 lines)

**Sections implemented**:
- Command Syntax (single task + feature modes)
- Available Flags table (--dry-run, --force, --no-cleanup, --verbose, --verify)
- CLI Reference (slash command + shell equivalents)
- Examples (basic, preview, force, feature)
- How It Works (mode detection, merge process)
- Single Task Mode (merge workflow)
- Feature Mode (multi-task orchestration)
- When to Use (vs alternatives)
- Workflow Integration (task + feature workflows)
- State Management (archive structure)
- Troubleshooting (common errors)
- CRITICAL EXECUTION INSTRUCTIONS FOR CLAUDE (249 lines)

## Completion Report

**Completed**: 2026-01-24T21:55:00Z

**Verification Results**:
- ✅ Skill file exists at `installer/core/commands/feature-complete.md` (22,389 bytes)
- ✅ Symlink created at `~/.agentecflow/commands/feature-complete.md`
- ✅ All acceptance criteria met

**Deliverables**:
1. `installer/core/commands/feature-complete.md` - Complete skill file (732 lines)
2. Symlink at `~/.agentecflow/commands/feature-complete.md`

**Duration**: ~2.5 hours (estimated 30 minutes - included review and install)
