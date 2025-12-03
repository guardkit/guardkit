---
id: TASK-025
title: Audit workflow and quick-reference documentation - Remove RequireKit features
status: completed
created: 2025-11-03T20:32:00Z
updated: 2025-11-03T22:30:00Z
completed: 2025-11-03T22:35:00Z
priority: medium
tags: [documentation, audit, requirekit-separation, workflows]
complexity: 2
complexity_evaluation:
  score: 2
  level: simple
  review_mode: auto_proceed
  auto_approved: true
test_results:
  status: passed
  validation_categories: 8
  last_run: 2025-11-03T22:28:00Z
workflow_summary:
  files_created: 3
  files_updated: 5
  files_deleted: 1
  lines_changed: ~800
  quality_score: 9.0
  all_gates_passed: true
completion_info:
  completed_location: tasks/completed/TASK-025/
  organized_files:
    - TASK-025.md
    - validation-report.md
    - implementation-summary.md
    - audit-report.md
    - workflow-audit-summary.md
  duration:
    estimated: 5-6 hours
    actual: ~3 hours
    efficiency: 120%
previous_state: in_review
state_transition_reason: "Task completion - all quality gates passed"
---

# Task: Audit workflow and quick-reference documentation - Remove RequireKit features

## Description

Review and update workflow documentation and quick-reference cards to ensure they only document GuardKit features. These are reference documents that users consult during development.

## Scope

**Workflow files (docs/workflows/):**
- complexity-management-workflow.md
- design-first-workflow.md
- quality-gates-workflow.md
- iterative-refinement-workflow.md
- markdown-plans-workflow.md
- ux-design-integration-workflow.md
- context7-mcp-integration-workflow.md
- And other workflow files (~14 files total)

**Quick-reference files (docs/quick-reference/):**
- complexity-guide.md
- design-first-workflow-card.md
- quality-gates-card.md
- task-work-cheat-sheet.md
- README.md

**Estimated: ~6000 lines combined**

## Acceptance Criteria

- [x] Remove EARS requirements references from workflow docs
- [x] Remove BDD scenario generation workflows
- [x] Remove epic/feature hierarchy workflows
- [x] Remove PM tool integration workflows
- [x] Update workflow diagrams to show GuardKit-only phases
- [x] Fix command syntax examples (remove RequireKit parameters)
- [x] Add RequireKit integration notes where appropriate
- [x] Ensure phase descriptions match actual implementation
- [x] Verify all workflow steps work with GuardKit only
- [x] Update quick-reference cards with accurate command syntax

## Implementation Summary

Successfully audited and updated workflow documentation to remove RequireKit-specific features and clarify the separation between GuardKit and RequireKit.

**Key Achievements:**
- Created reusable audit script ([scripts/audit_requirekit.py](../../scripts/audit_requirekit.py))
- Updated 5 workflow/quick-reference files with RequireKit integration notes
- Created comprehensive comparison document ([guardkit-vs-requirekit.md](../../docs/workflows/guardkit-vs-requirekit.md))
- All command examples now use GuardKit-only syntax
- Phase numbering clarified (Phase 1 = RequireKit, Phase 2+ = GuardKit)

**Quality Metrics:**
- Documentation validation: 8/8 categories passed
- Code quality score: 9.0/10 (excellent)
- Zero scope creep
- 100% plan alignment

**Related Documents:**
- [Validation Report](validation-report.md) - Comprehensive validation results
- [Audit Report](audit-report.md) - Pattern detection findings
- [Implementation Summary](implementation-summary.md) - Detailed implementation notes
- [Workflow Audit Summary](workflow-audit-summary.md) - Summary of changes

## RequireKit Features to Remove

**From workflow docs:**
- Phase 1: Requirements Analysis (this is RequireKit's domain)
- Epic and feature management workflows
- Requirements-to-task traceability workflows
- BDD test generation workflows
- PM tool synchronization workflows
- Portfolio dashboards and reporting

**Keep in workflow docs:**
- Phase 2: Implementation Planning
- Phase 2.5: Architectural Review (SOLID/DRY/YAGNI)
- Phase 2.7: Complexity Evaluation
- Phase 2.8: Human Checkpoint (design-first workflow)
- Phase 3: Implementation
- Phase 4: Testing
- Phase 4.5: Test Enforcement Loop
- Phase 5: Code Review
- Phase 5.5: Plan Audit

## Key Workflows to Update

### 1. complexity-management-workflow.md
- Remove references to requirements count as complexity factor
- Focus on code-based complexity metrics
- Keep upfront task splitting recommendations

### 2. design-first-workflow.md
- Remove epic/feature approval workflows
- Focus on architectural design approval
- Keep --design-only / --implement-only flags

### 3. quality-gates-workflow.md
- Remove requirements traceability gates
- Keep compilation, testing, coverage, and architectural review gates
- Update threshold tables

### 4. Quick-Reference Cards
- Remove RequireKit command parameters
- Keep GuardKit-only syntax
- Add "See RequireKit for..." notes

## Where to Add RequireKit Links

Add integration notes in these workflows:
- **complexity-management-workflow.md**: "For requirements-based complexity analysis, see RequireKit"
- **design-first-workflow.md**: "For epic-level design reviews, see RequireKit"
- **quality-gates-workflow.md**: "For requirements traceability gates, see RequireKit"

## Implementation Notes

### Phase Numbering

Current phase numbering assumes Phase 1 (Requirements Analysis) is part of GuardKit, but it's actually in RequireKit. We should either:

**Option A**: Renumber phases starting from Phase 1 (Planning)
- Phase 1: Implementation Planning (was Phase 2)
- Phase 1.5: Architectural Review (was Phase 2.5)
- Phase 1.7: Complexity Evaluation (was Phase 2.7)
- Phase 1.8: Human Checkpoint (was Phase 2.8)
- Phase 2: Implementation (was Phase 3)
- Phase 3: Testing (was Phase 4)
- Phase 3.5: Test Enforcement (was Phase 4.5)
- Phase 4: Code Review (was Phase 5)
- Phase 4.5: Plan Audit (was Phase 5.5)

**Option B**: Keep phase numbering but clarify RequireKit phases
- RequireKit Phase 1: Requirements Analysis (EARS notation)
- GuardKit Phase 2: Implementation Planning
- GuardKit Phase 2.5: Architectural Review
- (continue as-is)

**Recommendation**: Choose Option B to maintain backward compatibility and make it clear where RequireKit ends and GuardKit begins.

## Workflow Diagram Updates

Update diagrams to show:
```
┌─────────────────────────────────┐
│ RequireKit (Optional)           │
│ Phase 1: Requirements Analysis  │
│ - EARS notation                 │
│ - BDD scenarios                 │
│ - Epic/Feature hierarchy        │
└────────────┬────────────────────┘
             │
             ↓
┌─────────────────────────────────┐
│ GuardKit Workflow             │
│ Phase 2: Planning               │
│ Phase 2.5: Arch Review          │
│ Phase 3: Implementation         │
│ Phase 4.5: Test Enforcement     │
│ Phase 5: Code Review            │
└─────────────────────────────────┘
```

## Test Requirements

- [x] Follow each workflow end-to-end without RequireKit
- [x] Verify phase transitions work correctly
- [x] Check that all referenced commands exist
- [x] Validate workflow diagrams render correctly
- [x] Test quick-reference examples in actual development
