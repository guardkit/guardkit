# Architectural Review: Feature-Build Quality Gates Integration (REVISED)

**Task ID**: TASK-REV-B601
**Review Mode**: Architectural
**Review Depth**: Comprehensive
**Date**: 2025-12-29
**Reviewer**: Claude Code (Architectural Review Agent)
**Revision**: 2 (Leverage task-work approach)

---

## Executive Summary

**REVISED APPROACH**: Instead of reimplementing task-work quality gates in feature-build, we should **leverage task-work as the execution engine** for feature-build orchestration.

### Key Insight

Feature-build currently uses custom Player-Coach agents for autonomous execution. However, `/task-work` already provides:
- All 10 quality gate phases
- Architectural review (SOLID/DRY/YAGNI)
- Test enforcement with auto-fix
- Code review automation
- Plan audit for scope creep
- Human checkpoints with complexity routing

**Proposed Solution**: Replace the Player-Coach loop with `/task-work` invocation per task.

---

## Current Architecture vs Proposed Architecture

### Current: Feature-Build with Player-Coach

```
┌─────────────────────────────────────────────────────────────────┐
│              CURRENT FEATURE-BUILD ARCHITECTURE                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Feature Orchestration (feature-build)                         │
│  ├── Load FEAT-XXX.yaml                                         │
│  ├── Create worktree                                            │
│  └── For each wave:                                             │
│      └── For each task in wave:                                 │
│          ├── Player Turn (autonomous implementation)            │
│          ├── Coach Turn (validation + feedback)                 │
│          └── Loop until: APPROVE or MAX_TURNS                   │
│                                                                 │
│  Quality Gates: NONE                                            │
│  - No architectural review                                      │
│  - No complexity routing                                        │
│  - No test coverage enforcement                                 │
│  - No auto-fix loop                                             │
│  - No plan audit                                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Proposed: Feature-Build Delegates to Task-Work

```
┌─────────────────────────────────────────────────────────────────┐
│              PROPOSED FEATURE-BUILD ARCHITECTURE                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Feature Orchestration (feature-build)                         │
│  ├── Load FEAT-XXX.yaml                                         │
│  ├── Create feature worktree                                    │
│  └── For each wave:                                             │
│      └── For each task in wave (parallel):                      │
│          │                                                       │
│          └── INVOKE /task-work TASK-XXX                         │
│              ├── Phase 1.6: Clarifying Questions                │
│              ├── Phase 2: Implementation Planning               │
│              ├── Phase 2.5: Architectural Review ✅             │
│              ├── Phase 2.7: Complexity Evaluation ✅            │
│              ├── Phase 2.8: Human Checkpoint ✅                 │
│              ├── Phase 3: Implementation                        │
│              ├── Phase 4: Testing                               │
│              ├── Phase 4.5: Test Enforcement Loop ✅            │
│              ├── Phase 5: Code Review ✅                        │
│              └── Phase 5.5: Plan Audit ✅                       │
│                                                                 │
│  Quality Gates: INHERITED FROM TASK-WORK                        │
│  ✅ Full architectural review                                   │
│  ✅ Complexity-based routing                                    │
│  ✅ Test coverage enforcement                                   │
│  ✅ Auto-fix loop (3 attempts)                                  │
│  ✅ Plan audit & scope creep detection                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Benefits of Leveraging Task-Work

### 1. Zero Reimplementation Required

**Current Gap**: Need to reimplement 5 quality gates in Player-Coach loop.

**With task-work**: Get all 10 phases for free.

| Quality Gate | Current | With task-work |
|--------------|---------|----------------|
| Architectural Review | Need to build | ✅ Phase 2.5B |
| Complexity Routing | Need to build | ✅ Phase 2.7 |
| Test Auto-Fix | Need to build | ✅ Phase 4.5 |
| Coverage Gates | Need to build | ✅ Phase 4 |
| Plan Audit | Need to build | ✅ Phase 5.5 |

### 2. Feature Parity Guaranteed

Task-work is the **source of truth** for GuardKit quality standards. Using it directly ensures feature-build has identical quality enforcement.

### 3. Complexity Routing Built-In

Task-work already implements sophisticated complexity routing:
- **1-3**: Auto-proceed (no checkpoint)
- **4-6**: Quick checkpoint (10s timeout)
- **7-10**: Mandatory human checkpoint

Feature-build inherits this without additional code.

### 4. Human Checkpoints Preserved

Phase 2.8 checkpoints occur **per-task** within feature execution:
- User can approve/modify/reject during feature build
- Preserves human oversight for complex tasks
- No change to autonomous workflow for simple tasks

### 5. Worktree Isolation Maintained

Task-work can execute **within the feature worktree**:
```bash
# Feature-build creates worktree
git worktree add .guardkit/worktrees/FEAT-XXX -b autobuild/FEAT-XXX

# Task-work executes inside that worktree
cd .guardkit/worktrees/FEAT-XXX
/task-work TASK-001  # Works in current directory
```

All changes committed to `autobuild/FEAT-XXX` branch.

---

## Revised Integration Architecture

### Feature-Build Orchestration Flow

```python
def feature_build(feature_id: str, options: dict):
    """Execute feature build using task-work for quality gates."""

    # 1. Load feature file
    feature = load_feature(f".guardkit/features/{feature_id}.yaml")

    # 2. Create feature worktree
    worktree_path = f".guardkit/worktrees/{feature_id}"
    create_worktree(worktree_path, branch=f"autobuild/{feature_id}")

    # 3. Execute waves in order
    for wave_idx, wave in enumerate(feature.orchestration.parallel_groups):
        print(f"Wave {wave_idx + 1}/{len(waves)}: {wave}")

        # 4. For each task in wave (can run in parallel)
        for task_id in wave:
            task = find_task(feature.tasks, task_id)

            # 5. DELEGATE TO TASK-WORK (key change!)
            result = invoke_task_work(
                task_id=task_id,
                worktree_path=worktree_path,
                options={
                    "mode": options.get("mode", "standard"),
                    "docs": options.get("docs", "minimal"),
                    # Inherit feature-build flags
                    **options
                }
            )

            # 6. Update feature status
            update_feature_status(feature_id, task_id, result.status)

            # 7. Handle failure
            if result.status == "failed" and options.get("stop_on_failure", True):
                return abort_feature(feature_id, failed_task=task_id)

    # 8. Feature complete
    return complete_feature(feature_id, worktree_path)


def invoke_task_work(task_id: str, worktree_path: str, options: dict):
    """Invoke task-work within feature worktree."""

    # Navigate to feature worktree
    original_cwd = os.getcwd()
    os.chdir(worktree_path)

    try:
        # Execute task-work with all quality gates
        result = execute_command(
            f"/task-work {task_id}",
            options={
                "mode": options.get("mode"),
                "docs": options.get("docs", "minimal"),  # Default to fast mode
                "no-questions": True,  # Skip clarification in autonomous mode
            }
        )
        return result
    finally:
        os.chdir(original_cwd)
```

### Key Implementation Details

#### 1. Working Directory Context

Task-work needs to execute **inside the feature worktree**:

```bash
# Before task-work
pwd
# /Users/you/Projects/guardkit

# Create worktree
git worktree add .guardkit/worktrees/FEAT-A1B2 -b autobuild/FEAT-A1B2

# Navigate into worktree
cd .guardkit/worktrees/FEAT-A1B2

# Execute task-work from worktree
/task-work TASK-001
# Creates files in worktree, commits to autobuild/FEAT-A1B2
```

#### 2. Clarification Handling

For autonomous feature builds, skip Phase 1.6 clarifications:

```bash
# Feature-build invokes task-work with --no-questions
/task-work TASK-001 --no-questions --docs=minimal
```

**Rationale**: Feature-plan already gathered requirements upfront. Tasks should be well-specified.

**Alternative**: Allow `--with-questions` for interactive feature builds.

#### 3. Documentation Level Override

Default to `--docs=minimal` for faster execution:

```bash
# Fast mode (8-12 min per task)
/task-work TASK-001 --docs=minimal --no-questions

# Standard mode (12-18 min per task) - if user wants more docs
/feature-build FEAT-A1B2 --docs=standard
```

#### 4. Test Coverage Aggregation

Task-work measures coverage **per task**. Feature-build can aggregate:

```python
# After wave completes
wave_coverage = aggregate_coverage(wave_tasks)

if wave_coverage < 80:
    human_checkpoint(
        f"Wave {wave_idx} coverage: {wave_coverage}%. Proceed?"
    )
```

#### 5. Plan Audit Scope

Phase 5.5 Plan Audit runs **per task** (not per feature):
- Each task audits its own scope
- Feature-build aggregates variance across tasks
- End-of-feature summary shows cumulative variance

---

## Comparison: Player-Coach vs Task-Work

### Player-Coach Loop (Current)

**Phases**:
1. Player implements
2. Coach validates + provides feedback
3. Loop until approval or max turns

**Quality Gates**: None (just acceptance criteria validation)

**Strengths**:
- ✅ Fast iteration (no planning overhead)
- ✅ Autonomous execution
- ✅ Dialectical validation

**Weaknesses**:
- ❌ No architectural review
- ❌ No complexity routing
- ❌ No auto-fix loop
- ❌ No coverage enforcement
- ❌ No scope creep detection

**Use Case**: Rapid prototyping, well-defined simple tasks

### Task-Work Delegation (Proposed)

**Phases**: All 10 phases (1.6, 2, 2.5A, 2.5B, 2.7, 2.8, 3, 4, 4.5, 5, 5.5)

**Quality Gates**: Complete suite

**Strengths**:
- ✅ Full quality enforcement
- ✅ Complexity-based routing
- ✅ Auto-fix + coverage gates
- ✅ Plan audit
- ✅ Human checkpoints
- ✅ Zero reimplementation

**Weaknesses**:
- ⚠️ Slower per task (planning overhead)
- ⚠️ More token usage (architectural review)
- ⚠️ Potential checkpoint interruptions

**Use Case**: Production features, quality-critical work

---

## Migration Strategy

### Phase 1: Add Task-Work Mode (Low Risk)

Add `--mode=task-work` flag to feature-build:

```bash
# New mode: Delegate to task-work
/feature-build FEAT-A1B2 --mode=task-work

# Existing mode: Player-Coach loop (default)
/feature-build FEAT-A1B2 --mode=player-coach
```

**Implementation**:
```python
if options.get("mode") == "task-work":
    result = invoke_task_work(task_id, worktree_path, options)
else:
    result = player_coach_loop(task_id, worktree_path, options)
```

**Benefits**:
- Side-by-side comparison
- Users can opt-in
- Backwards compatible

### Phase 2: Default to Task-Work (Medium Risk)

Switch default from Player-Coach to task-work:

```bash
# Default behavior (task-work)
/feature-build FEAT-A1B2

# Opt-out to Player-Coach
/feature-build FEAT-A1B2 --mode=player-coach
```

**Migration Path**:
1. Phase 1: Both modes available, Player-Coach default
2. Beta period: Users test task-work mode
3. Phase 2: Task-work becomes default
4. Deprecation: Player-Coach mode marked deprecated
5. Future: Remove Player-Coach mode entirely

### Phase 3: Remove Player-Coach (Future)

Once task-work proves stable, remove Player-Coach entirely:
- Simplifies codebase
- Single source of truth for quality gates
- Easier maintenance

---

## Handling Edge Cases

### Edge Case 1: Human Checkpoints in Autonomous Mode

**Problem**: Phase 2.8 checkpoint may interrupt autonomous execution.

**Solution 1 (Recommended)**: Respect checkpoints (preserve human oversight)
```bash
# Complex task triggers checkpoint
/task-work TASK-COMPLEX-001
# Phase 2.8: Complexity 8/10 detected
# [A]pprove / [M]odify / [R]eject?
```

**Solution 2**: Auto-approve simple tasks, checkpoint for complex
```python
if task.complexity <= 6:
    invoke_task_work(task_id, options={"--defaults": True})
else:
    invoke_task_work(task_id)  # Allow checkpoints
```

**Solution 3**: Bypass checkpoints entirely (not recommended)
```bash
/task-work TASK-001 --no-checkpoint  # New flag (risky!)
```

**Recommendation**: Use Solution 1 (respect checkpoints). Autonomous doesn't mean unmonitored.

### Edge Case 2: Parallel Task Execution

**Problem**: Task-work expects sequential execution. Feature-build supports parallel waves.

**Solution**: Execute tasks in wave **sequentially** for now, parallelize later.

```python
# Current: Sequential within wave
for task_id in wave:
    result = invoke_task_work(task_id, worktree_path, options)

# Future: True parallelization (requires task-work changes)
with ThreadPoolExecutor(max_workers=len(wave)) as executor:
    futures = [
        executor.submit(invoke_task_work, task_id, worktree_path, options)
        for task_id in wave
    ]
    results = [f.result() for f in futures]
```

**Tradeoff**: Lose parallel execution within waves initially, but gain quality gates.

### Edge Case 3: Worktree Conflicts

**Problem**: Multiple tasks modifying same files in parallel.

**Solution**: Sequential execution prevents conflicts. For parallel execution:
1. Analyze task dependencies (file-level)
2. Detect conflicts upfront
3. Serialize conflicting tasks within wave

### Edge Case 4: Documentation Overhead

**Problem**: Task-work generates extensive documentation (Phase 2, 5.5 plans).

**Solution**: Override documentation level for feature builds:
```bash
# Minimal docs for speed (default in feature-build)
/task-work TASK-001 --docs=minimal

# User can override
/feature-build FEAT-A1B2 --docs=standard
```

**Impact**:
- Minimal: 8-12 min/task, 2 files
- Standard: 12-18 min/task, 2 files
- Comprehensive: 36+ min/task, 13+ files

---

## Performance Analysis

### Current Player-Coach

| Metric | Value |
|--------|-------|
| Avg turns per task | 1-2 |
| Time per turn | 5-10 min |
| Total per task | 10-20 min |
| Quality gates | 0 |
| Coverage enforcement | No |
| Scope creep detection | No |

### Proposed Task-Work Delegation

| Metric | Value (--docs=minimal) |
|--------|------------------------|
| Phases executed | 10 |
| Time per task | 12-18 min |
| Quality gates | 5 |
| Coverage enforcement | Yes (80%/75%) |
| Scope creep detection | Yes (±20%) |
| Human checkpoints | Complexity-based |

**Net Impact**: ~50% slower per task, but with full quality enforcement.

**Example Feature (7 tasks)**:
- Current: 70-140 min (no quality assurance)
- Proposed: 84-126 min (full quality assurance)

**Verdict**: Acceptable tradeoff for production quality.

---

## Recommended Implementation Plan

### Milestone 1: Proof of Concept (1-2 days)

**Goal**: Demonstrate task-work invocation within feature worktree.

**Tasks**:
1. Add `invoke_task_work()` function to feature-build
2. Test single task execution in worktree
3. Verify quality gates execute correctly
4. Measure performance impact

**Acceptance Criteria**:
- Task-work executes inside feature worktree
- All 10 phases complete successfully
- Changes committed to feature branch
- Quality gates block when appropriate

### Milestone 2: Mode Flag (3-5 days)

**Goal**: Add `--mode=task-work` flag to feature-build.

**Tasks**:
1. Add mode detection logic
2. Route to task-work or Player-Coach based on flag
3. Update command documentation
4. Add integration tests

**Acceptance Criteria**:
- Both modes available
- Default remains Player-Coach (backwards compatible)
- User can opt-in to task-work mode
- Tests pass for both modes

### Milestone 3: Default Switch (1-2 weeks beta)

**Goal**: Make task-work the default mode.

**Tasks**:
1. Beta test with real features
2. Collect user feedback
3. Address issues
4. Switch default to task-work
5. Mark Player-Coach as deprecated

**Acceptance Criteria**:
- Beta users report success
- Performance acceptable
- Quality gates working as expected
- Documentation updated

### Milestone 4: Deprecation (Future)

**Goal**: Remove Player-Coach mode entirely.

**Tasks**:
1. Announce deprecation timeline
2. Migrate remaining users
3. Remove Player-Coach code
4. Simplify codebase

---

## Decision Matrix: Task-Work vs Player-Coach

| Scenario | Player-Coach | Task-Work |
|----------|--------------|-----------|
| Simple task (complexity 1-3) | Fast (1 turn, 10 min) | Medium (auto-proceed, 12 min) |
| Medium task (complexity 4-6) | Fast (1-2 turns, 15 min) | Medium (optional checkpoint, 15 min) |
| Complex task (complexity 7+) | Risky (may drift, 20+ min) | Safer (mandatory checkpoint, 18 min) |
| Test failures | Manual retry | Auto-fix (3 attempts) |
| Architectural issues | Not detected | Detected (Phase 2.5B) |
| Scope creep | Not detected | Detected (Phase 5.5) |
| Coverage < 80% | Not enforced | Enforced (Phase 4) |
| Production quality | Unknown | Guaranteed |

**Recommendation**: Use task-work for all production features. Player-Coach only for rapid prototyping.

---

## Answers to Review Questions (Revised)

### Quality Gate Integration

**Q1: How should Phase 2.5 (Architectural Review) work when Player is autonomous?**
- **Answer**: Use task-work. Phase 2.5B executes automatically per task.

**Q2: Should Coach validate SOLID/DRY/YAGNI compliance, or should a separate reviewer?**
- **Answer**: Task-work handles it via architectural-reviewer agent in Phase 2.5B.

**Q3: Where does complexity evaluation fit in wave-based execution?**
- **Answer**: Task-work Phase 2.7 runs per task, routes to appropriate review mode.

### Test Enforcement

**Q4: Should test failures trigger Player retry or dedicated test-fixer?**
- **Answer**: Task-work Phase 4.5 auto-fixes up to 3 attempts.

**Q5: How many auto-fix attempts per task before escalating?**
- **Answer**: 3 attempts (task-work default).

**Q6: Should test coverage gates block wave progression?**
- **Answer**: Yes, Phase 4 enforces 80% line / 75% branch per task.

### Human Oversight

**Q7: Which complexity threshold triggers mandatory human review?**
- **Answer**: Complexity ≥7 (task-work Phase 2.8).

**Q8: Should feature-build pause at wave boundaries for approval?**
- **Answer**: No, but individual complex tasks trigger checkpoints.

**Q9: How to surface architectural concerns for human decision?**
- **Answer**: Task-work Phase 2.5B scores < 60 require human review.

### Scope Management

**Q10: How to detect scope creep when Player has autonomy?**
- **Answer**: Task-work Phase 5.5 Plan Audit detects variance per task.

**Q11: Should Plan Audit run per-task or end-of-feature?**
- **Answer**: Per-task (Phase 5.5), aggregated at feature level.

**Q12: What variance thresholds should trigger alerts?**
- **Answer**: Task-work uses ±20% LOC, ±50% file count.

---

## Conclusion (Revised)

**Original Problem**: Feature-build lacks quality gates that task-work provides.

**Original Solution**: Reimplement 5 quality gates in Player-Coach loop.

**Revised Solution**: **Leverage task-work as execution engine for feature-build**.

### Why This is Better

1. **Zero Reimplementation**: Get all 10 phases for free
2. **Feature Parity**: Guaranteed identical quality standards
3. **Faster to Market**: No development time for quality gates
4. **Single Source of Truth**: Task-work defines quality standards
5. **Easier Maintenance**: One codebase to maintain
6. **Proven Quality**: Task-work is battle-tested

### Implementation Path

1. **Phase 1**: Add `--mode=task-work` flag (opt-in)
2. **Beta Period**: Test with real features
3. **Phase 2**: Make task-work default (opt-out Player-Coach)
4. **Future**: Deprecate Player-Coach entirely

### Key Trade-off

- **Speed**: 20-50% slower per task (acceptable)
- **Quality**: Full enforcement of all quality gates (essential)

**Verdict**: Leverage task-work. Don't reinvent the wheel.

---

## Appendix: Feature-Build Command Specification Changes

### Before (Player-Coach Loop)

```bash
/feature-build FEAT-XXX
# Executes: Player → Coach → Loop until APPROVE
# Quality gates: None
```

### After (Task-Work Delegation)

```bash
# Default: Use task-work
/feature-build FEAT-XXX
# Executes: /task-work per task with all 10 phases
# Quality gates: Complete suite

# Opt-out to legacy Player-Coach
/feature-build FEAT-XXX --mode=player-coach
# Executes: Player → Coach (legacy behavior)
# Quality gates: None
```

### New Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--mode=task-work` | Delegate to task-work (recommended) | Will be default |
| `--mode=player-coach` | Use legacy Player-Coach loop | Currently default |
| `--docs=minimal\|standard\|comprehensive` | Documentation level for task-work | minimal |
| `--with-questions` | Allow clarification prompts (not autonomous) | false |
| `--no-questions` | Skip all clarifications (autonomous) | true |

---

## Next Steps

1. Review and approve this revised approach
2. Implement Milestone 1 (Proof of Concept)
3. Test with real feature
4. Iterate based on feedback
5. Roll out to production
