# Hash-Based ID Implementation - Task Summary

## Overview

Created 10 tasks (TASK-046 through TASK-055) to implement the hash-based ID system and eliminate duplicate task IDs.

**Total Estimated Effort**: ~2-3 weeks (with parallel development), **10-14 days solo**
**Priority**: High (all core infrastructure tasks)
**Parallelization**: 4 waves with 3 concurrent worktrees in Wave 1
**Migration**: Simplified for personal use (complexity reduced 7→5)

---

## Wave-Based Implementation Strategy

### Why Waves?

Waves represent groups of tasks that can be developed **in parallel** using Conductor.build git worktrees. Each wave has minimal inter-dependencies, allowing multiple developers (or AI agents) to work simultaneously without conflicts.

**Benefits**:
- ⚡ **Faster completion**: Parallel development reduces timeline from 3 weeks to 2 weeks
- 🔄 **Independent work**: Each worktree works on isolated features
- ✅ **Safe merging**: Hash-based IDs eliminate merge conflicts
- 🎯 **Clear ownership**: Each worktree has a specific focus area

---

## Wave 0: Foundation (Sequential - Days 1-3)

**Objective**: Build core hash ID infrastructure that all other tasks depend on

**Tasks**: 2 tasks (Sequential)
**Complexity**: 9/20
**Duration**: 2-3 days
**Worktrees**: 1 (main repository)

### TASK-046: Implement core hash-based ID generator
**Complexity**: 5/10 | **Implementation**: `/task-work TASK-046`

- Hash ID generation using SHA-256
- Progressive length scaling (4→5→6 chars)
- Collision detection
- Performance: 1,000 IDs in <1 second
- **File**: `installer/core/lib/id_generator.py`
- **Use /task-work**: ✅ Yes (includes architectural review + test enforcement)

**Implementation Command**:
```bash
/task-work TASK-046
```

**Why Sequential**: Foundation for all subsequent tasks.

---

### TASK-047: Add ID validation and collision detection
**Complexity**: 4/10 | **Implementation**: `/task-work TASK-047`

- Format validation regex
- Duplicate checking across all directories
- Subtask validation (dot notation)
- Thread-safe validation
- **Enhances**: `installer/core/lib/id_generator.py`
- **Depends on**: TASK-046
- **Use /task-work**: ✅ Yes

**Implementation Command**:
```bash
/task-work TASK-047
```

**Why Sequential**: Extends TASK-046, must be completed before Wave 1.

---

### Wave 0 Completion Criteria

```bash
# Verify Wave 0 complete
pytest installer/core/lib/test_id_generator.py -v
python3 -c "from installer.core.lib.id_generator import generate_task_id; print(generate_task_id())"

# Expected output: TASK-a3f8 (or similar 4-char hash)
```

---

## Wave 1: Parallel Development (Concurrent - Days 4-8)

**Objective**: Implement three independent feature areas in parallel

**Tasks**: 5 tasks (3 parallel worktrees)
**Complexity**: 24/50
**Duration**: 4-5 days
**Worktrees**: 3 concurrent (using Conductor.build)

### Conductor.build Setup

```bash
# Create 3 parallel worktrees using Conductor.build
conductor worktree create hash-id-integration    # Worktree A
conductor worktree create hash-id-pm-tools       # Worktree B
conductor worktree create hash-id-frontmatter    # Worktree C

# Verify symlinks intact
ls -la hash-id-integration/.claude/
ls -la hash-id-pm-tools/.claude/
ls -la hash-id-frontmatter/.claude/
```

---

### Worktree A: Integration Layer (hash-id-integration)

**Focus**: Update /task-create command and add prefix support
**Developer/Agent**: Alpha Team
**Complexity**: 11/20

#### TASK-048: Update /task-create to use hash-based IDs
**Complexity**: 6/10 | **Implementation**: `/task-work TASK-048`

- Replace sequential ID logic with hash generator
- Add prefix parameter support
- Backward compatibility for reading old formats
- **Modifies**: `installer/core/commands/task-create.md` + implementation
- **Depends on**: TASK-046, TASK-047
- **Use /task-work**: ✅ Yes

#### TASK-054: Add prefix support and inference
**Complexity**: 5/10 | **Implementation**: `/task-work TASK-054`

- Manual prefix specification
- Auto-inference from epic, tags, title
- Prefix validation and registry
- **Enhances**: `installer/core/lib/id_generator.py`
- **Depends on**: TASK-046
- **Use /task-work**: ✅ Yes

**Worktree A Commands**:
```bash
# In hash-id-integration worktree
cd hash-id-integration

/task-work TASK-048
# ... complete and test ...

/task-work TASK-054
# ... complete and test ...

# Merge back to main
git add .
git commit -m "feat: Hash ID integration layer (TASK-048, TASK-054)"
conductor worktree merge
```

**Why Together**: Both modify /task-create workflow, easier to test together.

---

### Worktree B: PM Tool Integration (hash-id-pm-tools)

**Focus**: External ID mapping for PM tools
**Developer/Agent**: Beta Team
**Complexity**: 10/20

#### TASK-049: Implement external ID mapper for PM tools
**Complexity**: 6/10 | **Implementation**: `/task-work TASK-049`

- Bidirectional mapping (internal ↔ external)
- Support JIRA, Azure DevOps, Linear, GitHub
- Thread-safe counter management
- **File**: `installer/core/lib/external_id_mapper.py`
- **Depends on**: TASK-046 (for ID format understanding)
- **Use /task-work**: ✅ Yes

#### TASK-050: Add JSON persistence for ID mappings
**Complexity**: 4/10 | **Implementation**: `/task-work TASK-050`

- Atomic read-modify-write operations
- File locking for concurrent access
- Backup before write
- Corruption detection
- **Files**: `.claude/state/external_id_mapping.json`, `.claude/state/external_id_counters.json`
- **Depends on**: TASK-049
- **Use /task-work**: ✅ Yes

**Worktree B Commands**:
```bash
# In hash-id-pm-tools worktree
cd hash-id-pm-tools

/task-work TASK-049
# ... complete and test ...

/task-work TASK-050
# ... complete and test ...

# Merge back to main
git add .
git commit -m "feat: PM tool ID mapping (TASK-049, TASK-050)"
conductor worktree merge
```

**Why Together**: TASK-050 directly depends on TASK-049, natural sequence.

---

### Worktree C: Frontmatter Schema (hash-id-frontmatter)

**Focus**: Update task metadata schema
**Developer/Agent**: Gamma Team
**Complexity**: 3/10

#### TASK-051: Update task frontmatter schema for external_ids
**Complexity**: 3/10 | **Implementation**: `/task-work TASK-051`

- Add `external_ids` field
- Add `legacy_id` field for migration
- Backward/forward compatibility
- **Modifies**: Task creation, reading, writing code
- **Depends on**: TASK-049 (for schema definition)
- **Use /task-work**: ✅ Yes

**Worktree C Commands**:
```bash
# In hash-id-frontmatter worktree
cd hash-id-frontmatter

/task-work TASK-051
# ... complete and test ...

# Merge back to main
git add .
git commit -m "feat: Task frontmatter schema update (TASK-051)"
conductor worktree merge
```

**Why Separate**: Independent schema change, can be developed and merged independently.

---

### Wave 1 Parallel Execution

**Timeline**:
```
Day 4:
  Worktree A: Start TASK-048
  Worktree B: Start TASK-049
  Worktree C: Start TASK-051

Day 5:
  Worktree A: Complete TASK-048, start TASK-054
  Worktree B: Complete TASK-049, start TASK-050
  Worktree C: Complete TASK-051

Day 6:
  Worktree A: Complete TASK-054
  Worktree B: Complete TASK-050
  Worktree C: Merged

Day 7:
  Worktree A: Merged
  Worktree B: Merged

Day 8:
  Integration testing across all Wave 1 changes
```

### Wave 1 Completion Criteria

```bash
# Verify all worktrees merged
git log --oneline -3

# Verify components work together
/task-create "Test task" prefix:TEST
# Expected: TASK-TEST-b2c4 (with external IDs in frontmatter)

# Run integration tests
pytest tests/integration/test_wave1_integration.py -v
```

---

## Wave 2: Migration & Documentation (Sequential - Days 9-11)

**Objective**: Migrate YOUR existing tasks and update documentation

**Tasks**: 2 tasks (Sequential)
**Complexity**: 9/20 (reduced from 11/20 - migration simplified)
**Duration**: 2-3 days (reduced from 3-4 days)
**Worktrees**: 1 (main repository)

### TASK-052: Create migration script for existing tasks (solo use)
**Complexity**: 5/10 | **Implementation**: `/task-work TASK-052`

- Migrate YOUR existing ~40-50 tasks to hash IDs
- Preserve old IDs in `legacy_id` field
- Update cross-references within tasks
- Dry-run mode
- Simple rollback script (nuke & restore from backup)
- **Simplified**: Personal use only, no generic tool, no user docs
- **File**: `scripts/migrate-my-tasks.py` (single self-contained script)
- **Depends on**: ALL Wave 0 and Wave 1 tasks
- **Use /task-work**: ✅ Yes (benefits from test enforcement)

**Implementation Command**:
```bash
/task-work TASK-052
```

**Why Sequential**: Requires all previous components to be complete and integrated.

---

### TASK-053: Update documentation for hash-based IDs
**Complexity**: 4/10 | **Implementation**: `/task-work TASK-053`

- Update CLAUDE.md, task-create.md
- Update all workflow guides
- Add migration guide
- Add FAQ section
- **Create new guides**:
  - `docs/guides/hash-id-parallel-development.md` - Wave-based Conductor.build workflow
  - `docs/guides/hash-id-pm-tools.md` - PM tool integration
- **Link research documents** from main documentation:
  - Link to `implementation-tasks-summary.md` (this document)
  - Link to `task-id-strategy-analysis.md`
  - Link to `task-id-decision-guide.md`
- **Migration**: FAQ entry only, no separate guide (personal script documented in source)
- **Modifies**: All documentation files
- **Depends on**: TASK-052 (to reference migration process)
- **Use /task-work**: ✅ Yes (ensures thorough documentation review)

**Implementation Command**:
```bash
# Can start when TASK-052 is stable (doesn't need to be 100% complete)
/task-work TASK-053
```

**Why Sequential**: Documentation should reflect actual migration process.

---

### Wave 2 Completion Criteria

```bash
# Test migration in dry-run mode
./installer/scripts/migrate-task-ids.sh --dry-run

# Verify documentation updated
grep "TASK-.*-[a-f0-9]{4,6}" CLAUDE.md
grep "hash-based" docs/guides/guardkit-workflow.md
```

---

## Wave 3: Validation & Rollback (Final - Days 13-15)

**Objective**: Comprehensive testing and safety mechanisms

**Tasks**: 1 task
**Complexity**: 6/10
**Duration**: 2-3 days
**Worktrees**: 1 (main repository)

### TASK-055: Integration testing and rollback script
**Complexity**: 6/10 | **Implementation**: `/task-work TASK-055`

- End-to-end workflow tests
- Concurrent creation tests
- PM tool integration tests
- Migration validation tests
- Performance benchmarks (1,000+ tasks)
- Conductor.build worktree tests
- **Files**: `tests/integration/test_hash_id_system.py`, `installer/scripts/rollback-hash-ids.sh`
- **Depends on**: ALL previous tasks (046-054)
- **Use /task-work**: ✅ Yes (comprehensive test coverage required)

**Implementation Command**:
```bash
/task-work TASK-055
```

**Why Last**: Validates entire system end-to-end.

---

### Wave 3 Completion Criteria

```bash
# Run full integration test suite
pytest tests/integration/test_hash_id_system.py -v --cov

# Performance benchmark
python3 tests/integration/benchmark_hash_ids.py
# Expected: 1,000 IDs in <1 second

# Verify rollback script
./installer/scripts/rollback-hash-ids.sh --verify

# Success metrics
- [ ] All integration tests pass
- [ ] Performance benchmarks met
- [ ] Rollback script tested
- [ ] Zero collisions in 10,000 ID test
```

---

## Complete Implementation Timeline

### Wave-Based Schedule

```
┌─────────────────────────────────────────────────────────────────┐
│ Wave 0: Foundation (Days 1-3)                                   │
├─────────────────────────────────────────────────────────────────┤
│ Day 1-2: TASK-046 (Hash Generator)                              │
│ Day 3:   TASK-047 (Validation)                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Wave 1: Parallel Development (Days 4-8)                         │
├─────────────────────────────────────────────────────────────────┤
│ Worktree A (Integration):                                       │
│   Day 4-5: TASK-048 (/task-create update)                       │
│   Day 6-7: TASK-054 (Prefix support)                            │
│                                                                  │
│ Worktree B (PM Tools):                                          │
│   Day 4-5: TASK-049 (External mapper)                           │
│   Day 6-7: TASK-050 (Persistence)                               │
│                                                                  │
│ Worktree C (Schema):                                            │
│   Day 4-5: TASK-051 (Frontmatter)                               │
│   Day 6-7: Testing & cleanup                                    │
│                                                                  │
│ Day 8:   Integration testing + merge all worktrees              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Wave 2: Migration (Days 9-11) - Simplified                      │
├─────────────────────────────────────────────────────────────────┤
│ Day 9-10:  TASK-052 (Migration script - personal use only)      │
│ Day 11:    TASK-053 (Documentation - no migration guide)        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Wave 3: Validation (Days 13-15)                                 │
├─────────────────────────────────────────────────────────────────┤
│ Day 13-15: TASK-055 (Integration testing + rollback)            │
└─────────────────────────────────────────────────────────────────┘

Total Timeline: 13-14 days (~2.5 weeks) - Solo developer
With aggressive parallelization (team): 10-11 days (~2 weeks)

**Note**: Timeline reduced after simplifying TASK-052 for personal use
```

---

## Conductor.build Worktree Strategy

### Initial Setup

```bash
# Ensure GuardKit installer has created symlinks
./installer/scripts/install.sh

# Verify state directory is symlinked
ls -la .claude/state  # Should show symlink to main repo

# Create worktrees for Wave 1
conductor worktree create hash-id-integration
conductor worktree create hash-id-pm-tools
conductor worktree create hash-id-frontmatter
```

### Worktree Isolation Benefits

**Why hash-based IDs are perfect for parallel development**:

1. **No ID collisions**: Each worktree generates unique hash IDs independently
2. **Safe merging**: No sequential counter conflicts
3. **State isolation**: Each worktree has independent task state
4. **Clean merges**: Hash IDs + file-based state = minimal conflicts

### Merge Strategy

```bash
# Recommended merge order for Wave 1:
# 1. Worktree C (Schema) - smallest changes, foundation for others
# 2. Worktree B (PM Tools) - independent feature
# 3. Worktree A (Integration) - depends on schema, final integration

# In each worktree:
git add .
git commit -m "feat: <description> (TASK-XXX, TASK-YYY)"

# Merge via Conductor
conductor worktree merge

# Or manual merge:
git checkout main
git merge hash-id-frontmatter
git merge hash-id-pm-tools
git merge hash-id-integration
```

---

## Task Implementation Methods

### All Tasks Use `/task-work`

**Why**: `/task-work` provides:
- ✅ **Phase 2.5**: Architectural review (SOLID/DRY/YAGNI)
- ✅ **Phase 4.5**: Test enforcement (auto-fix up to 3 attempts)
- ✅ **Phase 5**: Code review
- ✅ **Phase 5.5**: Plan audit (scope creep detection)

**Exception**: None. All 10 tasks benefit from quality gates.

### Task Execution Template

```bash
# Standard execution for all tasks
/task-work TASK-XXX

# Alternative: Design-first for complex tasks (TASK-052)
/task-work TASK-052 --design-only
# [Review and approve plan]
/task-work TASK-052 --implement-only

# Alternative: TDD mode for core logic (TASK-046, TASK-049)
/task-work TASK-046 --mode=tdd
```

---

## Dependency Graph (Visual)

```
Wave 0 (Foundation)
├─ 046 (Hash Generator) ──────┬─────────┬──────────┐
└─ 047 (Validation) ───────────┤         │          │
                               │         │          │
Wave 1 (Parallel - 3 worktrees)│         │          │
├─ Worktree A                  │         │          │
│  ├─ 048 (Update /task-create)│         │          │
│  └─ 054 (Prefix support) ────┤         │          │
│                               │         │          │
├─ Worktree B                   │         │          │
│  ├─ 049 (External mapper) ────┤         │          │
│  └─ 050 (Persistence) ────────┤         │          │
│                               │         │          │
└─ Worktree C                   │         │          │
   └─ 051 (Frontmatter) ────────┴─────────┼──────────┤
                                           │          │
Wave 2 (Migration)                         │          │
├─ 052 (Migration script) ─────────────────┘          │
└─ 053 (Documentation) ────────────────────┬──────────┤
                                           │          │
Wave 3 (Validation)                        │          │
└─ 055 (Integration testing) ──────────────┴──────────┘
```

---

## Complexity Distribution by Wave

| Wave | Tasks | Total Complexity | Average | Duration |
|------|-------|------------------|---------|----------|
| Wave 0 | 2 | 9/20 | 4.5/10 | 2-3 days |
| Wave 1 | 5 | 24/50 | 4.8/10 | 4-5 days |
| Wave 2 | 2 | 9/20 | 4.5/10 | 2-3 days |
| Wave 3 | 1 | 6/10 | 6.0/10 | 2-3 days |
| **Total** | **10** | **48/100** | **4.8/10** | **10-14 days** |

**Note**: TASK-052 complexity reduced from 7/10 to 5/10 (simplified for personal use only)

---

## Parallel Development Scenarios

### Scenario 1: Solo Developer (Your Use Case)

**Approach**: Sequential with Wave 1 tasks spread over time
```bash
# Wave 0
/task-work TASK-046
/task-work TASK-047

# Wave 1 (sequential, one at a time)
/task-work TASK-048
/task-work TASK-054
/task-work TASK-049
/task-work TASK-050
/task-work TASK-051

# Wave 2 (simplified migration)
/task-work TASK-052  # Personal migration script only
/task-work TASK-053  # No migration guide needed

# Wave 3
/task-work TASK-055
```

**Timeline**: 13-14 days (~2.5 weeks)
**Reduced from**: 15 days (migration simplified for solo use)

---

### Scenario 2: Team of 3 Developers

**Approach**: Full parallelization of Wave 1

**Developer Alpha** (Worktree A):
```bash
conductor worktree create hash-id-integration
cd hash-id-integration
/task-work TASK-048
/task-work TASK-054
```

**Developer Beta** (Worktree B):
```bash
conductor worktree create hash-id-pm-tools
cd hash-id-pm-tools
/task-work TASK-049
/task-work TASK-050
```

**Developer Gamma** (Worktree C):
```bash
conductor worktree create hash-id-frontmatter
cd hash-id-frontmatter
/task-work TASK-051
```

**Timeline**: 10-11 days (~2 weeks) - **20-25% faster**
**Reduced from**: 12 days (migration simplified)

---

### Scenario 3: AI Agent Swarm

**Approach**: Maximum parallelization with multiple Claude Code instances

**Agent 1** (Foundation):
```bash
/task-work TASK-046
/task-work TASK-047
```

**Agent 2** (Integration - starts after Wave 0):
```bash
conductor worktree create hash-id-integration
/task-work TASK-048
/task-work TASK-054
```

**Agent 3** (PM Tools - starts after Wave 0):
```bash
conductor worktree create hash-id-pm-tools
/task-work TASK-049
/task-work TASK-050
```

**Agent 4** (Schema - starts after Wave 0):
```bash
conductor worktree create hash-id-frontmatter
/task-work TASK-051
```

**Agent 5** (Migration - starts after Wave 1):
```bash
/task-work TASK-052
/task-work TASK-053
```

**Agent 6** (Testing - starts after Wave 2):
```bash
/task-work TASK-055
```

**Timeline**: 8-9 days (1.5 weeks) - **35-40% faster**
**Reduced from**: 10 days (migration simplified)

---

## Acceptance Criteria Summary

### Per-Task Criteria

**All tasks must achieve**:
- ✅ Test coverage ≥80% (85-90% for critical tasks)
- ✅ All unit tests pass
- ✅ Integration tests pass (where applicable)
- ✅ Documentation complete
- ✅ Backward compatibility maintained
- ✅ Architectural review score ≥60/100
- ✅ Zero scope creep (Phase 5.5 audit)

### System-Level Criteria (TASK-055)

- ✅ Zero collisions in 10,000 ID generation test
- ✅ Performance: 1,000 IDs in <1 second
- ✅ Concurrent creation produces unique IDs
- ✅ PM tool mapping works for JIRA, Azure DevOps, Linear, GitHub
- ✅ Migration preserves all data (100% data integrity)
- ✅ Rollback script verified and tested
- ✅ Conductor.build parallel worktrees work correctly
- ✅ Cross-reference updates 100% accurate
- ✅ All documentation updated and accurate

---

## Quick Start Commands

### Wave 0: Foundation
```bash
# Sequential execution
/task-work TASK-046
/task-work TASK-047
```

### Wave 1: Parallel (Conductor.build)
```bash
# Create worktrees
conductor worktree create hash-id-integration
conductor worktree create hash-id-pm-tools
conductor worktree create hash-id-frontmatter

# Terminal 1 (Worktree A)
cd hash-id-integration
/task-work TASK-048
/task-work TASK-054

# Terminal 2 (Worktree B)
cd hash-id-pm-tools
/task-work TASK-049
/task-work TASK-050

# Terminal 3 (Worktree C)
cd hash-id-frontmatter
/task-work TASK-051

# Merge all worktrees
conductor worktree merge  # In each worktree
```

### Wave 2: Migration
```bash
/task-work TASK-052
/task-work TASK-053
```

### Wave 3: Validation
```bash
/task-work TASK-055
```

---

## Files Created

All task files in: `tasks/backlog/`

**Wave 0 (Foundation)**:
1. `TASK-046-implement-hash-id-generator.md`
2. `TASK-047-add-id-validation.md`

**Wave 1 (Parallel)**:
3. `TASK-048-update-task-create-command.md` (Worktree A)
4. `TASK-054-add-prefix-support.md` (Worktree A)
5. `TASK-049-implement-external-id-mapper.md` (Worktree B)
6. `TASK-050-add-mapping-persistence.md` (Worktree B)
7. `TASK-051-update-task-frontmatter-schema.md` (Worktree C)

**Wave 2 (Migration & Documentation)**:
8. `TASK-052-create-migration-script.md`
9. `TASK-053-update-documentation.md` (includes implementation strategy docs)

**Wave 3 (Validation)**:
10. `TASK-055-integration-testing.md`

---

## Success Metrics

### Per-Wave Metrics

**Wave 0 Completion**:
- [ ] Hash generator produces valid IDs
- [ ] Validation prevents duplicates
- [ ] Performance benchmarks met

**Wave 1 Completion**:
- [ ] /task-create uses hash IDs
- [ ] Prefix inference works
- [ ] PM tool mapping functional
- [ ] Persistence layer working
- [ ] Frontmatter schema updated
- [ ] All worktrees merged cleanly

**Wave 2 Completion**:
- [ ] Migration script tested (dry-run on YOUR tasks)
- [ ] Migration preserves all data (YOUR ~40-50 tasks)
- [ ] Documentation updated (CLAUDE.md, README.md, all guides)
- [ ] Parallel development guide created (`docs/guides/hash-id-parallel-development.md`)
- [ ] PM tools guide created (`docs/guides/hash-id-pm-tools.md`)
- [ ] Research documents linked from main docs
- [ ] Implementation strategy documented
- [ ] Migration FAQ added (no separate guide needed)

**Wave 3 Completion**:
- [ ] All integration tests pass
- [ ] Performance benchmarks met
- [ ] Rollback script verified
- [ ] System production-ready

### Final System Metrics

- [ ] All 10 tasks completed
- [ ] Zero duplicate IDs in codebase
- [ ] 100% of tasks using hash format
- [ ] PM tool integration working
- [ ] Migration successful (all data preserved)
- [ ] Documentation comprehensive (including implementation strategy and parallel development guides)
- [ ] Integration tests passing (≥95%)
- [ ] Performance benchmarks met
- [ ] Rollback capability verified

---

## References

- **Analysis**: [task-id-strategy-analysis.md](./task-id-strategy-analysis.md)
- **Decision Guide**: [task-id-decision-guide.md](./task-id-decision-guide.md)
- **Summary**: [task-id-summary.md](./task-id-summary.md)
- **POC**: [task-id-poc.py](./task-id-poc.py)
- **Conductor.build**: [Conductor Documentation](https://conductor.build)

---

## Troubleshooting Parallel Development

### Issue: Worktree state conflicts

**Symptom**: Tasks created in different worktrees have ID conflicts
**Cause**: Hash IDs should prevent this, but if using old sequential logic
**Solution**: Ensure TASK-046/047 completed and merged before Wave 1

### Issue: Merge conflicts in .claude/state/

**Symptom**: Git conflicts when merging worktrees
**Cause**: State directory not properly symlinked
**Solution**:
```bash
./installer/scripts/install.sh  # Re-run installer
ls -la .claude/state  # Verify symlink
```

### Issue: Integration tests fail after merge

**Symptom**: Tests pass in worktrees but fail after merge
**Cause**: Component interactions not tested in isolation
**Solution**: Run integration tests after each merge:
```bash
pytest tests/integration/test_wave1_integration.py -v
```

---

**Ready to begin?**

```bash
# Start Wave 0
/task-work TASK-046
```
