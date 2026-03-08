---
id: TASK-REV-A00F
title: "Design simplified quality gate profile expansion to replace CSC epic"
status: backlog
created: 2026-03-08T12:00:00Z
updated: 2026-03-08T12:00:00Z
priority: high
tags: [quality-gates, coach-validator, task-types, design-review, architecture]
complexity: 5
task_type: review
decision_required: true
supersedes: [TASK-CSC-001, TASK-CSC-002, TASK-CSC-003, TASK-CSC-004, TASK-CSC-005, TASK-CSC-006, TASK-CSC-007]
related: [TASK-REV-FB22, TASK-REV-CSC1, TASK-FBSDK-025, TASK-FIX-ARIMPL, TASK-TT-001, TASK-FIX-93C1]
---

# Task: Design Simplified Quality Gate Profile Expansion

## Background

The Context-Sensitive Coach (CSC) epic (7 tasks: TASK-CSC-001 through TASK-CSC-007) proposed an AI-powered dynamic profile selection system to address false positives where simple feature tasks fail strict quality gates. A deep review on 2026-03-08 found that **80-90% of the original problem has been solved through incremental profile expansion** since the proposal was written (2026-01-23).

### Problem Originally Identified (TASK-REV-FB22)

Simple `task_type=feature` tasks (e.g., 20-line Pydantic Settings, app init code) were failing arch review (score 0 < threshold 60) and coverage gates (80% required for untestable declarative code).

### What Has Been Fixed Since

| Fix | Task | Impact |
|-----|------|--------|
| task_type data flow to CoachValidator | TASK-FBSDK-025 | Profile system actually works end-to-end |
| Arch review auto-skipped in feature-build | TASK-FIX-ARIMPL | `skip_arch_review=not enable_pre_loop` |
| TESTING task type added | TASK-TT-001 | Test-only tasks bypass feature gates |
| REFACTOR task type added | TASK-TT-001 | Refactor tasks get appropriate profile |
| INTEGRATION task type added | TASK-FIX-93C1 | Wiring tasks bypass arch review/coverage |
| Zero-test blocking is profile-aware | TASK-AQG-002 | Only blocks for FEATURE/REFACTOR |
| Alias normalization | TASK-FIX-7531/7534 | No more `Invalid task_type` failures |
| Scaffolding independent test skip | TASK-FIX-SCAF | Config tasks skip test verification |

### Remaining Gap (10-20%)

**Scenario**: `guardkit autobuild task TASK-XXX` (standalone mode) where `task_type=feature` and implementation is trivial (20-30 LOC declarative code):
- `enable_pre_loop=True` (default for standalone) so `skip_arch_review=False`
- Arch review enforced with threshold 60 -- trivial code scores 0 -- **BLOCKED**
- Coverage 80% enforced for untestable declarative code -- **BLOCKED**

**In feature-build mode**: Mostly mitigated by blanket `skip_arch_review=True` (enable_pre_loop defaults to False), but coverage gates still apply universally to all `task_type=feature` tasks.

### Why CSC Is Over-Engineered

The CSC epic proposes 7 tasks (UniversalContextGatherer, FastClassifier, AIContextAnalyzer, ContextCache, integration, tests, docs) to solve a problem that has been incrementally addressed. The remaining gap is better solved by following the **same pattern** that already resolved similar cases: adding 1-2 new task type profiles.

## Objective

Design a minimal profile expansion that closes the remaining quality gate gap without implementing the full CSC epic. Validate via C4 sequence diagrams that no regressions are introduced.

## Acceptance Criteria

### Design Deliverables
- [ ] Define 1-2 new task types (e.g., `DECLARATIVE`, `SIMPLE_FEATURE`) with appropriate `QualityGateProfile` settings
- [ ] Document profile field values with rationale for each gate threshold
- [ ] Map which existing failing scenarios each new profile addresses

### Execution Flow Validation (C4 Sequence Diagrams)
- [ ] **Path A trace**: `autobuild task` (standalone) with new profile -- sequence diagram from CLI through to `verify_quality_gates()` showing profile resolution
- [ ] **Path B trace**: `autobuild feature` with new profile -- sequence diagram showing feature-build path with `enable_pre_loop` resolution
- [ ] **Path C trace**: `feature-plan` task generation -- sequence diagram showing how new task_type values get assigned during planning
- [ ] **Regression validation**: Confirm existing profiles (FEATURE, SCAFFOLDING, INTEGRATION, etc.) are unchanged and all existing tests continue to pass

### Integration Points to Validate
- [ ] `task_types.py`: New `TaskType` enum values + `QualityGateProfile` entries in `DEFAULT_PROFILES`
- [ ] `task_types.py`: New entries in `TASK_TYPE_ALIASES` if needed
- [ ] `coach_validator.py`: No changes required (verify profile system is generic enough)
- [ ] `autobuild.py`: No changes required (verify task_type flows through unchanged)
- [ ] `feature_orchestrator.py`: No changes required (verify task_type resolution cascade)
- [ ] Feature-plan templates: Where task_type is assigned -- can new types be selected?
- [ ] `normalise_task_type()`: Does it handle the new values correctly?

### Decision Criteria
- [ ] Confirm CSC epic (TASK-CSC-001 through 007) should be archived as superseded
- [ ] Identify if any CSC concepts should be preserved for future consideration
- [ ] Estimate implementation effort for the simplified alternative (expected: 1-2 tasks, <4 hours total)

## Scope

### In Scope
- New `TaskType` enum values and `QualityGateProfile` definitions
- C4 sequence diagrams for all three execution paths
- Regression analysis against existing test suite
- Recommendation for CSC epic disposition (archive/supersede)
- Feature-plan integration: how new task types get assigned to generated tasks

### Out of Scope
- Actual implementation (separate task after review approval)
- AI-based context analysis (explicitly rejected as over-engineered)
- Changes to CoachValidator internals
- Changes to AutoBuildOrchestrator flow

## Key Files to Review

| File | Purpose |
|------|---------|
| `guardkit/models/task_types.py` | TaskType enum, QualityGateProfile, DEFAULT_PROFILES |
| `guardkit/orchestrator/quality_gates/coach_validator.py` | Profile consumption in validation flow |
| `guardkit/orchestrator/autobuild.py` | task_type resolution and propagation |
| `guardkit/orchestrator/feature_orchestrator.py` | enable_pre_loop resolution cascade |
| `guardkit/cli/autobuild.py` | CLI entry points for task/feature commands |
| `tasks/backlog/context-sensitive-coach/` | CSC epic to be superseded |
| `docs/research/context-sensitive-coach-proposal.md` | Original proposal for reference |

## Suggested Profile Design (Starting Point for Review)

```python
# Option A: Single new type
TaskType.DECLARATIVE = "declarative"
# For: Pydantic models, config classes, DTOs, app init, constant definitions
QualityGateProfile(
    arch_review_required=False,
    arch_review_threshold=0,
    coverage_required=False,   # Declarative code has nothing meaningful to test
    coverage_threshold=0.0,
    tests_required=False,      # No logic to test
    plan_audit_required=True,  # Still verify completeness
    zero_test_blocking=False,
    seam_tests_recommended=False,
)

# Option B: Two new types for finer granularity
TaskType.DECLARATIVE = "declarative"   # Zero-logic: DTOs, configs, constants
TaskType.SIMPLE = "simple"             # Light logic: thin wrappers, basic validation
QualityGateProfile(  # SIMPLE
    arch_review_required=False,
    arch_review_threshold=0,
    coverage_required=True,
    coverage_threshold=50.0,   # Relaxed from 80%
    tests_required=True,       # Some logic exists
    plan_audit_required=True,
    zero_test_blocking=False,
    seam_tests_recommended=False,
)
```

## Review Mode

This is a **design review** task. Expected workflow:
1. `/task-review TASK-REV-A00F --mode=architectural --depth=detailed`
2. Review generates C4 sequence diagrams for all paths
3. Decision checkpoint: [A]ccept / [I]mplement / [R]evise / [C]ancel
4. If accepted: Create 1-2 implementation tasks from the approved design

## Implementation Notes

The review should consider:
- **Naming**: `declarative` vs `config` vs `simple_feature` -- what conveys intent best?
- **Feature-plan integration**: Should `/feature-plan` auto-detect and assign these types based on task descriptions containing keywords like "config", "model", "DTO"?
- **Backward compatibility**: Existing tasks with `task_type: feature` must continue to work unchanged
- **Migration**: Should any existing backlog tasks be updated to use new types?

## Test Execution Log
[Automatically populated by /task-work]
