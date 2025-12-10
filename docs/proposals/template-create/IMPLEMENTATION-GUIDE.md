# Template-Create Redesign: Implementation Guide

**Date**: 2025-11-18
**Strategy**: Wave-based parallel development using Conductor
**Command**: `/task-work` for all implementation tasks

---

## Overview

This guide organizes the 8-phase redesign into 4 waves optimized for parallel development using Conductor's git worktrees. Each wave groups tasks that can run simultaneously without blocking each other.

---

## Wave Structure

```
Wave 1: Foundation (No dependencies - fully parallel)
├── Worktree A: TASK-ARTIFACT-FILTER (Phase 1)
└── Worktree B: TASK-AGENT-BRIDGE-COMPLETE (Phase 2)

Wave 2: AI Integration (Depends on Wave 1 - fully parallel)
├── Worktree A: TASK-PHASE-1-CHECKPOINT (Phase 3)
├── Worktree B: TASK-PHASE-5-CHECKPOINT (Phase 4)
└── Worktree C: TASK-PHASE-7-5-CHECKPOINT (Phase 5) [existing]

Wave 3: Integration (Depends on Wave 2 - sequential)
├── TASK-REMOVE-DETECTOR (Phase 6)
└── TASK-RENAME-LEGACY-BUILD-NEW (Phase 7)

Wave 4: Documentation (Depends on Wave 3)
└── TASK-OPEN-SOURCE-DOCUMENTATION (Phase 8)
```

---

## Wave 1: Foundation

**Parallel Worktrees**: 2
**Total Hours**: 6-9 hours
**Dependencies**: None - can start immediately

### Worktree A: Build Artifact Filtering

```bash
# In Conductor, create worktree
conductor workspace create artifact-filter

# In the worktree
cd ~/conductor/guardkit-artifact-filter
/task-work TASK-ARTIFACT-FILTER
```

**Task**: TASK-ARTIFACT-FILTER
**Hours**: 2-3
**Output**: `exclusion_patterns.py` module with filtering logic

**Deliverables**:
- `installer/core/lib/codebase_analyzer/exclusion_patterns.py`
- `tests/unit/codebase_analyzer/test_exclusion_patterns.py`
- Modified `stratified_sampler.py`

### Worktree B: Agent Bridge Infrastructure

```bash
# In Conductor, create worktree
conductor workspace create agent-bridge

# In the worktree
cd ~/conductor/guardkit-agent-bridge
/task-work TASK-AGENT-BRIDGE-COMPLETE
```

**Task**: TASK-AGENT-BRIDGE-COMPLETE
**Hours**: 4-6
**Output**: Complete checkpoint-resume infrastructure

**Deliverables**:
- `installer/core/lib/agent_bridge/checkpoint_manager.py`
- `installer/core/lib/agent_bridge/mock_invoker.py`
- `tests/unit/agent_bridge/test_checkpoint_manager.py`
- `tests/integration/test_agent_workflow.py`

### Wave 1 Completion Criteria

Before moving to Wave 2:
- [ ] Both worktrees merged to main
- [ ] All tests passing
- [ ] `.NET project detected as C#` (not Java)
- [ ] Checkpoint save/load working

---

## Wave 2: AI Integration

**Parallel Worktrees**: 3
**Total Hours**: 7-10 hours
**Dependencies**: Wave 1 complete

All three tasks can run in parallel because they each implement checkpoint-resume for different phases and don't modify the same code.

### Worktree A: Phase 1 AI Analysis

```bash
conductor workspace create phase-1-checkpoint

cd ~/conductor/guardkit-phase-1-checkpoint
/task-work TASK-PHASE-1-CHECKPOINT
```

**Task**: TASK-PHASE-1-CHECKPOINT
**Hours**: 2-3
**Output**: AI-powered codebase analysis with 90%+ confidence

**Key Changes**:
- `_phase1_ai_analysis()` method
- `_run_from_phase_1()` resume method
- `CodebaseAnalysis.from_ai_response()`

### Worktree B: Phase 5 Agent Creation

```bash
conductor workspace create phase-5-checkpoint

cd ~/conductor/guardkit-phase-5-checkpoint
/task-work TASK-PHASE-5-CHECKPOINT
```

**Task**: TASK-PHASE-5-CHECKPOINT
**Hours**: 2-3
**Output**: AI-powered agent creation (7-9 agents)

**Key Changes**:
- `_phase5_agent_creation()` method
- `_inventory_existing_agents()` method
- `_run_from_phase_5()` resume method
- `AgentCreationResult` dataclass

### Worktree C: Phase 7.5 Agent Enhancement

```bash
conductor workspace create phase-7-5-checkpoint

cd ~/conductor/guardkit-phase-7-5-checkpoint
/task-work TASK-PHASE-7-5-CHECKPOINT
```

**Task**: TASK-PHASE-7-5-CHECKPOINT (existing task in `tasks/in_review/`)
**Hours**: 3-4
**Output**: Enhanced agents (150-250 lines)

**Note**: The `agent_enhancer.py` changes (relevance-based template selection, code sampling) should be committed before this task starts, as they provide the foundation.

**Key Changes**:
- `_phase7_5_enhance_agents()` method
- `_run_from_phase_7()` resume method
- Agent serialization methods

### Wave 2 Completion Criteria

Before moving to Wave 3:
- [ ] All three worktrees merged to main
- [ ] All tests passing
- [ ] Phase 1 produces 90%+ confidence
- [ ] Phase 5 creates 7-9 agents
- [ ] Phase 7.5 enhances to 150-250 lines
- [ ] Checkpoint-resume works for all phases

---

## Wave 3: Integration

**Parallel Worktrees**: 1 (sequential tasks)
**Total Hours**: 3-5 hours
**Dependencies**: Wave 2 complete

These tasks must run sequentially because Phase 7 integrates all previous work.

### Task 1: Remove Hard-Coded Detection

```bash
conductor workspace create integration

cd ~/conductor/guardkit-integration
/task-work TASK-REMOVE-DETECTOR
```

**Task**: TASK-REMOVE-DETECTOR
**Hours**: 1-2
**Output**: 1,045 LOC removed

**Verification before deletion**:
```bash
# Ensure AI phases work before removing fallback
/template-create --validate --name test-before-removal
# Must show 90%+ confidence
```

### Task 2: Build Clean Main Command

```bash
# Continue in same worktree after TASK-REMOVE-DETECTOR completes
/task-work TASK-RENAME-LEGACY-BUILD-NEW
```

**Task**: TASK-RENAME-LEGACY-BUILD-NEW
**Hours**: 2-3
**Output**: Clean `/template-create` command with all fixes

**Steps**:
1. Rename existing files to `-legacy`
2. Create new command spec
3. Create new orchestrator integrating all Phase 1-6 fixes
4. E2E test on 4 reference projects

### Wave 3 Completion Criteria

Before moving to Wave 4:
- [ ] Integration worktree merged to main
- [ ] `/template-create` works (new version)
- [ ] `/template-create-legacy` available as fallback
- [ ] E2E tests pass on all 4 reference projects:
  - DeCUK.Mobile.MyDrive (C#, .NET MAUI)
  - bulletproof-react (TypeScript, React)
  - fastapi-best-practices (Python, FastAPI)
  - nextjs-boilerplate (TypeScript, Next.js)
- [ ] Confidence 90%+, 7-9 agents, 150-250 line agents

---

## Wave 4: Documentation

**Parallel Worktrees**: 1
**Total Hours**: 2-3 hours
**Dependencies**: Wave 3 complete

### Documentation Task

```bash
conductor workspace create documentation

cd ~/conductor/guardkit-documentation

# Option 1: Use /task-work for consistency
/task-work TASK-OPEN-SOURCE-DOCUMENTATION

# Option 2: Manual implementation (simpler for docs)
# Create the markdown files directly following the task spec
```

**Task**: TASK-OPEN-SOURCE-DOCUMENTATION
**Hours**: 2-3
**Output**: Complete documentation for open source release

**Deliverables**:
- `docs/guides/template-creation-guide.md`
- `docs/architecture/template-create-architecture.md`
- `docs/troubleshooting/template-create-troubleshooting.md`
- Updated `CLAUDE.md`
- Updated `README.md`

### Wave 4 Completion Criteria

- [ ] All documentation created
- [ ] No references to "legacy" in user-facing docs
- [ ] Examples cover all major stacks
- [ ] Links work
- [ ] Professional tone

---

## Conductor Workflow Commands

### Starting a Wave

```bash
# Create all worktrees for a wave
conductor workspace create <name>

# List active worktrees
conductor workspace list

# Switch to a worktree
conductor workspace switch <name>
```

### Running Tasks

```bash
# In each worktree, use /task-work
/task-work TASK-ARTIFACT-FILTER

# Check task status
/task-status TASK-ARTIFACT-FILTER

# Complete task after review
/task-complete TASK-ARTIFACT-FILTER
```

### Merging Results

```bash
# After task completion in worktree
git add . && git commit -m "feat: implement TASK-ARTIFACT-FILTER"
git push origin feature/artifact-filter

# Create PR and merge to main
gh pr create --title "feat: build artifact filtering" --body "..."

# After merge, delete worktree
conductor workspace delete artifact-filter
```

---

## Parallel Execution Timeline

```
Wave 1 (Foundation)          Wave 2 (AI Integration)       Wave 3        Wave 4
─────────────────────────    ─────────────────────────    ──────────    ────────
[Artifact Filter  2-3h]      [Phase 1 Checkpoint  2-3h]   [Remove  1-2h]
[Agent Bridge     4-6h]  →   [Phase 5 Checkpoint  2-3h]   [Build   2-3h] → [Docs 2-3h]
                             [Phase 7.5 Checkpoint 3-4h]

Elapsed: 4-6h                Elapsed: 3-4h                 Elapsed: 3-5h   Elapsed: 2-3h

Total Elapsed Time: ~12-18 hours (vs 18-26 sequential)
```

**Time Savings**: Parallel execution saves approximately 6-8 hours compared to sequential implementation.

---

## Pre-Implementation Checklist

### Before Wave 1

- [ ] Commit existing `agent_enhancer.py` changes (code sampling, relevance selection)
- [ ] Review all task specifications
- [ ] Ensure Conductor is configured
- [ ] Set up git worktrees directory

### Before Each Task

```bash
# Pull latest main
git checkout main && git pull

# Create feature branch in worktree
conductor workspace create <name>
cd ~/conductor/guardkit-<name>
git checkout -b feature/<task-name>

# Verify task file exists
cat tasks/backlog/TASK-<NAME>.md
```

### After Each Task

```bash
# Run tests
pytest tests/ -v --cov

# Verify acceptance criteria
# (specific to each task)

# Commit and push
git add . && git commit -m "feat: implement TASK-<NAME>"
git push origin feature/<task-name>

# Create PR
gh pr create
```

---

## Risk Mitigation

### Wave 2 Merge Conflicts

The three Wave 2 tasks all modify `template_create_orchestrator.py`. To minimize conflicts:

1. **Define clear boundaries**: Each task adds specific methods (not modifying same lines)
2. **Merge order**: Phase 1 → Phase 5 → Phase 7.5 (bottom-up in file)
3. **Rebase before merge**: Each PR rebases on latest main before merge

### Wave 3 Failure Recovery

If AI phases prove insufficient after removing detector:

```bash
# Emergency rollback
git revert HEAD  # Revert removal commit
# Keep legacy as fallback while investigating
```

---

## Success Metrics

### Per-Wave Metrics

| Wave | Key Metric | Target |
|------|------------|--------|
| 1 | Language detection accuracy | 95%+ |
| 2 | Confidence score | 90%+ |
| 2 | Agents created | 7-9 |
| 2 | Agent line count | 150-250 |
| 3 | E2E success rate | 100% (4/4 projects) |
| 4 | Documentation complete | All 3 guides |

### Final Validation

```bash
# Run on all reference projects
for project in maui react fastapi nextjs; do
    /template-create --validate --name final-test-$project
done

# All must show:
# ✅ Confidence 90%+
# ✅ 7-9 agents
# ✅ Agent files 150-250 lines
# ✅ Correct language/framework
```

---

## Quick Reference

### Wave Summary

| Wave | Tasks | Worktrees | Hours | Dependencies |
|------|-------|-----------|-------|--------------|
| 1 | 2 | 2 parallel | 6-9 | None |
| 2 | 3 | 3 parallel | 7-10 | Wave 1 |
| 3 | 2 | 1 sequential | 3-5 | Wave 2 |
| 4 | 1 | 1 | 2-3 | Wave 3 |

### Task → Command

| Task | Command |
|------|---------|
| TASK-ARTIFACT-FILTER | `/task-work TASK-ARTIFACT-FILTER` |
| TASK-AGENT-BRIDGE-COMPLETE | `/task-work TASK-AGENT-BRIDGE-COMPLETE` |
| TASK-PHASE-1-CHECKPOINT | `/task-work TASK-PHASE-1-CHECKPOINT` |
| TASK-PHASE-5-CHECKPOINT | `/task-work TASK-PHASE-5-CHECKPOINT` |
| TASK-PHASE-7-5-CHECKPOINT | `/task-work TASK-PHASE-7-5-CHECKPOINT` |
| TASK-REMOVE-DETECTOR | `/task-work TASK-REMOVE-DETECTOR` |
| TASK-RENAME-LEGACY-BUILD-NEW | `/task-work TASK-RENAME-LEGACY-BUILD-NEW` |
| TASK-OPEN-SOURCE-DOCUMENTATION | `/task-work TASK-OPEN-SOURCE-DOCUMENTATION` |

---

## Next Steps

1. **Now**: Commit existing `agent_enhancer.py` changes
2. **Wave 1**: Start both worktrees in parallel
3. **Merge Wave 1**: Both tasks complete, merge to main
4. **Wave 2**: Start all three worktrees in parallel
5. **Continue**: Through Waves 3 and 4

**Ready to begin?** Create the first two worktrees for Wave 1:

```bash
conductor workspace create artifact-filter
conductor workspace create agent-bridge
```

---

**Created**: 2025-11-18
**Parallel Optimization**: 4 waves with up to 3 concurrent worktrees
**Total Elapsed Time**: ~12-18 hours (vs 18-26 sequential)
