# Decision Analysis Report: TASK-REV-FB16 (REVISED)

## Workflow Optimization Strategy: Adversarial Intensity and Conditional Phases

**Review ID**: TASK-REV-FB16
**Review Mode**: Decision Analysis
**Depth**: Standard (Revised after user feedback)
**Date**: 2026-01-16
**Reviewer**: Claude (automated decision analysis)
**Status**: COMPLETE - Decision Required
**Prior Analysis**: TASK-REV-FB14, TASK-REV-FB15
**Implementation Tasks Created**: TASK-TWP-a1b2, TASK-TWP-c3d4, TASK-TWP-e5f6

---

## Executive Summary

**Core Question**: How should GuardKit systematize adaptive ceremony through adversarial intensity tuning and conditional phase execution?

**Key User Feedback**: Using `--micro` on complexity 2-3 subtasks (that came from a prior `/task-review`) resulted in 10-20 minute completions with excellent quality - despite the tasks "not qualifying" for micro mode per current criteria.

**Critical Insight**: **Task provenance matters more than complexity score alone.** When a task originates from `/task-review` or `/feature-plan`, the heavyweight ceremony (planning, architectural review) has already been done. `/task-work` shouldn't repeat it.

---

## The Workflow Evolution Problem

### Before: Only `/task-work`

When `/task-work` was the only command, it made sense for it to do everything:
- Planning, architectural review, implementation, testing, code review

### Now: Multiple Specialized Commands

The workflow has evolved:

| Command | Primary Purpose | Ceremony Level |
|---------|-----------------|----------------|
| `/task-review` | Analysis, architectural review, decision-making | Full ceremony |
| `/feature-plan` | Planning, subtask creation, dependency mapping | Full ceremony |
| `/feature-build` | Autonomous implementation with Player-Coach | Dialectical loop |
| `/task-work` | Implementation with quality gates | **Variable** ← This is the question |

### The Duplication Problem

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CURRENT CEREMONY DUPLICATION                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  UPSTREAM: /task-review TASK-REV-G001                                       │
│  ═══════════════════════════════════════════════════════════════════════════│
│  ✓ Architectural review (85/100 score)                                      │
│  ✓ Code quality assessment                                                  │
│  ✓ SOLID/DRY analysis                                                       │
│  ✓ Recommendations with rationale                                           │
│  ✓ Subtasks created with clear acceptance criteria                          │
│  Duration: Comprehensive analysis (~2 hours)                                │
│                                                                             │
│  DOWNSTREAM: /task-work TASK-GS-011a (standard mode)                        │
│  ═══════════════════════════════════════════════════════════════════════════│
│  ✓ Phase 2: Implementation planning          ← WASTED (already planned)    │
│  ✓ Phase 2.5A: Pattern suggestion            ← WASTED (already analyzed)   │
│  ✓ Phase 2.5B: Architectural review          ← WASTED (just reviewed!)     │
│  ✓ Phase 2.7: Complexity evaluation          ← WASTED (scored at creation) │
│  ✓ Phase 2.8: Human checkpoint               ← WASTED (approved in review) │
│  ✓ Phase 3: Implementation                   ← NEEDED                       │
│  ✓ Phase 4: Testing                          ← NEEDED                       │
│  ✓ Phase 5: Code review                      ← NEEDED (but lighter)         │
│  Duration: 65+ minutes (58 min in Phase 2 alone!)                           │
│                                                                             │
│  DOWNSTREAM: /task-work TASK-GS-011a --micro                                │
│  ═══════════════════════════════════════════════════════════════════════════│
│  ✓ Phase 1: Load context                     ← NEEDED                       │
│  ✓ Phase 3: Implementation                   ← NEEDED                       │
│  ✓ Phase 4: Quick testing                    ← NEEDED                       │
│  ✓ Phase 5: Quick review (lint)              ← NEEDED                       │
│  Duration: 10-20 minutes with same quality!                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**User's Real-World Results**:
- TASK-GS-011a through 011f: complexity 2-3, multi-file changes
- Current criteria said: "❌ Not eligible for --micro"
- User used `--micro` anyway
- Result: 10-20 minutes each, quality maintained

---

## Revised Intensity Model: Provenance-Aware

### New Principle: Task Provenance Informs Intensity

| Task Origin | Ceremony Already Done | `/task-work` Should Do |
|-------------|----------------------|------------------------|
| `/task-review` [I]mplement | Arch review, planning, recommendations | Implementation + quality gates only |
| `/feature-plan` | Planning, dependencies, complexity scoring | Light review + implementation + gates |
| `/task-create` (fresh) | Nothing | Complexity-based full ceremony |

### Proposed Intensity Levels (Revised)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     REVISED INTENSITY GRADIENT                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  MINIMAL (--intensity=minimal, --micro alias)                               │
│  ───────────────────────────────────────────────────────────────────────────│
│  When: Complexity ≤3 OR task from /task-review subtask                      │
│  Phases: 1 → 3 → 4 (no coverage) → 5 (lint only)                            │
│  Duration: 3-10 minutes                                                     │
│                                                                             │
│  LIGHT (--intensity=light) [NEW]                                            │
│  ───────────────────────────────────────────────────────────────────────────│
│  When: Complexity 4-5 OR task from /feature-plan                            │
│  Phases: 1 → 2 (brief) → 3 → 4 → 5                                          │
│  Skips: 2.5A (MCP), 2.5B (arch review), 2.8 (checkpoint)                    │
│  Duration: 10-20 minutes                                                    │
│                                                                             │
│  STANDARD (--intensity=standard, default for fresh tasks)                   │
│  ───────────────────────────────────────────────────────────────────────────│
│  When: Complexity 5-6 AND fresh /task-create                                │
│  Phases: All except 2.5A if no pattern need detected                        │
│  Duration: 20-40 minutes                                                    │
│                                                                             │
│  STRICT (--intensity=strict)                                                │
│  ───────────────────────────────────────────────────────────────────────────│
│  When: Complexity 7+ OR security/database/API keywords                      │
│  Phases: All phases, blocking checkpoints                                   │
│  Duration: 45-90 minutes                                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Auto-Detection Logic (Revised)

```python
def determine_intensity(task: Task) -> Intensity:
    """Determine intensity based on provenance + complexity."""

    # Check provenance first
    if task.parent_review:  # Came from /task-review [I]mplement
        if task.complexity <= 4:
            return Intensity.MINIMAL  # Review already did the heavy lifting
        else:
            return Intensity.LIGHT    # Still skip arch review, it was just done

    if task.feature_id:  # Came from /feature-plan
        if task.complexity <= 3:
            return Intensity.MINIMAL
        elif task.complexity <= 5:
            return Intensity.LIGHT  # Planning done, skip redundant phases
        else:
            return Intensity.STANDARD  # Higher complexity needs more scrutiny

    # Fresh task from /task-create - use complexity-based logic
    if has_high_risk_keywords(task):
        return Intensity.STRICT

    if task.complexity <= 3:
        return Intensity.MINIMAL  # Raise threshold from 1 to 3
    elif task.complexity <= 5:
        return Intensity.LIGHT
    elif task.complexity <= 6:
        return Intensity.STANDARD
    else:
        return Intensity.STRICT
```

---

## The --micro Threshold Problem

### Current Criteria (Too Restrictive)

```
Micro eligibility:
- Complexity: ≤1/10  ← Too restrictive!
- Files: Single file ← Too restrictive!
- No high-risk keywords
- Estimated effort: <1 hour
```

### Proposed Criteria (Based on User Evidence)

```
Minimal intensity eligibility:
- Complexity: ≤3/10  ← Raised from 1
- Files: Any (if from reviewed parent) ← Relaxed when provenance is trusted
- No high-risk keywords  ← Keep this
- OR: Task has parent_review field ← NEW: Provenance-based eligibility
```

### Why This Works

Your TASK-GS-011a-f tasks:
- **Came from**: `/task-review` (TASK-REV-G001)
- **Parent review**: 85/100 architecture score, comprehensive analysis
- **Acceptance criteria**: Clearly defined in review recommendations
- **Complexity**: 2-3 (but multi-file)

The heavyweight ceremony was **already done**. `/task-work` just needed to:
1. Implement the clearly-defined change
2. Run tests
3. Quick lint check

That's exactly what `--micro` does - and it worked perfectly.

---

## Revised Decision Points

### Decision 1: Intensity Parameter Design (Revised)

**Previous Recommendation**: Option B (replace --micro with --intensity, keep alias)

**Revised Recommendation**: Same, but with **provenance-aware auto-detection**

```bash
# Current behavior (user must specify)
/task-work TASK-GS-011a --micro

# Proposed behavior (auto-detected)
/task-work TASK-GS-011a
# Output: "Auto-detected: minimal intensity (parent review: TASK-REV-G001)"
```

**Key Addition**: Tasks with `parent_review` in frontmatter auto-qualify for minimal/light intensity.

### Decision 2: Where Does Ceremony Belong?

**Current State**:
- `/task-review`: Does architectural review
- `/feature-plan`: Does planning + creates subtasks
- `/task-work`: Redoes architectural review + planning (!!)

**Proposed State**:

| Ceremony | Should Happen In | Notes |
|----------|-----------------|-------|
| Architectural Review | `/task-review` OR `/task-work` (if fresh task) | Not both |
| Planning | `/feature-plan` OR `/task-work` (if fresh task) | Not both |
| Complexity Scoring | At task creation time | Once, not every execution |
| Implementation | `/task-work` OR `/feature-build` | Always needed |
| Quality Gates | `/task-work` OR `/feature-build` | Always needed |

### Decision 3: Phase Skipping Implementation (Revised)

**Previous Recommendation**: Hardcoded phase-skip logic

**Revised Recommendation**: Hardcoded + **provenance-aware defaults**

```python
def get_phase_config(task: Task, intensity: Intensity) -> PhaseConfig:
    """Get phase configuration based on intensity and provenance."""

    config = INTENSITY_PHASES[intensity]  # Base config from intensity

    # Provenance-based overrides
    if task.parent_review:
        # Parent review already did arch analysis - skip redundant phases
        config.skip_phases.add(Phase.PATTERN_SUGGESTION)  # 2.5A
        config.skip_phases.add(Phase.ARCHITECTURAL_REVIEW)  # 2.5B
        config.skip_phases.add(Phase.COMPLEXITY_EVAL)  # 2.7
        config.reduce_checkpoint_timeout(5)  # Quick confirm only

    if task.feature_id:
        # Feature plan already did planning
        config.planning_mode = PlanningMode.BRIEF  # Just verify, don't recreate
        config.skip_phases.add(Phase.COMPLEXITY_EVAL)  # Already scored

    return config
```

---

## Implementation Recommendations

### Immediate (This Week)

**Priority 0**: Complete TASK-TWP Wave 1 (already in progress)
- TASK-TWP-a1b2: Documentation constraints (fixes 89% of Phase 2 bloat)
- TASK-TWP-c3d4: Raise micro threshold to ≤3 (your evidence validates this)

### Short-Term (After Wave 1 Validation)

**Priority 1**: Add provenance-aware intensity detection
```yaml
# Task frontmatter additions
parent_review: TASK-REV-G001  # If created from /task-review [I]mplement
feature_id: FEAT-A1B2         # If created from /feature-plan
```

**Priority 2**: Implement `--intensity` flag with 4 levels
- minimal (alias: --micro)
- light
- standard (default)
- strict

**Priority 3**: Auto-detect intensity from provenance
- Tasks with `parent_review` → default to minimal
- Tasks with `feature_id` → default to light
- Fresh tasks → complexity-based

### Medium-Term

**Priority 4**: Review where `/feature-build` fits
- `/feature-build` uses Player-Coach (adversarial) for implementation
- Should `/task-work` still do its own code review, or delegate to Coach pattern?

---

## Validation: Your Evidence Supports This Model

| Task | Complexity | Files | Per Current Rules | You Used | Result |
|------|------------|-------|-------------------|----------|--------|
| TASK-GS-010 | 2 | 3 | ❌ No micro | --micro | ✅ 10-20 min |
| TASK-GS-011a | 2 | 1 | ❌ No (complexity>1) | --micro | ✅ 10-20 min |
| TASK-GS-011b | 3 | 2 | ❌ No | --micro | ✅ 10-20 min |
| TASK-GS-011c | 3 | 1 | ❌ No | --micro | ✅ 10-20 min |
| TASK-GS-011d | 3 | 2 | ❌ No | --micro | ✅ 10-20 min |
| TASK-GS-011e | 3 | 2 | ❌ No | --micro | ✅ 10-20 min |

**Why it worked**: All these tasks came from TASK-REV-G001, which did:
- Comprehensive architectural review (85/100)
- SOLID/DRY/YAGNI analysis
- Clear acceptance criteria per subtask

The ceremony was **front-loaded** in the review. `/task-work` just needed to implement.

---

## Risk Assessment (Revised)

### Risk 1: Skipping Review for Tasks That Need It

**Mitigation**: Provenance-based intensity only applies to tasks WITH a parent review. Fresh tasks still go through complexity-based ceremony.

### Risk 2: Parent Review Was Insufficient

**Mitigation**:
- Parent review quality is visible (85/100 score)
- `/task-work` can still escalate if it detects issues during implementation
- Quality gates (tests, lint) still run regardless of intensity

### Risk 3: Over-Engineering the Provenance System

**Mitigation**: Start simple:
1. Just add `parent_review` field to task frontmatter
2. Use it to auto-suggest `--micro` (don't auto-apply)
3. Iterate based on results

---

## Summary: The Key Insight

**Before**: Intensity based on **task complexity alone**
**After**: Intensity based on **provenance + complexity**

```
                    OLD MODEL                         NEW MODEL
                    ─────────                         ─────────

Complexity 1 ───▶ minimal                Task from /task-review ───▶ minimal
Complexity 2-6 ──▶ standard              Task from /feature-plan ──▶ light
Complexity 7+ ──▶ strict                 Fresh + complexity 1-3 ───▶ minimal
                                         Fresh + complexity 4-6 ───▶ standard
                                         Fresh + complexity 7+ ────▶ strict
```

The ceremony should happen **once, at the right level**:
- `/task-review` for analysis/decisions → creates tasks that skip analysis
- `/feature-plan` for planning → creates tasks that skip planning
- `/task-work` for implementation → focuses on what upstream commands didn't do

---

## Decision Checkpoint (Revised)

**Select an option:**

| Option | Action |
|--------|--------|
| **[A] Accept** | Approve revised analysis. Complete TASK-TWP Wave 1, then implement provenance-aware intensity. |
| **[R] Revise** | Request further analysis (specify area) |
| **[I] Implement** | Create additional implementation tasks for provenance-aware intensity system |
| **[C] Cancel** | Discard this review |

---

## References

- [TASK-REV-FB14 Review Report](.claude/reviews/TASK-REV-FB14-review-report.md) - Original performance analysis
- [TASK-REV-FB15 Review Report](.claude/reviews/TASK-REV-FB15-review-report.md) - Root cause analysis
- [TASK-REV-G001 Review Report](MyDrive/.claude/reviews/TASK-REV-G001-review-report.md) - User's real-world example
- [Adversarial Intensity Research](docs/research/guardkit-agent/Adversarial_Intensity_and_Adaptive_Ceremony_Research.md) - Intensity gradient design
- [task-work.md](installer/core/commands/task-work.md) - Command specification
- [TASK-TWP Implementation Guide](tasks/backlog/task-work-performance/IMPLEMENTATION-GUIDE.md) - Wave execution plan
