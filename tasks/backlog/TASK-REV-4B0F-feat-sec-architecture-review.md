---
id: TASK-REV-4B0F
title: "Review FEAT-SEC architecture for feature-build compatibility"
status: completed
task_type: review
created: 2026-01-24T16:00:00Z
updated: 2026-01-24T17:00:00Z
priority: high
tags: [architecture-review, security, feature-build, coach-integration]
complexity: 5
decision_required: true
review_mode: architectural
review_depth: standard
review_results:
  mode: architectural
  depth: standard
  score: 62
  findings_count: 5
  recommendations_count: 5
  decision: implement_with_modifications
  report_path: .claude/reviews/TASK-REV-4B0F-review-report.md
  completed_at: 2026-01-24T17:00:00Z
  implementation_action: "Modified subtask files to reflect revised architecture"
---

# Task: Review FEAT-SEC Architecture for Feature-Build Compatibility

## Problem Statement

The Coach Security Integration feature (`FEAT-SEC`) and its subtasks in `tasks/backlog/coach-security-integration/` were designed **before the `/feature-build` command was fully implemented**. The architecture and design may contain assumptions, patterns, or integration points that are now outdated or incompatible with the current AutoBuild Player-Coach workflow.

Key concerns to investigate:

1. **Integration Points**: The proposed `security_checker.py` integration with `coach_validator.py` may not align with how Coach actually works (Option D: reads task-work results, doesn't reimplement gates)

2. **Agent Invocation Pattern**: The design proposes invoking `security-specialist` via Task tool, but the current Coach agent is read-only and doesn't invoke other agents

3. **Quality Gate Flow**: Security checks are proposed to run during Coach validation, but the current architecture has quality gates run by Player (task-work), not Coach

4. **Feature File Structure**: The `FEAT-SEC.yaml` may need updates to align with current feature-build orchestration patterns

5. **Task File Structure**: Individual subtask files may need frontmatter updates for AutoBuild compatibility

## Scope

### In Scope

- `.guardkit/features/FEAT-SEC.yaml` - Feature definition file
- `tasks/backlog/coach-security-integration/` - All 6 subtask files
- `guardkit/orchestrator/quality_gates/coach_validator.py` - Current Coach implementation
- `guardkit/orchestrator/quality_gates/pre_loop.py` - Pre-loop quality gate integration
- `installer/core/commands/feature-build.md` - Current feature-build specification
- `.claude/agents/autobuild-coach.md` - Coach agent definition
- `.claude/agents/autobuild-player.md` - Player agent definition

### Out of Scope

- Actual implementation of security features (that's for subtasks)
- Performance optimization concerns
- Non-security quality gates

## Review Questions

### Architecture Alignment

1. Does the two-tier security model (quick checks + full review) fit within the current Coach validation flow?
2. Should security checks run in Player (during task-work) or Coach (during validation)?
3. Is invoking `security-specialist` agent from Coach architecturally sound, or does it violate Coach's read-only principle?

### Implementation Patterns

4. Does the proposed `security_checker.py` module fit the existing quality gate patterns in `guardkit/orchestrator/quality_gates/`?
5. Are the proposed dataclasses (`SecurityFinding`, etc.) consistent with existing models?
6. Is the async `invoke_security_specialist()` function compatible with the current synchronous Coach validation?

### Feature-Build Compatibility

7. Does `FEAT-SEC.yaml` have all required fields for `/feature-build` execution?
8. Do the subtask files have proper `requirements` and `acceptance_criteria` fields?
9. Are the parallel groups correctly defined for the dependency graph?
10. Do the `implementation_mode` values (task-work, direct) make sense for each subtask?

### Task Type Integration

11. Does the design account for the task type system (`TaskType`, `QualityGateProfile`)?
12. Should security-focused tasks have a custom task type?

## Expected Deliverables

1. **Architecture Assessment**: Score current design against SOLID/DRY/YAGNI (target: 85+)
2. **Compatibility Matrix**: Which subtasks are compatible vs need modification
3. **Recommended Changes**: Specific modifications needed for each file
4. **Risk Assessment**: Impact of implementing as-is vs with modifications
5. **Decision Recommendation**: Proceed, modify, or redesign

## Acceptance Criteria

- [ ] Reviewed all 6 subtask files in coach-security-integration/
- [ ] Analyzed FEAT-SEC.yaml against current feature-build spec
- [ ] Compared proposed coach_validator.py changes with actual implementation
- [ ] Identified all architectural misalignments
- [ ] Provided specific recommendations for each subtask
- [ ] Recommended action: [I]mplement / [R]evise / [R]edesign
- [ ] Created follow-up tasks if modifications needed

## Files to Review

| File | Purpose | Key Questions |
|------|---------|---------------|
| `.guardkit/features/FEAT-SEC.yaml` | Feature definition | Orchestration correct? |
| `TASK-SEC-001-quick-security-checks.md` | Quick checks task | Integration point valid? |
| `TASK-SEC-002-security-config-schema.md` | Config schema task | Fits existing patterns? |
| `TASK-SEC-003-security-specialist-invocation.md` | Agent invocation | Read-only violation? |
| `TASK-SEC-004-task-tagging-detection.md` | Tag detection | Where should this run? |
| `TASK-SEC-005-security-validation-tests.md` | Test coverage | Correct task_type? |
| `TASK-SEC-006-coach-documentation-update.md` | Documentation | Scope appropriate? |
| `guardkit/orchestrator/quality_gates/coach_validator.py` | Current Coach | Integration points? |
| `guardkit/orchestrator/quality_gates/pre_loop.py` | Pre-loop gates | Alternative location? |

## Notes

- Original design source: TASK-REV-SEC1 review
- Feature complexity: 5/10 (originally estimated)
- Estimated duration: 6 subtasks across 4 waves (~13 hours)
- This review should take ~1-2 hours (standard depth)

## Review Command

```bash
/task-review TASK-REV-4B0F --mode=architectural --depth=standard
```
