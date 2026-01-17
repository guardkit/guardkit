# Review Report: TASK-REV-PL01

## Executive Summary

This review analyzes the pre-loop architecture tension in AutoBuild and recommends a path forward. The core question is whether to:
- **Option A**: Restore pre-loop (full design phases before Player-Coach loop)
- **Option B**: Accept minimal pre-loop (current state, no design phases)
- **Option C**: Hybrid approach (conditional design based on task metadata)
- **Option D**: Document current behavior and move on

**Recommendation**: **Option B + Enhanced Documentation** - Accept minimal pre-loop behavior but strengthen documentation about when to enable it. The current architecture is sound; what's needed is better guidance for users.

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Standard
- **Duration**: ~45 minutes
- **Task ID**: TASK-REV-PL01

---

## Context: The Architectural Tension

### Original Design Intent (From Feature Docs)

The original AutoBuild design (FEATURE-005, FEATURE-006) envisioned a **simple adversarial loop**:

```
Task → Player (implement) → Coach (validate) → Loop or Complete
```

The original design did **not** include a design phase:
- Player receives task requirements directly
- Player implements, Coach validates
- Loop until approval or max turns

### What Was Added (Pre-Loop)

The `pre_loop.py` and `task_work_interface.py` were added to support delegating to task-work for design phases:

```
Task → [Pre-Loop: task-work --design-only] → Player (implement) → Coach (validate)
```

This pre-loop executes:
- Phase 1.6: Clarifying Questions
- Phase 2: Implementation Planning
- Phase 2.5: Architectural Review
- Phase 2.7: Complexity Evaluation
- Phase 2.8: Human Checkpoint

### The Current State (Post FB-FIX-015, FB-FIX-018)

FB-FIX-015 changed the defaults:
- **feature-build**: `enable_pre_loop = False` by default (tasks from feature-plan have detailed specs)
- **task-build**: `enable_pre_loop = True` by default (standalone tasks benefit from design)

FB-FIX-018 changed documentation defaults to "minimal" for speed.

The result: **Pre-loop is disabled by default for feature-build**, meaning no design phase runs before the Player-Coach loop.

---

## Evidence Analysis

### Evidence 1: Feature-Plan Task Quality

Tasks created via `/feature-plan` already have:
- Detailed requirements from review analysis
- Extracted subtasks with acceptance criteria
- Implementation mode assignments (task-work/direct/manual)
- Wave groupings for parallel execution

**Finding**: Feature-plan tasks are already "designed" - they have the equivalent of Phase 2 output embedded in their creation.

### Evidence 2: Pre-Loop Duration Impact

From task documentation and timeout analysis:
- Pre-loop (Phases 2-2.8): ~60-90 minutes
- Loop (Phases 3-5.5): ~15-25 minutes per turn

**Finding**: Pre-loop adds 3-4x the time overhead. For feature-build with 5+ tasks, this is prohibitive.

### Evidence 3: Player Agent Capability

The Player agent (`autobuild-player.md`) is designed to:
- Delegate to `task-work --implement-only` for Phases 3-5.5
- Leverage stack-specific specialists
- Use quality gates (Phase 4.5 test enforcement)

**Finding**: Player receives implementation guidance from task-work delegation, not from pre-loop design phases.

### Evidence 4: Coach Agent Role

The Coach agent (`autobuild-coach.md`) validates:
- Requirements met from acceptance criteria
- Tests pass (runs independently)
- Code quality acceptable

**Finding**: Coach validates against task acceptance criteria, not implementation plans. Pre-loop design documents are not consumed by Coach.

### Evidence 5: Implementation Plan Usage

When pre-loop runs, it creates `.claude/task-plans/{task_id}-implementation-plan.md`. However:
- Player doesn't explicitly reference this plan
- Coach doesn't check implementation against plan
- The plan serves primarily the human checkpoint (Phase 2.8)

**Finding**: Implementation plans are valuable for human review but not actively consumed by the adversarial loop.

---

## Option Evaluation

### Option A: Restore Pre-Loop (Full Design)

**Description**: Make pre-loop enabled by default again, running full design phases before every task.

| Factor | Assessment |
|--------|------------|
| Duration | ❌ Bad - Adds 60-90 min per task |
| Quality | ✅ Good - Design phases catch issues early |
| Redundancy | ⚠️ Mixed - Feature-plan tasks already have specs |
| User Experience | ❌ Bad - Too slow for feature-build |

**Score**: 3/10

**Rationale**: This restores theoretical correctness but makes feature-build impractically slow. The original design never included a design phase - it was added as an enhancement, not a core requirement.

### Option B: Accept Minimal Pre-Loop (Current State)

**Description**: Keep pre-loop disabled by default for feature-build, enabled for task-build. Document the behavior clearly.

| Factor | Assessment |
|--------|------------|
| Duration | ✅ Good - Fast execution (15-25 min) |
| Quality | ⚠️ Acceptable - Quality gates in loop |
| Redundancy | ✅ Good - No duplication with feature-plan |
| User Experience | ✅ Good - Reasonable expectations |

**Score**: 8/10

**Rationale**: This matches how the system actually works. Feature-plan tasks don't need design phases because they're already designed. Task-build still gets design for standalone tasks.

### Option C: Hybrid (Conditional Design)

**Description**: Auto-detect whether pre-loop is needed based on task metadata (complexity, acceptance criteria completeness).

| Factor | Assessment |
|--------|------------|
| Duration | ⚠️ Variable - Depends on detection |
| Quality | ✅ Good - Design when needed |
| Redundancy | ✅ Good - Smart about when to skip |
| User Experience | ⚠️ Confusing - Non-deterministic behavior |

**Score**: 6/10

**Rationale**: Technically elegant but adds complexity. Users won't understand why some tasks get design phases and others don't. The current explicit flag (`--enable-pre-loop`) is clearer.

### Option D: Document and Move On

**Description**: No code changes. Just improve documentation to explain the current behavior.

| Factor | Assessment |
|--------|------------|
| Duration | ✅ Good - No change |
| Quality | ⚠️ Acceptable - Status quo |
| Redundancy | ⚠️ Unknown - Users may not understand |
| User Experience | ❌ Poor - Leaves confusion |

**Score**: 5/10

**Rationale**: Documentation alone doesn't solve the issue of unclear user expectations. Need to ensure the documented behavior is actually correct before documenting it.

---

## Decision Matrix

| Criterion | Weight | Option A | Option B | Option C | Option D |
|-----------|--------|----------|----------|----------|----------|
| Execution Speed | 30% | 1 | 9 | 7 | 8 |
| Quality Assurance | 25% | 9 | 7 | 8 | 6 |
| User Experience | 25% | 3 | 8 | 5 | 5 |
| Implementation Effort | 20% | 8 | 10 | 4 | 10 |
| **Weighted Total** | | **4.8** | **8.4** | **6.1** | **7.0** |

---

## Recommendation

**Recommended Option**: **Option B + Enhanced Documentation**

Accept the current minimal pre-loop behavior but strengthen documentation and user guidance:

### Immediate Actions (No Code Changes)

1. **Update CLAUDE.md Pre-Loop Section**:
   - Clarify that feature-build tasks are "pre-designed" by feature-plan
   - Explain when to use `--enable-pre-loop` flag
   - Add examples of each scenario

2. **Add Decision Tree to Docs**:
   ```
   Is this a feature-build task?
   ├── Yes → Is task from feature-plan?
   │   ├── Yes → Pre-loop not needed (default: disabled)
   │   └── No → Consider --enable-pre-loop for complex tasks
   └── No (task-build) → Pre-loop runs by default
   ```

3. **Update feature-build Help Text**:
   - Add note that pre-loop is disabled by default
   - Explain how to enable it if needed

### Future Consideration (Optional Enhancement)

If users frequently request design phases for feature-build tasks, consider:
- Adding `--design-first` flag as an alias for `--enable-pre-loop`
- Logging a suggestion when task complexity is high

---

## Appendix: Key Files Reviewed

| File | Purpose | Relevance |
|------|---------|-----------|
| `guardkit/orchestrator/autobuild.py` | Main orchestrator | Current behavior |
| `guardkit/orchestrator/feature_orchestrator.py` | Feature execution | Pre-loop resolution |
| `guardkit/orchestrator/quality_gates/pre_loop.py` | Pre-loop implementation | Design phase delegation |
| `guardkit/orchestrator/quality_gates/task_work_interface.py` | task-work delegation | SDK integration |
| `tasks/completed/TASK-FB-FIX-015/` | Default change task | Historical context |
| `docs/research/guardkit-agent/FEATURE-005-adversarial-orchestrator.md` | Original design | Architecture intent |
| `docs/research/guardkit-agent/archived/FEATURE-006-autobuild-cli.md` | CLI design | Original workflow |

---

## Author

Generated by `/task-review TASK-REV-PL01 --mode=decision --depth=standard`

Date: 2026-01-13
