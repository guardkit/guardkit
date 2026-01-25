---
id: TASK-PLD-002
title: Add Decision Tree to Workflow Docs
status: completed
priority: medium
complexity: 2
implementation_mode: direct
parallel_group: wave-1
conductor_workspace: preloop-docs-wave1-2
tags: [documentation, preloop, workflow]
parent_review: TASK-REV-PL01
---

# Add Decision Tree to Workflow Docs

## Description

Add a visual decision tree to `docs/guides/guardkit-workflow.md` helping users decide whether to enable or disable pre-loop for their tasks.

## Requirements

### Decision Tree Content

Add the following decision tree to the AutoBuild section of the workflow guide:

```markdown
## Pre-Loop Decision Guide

Use this decision tree to determine whether pre-loop design phases are needed:

```
Starting AutoBuild?
│
├─► Using feature-build (guardkit autobuild feature)?
│   │
│   ├─► Tasks from /feature-plan?
│   │   └─► Pre-loop NOT needed (default: disabled)
│   │       Tasks already have detailed specs from feature-plan
│   │
│   └─► Custom feature.yaml with minimal task specs?
│       │
│       ├─► Tasks have clear acceptance criteria?
│       │   └─► Pre-loop NOT needed (default: disabled)
│       │
│       └─► Tasks need clarification/design?
│           └─► Use --enable-pre-loop
│               Adds 60-90 min per task for design phases
│
└─► Using task-build (guardkit autobuild task)?
    │
    ├─► Task from /task-create with detailed requirements?
    │   └─► Pre-loop runs by default (can skip with --no-pre-loop)
    │
    └─► Simple bug fix or documentation task?
        └─► Consider --no-pre-loop for faster execution
```

### Quick Reference Table

| Scenario | Command | Pre-Loop? | Duration |
|----------|---------|-----------|----------|
| Feature from feature-plan | `guardkit autobuild feature FEAT-XXX` | No | 15-25 min/task |
| Feature needing design | `guardkit autobuild feature FEAT-XXX --enable-pre-loop` | Yes | 75-105 min/task |
| Standalone task | `guardkit autobuild task TASK-XXX` | Yes | 75-105 min |
| Simple standalone task | `guardkit autobuild task TASK-XXX --no-pre-loop` | No | 15-25 min |
```

## Acceptance Criteria

- [ ] Decision tree added to `docs/guides/guardkit-workflow.md`
- [ ] Quick reference table included
- [ ] Timing estimates are accurate
- [ ] Integrates naturally with existing workflow documentation

## Implementation Notes

Add this section after the existing AutoBuild documentation in the workflow guide. If there's no existing AutoBuild section, create one.

## Files to Modify

- `docs/guides/guardkit-workflow.md`
