---
id: TASK-CMD1-005
title: Condense FAQ and remove JSON examples
status: completed
created: 2026-01-13T11:35:00Z
completed: 2026-01-13T18:00:00Z
priority: medium
tags: [documentation, cleanup]
complexity: 2
parent: TASK-REV-CMD1
implementation_mode: direct
parallel_group: wave-2
conductor_workspace: claude-md-reduction-wave2-2
---

# Task: Condense FAQ and remove JSON examples

## Problem Statement

Root CLAUDE.md contains FAQ sections and detailed JSON examples that add significant bulk but are rarely needed during normal operation.

## Acceptance Criteria

- [x] Remove "Migration Note" subsection from Hash-Based IDs (after moving to rules file)
- [x] Remove detailed JSON examples (player_turn_*.json, coach_turn_*.json) from AutoBuild
- [x] Condense any remaining FAQ to 3 most common questions max
- [x] Move detailed examples to docs/ if needed for reference

## Implementation Notes

### Content to Remove from AutoBuild (in rules/autobuild.md)

The following JSON examples can be condensed to schema references:

**Player Report** (remove full JSON, keep summary):
```markdown
**Player Report** (`.guardkit/autobuild/TASK-XXX/player_turn_N.json`):
Fields: task_id, turn, files_modified, files_created, tests_written, tests_run, tests_passed, implementation_notes, concerns, requirements_addressed/remaining
```

**Coach Decision** (remove full JSON, keep summary):
```markdown
**Coach Decision** (`.guardkit/autobuild/TASK-XXX/coach_turn_N.json`):
Fields: task_id, turn, decision, validation_results, rationale
```

### Content to Remove from root

- "Migration Note" subsection in Hash-Based IDs (will be in rules file)
- Any FAQ with more than 3 questions

### FAQ Consolidation Rule

Keep only these 3 questions in any FAQ section:
1. Most common user confusion point
2. Most common error scenario
3. Most common "how do I..." question

## Estimated Savings

~2,000 characters total

## Related Files

- Source: `/CLAUDE.md` (various sections)
- Target: `.claude/rules/autobuild.md` (after TASK-CMD1-001)
