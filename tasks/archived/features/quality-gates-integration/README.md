# Quality Gates Integration - Implementation Plan

**Epic**: Integrate task-work quality gates into feature-build adversarial cooperation
**Based on**: TASK-REV-B601 v3 (Hybrid Approach) + TASK-REV-0414 (Option D)
**Duration**: 3.5-6 days (reduced from 13-20 days via task-work delegation)
**Priority**: High

---

## Architecture Decision: Option D - Task-Work Delegation

**Decision made in TASK-REV-0414 review:**

Instead of reimplementing task-work quality gates inside feature-build, we **delegate** to task-work directly:

```
/feature-build TASK-XXX
    ├── PHASE 1: SETUP (worktree)
    │
    ├── PHASE 2: PRE-LOOP
    │   └── /task-work TASK-XXX --design-only
    │       └── Phases 1.6, 2, 2.5A, 2.5B, 2.7, 2.8
    │
    ├── PHASE 3: ADVERSARIAL LOOP
    │   ├── PLAYER TURN
    │   │   └── /task-work TASK-XXX --implement-only
    │   │       └── Phases 3, 4, 4.5, 5, 5.5
    │   │
    │   └── COACH TURN (lightweight validator)
    │       └── Verify task-work gates passed
    │       └── Run independent test verification
    │       └── Decision: APPROVE or FEEDBACK
    │
    └── PHASE 4: FINALIZE (preserve worktree, update status)
```

**Why This Approach?**
- ✅ **100% code reuse** - No reimplementation of quality gates
- ✅ **Single source of truth** - task-work is THE quality gate implementation
- ✅ **Automatic improvements** - Feature-build benefits from task-work updates
- ✅ **Massive complexity reduction** - From 20+ LOC to 4 LOC
- ✅ **Duration reduction** - From 13-20 days to 3.5-6 days

---

## Implementation Phases (Revised)

### Phase 1: Pre-Loop via task-work Delegation (1-2 days)
**Task**: [TASK-QG-P1-PRE](TASK-QG-P1-PRE-pre-loop-quality-gates.md)

**What it does**: Thin orchestrator that delegates to `/task-work --design-only`

**Components**:
- `PreLoopQualityGates` class (~100 LOC)
- Task-work interface for delegation
- Pass-through of flags (--no-questions, --answers, etc.)
- Extract plan, complexity, max_turns for adversarial loop

**Files**:
- `guardkit/orchestrator/quality_gates/__init__.py`
- `guardkit/orchestrator/quality_gates/pre_loop.py`
- `guardkit/orchestrator/quality_gates/task_work_interface.py`
- `tests/unit/test_pre_loop_delegation.py`

---

### Phase 2: Lightweight Coach Validator (2-3 days)
**Task**: [TASK-QG-P2-COACH](TASK-QG-P2-COACH-enhanced-coach-agent.md)

**What it does**: Coach validates that task-work quality gates passed (doesn't reimplement them)

**Components**:
- `CoachValidator` class (~150 LOC)
- Read task-work results from JSON
- Verify all gates passed
- Independent test verification (trust but verify)
- Requirements validation

**What Coach Does NOT Do**:
- ❌ Reimplement Phase 4.5 (Test Enforcement)
- ❌ Reimplement Phase 5 (Code Review)
- ❌ Reimplement architectural scoring
- ❌ Reimplement coverage measurement

**Files**:
- `guardkit/orchestrator/quality_gates/coach_validator.py`
- `tests/unit/test_coach_validator.py`
- `.claude/agents/autobuild-coach.md` (update to lightweight role)

---

### Phase 3: Post-Loop Finalization (0.5-1 day)
**Task**: [TASK-QG-P3-POST](TASK-QG-P3-POST-post-loop-plan-audit.md)

**What it does**: Minimal finalization - Phase 5.5 already runs via task-work

**Components**:
- `finalize_autobuild()` function (~50 LOC)
- Preserve worktree for human review
- Update task status
- Generate summary from task-work results

**What We Do NOT Need**:
- ❌ `PostLoopQualityGates` class (redundant)
- ❌ Plan audit implementation (task-work handles it)

**Files**:
- `guardkit/orchestrator/autobuild.py` (add finalization)
- `tests/unit/test_autobuild_finalization.py`

---

## Comparison: Original vs Option D

| Aspect | Original (Reimplementation) | Option D (Delegation) |
|--------|----------------------------|----------------------|
| **Total LOC** | ~1,400 | ~300 |
| **Total Complexity** | 20 | 11 |
| **Duration** | 13-20 days | 3.5-6 days |
| **Code Reuse** | ~20% | 100% |
| **Files to Create** | 10+ | 5 |
| **Maintenance Burden** | Two implementations | Single source |
| **Future Improvements** | Manual sync | Automatic |

### Per-Task Reduction

| Task | Original | Option D |
|------|----------|----------|
| TASK-QG-P1-PRE | 7 complexity, 3-5 days | 4 complexity, 1-2 days |
| TASK-QG-P2-COACH | 8 complexity, 5-7 days | 5 complexity, 2-3 days |
| TASK-QG-P3-POST | 5 complexity, 2-3 days | 2 complexity, 0.5-1 day |
| TASK-QG-P4-TEST | 5 complexity, 3-5 days | **Eliminated** (task-work tested) |

---

## New Architecture Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    /feature-build TASK-XXX                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: SETUP                                              │
│ ├── Load task from tasks/backlog/TASK-XXX.md                │
│ └── Create worktree: .guardkit/worktrees/TASK-XXX/          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: PRE-LOOP QUALITY GATES                             │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ PreLoopQualityGates.execute()                           │ │
│ │   └── /task-work TASK-XXX --design-only                 │ │
│ │       ├── Phase 1.6: Clarifying Questions               │ │
│ │       ├── Phase 2: Implementation Planning              │ │
│ │       ├── Phase 2.5A: Pattern Suggestions               │ │
│ │       ├── Phase 2.5B: Architectural Review              │ │
│ │       ├── Phase 2.7: Complexity Evaluation              │ │
│ │       └── Phase 2.8: Human Checkpoint (if needed)       │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ Output: plan, complexity, max_turns                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: ADVERSARIAL LOOP (max_turns from complexity)       │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ PLAYER TURN                                             │ │
│ │   └── /task-work TASK-XXX --implement-only              │ │
│ │       ├── Phase 3: Implementation                       │ │
│ │       ├── Phase 4: Testing                              │ │
│ │       ├── Phase 4.5: Test Enforcement Loop              │ │
│ │       ├── Phase 5: Code Review                          │ │
│ │       └── Phase 5.5: Plan Audit                         │ │
│ │   └── Save results to task_work_results.json            │ │
│ └─────────────────────────────────────────────────────────┘ │
│                              │                              │
│                              ▼                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ COACH TURN (Lightweight Validator)                      │ │
│ │   ├── Read task_work_results.json                       │ │
│ │   ├── Verify all quality gates passed                   │ │
│ │   ├── Run independent test verification                 │ │
│ │   └── Decision: APPROVE or FEEDBACK                     │ │
│ └─────────────────────────────────────────────────────────┘ │
│                              │                              │
│              ┌───────────────┴───────────────┐              │
│              │                               │              │
│              ▼                               ▼              │
│         APPROVED                        FEEDBACK            │
│              │                               │              │
│              │                    ┌──────────┘              │
│              │                    │                         │
│              │                    ▼                         │
│              │            Next turn (if < max_turns)        │
│              │                    │                         │
│              │                    └──► PLAYER TURN          │
│              │                                              │
└──────────────┼──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4: FINALIZE                                           │
│ ├── Preserve worktree for human review                      │
│ ├── Update task status: READY_FOR_REVIEW                    │
│ ├── Generate summary from task-work results                 │
│ └── Output: worktree path, next steps                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Task Dependencies (Simplified)

```
TASK-QG-P1-PRE (Pre-Loop Delegation)
    │
    └─► TASK-QG-P2-COACH (Coach Validator)
            │
            └─► TASK-QG-P3-POST (Finalization)
```

**Execution Order**: Sequential (P1 → P2 → P3)

**Note**: TASK-QG-P4-TEST (Integration Testing) is **eliminated** because:
- Task-work quality gates are already tested
- We're delegating, not reimplementing
- Coach validator has its own unit tests

---

## Files Structure (Minimal)

```
guardkit/
└── orchestrator/
    ├── quality_gates/
    │   ├── __init__.py                # [NEW] - Exports
    │   ├── pre_loop.py                # [NEW] - ~100 LOC
    │   ├── task_work_interface.py     # [NEW] - ~50 LOC
    │   └── coach_validator.py         # [NEW] - ~150 LOC
    └── autobuild.py                   # [MODIFIED] - Wire up + finalization

.claude/
└── agents/
    └── autobuild-coach.md             # [MODIFIED] - Lightweight role

tests/
└── unit/
    ├── test_pre_loop_delegation.py    # [NEW]
    ├── test_coach_validator.py        # [NEW]
    └── test_autobuild_finalization.py # [NEW]
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Task completion rate | ≥70% | Tasks approved without human intervention |
| Average turns to completion | ≤4 | Mean turns for approved tasks |
| Quality gate enforcement | 100% | Via task-work delegation |
| Test passing before approval | 100% | Coach independent verification |
| Time overhead | ≤30% | Compared to current Player-Coach |
| Code duplication | 0% | All gates via task-work |

---

## References

- **Architecture Decision**: [TASK-REV-0414 Review](.claude/reviews/TASK-REV-0414-review-report.md)
- **Original Review**: [TASK-REV-B601 v3](../../in_review/TASK-REV-B601-feature-build-quality-gates-integration.md)
- **Task-Work Spec**: [installer/core/commands/task-work.md](../../../installer/core/commands/task-work.md)
- **Feature-Build Spec**: [installer/core/commands/feature-build.md](../../../installer/core/commands/feature-build.md)

---

## Next Steps

1. ✅ Architecture decision made (Option D approved)
2. ✅ Tasks rewritten with delegation approach
3. Start with TASK-QG-P1-PRE (Pre-Loop Delegation)
4. Execute phases sequentially
5. Test with real tasks from backlog
