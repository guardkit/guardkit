# Architectural Review: Feature-Build Quality Gates Integration

**Task ID**: TASK-REV-B601
**Review Mode**: Architectural
**Review Depth**: Comprehensive
**Date**: 2025-12-29
**Reviewer**: Claude Code (Architectural Review Agent)

---

## Executive Summary

This review analyzes the output from `/feature-build FEAT-0E25` and proposes how to integrate `/task-work` quality gates into the feature-build autonomous workflow while preserving autonomy.

### Key Findings

| Area | Current State | Gap | Risk |
|------|---------------|-----|------|
| Architectural Review | Not present | Player-Coach loop lacks SOLID/DRY/YAGNI validation | Medium |
| Complexity Evaluation | Not present | No routing to different review modes | Low |
| Test Enforcement | Basic (Coach runs tests) | No auto-fix loop, no coverage gates | High |
| Code Review | Implicit (Coach validates) | No structured code review phase | Medium |
| Plan Audit | Not present | No scope creep detection | Medium |

**Overall Assessment**: Feature-build successfully implements autonomous task execution but lacks the guardrails that prevent architectural drift, test coverage decay, and scope creep that task-work enforces.

---

## Current Feature-Build Execution Flow

Based on analysis of `docs/reviews/feature-build/feature-build-output.md`:

### Three-Phase Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     FEATURE BUILD FLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PHASE 1: SETUP                                                 │
│  ├── Load feature file (.guardkit/features/FEAT-XXX.yaml)       │
│  ├── Create git worktree (.guardkit/worktrees/FEAT-XXX/)        │
│  └── Initialize branch (autobuild/FEAT-XXX)                     │
│                                                                 │
│  PHASE 2: DIALECTICAL LOOP (per task, per wave)                 │
│  ├── Player: Implement (Read, Write, Edit, Bash)                │
│  ├── Coach: Validate (Read-only, runs tests)                    │
│  └── Loop until: APPROVE or MAX_TURNS                           │
│                                                                 │
│  PHASE 3: FINALIZE                                              │
│  ├── Update feature YAML status                                 │
│  ├── Preserve worktree (never auto-merge)                       │
│  └── Display summary                                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Observations from FEAT-0E25 Execution

1. **Parallel Wave Execution**: Tasks within waves executed in parallel (Wave 1: TASK-INFRA-001 + TASK-INFRA-005)
2. **Player Reports**: Structured implementation summaries with files created/modified
3. **Coach Validation**: Independent test execution, acceptance criteria verification
4. **No Architectural Review**: Player implemented freely without SOLID/DRY/YAGNI scoring
5. **No Coverage Gates**: Tests passed but coverage not measured or enforced
6. **No Plan Audit**: No detection of scope creep or variance from plan

---

## Task-Work Quality Gates (To Be Integrated)

Based on analysis of `installer/core/commands/task-work.md`:

### Quality Gate Phases

| Phase | Name | Purpose | Current in Feature-Build? |
|-------|------|---------|---------------------------|
| 2.5A | Pattern Suggestion | Design patterns via MCP | No |
| 2.5B | Architectural Review | SOLID/DRY/YAGNI scoring | No |
| 2.7 | Complexity Evaluation | Route to review modes | No |
| 2.8 | Human Checkpoint | Approval gate | No (Coach serves similar purpose) |
| 4.5 | Test Enforcement Loop | Auto-fix up to 3 attempts | Partial (Coach validates but no auto-fix) |
| 5 | Code Review | Structural review | No (Coach validates behavior only) |
| 5.5 | Plan Audit | Scope creep detection | No |

### Quality Gate Thresholds (from task-work)

```yaml
compilation: 100%          # Required - task blocked if fails
tests_pass: 100%           # Required - auto-fix loop (3 attempts)
line_coverage: 80%         # Soft gate - request more tests
branch_coverage: 75%       # Soft gate - request more tests
architectural_score: 60/100 # Human checkpoint if below
plan_variance: 20%         # Escalate if exceeded
```

---

## Gap Analysis

### Gap 1: No Architectural Review in Autonomous Mode

**Current State**: Player implements freely; Coach only validates tests pass and acceptance criteria met.

**Risk**: Architectural drift over time - Player may introduce:
- Tight coupling (violates DIP)
- Code duplication (violates DRY)
- Premature abstractions (violates YAGNI)
- God classes (violates SRP)

**Evidence from FEAT-0E25**: Health router implementation had no architectural scoring despite creating multiple interdependent modules.

### Gap 2: No Complexity-Based Routing

**Current State**: All tasks go through same Player-Coach loop regardless of complexity.

**Risk**: Simple tasks (typo fixes) go through 5 turns; complex tasks (architectural changes) get same scrutiny as simple ones.

**Task-Work Behavior**:
- Complexity 1-3: Auto-proceed
- Complexity 4-6: Quick review (30s timeout)
- Complexity 7+: Mandatory human checkpoint

### Gap 3: Test Enforcement Without Auto-Fix

**Current State**: If tests fail, Coach provides feedback; Player must fix manually.

**Risk**: Max turns may be reached due to fixable test failures.

**Task-Work Behavior**: Phase 4.5 automatically attempts fixes up to 3 times before blocking.

### Gap 4: No Coverage Gates

**Current State**: Tests pass/fail only; no coverage measurement.

**Risk**: Implementation may pass with minimal test coverage, leading to quality degradation.

**Task-Work Thresholds**: 80% line, 75% branch coverage.

### Gap 5: No Scope Creep Detection

**Current State**: Player may implement beyond acceptance criteria; no detection mechanism.

**Risk**: Feature creep, bloated implementations, unexpected changes.

**Task-Work Behavior**: Phase 5.5 Plan Audit compares:
- Files created vs planned
- LOC variance (±20%)
- Unplanned files

---

## Integration Recommendations

### Recommendation 1: Per-Task Architectural Review

**Proposal**: Add architectural review as Coach responsibility after Player implements.

**Integration Point**: After each Player turn, before Coach approval decision.

```
Player Turn N
    ↓
[NEW] Architectural Score (Coach calculates)
    ↓
Coach Validation
    ↓
Decision: APPROVE (if score >= 60) / FEEDBACK (if score < 60)
```

**Implementation**:
```yaml
coach_validation:
  architectural_review:
    solid_compliance: 0-100
    dry_violations: count
    yagni_violations: count
    minimum_score: 60
    action_if_below: provide_feedback  # Not block, just feedback
```

**Trade-off**: Adds latency per turn but catches architectural issues early.

### Recommendation 2: Lightweight Complexity Routing

**Proposal**: Skip or abbreviate Coach validation for simple tasks.

**Integration Point**: Before Player-Coach loop starts.

```
Load Task
    ↓
Evaluate Complexity (1-10)
    ↓
[1-3]: Single turn, trust Player
[4-6]: Standard loop (max 3 turns)
[7+]: Extended loop (max 5 turns) + mandatory human review
```

**Implementation**:
```yaml
complexity_routing:
  simple: 1-3
    max_turns: 1
    coach_validation: light  # Tests only, no architectural review
  medium: 4-6
    max_turns: 3
    coach_validation: standard
  complex: 7-10
    max_turns: 5
    coach_validation: full  # Architectural + coverage
    human_checkpoint: true
```

### Recommendation 3: Test Auto-Fix in Player Turn

**Proposal**: Allow Player to self-correct test failures within turn before Coach review.

**Integration Point**: End of each Player turn.

```
Player Implementation
    ↓
Player Runs Tests
    ↓
[If fail] Player Auto-Fix (1 attempt)
    ↓
Player Report
    ↓
Coach Validation
```

**Implementation**:
```yaml
player_turn:
  auto_fix:
    enabled: true
    max_attempts: 1  # Within turn
    scope: test_failures_only
```

**Trade-off**: Reduces turns but increases per-turn duration.

### Recommendation 4: Wave-Level Coverage Gates

**Proposal**: Measure coverage after each wave completes (not per-task).

**Integration Point**: After all tasks in wave complete, before proceeding to next wave.

```
Wave N Complete
    ↓
Run Coverage Report
    ↓
[If < 80%] Human Checkpoint: Proceed / Add Tests / Abort
    ↓
Wave N+1
```

**Rationale**: Per-task coverage is too granular; wave-level gives meaningful measurement.

**Implementation**:
```yaml
wave_completion:
  coverage_gate:
    enabled: true
    threshold: 80%  # Soft gate
    action: human_checkpoint  # Not auto-block
```

### Recommendation 5: End-of-Feature Plan Audit

**Proposal**: Run Plan Audit at feature completion (not per-task).

**Integration Point**: After all waves complete, before final status.

```
All Waves Complete
    ↓
Plan Audit
    ├── Files created vs planned
    ├── LOC variance
    └── Unplanned changes
    ↓
[If variance > 20%] Human Review Required
    ↓
Feature Complete
```

**Rationale**: Scope creep detection makes sense at feature level, not individual tasks.

---

## Decision Matrix: Autonomous vs Human-Required

| Scenario | Current Behavior | Proposed Behavior |
|----------|------------------|-------------------|
| Test failure | Coach feedback → Player retry | Player auto-fix → then Coach |
| Architectural score < 60 | N/A (not measured) | Coach provides feedback, continues |
| Architectural score < 40 | N/A | Human checkpoint required |
| Coverage < 80% (wave) | N/A | Human checkpoint (soft gate) |
| Plan variance > 20% | N/A | Human checkpoint (end of feature) |
| Complexity 7+ task | Standard loop | Extended loop + human checkpoint |
| Max turns reached | Feature blocked | Human decides: extend / manual / abort |

### Human Checkpoint Decision Points

```
┌─────────────────────────────────────────────────────────────────┐
│                   HUMAN CHECKPOINT TRIGGERS                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PER-TASK:                                                      │
│  ├── Complexity >= 7                                            │
│  ├── Architectural score < 40                                   │
│  └── Max turns reached                                          │
│                                                                 │
│  PER-WAVE:                                                      │
│  └── Coverage < 80%                                             │
│                                                                 │
│  PER-FEATURE:                                                   │
│  ├── Plan variance > 20%                                        │
│  ├── Any task failed                                            │
│  └── Feature complete (always - never auto-merge)               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Roadmap

### Phase 1: Foundation (Low Risk)
1. Add complexity evaluation to feature-build task loading
2. Route tasks to complexity-appropriate turn limits
3. Add Player auto-fix within turn

### Phase 2: Quality Gates (Medium Risk)
4. Add Coach architectural scoring (SOLID/DRY/YAGNI)
5. Add wave-level coverage measurement
6. Implement soft gates with human checkpoints

### Phase 3: Plan Audit (Medium Risk)
7. Add end-of-feature plan audit
8. Implement variance detection
9. Add scope creep alerting

### Phase 4: Human Checkpoint UX (Low Risk)
10. Design human checkpoint UI/UX
11. Implement checkpoint state persistence
12. Add resume from checkpoint

---

## Answers to Review Questions

### Quality Gate Integration

**Q1: How should Phase 2.5 (Architectural Review) work when Player is autonomous?**
- Coach should calculate architectural score after each Player turn
- Score < 60: Provide specific feedback, continue loop
- Score < 40: Trigger human checkpoint

**Q2: Should Coach validate SOLID/DRY/YAGNI compliance, or should a separate reviewer?**
- Coach should do it (maintains two-agent dialectic)
- Coach already has read-only access needed for code analysis

**Q3: Where does complexity evaluation fit in wave-based execution?**
- Before loop starts for each task
- Routes to turn limit and validation depth

### Test Enforcement

**Q4: Should test failures trigger Player retry or dedicated test-fixer?**
- Player should have 1 auto-fix attempt within turn
- Reduces turns while maintaining simplicity

**Q5: How many auto-fix attempts per task before escalating?**
- 1 within-turn auto-fix by Player
- 3 turns max with Coach feedback
- Then human escalation

**Q6: Should test coverage gates block wave progression?**
- Soft gate (human checkpoint) not hard block
- Allows human to proceed if coverage is acceptable

### Human Oversight

**Q7: Which complexity threshold triggers mandatory human review?**
- Complexity >= 7 (consistent with task-work)

**Q8: Should feature-build pause at wave boundaries for approval?**
- Only if coverage < 80%
- Otherwise proceed autonomously

**Q9: How to surface architectural concerns for human decision?**
- Coach includes architectural score in turn report
- Score < 40 triggers checkpoint with specific violations listed

### Scope Management

**Q10: How to detect scope creep when Player has autonomy?**
- End-of-feature Plan Audit comparing actual vs planned
- List files created, modified, deleted
- Calculate LOC variance

**Q11: Should Plan Audit run per-task or end-of-feature?**
- End-of-feature (scope creep is feature-level concern)

**Q12: What variance thresholds should trigger alerts?**
- LOC variance > 20%: Human checkpoint
- Unplanned files: Human checkpoint
- Extra features: Human checkpoint

---

## Conclusion

Feature-build successfully demonstrates autonomous task execution with Player-Coach adversarial validation. However, it lacks the quality gates that task-work uses to prevent architectural drift, ensure test coverage, and detect scope creep.

**Recommendation**: Integrate quality gates incrementally:
1. Start with complexity routing (low risk, immediate value)
2. Add Coach architectural scoring (medium risk, high value)
3. Add wave-level coverage gates (medium risk, medium value)
4. Add end-of-feature plan audit (medium risk, medium value)

**Key Principle**: Quality gates should inform, not block. Use human checkpoints instead of hard blocks to preserve the autonomous nature of feature-build while ensuring human oversight at critical decision points.

---

## Appendix: Task-Work Phase Reference

| Phase | Description | Duration | Feature-Build Equivalent |
|-------|-------------|----------|--------------------------|
| 1 | Load Task Context | 30s | Player receives task |
| 1.6 | Clarifying Questions | 0-60s | N/A (task-level questions) |
| 2 | Implementation Planning | 5-15min | Player plans within turn |
| 2.5A | Pattern Suggestion | 2-5min | N/A (could add to Coach) |
| 2.5B | Architectural Review | 5-10min | **Gap: Add to Coach** |
| 2.7 | Complexity Evaluation | 30s | **Gap: Add before loop** |
| 2.8 | Human Checkpoint | Variable | Coach approval |
| 3 | Implementation | 15-60min | Player turn |
| 4 | Testing | 5-15min | Coach validation |
| 4.5 | Test Enforcement Loop | 0-30min | **Gap: Player auto-fix** |
| 5 | Code Review | 5-15min | Coach validation |
| 5.5 | Plan Audit | 5-10min | **Gap: Add end-of-feature** |
