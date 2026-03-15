---
id: TASK-IGP-002
title: Document two-phase seeding architecture in init output
status: completed
created: 2026-03-15T12:30:00Z
updated: 2026-03-15T13:15:00Z
completed: 2026-03-15T13:15:00Z
completed_location: tasks/completed/TASK-IGP-002/
priority: low
tags: [init, graphiti, documentation, ux]
task_type: implementation
parent_review: TASK-REV-A73F
feature_id: FEAT-IGP
implementation_mode: direct
wave: 1
complexity: 2
depends_on: []
previous_state: in_review
state_transition_reason: "All acceptance criteria met - documentation and console output changes only"
test_results:
  status: not_applicable
  coverage: null
  last_run: null
---

# Task: Document two-phase seeding architecture in init output

## Description

Improve the init command's console output and the Graphiti knowledge documentation to clearly explain the two-phase seeding architecture:

1. `guardkit init` seeds **project-specific** knowledge (project overview from CLAUDE.md/README.md)
2. `guardkit graphiti seed-system` seeds **system-scoped** knowledge (templates, rules, role constraints, implementation modes)

This is a documentation/messaging improvement identified in TASK-REV-A73F Recommendation 3.

## Context

From TASK-REV-A73F review:
- The boundary between project and system seeding is clean at the code level
- But the user-facing messaging doesn't explain WHY there are two phases
- Users need to understand what each command does and when to run them
- `--copy-graphiti` should be encouraged for multi-project FalkorDB setups

## Acceptance Criteria

- [x] Init success message briefly explains what was seeded (project overview) and what still needs seeding (system knowledge)
- [x] `.claude/rules/graphiti-knowledge.md` has a section explaining the two-phase architecture
- [x] `--copy-graphiti` is mentioned as the recommended path for multi-project FalkorDB setups
- [x] No code logic changes (documentation and console output only)

## Key Files

- `guardkit/cli/init.py` - Update summary output (around line 801-812)
- `.claude/rules/graphiti-knowledge.md` - Add two-phase seeding section

## Implementation Notes

This is a small documentation task. Update the "Next steps" section in init.py to be more informative:

```python
console.print("\n[bold green]GuardKit initialized successfully![/bold green]")
console.print(f"\n  Seeded: project overview (from CLAUDE.md)")
console.print(f"  Not yet seeded: system knowledge (templates, rules, constraints)")
console.print(f"\nNext steps:")
console.print(f"  1. Seed system knowledge: guardkit graphiti seed-system")
```

If TASK-IGP-001 lands first, this task should adjust to reflect that system seeding may have already run.
