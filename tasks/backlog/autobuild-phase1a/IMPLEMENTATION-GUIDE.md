# AutoBuild Phase 1a - Implementation Guide

## Overview

This guide provides wave-based execution strategy for implementing the AutoBuild Phase 1a feature with optimal parallelization using Conductor.

## Wave Breakdown

### Wave 1: Foundation Components (Parallel Execution)

**Duration**: 4-5 hours (with Conductor) vs 10-14 hours (sequential)
**Parallelization**: ✅ All 4 tasks can run simultaneously
**Conductor Workspaces**: 4 workspaces

#### Task 1: TASK-AB-6908 - Update Agent Definitions
- **Workspace**: `autobuild-phase1a-wave1-1`
- **Mode**: Direct edit (no /task-work needed)
- **Duration**: 1-2 hours
- **Dependencies**: None
- **Files Modified**:
  - `.claude/agents/autobuild-player.md`
  - `.claude/agents/autobuild-coach.md`
- **Deliverable**: Agents with frontmatter and Boundaries sections

#### Task 2: TASK-AB-F55D - Implement WorktreeManager
- **Workspace**: `autobuild-phase1a-wave1-2`
- **Mode**: /task-work (requires testing)
- **Duration**: 3-4 hours
- **Dependencies**: None
- **Files Created**:
  - `guardkit/orchestrator/__init__.py`
  - `guardkit/orchestrator/worktrees.py`
  - `tests/unit/test_worktree_manager.py`
- **Deliverable**: WorktreeManager class with ≥80% test coverage

#### Task 3: TASK-AB-A76A - Implement AgentInvoker
- **Workspace**: `autobuild-phase1a-wave1-3`
- **Mode**: /task-work (requires testing)
- **Duration**: 4-5 hours
- **Dependencies**: None
- **Files Created**:
  - `guardkit/orchestrator/agent_invoker.py`
  - `tests/unit/test_agent_invoker.py`
- **Deliverable**: AgentInvoker class with SDK integration

#### Task 4: TASK-AB-584A - Implement ProgressDisplay
- **Workspace**: `autobuild-phase1a-wave1-4`
- **Mode**: /task-work (requires testing)
- **Duration**: 2-3 hours
- **Dependencies**: None
- **Files Created**:
  - `guardkit/orchestrator/progress.py`
  - `tests/unit/test_progress_display.py`
- **Deliverable**: ProgressDisplay class with Rich library integration

**Wave 1 Completion Criteria**:
- ✅ All 4 components implemented independently
- ✅ All unit tests passing (≥80% coverage per component)
- ✅ No file conflicts (components are independent)
- ✅ Ready for integration in Wave 2

**Conductor Setup**:
```bash
# Create 4 parallel workspaces
conductor workspace create autobuild-phase1a-wave1-1 --branch autobuild-phase1a-wave1-1
conductor workspace create autobuild-phase1a-wave1-2 --branch autobuild-phase1a-wave1-2
conductor workspace create autobuild-phase1a-wave1-3 --branch autobuild-phase1a-wave1-3
conductor workspace create autobuild-phase1a-wave1-4 --branch autobuild-phase1a-wave1-4

# Execute tasks in parallel (different terminal tabs)
cd ~/.conductor/workspaces/autobuild-phase1a-wave1-1 && /task-work TASK-AB-6908
cd ~/.conductor/workspaces/autobuild-phase1a-wave1-2 && /task-work TASK-AB-F55D
cd ~/.conductor/workspaces/autobuild-phase1a-wave1-3 && /task-work TASK-AB-A76A
cd ~/.conductor/workspaces/autobuild-phase1a-wave1-4 && /task-work TASK-AB-584A
```

---

### Wave 2: Orchestration Integration (Sequential Execution)

**Duration**: 5-6 hours
**Parallelization**: ❌ Requires Wave 1 completion
**Dependencies**: All Wave 1 tasks must be merged to main

#### Task 5: TASK-AB-9869 - Implement AutoBuildOrchestrator
- **Workspace**: Main repo or single Conductor workspace
- **Mode**: /task-work (requires integration testing)
- **Duration**: 5-6 hours
- **Dependencies**: TASK-AB-F55D, TASK-AB-A76A, TASK-AB-584A
- **Files Created**:
  - `guardkit/orchestrator/autobuild.py`
  - `tests/unit/test_autobuild_orchestrator.py`
- **Deliverable**: AutoBuildOrchestrator class integrating all Wave 1 components

**Wave 2 Pre-requisites**:
1. Merge all Wave 1 branches to main
2. Verify all Wave 1 tests passing on main
3. Resolve any merge conflicts (unlikely - independent components)

**Wave 2 Completion Criteria**:
- ✅ Orchestrator integrates WorktreeManager, AgentInvoker, ProgressDisplay
- ✅ Phase-based orchestration implemented (Setup, Loop, Finalize)
- ✅ Adversarial loop with turn management working
- ✅ Unit tests passing (≥80% coverage)

---

### Wave 3: CLI Interface (Sequential Execution)

**Duration**: 2-3 hours
**Parallelization**: ❌ Requires Wave 2 completion
**Dependencies**: TASK-AB-9869 must be merged to main

#### Task 6: TASK-AB-BD2E - Implement CLI Commands
- **Workspace**: Main repo or single Conductor workspace
- **Mode**: /task-work (requires CLI testing)
- **Duration**: 2-3 hours
- **Dependencies**: TASK-AB-9869
- **Files Modified/Created**:
  - `guardkit/cli/main.py` (add autobuild group)
  - `guardkit/cli/autobuild.py` (new)
  - `tests/unit/test_cli_autobuild.py` (new)
- **Deliverable**: `guardkit autobuild task TASK-XXX` command working

**Wave 3 Completion Criteria**:
- ✅ CLI commands functional (`guardkit autobuild task`, `guardkit autobuild status`)
- ✅ Command-line options working (`--max-turns`, `--auto-merge`, `--model`)
- ✅ Help text and examples complete
- ✅ CLI tests passing

---

### Wave 4: Integration Testing & Documentation (Sequential Execution)

**Duration**: 3-4 hours
**Parallelization**: ❌ Requires Wave 3 completion
**Dependencies**: TASK-AB-BD2E must be merged to main

#### Task 7: TASK-AB-2D16 - Integration Testing and Documentation
- **Workspace**: Main repo
- **Mode**: /task-work (requires comprehensive testing)
- **Duration**: 3-4 hours
- **Dependencies**: All previous waves complete
- **Files Created**:
  - `tests/integration/test_autobuild_e2e.py`
  - `tests/fixtures/TEST-SIMPLE.md`
  - `tests/fixtures/TEST-ITERATION.md`
  - Updated: `CLAUDE.md` (AutoBuild documentation section)
- **Deliverable**: Complete end-to-end tests and documentation

**Wave 4 Completion Criteria**:
- ✅ End-to-end integration tests passing
- ✅ TEST-SIMPLE completes in 1-2 turns
- ✅ TEST-ITERATION requires 2+ turns (validates feedback loop)
- ✅ Max turns exceeded scenario tested
- ✅ CLAUDE.md updated with AutoBuild usage guide
- ✅ All acceptance criteria from TASK-REV-47D2 verified

---

## Execution Strategy

### Recommended Approach: Maximize Parallelization

1. **Wave 1**: Use Conductor for 4 parallel workspaces (33% time savings)
2. **Wave 2-4**: Sequential execution on main (dependencies prevent parallelization)

**Total Time**:
- **With Conductor (recommended)**: 14-18 hours
- **Without Conductor (sequential)**: 20-27 hours

### Alternative: Sequential Execution

If Conductor not available or team prefers simpler workflow:

1. Execute tasks in order: TASK-AB-6908 → TASK-AB-F55D → TASK-AB-A76A → TASK-AB-584A → TASK-AB-9869 → TASK-AB-BD2E → TASK-AB-2D16
2. Each task completed before starting next
3. Total time: 20-27 hours

---

## Risk Mitigation

### Risk 1: Wave 1 Merge Conflicts
**Likelihood**: Low (independent components)
**Mitigation**: Components designed with no file overlap

### Risk 2: SDK API Changes During Development
**Likelihood**: Medium
**Mitigation**: Pin `claude-code-sdk = "~=0.1.0"` in pyproject.toml before Wave 1

### Risk 3: Integration Issues in Wave 2
**Likelihood**: Medium
**Mitigation**: Wave 1 unit tests verify component interfaces match expected usage

### Risk 4: Time Estimates Exceeded
**Likelihood**: Medium (typical 20-30% overrun)
**Mitigation**: Built 20% buffer into estimates, prioritize completing Waves 1-3 before Wave 4

---

## Testing Strategy

### Unit Tests (Per Wave)
- **Wave 1**: Each component has ≥80% test coverage
- **Wave 2**: Orchestrator mocks dependencies (fast tests)
- **Wave 3**: CLI tests mock orchestrator (isolation)

### Integration Tests (Wave 4)
- End-to-end with real SDK calls (mocked in CI, real in manual testing)
- Simple task fixture (1-2 turns expected)
- Complex task fixture (2+ turns expected)
- Max turns exceeded scenario

### Manual Testing Checklist
- [ ] `guardkit autobuild task TEST-SIMPLE` completes successfully
- [ ] `guardkit autobuild task TEST-ITERATION` requires multiple turns
- [ ] Progress display shows real-time updates
- [ ] Worktree isolated from main branch
- [ ] Merge on approval works correctly
- [ ] Preservation on failure works correctly

---

## Success Criteria

**Phase 1a Complete When**:
1. ✅ All 7 subtasks completed and merged
2. ✅ All tests passing (unit + integration)
3. ✅ `guardkit autobuild task TASK-XXX` command functional
4. ✅ Documentation updated in CLAUDE.md
5. ✅ Manual testing checklist completed
6. ✅ Block AI Research pattern validated (Player/Coach adversarial loop working)

**Metrics to Track** (post-implementation):
- Task completion rate (target: ≥50%)
- Average turns to completion (target: ≤4)
- Coach catch rate (target: >80%)
- False approval rate (target: 0%)

---

## Next Steps After Implementation

1. Deploy to production
2. Run pilot with 10 simple tasks
3. Analyze metrics (completion rate, turns, quality)
4. Tune Coach prompts based on approval patterns
5. Plan Phase 1b enhancements (multi-model, parallel tasks, memory)

---

**Created**: 2025-12-23
**Last Updated**: 2025-12-23
**Version**: 1.0
