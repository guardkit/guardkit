---
id: TASK-SC-005
title: "Create command markdown specs for all 3 commands"
status: backlog
created: 2026-02-10T11:20:00Z
updated: 2026-02-10T11:20:00Z
priority: high
task_type: feature
parent_review: TASK-REV-AEA7
feature_id: FEAT-SC-001
wave: 2
implementation_mode: task-work
complexity: 4
dependencies:
  - TASK-SC-001
  - TASK-SC-002
tags: [commands, slash-commands, spec]
---

# Task: Create command markdown specs for all 3 commands

## Description

Create 6 command markdown files (3 for `.claude/commands/` + 3 for `installer/core/commands/`) that define the `/system-overview`, `/impact-analysis`, and `/context-switch` slash commands. Each command spec follows the established patterns from `feature-plan.md` and `task-review.md`.

## Key Implementation Details

### Files to Create

1. `.claude/commands/system-overview.md` — /system-overview command spec
2. `.claude/commands/impact-analysis.md` — /impact-analysis command spec
3. `.claude/commands/context-switch.md` — /context-switch command spec
4. `installer/core/commands/system-overview.md` — installer copy
5. `installer/core/commands/impact-analysis.md` — installer copy
6. `installer/core/commands/context-switch.md` — installer copy

### /system-overview Spec Structure

```
# /system-overview - Architecture Summary

## Syntax
/system-overview [--verbose] [--section=SECTION] [--format=FORMAT]

## Execution Instructions for Claude
1. Import and call get_system_overview()
2. Format using format_overview_display()
3. Handle graceful degradation
4. Show helpful hints for next commands
```

### /impact-analysis Spec Structure

```
# /impact-analysis - Pre-Task Architecture Validation

## Syntax
/impact-analysis TASK-XXX [--depth=DEPTH] [--include-bdd] [--include-tasks]
/impact-analysis "topic description" [--depth=DEPTH]

## Execution Instructions for Claude
1. Parse task ID or topic
2. Call run_impact_analysis()
3. Display formatted results
4. Present decision checkpoint [P]roceed/[R]eview/[S]ystem-plan/[C]ancel
5. Handle user choice
```

### /context-switch Spec Structure

```
# /context-switch - Multi-Project Navigation

## Syntax
/context-switch [project-name]
/context-switch --list

## Execution Instructions for Claude
1. Load GuardKitConfig
2. If --list, show all known projects
3. If no args, show current project
4. If project-name, execute_context_switch()
5. Display orientation summary
```

### Command Spec Patterns (from existing commands)

Each spec must include:
- Command syntax and arguments table
- Execution flow steps
- Output format examples
- Error handling
- CRITICAL EXECUTION INSTRUCTIONS section (tells Claude what to do/not do)
- Graceful degradation messages

## Acceptance Criteria

- [ ] 6 command markdown files created
- [ ] Each spec follows established command pattern (syntax, flow, output, errors)
- [ ] /system-overview spec covers --verbose, --section, --format flags
- [ ] /impact-analysis spec covers task ID and topic modes, depth tiers, decision checkpoint
- [ ] /context-switch spec covers project switch, --list, no-args modes
- [ ] Graceful degradation messages included (no context, Graphiti down)
- [ ] .claude/commands/ and installer/core/commands/ versions are identical
- [ ] CRITICAL EXECUTION INSTRUCTIONS present in each spec

## Test Requirements

No unit tests needed for markdown specs. Validation via E2E tests in TASK-SC-008.

## Implementation Notes

- Study `installer/core/commands/feature-plan.md` for the established pattern
- Study `installer/core/commands/task-review.md` for decision checkpoint pattern
- Study `installer/core/commands/system-plan.md` for system-level command pattern
- The .claude/commands/ versions and installer/core/commands/ versions should be identical content
- Each spec should reference the Python module functions by name
