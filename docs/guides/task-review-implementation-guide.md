# Implementation Guide: /task-review Command

**Proposal**: [task-review-command-proposal.md](../proposals/task-review-command-proposal.md)

**Total Effort**: 22-36 hours across 5 phases

**Parallel Development**: Yes - Phases can be developed concurrently using [Conductor](https://conductor.build) git worktrees

---

## Table of Contents

1. [Overview](#overview)
2. [Development Waves](#development-waves)
3. [Task Dependencies](#task-dependencies)
4. [Parallel Development Strategy](#parallel-development-strategy)
5. [Conductor Setup](#conductor-setup)
6. [Wave-by-Wave Implementation](#wave-by-wave-implementation)
7. [Testing Strategy](#testing-strategy)
8. [Integration Points](#integration-points)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The `/task-review` command implementation is broken into **5 tasks** organized into **3 development waves** for parallel execution.

### Task Breakdown

| Task ID | Phase | Complexity | Effort | Wave | Parallelizable |
|---------|-------|------------|--------|------|----------------|
| TASK-REV-A4AB | 1 - Core | 6/10 | 4-8h | Wave 1 | No (foundation) |
| TASK-REV-3248 | 2 - Modes | 7/10 | 8-12h | Wave 2 | Yes (5 modes) |
| TASK-REV-2367 | 3 - Reports | 5/10 | 4-6h | Wave 2 | Yes (with Wave 2) |
| TASK-REV-5DC2 | 4 - Integration | 4/10 | 2-4h | Wave 3 | Yes (with Wave 3) |
| TASK-REV-4DE8 | 5 - Testing | 5/10 | 4-6h | Wave 3 | Yes (with Wave 3) |

### Critical Path

```
Wave 1: Foundation (Sequential)
  TASK-REV-A4AB (Phase 1 - Core Command)
        ↓
Wave 2: Features (Parallel)
  TASK-REV-3248 (Phase 2 - Review Modes)  ← Worktree 1
        +
  TASK-REV-2367 (Phase 3 - Reports)       ← Worktree 2
        ↓
Wave 3: Polish (Parallel)
  TASK-REV-5DC2 (Phase 4 - Integration)   ← Worktree 1
        +
  TASK-REV-4DE8 (Phase 5 - Testing)       ← Worktree 2
```

**Total Time**:
- Sequential: 22-36 hours
- Parallel (3 waves): 14-24 hours (35-40% time savings)

---

## Development Waves

### Wave 1: Foundation (Sequential) - 4-8 hours

**Objective**: Build core infrastructure that all other phases depend on

**Tasks**: 1 task (must complete before Wave 2)
- **TASK-REV-A4AB**: Core command, orchestrator, state management

**Why Sequential**: Foundation for all other work. No parallelization possible.

**Deliverables**:
- `installer/core/commands/task-review.md` (command spec)
- `installer/core/commands/lib/task_review_orchestrator.py` (orchestrator)
- `REVIEW_COMPLETE` state support
- Skeleton functions for Phases 2-5

**Success Criteria**:
- `/task-review TASK-XXX` command recognized
- All flags accepted (--mode, --depth, --output)
- Task context loads successfully
- State transitions work

**Developer Assignment**: 1 developer

---

### Wave 2: Features (Parallel) - 8-12 hours

**Objective**: Implement review modes and report generation concurrently

**Tasks**: 2 tasks (can be developed in parallel)
- **TASK-REV-3248**: Review modes (5 modes with agent invocations)
- **TASK-REV-2367**: Report generation (3 formats + decision checkpoint)

**Why Parallel**:
- Review modes output structured data
- Report generator consumes structured data
- Minimal interface: `Dict[str, Any]` between modes and reports
- No shared code modifications (separate modules)

**Parallelization Strategy**:

| Worktree | Task | Developer | Focus |
|----------|------|-----------|-------|
| `worktree-modes` | TASK-REV-3248 | Developer A | Review modes + agents |
| `worktree-reports` | TASK-REV-2367 | Developer B | Report formatting + checkpoint |

**Interface Contract** (agreed before Wave 2 starts):

```python
# Output from TASK-REV-3248 (review modes)
review_results: Dict[str, Any] = {
    "mode": str,           # "architectural", "code-quality", etc.
    "depth": str,          # "quick", "standard", "comprehensive"
    "overall_score": int,  # 0-100 or 0-10 depending on mode
    "findings": List[Dict],
    "recommendations": List[str],
    "evidence": List[str]  # File paths with issues
}

# Input to TASK-REV-2367 (report generation)
def generate_review_report(
    review_results: Dict[str, Any],
    recommendations: Dict[str, Any],
    output_format: str
) -> str:
    ...
```

**Integration Point**: Use mock data during parallel development, integrate at end of Wave 2.

**Deliverables**:
- `installer/core/commands/lib/review_modes/` (5 mode implementations)
- `installer/core/commands/lib/review_report_generator.py`
- `installer/core/commands/lib/review_templates/` (5 report templates)
- Decision checkpoint implementation

**Success Criteria**:
- All 5 review modes execute successfully
- All 3 report formats generate correctly
- Decision checkpoint is interactive
- Integration test passes (mock data → real report)

**Developer Assignment**: 2 developers in parallel

---

### Wave 3: Polish (Parallel) - 4-8 hours

**Objective**: Integration with existing commands and comprehensive testing

**Tasks**: 2 tasks (can be developed in parallel)
- **TASK-REV-5DC2**: Integration with task-create, documentation
- **TASK-REV-4DE8**: Comprehensive testing (60+ tests)

**Why Parallel**:
- Integration work touches `/task-create` and docs
- Testing validates existing code (read-only for review logic)
- No overlapping file modifications

**Parallelization Strategy**:

| Worktree | Task | Developer | Focus |
|----------|------|-----------|-------|
| `worktree-integration` | TASK-REV-5DC2 | Developer A | task-create hints, docs |
| `worktree-testing` | TASK-REV-4DE8 | Developer B | Test suite, coverage |

**Integration Point**: Merge integration first, then testing (validates integrated system).

**Deliverables**:
- Task creation detection and hints
- CLAUDE.md updates
- Workflow guide (`docs/workflows/task-review-workflow.md`)
- 60+ tests (unit, integration, performance)
- ≥80% code coverage

**Success Criteria**:
- `/task-create` suggests `/task-review` appropriately
- Documentation complete and accurate
- All tests pass
- Coverage thresholds met

**Developer Assignment**: 2 developers in parallel

---

## Task Dependencies

### Dependency Graph

```
TASK-REV-A4AB (Wave 1 - Foundation)
       ├─────────────────┬─────────────────┐
       │                 │                 │
       ↓                 ↓                 ↓
TASK-REV-3248     TASK-REV-2367    (Wave 2 - Features, parallel)
(Review Modes)    (Reports)
       │                 │
       └────────┬────────┘
                ↓
         Wave 2 Complete
                │
       ├────────┴────────┐
       ↓                 ↓
TASK-REV-5DC2     TASK-REV-4DE8    (Wave 3 - Polish, parallel)
(Integration)     (Testing)
       │                 │
       └────────┬────────┘
                ↓
         Complete
```

### Dependency Rules

1. **Wave 1 must complete before Wave 2 starts** (hard dependency)
2. **Wave 2 tasks can start simultaneously** (after Wave 1 complete)
3. **Wave 3 tasks can start simultaneously** (after Wave 2 complete)
4. **Within each wave**: Tasks are independent and parallelizable

---

## Parallel Development Strategy

### Using Conductor with Git Worktrees

[Conductor](https://conductor.build) enables true parallel development by creating isolated git worktrees for each task.

#### Benefits

✅ **Isolated Development**: Each task in its own directory
✅ **No Branch Conflicts**: Work on multiple tasks simultaneously
✅ **Shared Git Repo**: All worktrees share `.git/` (no duplication)
✅ **State Preservation**: GuardKit state synced via symlinks
✅ **Zero Context Switching**: Keep all worktrees open in separate IDE windows

#### Workflow

```bash
# Wave 1: Single worktree (sequential)
conductor create worktree-foundation
cd worktree-foundation
/task-work TASK-REV-A4AB
# ... complete Phase 1 ...
/task-complete TASK-REV-A4AB

# Wave 2: Two parallel worktrees
conductor create worktree-modes
conductor create worktree-reports

# Terminal 1 (Developer A or AI Session 1)
cd worktree-modes
/task-work TASK-REV-3248
# ... work on review modes ...

# Terminal 2 (Developer B or AI Session 2)
cd worktree-reports
/task-work TASK-REV-2367
# ... work on report generation ...

# Both complete in parallel
cd worktree-modes && /task-complete TASK-REV-3248
cd worktree-reports && /task-complete TASK-REV-2367

# Merge both branches
git checkout main
git merge worktree-modes/task-rev-3248
git merge worktree-reports/task-rev-2367

# Wave 3: Two parallel worktrees (same pattern)
conductor create worktree-integration
conductor create worktree-testing
# ... repeat parallel workflow ...
```

---

## Conductor Setup

### Prerequisites

```bash
# Install Conductor (if not already installed)
# See https://conductor.build for installation instructions

# Verify GuardKit is Conductor-compatible
guardkit doctor

# Expected output:
# ✅ Conductor integration: Enabled
# ✅ Symlinks configured: ~/.claude/* → ~/.agentecflow/*
# ✅ State persistence: Working
```

### Create Parallel Worktrees

#### Wave 1: Foundation (1 worktree)

```bash
# Create worktree for Phase 1
conductor create worktree-foundation

# Verify worktree
cd worktree-foundation
ls  # Should see project files
ls .claude  # Should see symlinked commands/agents

# Work on task
/task-work TASK-REV-A4AB
```

#### Wave 2: Features (2 worktrees)

```bash
# After Wave 1 complete, create 2 worktrees for parallel work

# Worktree 1: Review Modes
conductor create worktree-modes --branch=feature/review-modes
cd worktree-modes
/task-work TASK-REV-3248

# Worktree 2: Report Generation (in separate terminal/IDE)
cd ../  # Back to main repo
conductor create worktree-reports --branch=feature/report-generation
cd worktree-reports
/task-work TASK-REV-2367
```

**Parallel Development**:
- Developer A works in `worktree-modes/`
- Developer B works in `worktree-reports/`
- Both see same GuardKit commands (symlinked)
- Both have independent task state (isolated)
- No conflicts (different files modified)

#### Wave 3: Polish (2 worktrees)

```bash
# After Wave 2 complete and merged, create 2 worktrees for final parallel work

# Worktree 1: Integration
conductor create worktree-integration --branch=feature/task-review-integration
cd worktree-integration
/task-work TASK-REV-5DC2

# Worktree 2: Testing (in separate terminal/IDE)
cd ../
conductor create worktree-testing --branch=feature/task-review-testing
cd worktree-testing
/task-work TASK-REV-4DE8
```

### State Management Across Worktrees

GuardKit automatically syncs state across worktrees via symlinks:

```
Main Repo: ~/Projects/guardkit/
  ├── .claude/
  │   └── state/ → ~/.agentecflow/state/  (symlinked, shared)
  ├── worktree-modes/
  │   ├── .claude/
  │   │   └── state/ → ~/.agentecflow/state/  (same symlink, shared)
  ├── worktree-reports/
  │   └── .claude/
  │       └── state/ → ~/.agentecflow/state/  (same symlink, shared)
```

**Result**: All worktrees see the same task state, implementation plans, and review reports.

---

## Wave-by-Wave Implementation

### Wave 1: Foundation (Sequential)

**Duration**: 4-8 hours

**Single Developer Workflow**:

```bash
# Step 1: Create worktree
conductor create worktree-foundation --branch=feature/task-review-foundation
cd worktree-foundation

# Step 2: Start task
/task-work TASK-REV-A4AB

# Task will execute:
# Phase 1: Load task context
# Phase 2: Implementation planning
# Phase 2.5: Architectural review
# Phase 3: Implementation (core orchestrator, state management)
# Phase 4: Testing (unit tests)
# Phase 5: Code review

# Step 3: Verify deliverables
ls installer/core/commands/task-review.md
ls installer/core/commands/lib/task_review_orchestrator.py
ls installer/core/commands/lib/review_context_loader.py

# Step 4: Manual testing
/task-review TASK-09E9 --mode=architectural --depth=quick
# Should execute without errors (skeleton phases)

# Step 5: Complete task
/task-complete TASK-REV-A4AB

# Step 6: Merge to main
cd ..
git checkout main
git merge worktree-foundation/feature/task-review-foundation

# Step 7: Verify integration
pytest tests/unit/commands/test_task_review_orchestrator.py

# Step 8: Commit state files
git add docs/state/TASK-REV-A4AB/
git commit -m "Save state for TASK-REV-A4AB"

# Wave 1 complete! Ready for Wave 2.
```

**Success Gate**: All Wave 1 acceptance criteria met before proceeding to Wave 2.

---

### Wave 2: Features (Parallel)

**Duration**: 8-12 hours (with parallel development)

**Two-Developer Workflow**:

#### Developer A: Review Modes (TASK-REV-3248)

```bash
# Terminal 1 / IDE Window 1
conductor create worktree-modes --branch=feature/review-modes
cd worktree-modes

# Start task
/task-work TASK-REV-3248

# Implementation focus:
# - installer/core/commands/lib/review_modes/architectural_review.py
# - installer/core/commands/lib/review_modes/code_quality_review.py
# - installer/core/commands/lib/review_modes/decision_analysis.py
# - installer/core/commands/lib/review_modes/technical_debt_assessment.py
# - installer/core/commands/lib/review_modes/security_audit.py
# - Update execute_review_analysis() in orchestrator

# Test with mock task
/task-review TASK-09E9 --mode=architectural --depth=comprehensive
# Should invoke architectural-reviewer agent

# Complete task
/task-complete TASK-REV-3248
```

#### Developer B: Report Generation (TASK-REV-2367)

```bash
# Terminal 2 / IDE Window 2
conductor create worktree-reports --branch=feature/report-generation
cd worktree-reports

# Start task
/task-work TASK-REV-2367

# Implementation focus:
# - installer/core/commands/lib/review_report_generator.py
# - installer/core/commands/lib/review_templates/*.md.template
# - Update generate_review_report() in orchestrator
# - Implement present_decision_checkpoint()

# Test with mock data
python3 -c "
from installer.core.commands.lib.review_report_generator import generate_review_report
results = {'mode': 'architectural', 'overall_score': 75, 'findings': [...]}
report = generate_review_report(results, {}, 'detailed')
print(report)
"

# Complete task
/task-complete TASK-REV-2367
```

#### Integration (After Both Complete)

```bash
# Both developers have completed their tasks
# Now integrate the two branches

# Developer A or Lead
cd ~/Projects/guardkit  # Main repo

# Merge review modes first
git checkout main
git merge worktree-modes/feature/review-modes

# Merge report generation
git merge worktree-reports/feature/report-generation

# Integration test
/task-review TASK-09E9 --mode=architectural --output=detailed
# Should invoke agent, generate report, show decision checkpoint

# Verify end-to-end workflow
pytest tests/integration/test_task_review_workflow.py

# Commit state files
git add docs/state/TASK-REV-3248/ docs/state/TASK-REV-2367/
git commit -m "Save state for Wave 2 tasks"

# Wave 2 complete! Ready for Wave 3.
```

**Conflict Resolution**: If both branches modified `task_review_orchestrator.py`, resolve conflicts by combining changes:
- Developer A added mode selection logic
- Developer B added report generation logic
- Both changes are complementary (different functions)

---

### Wave 3: Polish (Parallel)

**Duration**: 4-8 hours (with parallel development)

**Two-Developer Workflow**:

#### Developer A: Integration (TASK-REV-5DC2)

```bash
# Terminal 1 / IDE Window 1
conductor create worktree-integration --branch=feature/task-review-integration
cd worktree-integration

# Start task
/task-work TASK-REV-5DC2

# Implementation focus:
# - Update installer/core/commands/lib/task_create_orchestrator.py
#   (add review task detection)
# - Update CLAUDE.md (add /task-review documentation)
# - Create docs/workflows/task-review-workflow.md
# - Update README.md

# Test task-create detection
/task-create "Review authentication architecture" decision_required:true
# Should suggest using /task-review

# Complete task
/task-complete TASK-REV-5DC2
```

#### Developer B: Testing (TASK-REV-4DE8)

```bash
# Terminal 2 / IDE Window 2
conductor create worktree-testing --branch=feature/task-review-testing
cd worktree-testing

# Start task
/task-work TASK-REV-4DE8

# Implementation focus:
# - tests/unit/commands/test_task_review_orchestrator.py (15+ tests)
# - tests/unit/commands/review_modes/*.py (5 test files, 5+ tests each)
# - tests/unit/commands/test_review_report_generator.py (10+ tests)
# - tests/integration/test_task_review_workflow.py (10+ tests)
# - tests/performance/test_review_performance.py (5+ tests)

# Run tests
pytest tests/unit/commands/test_task_review_orchestrator.py -v
pytest tests/integration/test_task_review_workflow.py -v

# Check coverage
pytest tests/ --cov=installer/core/commands/lib/task_review_orchestrator --cov-report=term

# Complete task
/task-complete TASK-REV-4DE8
```

#### Final Integration

```bash
# Both developers have completed their tasks
# Final integration and validation

cd ~/Projects/guardkit  # Main repo

# Merge integration first (documentation and task-create)
git checkout main
git merge worktree-integration/feature/task-review-integration

# Merge testing
git merge worktree-testing/feature/task-review-testing

# Final validation
pytest tests/ --cov=installer/core/commands/lib --cov-report=html
# Should show ≥80% coverage

# End-to-end manual test
/task-create "Architectural review of template-create" task_type:review
# Should suggest /task-review

/task-review TASK-XXX --mode=architectural --depth=comprehensive --output=detailed
# Should complete full workflow

# Commit state files
git add docs/state/TASK-REV-5DC2/ docs/state/TASK-REV-4DE8/
git commit -m "Save state for Wave 3 tasks"

# All waves complete!
git tag v1.0.0-task-review
```

---

## Testing Strategy

### Per-Wave Testing

#### Wave 1: Foundation Testing

```bash
# After TASK-REV-A4AB complete
pytest tests/unit/commands/test_task_review_orchestrator.py -v

# Expected tests:
# - test_execute_task_review_basic
# - test_validate_review_mode
# - test_validate_review_depth
# - test_load_review_context
# - test_state_transitions

# Manual testing
/task-review TASK-09E9  # Should accept command
/task-review TASK-09E9 --mode=invalid  # Should error
```

#### Wave 2: Features Testing

```bash
# After TASK-REV-3248 and TASK-REV-2367 complete
pytest tests/unit/commands/review_modes/ -v
pytest tests/integration/test_review_modes.py -v

# Expected tests:
# - test_architectural_review_quick
# - test_code_quality_review_standard
# - test_decision_analysis_comprehensive
# - test_generate_summary_report
# - test_generate_detailed_report
# - test_decision_checkpoint_accept

# Manual testing
/task-review TASK-09E9 --mode=architectural --output=detailed
# Should invoke agent, generate full report, show decision prompt
```

#### Wave 3: Comprehensive Testing

```bash
# After TASK-REV-4DE8 complete
pytest tests/ --cov=installer/core/commands/lib --cov-report=html

# Coverage goals:
# - Overall: ≥80% lines, ≥75% branches
# - Critical modules: ≥90% lines

# Performance testing
pytest tests/performance/test_review_performance.py -v --timeout=7200

# Expected tests:
# - test_quick_review_completes_in_time (≤30 min)
# - test_standard_review_completes_in_time (≤2 hours)
```

### Integration Testing Across Waves

```bash
# After each wave, run integration test
pytest tests/integration/test_task_review_workflow.py -v

# This test validates:
# Wave 1: Command structure works
# Wave 2: End-to-end review workflow works
# Wave 3: Integration with task-create works
```

---

## Integration Points

### Between Tasks in Same Wave

#### Wave 2 Integration: Modes + Reports

**Challenge**: Developer A (modes) and Developer B (reports) need to agree on data format.

**Solution**: Define interface contract upfront (before Wave 2 starts).

**Interface Contract**:

```python
# File: installer/core/commands/lib/review_modes/interface.py
# Created during Wave 1 (TASK-REV-A4AB)

from typing import TypedDict, List, Dict, Any

class ReviewResults(TypedDict):
    """Standard output format from all review modes."""
    mode: str              # "architectural", "code-quality", etc.
    depth: str             # "quick", "standard", "comprehensive"
    overall_score: int     # 0-100 or 0-10 depending on mode
    findings: List[Dict[str, Any]]  # List of findings with severity
    recommendations: List[str]       # List of actionable recommendations
    evidence: List[str]              # File paths with line numbers
```

**Usage**:

```python
# Developer A (TASK-REV-3248) implements modes
def architectural_review(context, depth) -> ReviewResults:
    return {
        "mode": "architectural",
        "depth": depth,
        "overall_score": 75,
        "findings": [...],
        "recommendations": [...],
        "evidence": [...]
    }

# Developer B (TASK-REV-2367) consumes results
def generate_review_report(results: ReviewResults, output_format: str) -> str:
    mode = results["mode"]  # Type-safe access
    score = results["overall_score"]
    # ... generate report ...
```

**Integration Test** (written during Wave 2):

```python
# tests/integration/test_modes_and_reports.py

def test_architectural_mode_with_detailed_report():
    """Test that architectural mode output works with detailed report."""
    # Developer A's code
    results = architectural_review(mock_context, "standard")

    # Developer B's code
    report = generate_review_report(results, "detailed")

    assert "Architecture Assessment" in report
    assert "75" in report  # overall score
```

### Between Waves

#### Wave 1 → Wave 2

**Handoff**: Wave 1 provides skeleton functions that Wave 2 implements.

**Verification**:

```bash
# After Wave 1, verify skeleton functions exist
python3 -c "
from installer.core.commands.lib.task_review_orchestrator import (
    execute_review_analysis,  # Skeleton for Wave 2
    generate_review_report    # Skeleton for Wave 2
)
print('Skeleton functions verified')
"
```

#### Wave 2 → Wave 3

**Handoff**: Wave 2 provides complete review workflow that Wave 3 integrates.

**Verification**:

```bash
# After Wave 2, verify end-to-end workflow
/task-review TASK-09E9 --mode=architectural
# Should complete without errors (even if decision is mocked)
```

---

## Troubleshooting

### Common Issues

#### Issue 1: Worktree State Conflicts

**Symptom**: Task state not syncing across worktrees

**Cause**: Symlinks not configured correctly

**Solution**:

```bash
# Verify symlinks
ls -la worktree-modes/.claude/state
# Should show: state -> /Users/you/.agentecflow/state

# If broken, reinstall GuardKit
cd worktree-modes
./installer/scripts/install.sh
```

#### Issue 2: Merge Conflicts in Orchestrator

**Symptom**: Git conflicts in `task_review_orchestrator.py` when merging Wave 2

**Cause**: Both TASK-REV-3248 and TASK-REV-2367 modify the same file

**Solution**:

```bash
# Check what each branch changed
git diff main worktree-modes/feature/review-modes -- installer/core/commands/lib/task_review_orchestrator.py
git diff main worktree-reports/feature/report-generation -- installer/core/commands/lib/task_review_orchestrator.py

# Manual merge (combine both changes)
# Developer A added: execute_review_analysis() implementation
# Developer B added: generate_review_report() implementation
# Both changes are complementary - keep both
```

#### Issue 3: Tests Fail After Wave Integration

**Symptom**: Tests pass in individual worktrees but fail after merge

**Cause**: Integration assumptions don't match reality

**Solution**:

```bash
# Run integration test in main branch after merge
pytest tests/integration/test_task_review_workflow.py -v -s

# Check error message
# Fix interface mismatches
# Re-run tests until passing
```

#### Issue 4: Conductor Worktree Quota Exceeded

**Symptom**: `conductor create` fails with quota error

**Cause**: Too many worktrees created (Conductor free tier limit)

**Solution**:

```bash
# List worktrees
conductor list

# Remove old worktrees
conductor remove worktree-foundation  # After Wave 1 complete
conductor remove worktree-modes       # After Wave 2 complete
conductor remove worktree-reports     # After Wave 2 complete

# Or upgrade Conductor plan
```

---

## Success Metrics

### Wave 1 Success

- [ ] `/task-review TASK-XXX` command recognized
- [ ] All flags work (--mode, --depth, --output)
- [ ] Skeleton phases execute without errors
- [ ] State transitions work (BACKLOG → REVIEW_COMPLETE)
- [ ] Unit tests pass (5+ tests)

### Wave 2 Success

- [ ] All 5 review modes execute successfully
- [ ] All 3 report formats generate correctly
- [ ] Decision checkpoint is interactive
- [ ] Integration test passes (modes → reports)
- [ ] Unit tests pass (30+ tests)

### Wave 3 Success

- [ ] `/task-create` suggests `/task-review` appropriately
- [ ] Documentation complete (CLAUDE.md, workflow guide)
- [ ] All tests pass (60+ tests)
- [ ] Coverage ≥80% lines, ≥75% branches
- [ ] Performance tests validate time limits

### Overall Success

- [ ] All 5 tasks completed
- [ ] All waves integrated successfully
- [ ] End-to-end workflow tested manually
- [ ] No regressions in `/task-work` command
- [ ] Production-ready and documented

---

## Timeline Estimates

### Sequential Development (Single Developer)

| Wave | Duration | Cumulative |
|------|----------|------------|
| Wave 1 | 4-8 hours | 4-8 hours |
| Wave 2 | 12-18 hours | 16-26 hours |
| Wave 3 | 6-10 hours | 22-36 hours |

**Total**: 22-36 hours (3-4.5 days full-time)

### Parallel Development (Two Developers + Conductor)

| Wave | Duration | Cumulative | Time Saved |
|------|----------|------------|------------|
| Wave 1 | 4-8 hours | 4-8 hours | 0% (sequential) |
| Wave 2 | 8-12 hours | 12-20 hours | 33% (parallel) |
| Wave 3 | 4-8 hours | 16-28 hours | 40% (parallel) |

**Total**: 16-28 hours (2-3.5 days full-time)

**Time Savings**: 6-8 hours (25-35% faster)

---

## Next Steps

1. **Review this guide** with team
2. **Set up Conductor** (if not already installed)
3. **Assign developers** to Wave 2 and Wave 3 parallel tasks
4. **Start Wave 1** (TASK-REV-A4AB)
5. **After Wave 1 complete**, start Wave 2 tasks in parallel
6. **After Wave 2 complete**, start Wave 3 tasks in parallel
7. **Final integration** and testing
8. **Release** `/task-review` command

---

## References

- **Proposal**: [task-review-command-proposal.md](../proposals/task-review-command-proposal.md)
- **Tasks**: `tasks/backlog/TASK-REV-*.md`
- **Conductor Docs**: https://conductor.build
- **GuardKit Workflows**: [guardkit-workflow.md](guardkit-workflow.md)

---

**Last Updated**: 2025-01-20
**Status**: Ready for implementation
**Estimated Completion**: 2-3.5 days (with parallel development)
