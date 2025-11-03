---
id: TASK-024
title: Audit core user guides - Remove RequireKit features
status: backlog
created: 2025-11-03T20:31:00Z
updated: 2025-11-03T20:31:00Z
priority: high
tags: [documentation, audit, requirekit-separation, user-guides]
complexity: 6
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Audit core user guides - Remove RequireKit features

## Description

Review and update essential user-facing guides to ensure they only document Taskwright features. These are critical onboarding documents that users encounter first.

## Scope

**Files to audit:**
- docs/guides/GETTING-STARTED.md
- docs/guides/QUICK_REFERENCE.md  
- docs/guides/taskwright-workflow.md

**Estimated: ~2000 lines combined**

## Acceptance Criteria

- [ ] Remove BDD mode workflow references (RequireKit feature)
- [ ] Remove EARS notation examples and explanations (RequireKit feature)
- [ ] Remove epic/feature hierarchy examples (RequireKit feature)
- [ ] Remove PM tool synchronization instructions (RequireKit feature)
- [ ] Remove requirements traceability examples (RequireKit feature)
- [ ] Update command examples to use Taskwright-only syntax
- [ ] Fix GitHub URLs to correct repositories
- [ ] Add "Need requirements management?" callout boxes with RequireKit links
- [ ] Ensure workflow diagrams show Taskwright-only flow
- [ ] Verify all command examples work without RequireKit installed

## RequireKit Features to Remove/Link

**Remove from guides:**
- `/task-create` with `epic:`, `feature:`, `requirements:`, `bdd:` parameters
- Epic and feature management workflows
- Requirements-to-task linking workflows
- BDD scenario generation workflows
- PM tool export workflows

**Keep in guides:**
- `/task-create "Title" priority:high tags:[tag1,tag2]` (basic syntax)
- `/task-work TASK-XXX` (with `--mode=standard|tdd` only, remove `bdd` mode)
- `/task-complete`, `/task-status`, `/task-refine`
- Quality gates workflow
- Complexity evaluation
- Design-first workflow
- Template-based initialization

## Where to Add RequireKit Integration Notes

Add integration callouts in these sections:
- After basic task creation examples
- In "Advanced Workflows" sections
- When discussing requirements or specifications
- In workflow decision trees

Example callout format:
```markdown
> **Need Formal Requirements?**  
> RequireKit adds EARS notation, BDD scenarios, and epic/feature hierarchy.  
> See: https://github.com/requirekit/require-kit
```

## Implementation Notes

### GETTING-STARTED.md
- Focus on 5-minute quickstart with basic features only
- Show simple task creation → work → complete flow
- Add RequireKit callout at the end of "Next Steps"

### QUICK_REFERENCE.md
- Remove RequireKit command parameters from syntax tables
- Keep simple parameter examples only
- Add "Extended Features" section pointing to RequireKit

### taskwright-workflow.md
- Update workflow diagrams to show Taskwright-only states
- Remove Requirements Analysis phase references
- Keep quality gates and test enforcement sections

## Test Requirements

- [ ] Follow each guide step-by-step without RequireKit installed
- [ ] Verify all command examples execute successfully
- [ ] Check that links point to correct documentation
- [ ] Ensure workflow diagrams are accurate
- [ ] Validate code blocks have correct syntax highlighting
