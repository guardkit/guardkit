---
id: TASK-024
title: Audit core user guides - Remove RequireKit features
status: completed
created: 2025-11-03T20:31:00Z
updated: 2025-11-03T21:20:00Z
completed: 2025-11-03T21:20:00Z
priority: high
tags: [documentation, audit, requirekit-separation, user-guides]
complexity: 6
previous_state: in_review
state_transition_reason: "All acceptance criteria met, all quality gates passed"
completed_location: tasks/completed/TASK-024/
organized_files: [
  "TASK-024-audit-core-user-guides.md",
  "implementation-summary.md",
  "test-verification-report.md",
  "validation-script.py",
  "validation-report.json"
]
duration_hours: 0.8
actual_effort: "~45 minutes (planning, implementation, validation, review)"
test_results:
  status: passed
  critical_tests: 51
  critical_passed: 51
  critical_pass_rate: 100
  total_tests: 72
  total_passed: 61
  total_pass_rate: 84.7
  non_critical_issues: 11
  last_run: "2025-11-03T21:12:00Z"

implementation_plan:
  file_path: "docs/state/TASK-024/implementation_plan.json"
  markdown_path: "docs/state/TASK-024/implementation_plan.md"
  generated_at: "2025-11-03T21:05:00Z"
  version: 1
  approved: true
  approved_by: "timeout"
  approved_at: "2025-11-03T21:10:00Z"
  auto_approved: true
  review_mode: "quick_optional"
  review_duration_seconds: 10

complexity_evaluation:
  score: 6
  level: "medium"
  file_path: "docs/state/TASK-024/complexity_score.json"
  calculated_at: "2025-11-03T21:05:00Z"
  review_mode: "quick_optional"
  forced_review_triggers: []
  factors:
    file_complexity: 1.5
    pattern_familiarity: 0.5
    risk_level: 1.5
    dependency_complexity: 0
  total_factors: 4
  force_triggers_present: false

code_review:
  quality_score: 9.2
  status: "approved"
  critical_issues: 0
  major_issues: 0
  minor_issues: 2
  reviewed_at: "2025-11-03T21:13:00Z"
  reviewer: "code-reviewer"

plan_audit:
  status: "approved"
  severity: "low"
  approved_by: "timeout"
  approved_at: "2025-11-03T21:15:00Z"
  files_planned: 3
  files_actual: 3
  loc_variance_percent: 14.1
  extra_files: 0
  extra_dependencies: 0
  scope_creep_detected: false
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

- [x] Remove BDD mode workflow references (RequireKit feature)
- [x] Remove EARS notation examples and explanations (RequireKit feature)
- [x] Remove epic/feature hierarchy examples (RequireKit feature)
- [x] Remove PM tool synchronization instructions (RequireKit feature)
- [x] Remove requirements traceability examples (RequireKit feature)
- [x] Update command examples to use Taskwright-only syntax
- [x] Fix GitHub URLs to correct repositories
- [x] Add "Need requirements management?" callout boxes with RequireKit links
- [x] Ensure workflow diagrams show Taskwright-only flow
- [x] Verify all command examples work without RequireKit installed

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

- [x] Follow each guide step-by-step without RequireKit installed
- [x] Verify all command examples execute successfully
- [x] Check that links point to correct documentation
- [x] Ensure workflow diagrams are accurate
- [x] Validate code blocks have correct syntax highlighting
