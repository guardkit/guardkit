---
id: TASK-PLD-001
title: Update CLAUDE.md Pre-Loop Section
status: completed
priority: medium
complexity: 3
implementation_mode: direct
parallel_group: wave-1
conductor_workspace: preloop-docs-wave1-1
tags: [documentation, preloop, feature-build]
parent_review: TASK-REV-PL01
---

# Update CLAUDE.md Pre-Loop Section

## Description

Enhance the Pre-Loop Configuration section in CLAUDE.md to better explain:
1. Why pre-loop is disabled by default for feature-build
2. When to enable pre-loop manually
3. The relationship between feature-plan output and pre-loop design phases

## Current State

The CLAUDE.md has a Pre-Loop Configuration section but it focuses on CLI flags without explaining the rationale behind the defaults.

## Requirements

### Add Rationale Section

After the "Default Behavior" bullet points, add explanation:

```markdown
**Why Feature-Build Defaults to Pre-Loop Disabled**:

Tasks created via `/feature-plan` are already "pre-designed":
- Detailed requirements extracted from review analysis
- Acceptance criteria generated from recommendations
- Implementation mode assignments (task-work/direct/manual)
- Wave groupings for parallel execution

Running pre-loop (Phases 1.6-2.8) would duplicate this design work, adding 60-90 minutes per task without additional value.

**Why Task-Build Defaults to Pre-Loop Enabled**:

Standalone tasks (`guardkit autobuild task`) may lack detailed specifications. The pre-loop design phases ensure:
- Requirements are clarified (Phase 1.6)
- Implementation is planned (Phase 2)
- Architecture is reviewed (Phase 2.5)
- Human checkpoint for complex tasks (Phase 2.8)
```

### Add "When to Override Defaults" Section

```markdown
**When to Enable Pre-Loop for Feature-Build**:
- Task has unclear acceptance criteria
- Task requires significant architectural decisions
- First task in a new feature area
- You want explicit human checkpoint before implementation

Command: `guardkit autobuild feature FEAT-XXX --enable-pre-loop`

**When to Disable Pre-Loop for Task-Build**:
- Task has detailed implementation notes in markdown
- Follow-up task where design is already established
- Simple bug fix or documentation update
- You want faster execution

Command: `guardkit autobuild task TASK-XXX --no-pre-loop`
```

## Acceptance Criteria

- [ ] CLAUDE.md Pre-Loop section explains WHY defaults are set
- [ ] Clear guidance on when to override defaults
- [ ] No code changes required
- [ ] Documentation reads naturally and flows logically

## Implementation Notes

This is a documentation-only change. Edit the existing Pre-Loop Configuration section in CLAUDE.md, don't create a new section.

## Files to Modify

- `CLAUDE.md` (Pre-Loop Configuration section)
