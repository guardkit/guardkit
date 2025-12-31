---
id: TASK-REV-B601
title: "Review feature-build output and integrate task-work quality gates"
status: review_complete
task_type: review
created: 2025-12-29T11:00:00Z
updated: 2025-12-29T22:00:00Z
priority: high
tags: [feature-build, quality-gates, review, autobuild, task-work]
complexity: 6
review_mode: architectural
review_depth: comprehensive
decision_required: true
decision: implement
review_report: docs/reviews/TASK-REV-B601-quality-gates-integration-report-v3.md
review_report_v2: docs/reviews/TASK-REV-B601-quality-gates-integration-report-v2.md
review_report_v1: docs/reviews/TASK-REV-B601-quality-gates-integration-report.md
implementation_epic: quality-gates-integration
implementation_tasks_location: tasks/backlog/quality-gates-integration/
---

# Review: Feature-Build Quality Gates Integration

## Overview

Review the output from the `/feature-build` command execution and analyze how to integrate the quality gates/guardrails from `/task-work` into the feature-build workflow while preserving the adversarial cooperation pattern.

## Review Scope

### Primary Artifacts
- **Feature-build output**: `docs/reviews/feature-build/feature-build-output.md`
- **Task-work command**: `installer/core/commands/task-work.md`
- **Feature-build command**: `installer/core/commands/feature-build.md`

### Key Areas to Analyze

1. **Current Feature-Build Flow**
   - Player-Coach adversarial loop
   - Task execution in parallel waves
   - Git worktree isolation
   - Final validation and reporting

2. **Task-Work Quality Gates (to be integrated)**
   - Phase 2.5: Architectural Review (SOLID/DRY/YAGNI scoring)
   - Phase 2.7: Complexity Evaluation (0-10 scale)
   - Phase 4.5: Test Enforcement Loop (auto-fix up to 3 attempts)
   - Phase 5: Code Review
   - Phase 5.5: Plan Audit (scope creep detection)

3. **Integration Questions**
   - Should quality gates run per-task or per-wave?
   - How should architectural review work with autonomous execution?
   - Where should human checkpoints be injected?
   - How to handle test failures in autonomous mode?

## Acceptance Criteria

- [x] Document current feature-build execution flow
- [x] Identify gaps between feature-build and task-work quality assurance
- [x] Propose integration points for each quality gate phase
- [x] Recommend human checkpoint strategy for autonomous builds
- [x] Define test enforcement behavior in Player-Coach loop
- [x] Assess scope creep detection feasibility in autonomous mode

## Analysis Questions

### Quality Gate Integration
1. How should Phase 2.5 (Architectural Review) work when Player is autonomous?
2. Should Coach validate SOLID/DRY/YAGNI compliance, or should a separate reviewer?
3. Where does complexity evaluation (Phase 2.7) fit in wave-based execution?

### Test Enforcement
4. Should test failures trigger Player retry (current) or dedicated test-fixer?
5. How many auto-fix attempts per task before escalating?
6. Should test coverage gates block wave progression?

### Human Oversight
7. Which complexity threshold triggers mandatory human review?
8. Should feature-build pause at wave boundaries for approval?
9. How to surface architectural concerns for human decision?

### Scope Management
10. How to detect scope creep when Player has autonomy?
11. Should Plan Audit (Phase 5.5) run per-task or end-of-feature?
12. What variance thresholds should trigger alerts?

## Expected Deliverables

1. **Gap Analysis Report**: Current vs desired quality assurance ✅
2. **Integration Proposal**: Where and how to add each quality gate ✅
3. **Decision Matrix**: Autonomous vs human-required decisions ✅
4. **Implementation Roadmap**: Phased approach to integration ✅

## Review Report (REVISION 3 - FINAL)

**Full report available at**: [docs/reviews/TASK-REV-B601-quality-gates-integration-report-v3.md](../../docs/reviews/TASK-REV-B601-quality-gates-integration-report-v3.md)

**Previous versions**:
- [v2 - Task-work delegation approach](../../docs/reviews/TASK-REV-B601-quality-gates-integration-report-v2.md)
- [v1 - Gap analysis approach](../../docs/reviews/TASK-REV-B601-quality-gates-integration-report.md)

### FINAL APPROACH (v3): Hybrid - Player-Coach + Quality Gates

**Combine** the adversarial cooperation pattern with task-work quality gates, don't replace one with the other.

#### Why This is Superior

| Aspect | v1: Reimplement | v2: Delegate | v3: Hybrid (FINAL) |
|--------|----------------|--------------|-------------------|
| Adversarial Cooperation | ✅ Yes | ❌ No | ✅ Yes |
| Fresh Context Per Turn | ✅ Yes | ❌ No | ✅ Yes |
| Quality Gate Coverage | Partial (5) | Complete (10) | Complete (10) |
| Block AI Research Pattern | ✅ Follows | ❌ Doesn't follow | ✅ Follows |
| Development Time | 2-4 weeks | 3-5 days | 3-4 weeks |
| Code Reuse | Low | High | High |
| Autonomous Completion | ✅ High | ⚠️ Moderate | ✅ High |
| Research-Backed | ✅ Yes | ❌ No | ✅ Yes |

#### Proposed Architecture

```
Enhanced Player-Coach with Quality Gates:

PRE-LOOP (Quality Gate Setup):
├── Phase 1.6: Clarifying Questions
├── Phase 2: Implementation Planning
├── Phase 2.5A: Pattern Suggestions
├── Phase 2.5B: Architectural Review (of plan)
├── Phase 2.7: Complexity Evaluation
└── Phase 2.8: Human Checkpoint (if complexity ≥7)

ADVERSARIAL LOOP (Dialectical Autocoding):
├── Turn N:
│   ├─► PLAYER
│   │   ├── Fresh context (requirements + feedback)
│   │   ├── Phase 3: Implementation
│   │   ├── Phase 4: Testing
│   │   └── Write report (no self-declaration)
│   │
│   ├─► COACH
│   │   ├── Fresh context (requirements + implementation)
│   │   ├── Phase 4.5: Test Enforcement (auto-fix x3)
│   │   ├── Phase 5: Code Review (architectural scoring)
│   │   └── Write decision (APPROVE/FEEDBACK)
│   │
│   └── If APPROVED → Exit loop
│       If FEEDBACK → Continue to Turn N+1
│       If MAX_TURNS → Escalate
│
└── (Repeat until APPROVED or MAX_TURNS)

POST-LOOP (Quality Gate Finalization):
└── Phase 5.5: Plan Audit
    ├── Compare actual vs planned implementation
    ├── Detect scope creep (±20% variance)
    └── Human checkpoint if needed
```

#### Key Research Finding

Block AI Research proved that **adversarial cooperation is essential**:
- g3 achieved **5/5 completeness** (vs 1-4.5 for single-agent)
- **Ablation study**: Without coach feedback, implementations fail
- Fresh context per turn prevents context pollution
- Independent coach validation catches false successes

**Therefore**: Cannot delegate to task-work (eliminates adversarial loop). Must enhance Player-Coach with quality gates.

#### Implementation Phases

1. **Phase 1**: Pre-Loop Quality Gates (3-5 days)
2. **Phase 2**: Enhanced Coach with Phase 4.5 + 5 (5-7 days)
3. **Phase 3**: Post-Loop Plan Audit (2-3 days)
4. **Phase 4**: Integration Testing (3-5 days)

**Total**: 3-4 weeks

## Review Methodology

Use `/task-review` with:
- `--mode=architectural` for quality gate design review
- `--depth=comprehensive` for full analysis

## Related Files

- `installer/core/commands/feature-build.md` - Current feature-build spec
- `installer/core/commands/task-work.md` - Quality gates implementation
- `guardkit/orchestrator/autobuild.py` - AutoBuild orchestration logic
- `guardkit/orchestrator/agent_invoker.py` - Agent invocation patterns
- `.claude/agents/autobuild-player.md` - Player agent definition
- `.claude/agents/autobuild-coach.md` - Coach agent definition

## Notes

The feature-build command currently uses a Player-Coach adversarial loop where:
- **Player**: Implements code autonomously
- **Coach**: Validates implementation and provides feedback

The task-work command has mature quality gates that ensure:
- Architectural compliance before coding
- Test coverage enforcement
- Code review automation
- Scope creep detection

The goal is to bring task-work's guardrails into feature-build without sacrificing autonomy.
