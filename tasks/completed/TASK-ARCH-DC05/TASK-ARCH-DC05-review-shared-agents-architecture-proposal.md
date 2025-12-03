---
id: TASK-ARCH-DC05
title: Review shared agents architecture proposal and create implementation tasks
status: review_complete
created: 2025-11-28T16:00:00Z
updated: 2025-11-28T20:30:00Z
priority: high
tags: [architecture, review, refactoring, shared-agents]
complexity: 0
task_type: review
decision_required: true
review_results:
  mode: architectural
  depth: comprehensive
  score: 82
  grade: "B+"
  recommendation: "APPROVE WITH LEAN IMPLEMENTATION"
  findings_count: 8
  critical_modifications_count: 1
  approach: "lean"
  tasks_created: 6
  estimated_duration: "1-2 days"
  report_path: .claude/reviews/TASK-ARCH-DC05-shared-agents-architectural-review.md
  implementation_plan_path: tasks/backlog/shared-agents-refactoring/IMPLEMENTATION-PLAN-LEAN.md
  implementation_plan_original_path: tasks/backlog/shared-agents-refactoring/archive/IMPLEMENTATION-PLAN.md
  test_plan_path: tests/integration/shared-agents/TEST-PLAN.md
  risk_plan_path: .claude/reviews/TASK-ARCH-DC05-risk-mitigation-plan.md
  completed_at: 2025-11-28T21:00:00Z
  decision_notes: "User chose lean approach (6 tasks vs 38) - pragmatic over perfect"
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Review shared agents architecture proposal and create implementation tasks

## Context

The shared agents architecture proposal ([docs/proposals/shared-agents-architecture-proposal.md](../../docs/proposals/shared-agents-architecture-proposal.md)) has been **approved** and outlines a plan to eliminate agent duplication between GuardKit and RequireKit by creating a dedicated `shared-agents` repository.

**Current Status**: Approved (November 28, 2025)

**Problem**: Both GuardKit and RequireKit maintain duplicate copies of universal agents (`requirements-analyst`, `bdd-generator`, `test-orchestrator`, `code-reviewer`), leading to:
- Version drift
- Maintenance burden
- Inconsistent behavior
- Testing complexity

**Agreed Solution**: Hybrid approach with build-time composition using a dedicated `guardkit/shared-agents` repository.

## Description

This review task will:

1. **Analyze the proposal** - Review the approved architecture for completeness and feasibility
2. **Identify risks** - Assess technical, operational, and user impact risks
3. **Create implementation task breakdown** - Generate detailed tasks for the 5-phase migration plan
4. **Define success criteria** - Establish measurable outcomes for each phase
5. **Plan testing strategy** - Define integration and regression testing approach
6. **Document decisions** - Capture key architectural decisions and rationale

## Review Scope

### Areas to Analyze

1. **Architecture Design**
   - Build-time composition strategy
   - Version pinning mechanism
   - Offline fallback approach
   - Directory structure after installation

2. **Technical Implementation**
   - GitHub Actions release workflow
   - Installer script modifications
   - Manifest.json structure
   - Fallback mechanism design

3. **Migration Strategy**
   - 5-phase migration plan feasibility
   - Dependencies between phases
   - Rollback procedures
   - Testing requirements

4. **Risk Assessment**
   - Breaking changes to existing users
   - CI/CD pipeline impacts
   - Version compatibility matrix
   - Offline installation scenarios

5. **Future Extensibility**
   - MCP server integration path
   - Additional shared resources (commands, templates)
   - Cross-repository agent discovery

## Acceptance Criteria

### Analysis Deliverables

- [ ] **Architectural Review Report**
  - SOLID/DRY/YAGNI compliance assessment
  - Dependency Inversion Principle (DIP) analysis
  - Identified architectural risks
  - Recommended mitigations

- [ ] **Task Breakdown Document**
  - Phase 1: Create shared-agents repository (tasks)
  - Phase 2: Update GuardKit (tasks)
  - Phase 3: Update RequireKit (tasks)
  - Phase 4: Integration testing (tasks)
  - Phase 5: Documentation & release (tasks)
  - Estimated effort per task
  - Dependencies between tasks

- [ ] **Testing Strategy**
  - Unit test requirements
  - Integration test scenarios
  - Regression test checklist
  - Offline fallback testing
  - Version compatibility matrix testing

- [ ] **Risk Mitigation Plan**
  - Identified risks with severity (high/medium/low)
  - Mitigation strategies for each risk
  - Rollback procedures
  - User communication plan

### Decision Outputs

- [ ] **Implementation Priority**
  - Recommended execution order
  - Critical path identification
  - Quick wins vs. complex changes

- [ ] **Breaking Changes Assessment**
  - Identified breaking changes
  - Backward compatibility strategy
  - User migration guide requirements

- [ ] **Success Metrics**
  - How to measure migration success
  - Quality gates for each phase
  - Acceptance criteria for completion

## Review Mode

**Suggested**: `--mode=architectural --depth=comprehensive`

**Rationale**:
- This is a cross-repository refactoring affecting two projects
- Architectural compliance is critical (DIP, single source of truth)
- Comprehensive analysis needed for risk assessment
- Multiple stakeholders (GuardKit users, RequireKit users)

## Expected Outputs

### 1. Architectural Review Report

Location: `.claude/reviews/TASK-ARCH-DC05-shared-agents-architectural-review.md`

Format:
```markdown
# Shared Agents Architecture Review

## Executive Summary
[Recommendation: Approve/Modify/Reject]

## SOLID Principles Compliance
- Single Responsibility: [Analysis]
- Dependency Inversion: [Analysis]
- [etc.]

## Identified Risks
1. [Risk 1] - Severity: High/Medium/Low
   - Impact: [description]
   - Mitigation: [strategy]

## Recommendations
[Key recommendations for implementation]

## Score: X/100
[Architectural quality score]
```

### 2. Implementation Task Breakdown

Location: `tasks/backlog/shared-agents-refactoring/IMPLEMENTATION-PLAN.md`

Format:
```markdown
# Shared Agents Refactoring - Implementation Plan

## Phase 1: Create Shared Agents Repository
- TASK-001: Create repository structure
- TASK-002: Migrate universal agents
- TASK-003: Create manifest.json
- TASK-004: Set up GitHub Actions
- TASK-005: Create v1.0.0 release

## Phase 2: Update GuardKit
[Detailed task breakdown]

## Phase 3: Update RequireKit
[Detailed task breakdown]

## Phase 4: Integration Testing
[Detailed task breakdown]

## Phase 5: Documentation & Release
[Detailed task breakdown]
```

### 3. Task Files

Create individual task files in `tasks/backlog/shared-agents-refactoring/`:
- `TASK-SHA-001-create-repository-structure.md`
- `TASK-SHA-002-migrate-universal-agents.md`
- `TASK-SHA-003-create-manifest-json.md`
- etc.

Each task should include:
- Clear acceptance criteria
- Estimated effort
- Dependencies
- Test requirements

## Questions to Answer

1. **Architecture**
   - Is the build-time composition approach optimal?
   - Are there simpler alternatives we should consider?
   - What are the DIP implications?

2. **Version Management**
   - Is semantic versioning appropriate?
   - How do we handle version conflicts?
   - What's the rollback strategy?

3. **User Impact**
   - Do existing users need to take action?
   - Is this a breaking change?
   - How do we communicate this?

4. **Testing**
   - What are the critical integration test scenarios?
   - How do we test offline fallback?
   - How do we test version pinning?

5. **Future Work**
   - What's the MCP migration path?
   - Can we share commands and templates?
   - How does this affect agent discovery?

## Testing Requirements

This is a review task - no code implementation testing required.

However, the review should define testing requirements for the implementation tasks:

- [ ] GuardKit standalone installation testing
- [ ] RequireKit standalone installation testing
- [ ] Combined installation testing
- [ ] Version pinning testing (different versions)
- [ ] Offline fallback testing
- [ ] CI/CD pipeline testing
- [ ] Agent discovery testing

## Related Documents

- **Proposal**: [docs/proposals/shared-agents-architecture-proposal.md](../../docs/proposals/shared-agents-architecture-proposal.md)
- **Agent Discovery**: [docs/guides/agent-discovery-guide.md](../../docs/guides/agent-discovery-guide.md)
- **DIP Principles**: [docs/research/bdd-mode-removal-decision.md](../../docs/research/bdd-mode-removal-decision.md) (DIP examples)

## Notes

### Proposal Key Points

**Architecture**: Dedicated `guardkit/shared-agents` repository with build-time download during installation.

**Agents to Share**:
1. `requirements-analyst.md` - EARS validation
2. `bdd-generator.md` - Gherkin scenario creation
3. `test-orchestrator.md` - Test execution coordination
4. `code-reviewer.md` - Quality standards enforcement

**Version Pinning**: Each repo has `installer/shared-agents-version.txt` specifying the version to download.

**Offline Fallback**: Bundled fallback agents if GitHub download fails.

**Migration Timeline**: 5 phases over 5 days (approved plan).

### Critical Success Factors

1. **Zero Disruption**: Existing users should not experience breaking changes
2. **Standalone Works**: Both GuardKit and RequireKit continue to work independently
3. **Easy Updates**: Bumping version in pinning file + re-run installer
4. **DIP Compliance**: No runtime dependencies on shared-agents repository
5. **Rollback Safety**: Can revert to previous version if issues discovered

### Review Focus Areas

**High Priority**:
- DIP compliance (no runtime dependencies)
- Breaking change assessment
- Rollback procedure validation
- Offline fallback reliability

**Medium Priority**:
- CI/CD integration complexity
- Version compatibility matrix
- Testing strategy completeness

**Low Priority**:
- Future MCP migration path
- Sharing additional resources beyond agents
