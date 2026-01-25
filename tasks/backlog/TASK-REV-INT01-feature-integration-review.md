---
id: TASK-REV-INT01
title: Integration Review - AutoBuild task-work Delegation and Coach Security Integration
status: review_complete
task_type: review
created: 2026-01-01T10:00:00Z
completed: 2026-01-01T12:30:00Z
priority: high
tags: [integration-review, autobuild, security, coach, architectural-review]
complexity: 5
review_mode: architectural
review_depth: standard
features_under_review:
  - id: autobuild-task-work-delegation
    path: tasks/backlog/autobuild-task-work-delegation/
    tasks: 9
  - id: coach-security-integration
    path: tasks/backlog/coach-security-integration/
    tasks: 6
review_results:
  score: 81
  overall_assessment: "Features are complementary and can be developed in parallel"
  findings_count: 6
  recommendations_count: 6
  decision: proceed_parallel
  report_path: .claude/reviews/TASK-REV-INT01-review-report.md
  key_findings:
    - "3 files with overlapping modifications (MEDIUM risk)"
    - "No hard dependencies - flexible implementation order"
    - "Both modify Coach validation; clear integration path exists"
    - "Configurations are orthogonal - easy to merge"
  recommendations:
    - "Parallel development with coordination"
    - "Merge TWD first, then SEC"
    - "Create TASK-INT-001 for unified validation flow"
    - "Security checks run before honesty verification"
  decision_checkpoint:
    choice: implement
    timestamp: 2026-01-01T12:45:00Z
    tasks_created:
      - id: TASK-INT-001
        title: "Unified Coach Validation Flow"
        path: tasks/backlog/feature-integration/TASK-INT-001-unified-coach-validation.md
      - id: TASK-INT-002
        title: "Integration Tests for Combined Features"
        path: tasks/backlog/feature-integration/TASK-INT-002-integration-tests.md
    feature_path: tasks/backlog/feature-integration/
---

# Task: Integration Review - AutoBuild task-work Delegation and Coach Security Integration

## Description

Review the integration between two in-flight features to ensure they will work together correctly and identify any areas requiring coordination or updates.

### Feature 1: AutoBuild task-work Delegation

Routes the AutoBuild Player phase through `task-work --implement-only --mode=tdd` to leverage existing subagent infrastructure. Key changes:

- **TASK-TWD-001**: Modify AgentInvoker.invoke_player() for task-work delegation
- **TASK-TWD-003**: Implement Coach feedback integration with task-work
- **TASK-TWD-007**: Escape Hatch Pattern
- **TASK-TWD-008**: Honesty Verification (Coach verifies Player claims)
- **TASK-TWD-009**: Promise-Based Completion

### Feature 2: Coach Security Integration

Adds security validation capabilities to the Coach agent:

- **TASK-SEC-001**: Quick security checks (always run, ~30s)
- **TASK-SEC-003**: Security-specialist invocation (conditional)
- Modifies Coach validation flow and decision logic

## Review Objectives

### 1. Shared File Analysis

Identify files modified by both features and assess conflict potential:

| File | TWD Changes | SEC Changes | Conflict Risk |
|------|-------------|-------------|---------------|
| `.claude/agents/autobuild-coach.md` | Honesty verification, promise verification | Security validation section | MEDIUM |
| `guardkit/orchestrator/agent_invoker.py` | invoke_player delegation | Likely unchanged | LOW |
| Coach validation logic | New verification methods | Security check integration | HIGH |

### 2. Execution Order Dependencies

Determine if features have execution order requirements:

- Can SEC be implemented before TWD?
- Can TWD be implemented before SEC?
- Are there merge conflicts if both develop in parallel?

### 3. Coach Decision Flow Impact

Both features modify how Coach makes decisions:

**TWD additions**:
- Honesty verification (TWD-008): Coach verifies Player claims before deciding
- Promise verification (TWD-009): Coach maps acceptance criteria to evidence

**SEC additions**:
- Quick security checks: Block on CRITICAL findings
- Full security review: Block on security issues in auth tasks

**Questions**:
- In what order should these checks run?
- How do security findings interact with honesty discrepancies?
- Should security block override honesty approval?

### 4. Player Phase Interactions

TWD routes Player through `task-work --implement-only`. SEC adds security checks to Coach.

**Questions**:
- Does task-work --implement-only already include security checks in Phase 5?
- If so, is SEC duplicating existing security validation?
- Should SEC checks happen in Player phase (via task-work) or Coach phase?

### 5. Configuration Compatibility

Both features may add configuration options:

**TWD**: Development mode (tdd/standard/bdd)
**SEC**: Security level (strict/standard/minimal/skip)

**Questions**:
- Are these configurations orthogonal or overlapping?
- Should they be in same configuration namespace?

## Acceptance Criteria

- [x] Document all shared/conflicting file modifications
- [x] Identify execution order requirements
- [x] Propose unified Coach decision flow with both features
- [x] Recommend merge strategy (sequential or parallel development)
- [x] Flag any design conflicts requiring resolution
- [x] Estimate additional integration work (if needed)

## Review Deliverables

1. **Integration Analysis**
   - File conflict matrix
   - Dependency diagram between features

2. **Unified Decision Flow**
   - Proposed Coach validation order
   - Security + Honesty + Promise verification integration

3. **Recommendations**
   - Implementation order recommendation
   - Integration tasks to add (if needed)
   - Risk assessment

## Files to Review

### AutoBuild task-work Delegation
- `tasks/backlog/autobuild-task-work-delegation/README.md`
- `tasks/backlog/autobuild-task-work-delegation/TASK-TWD-001-modify-agent-invoker.md`
- `tasks/backlog/autobuild-task-work-delegation/TASK-TWD-003-feedback-integration.md`
- `tasks/backlog/autobuild-task-work-delegation/TASK-TWD-008-honesty-verification.md`
- `tasks/backlog/autobuild-task-work-delegation/TASK-TWD-009-promise-completion.md`

### Coach Security Integration
- `tasks/backlog/coach-security-integration/README.md`
- `tasks/backlog/coach-security-integration/TASK-SEC-001-quick-security-checks.md`
- `tasks/backlog/coach-security-integration/TASK-SEC-003-security-specialist-invocation.md`

### Current Implementation
- `.claude/agents/autobuild-coach.md`
- `guardkit/orchestrator/agent_invoker.py`
- `guardkit/orchestrator/autobuild.py`

## Notes

This review should be completed BEFORE either feature begins implementation to avoid costly refactoring. Findings may result in:
- New integration tasks added to one or both features
- Modified task dependencies
- Unified Coach enhancement task that combines both

## Review Mode Guidance

Use **architectural** review mode to:
- Analyze component interactions
- Identify interface conflicts
- Propose unified design
- Assess SOLID/DRY implications of both features combined
