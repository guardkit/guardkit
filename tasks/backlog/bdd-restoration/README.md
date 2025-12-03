# BDD Mode Restoration - Task Package

**Created**: 2025-11-28
**Status**: Ready for Wave 1 execution
**Total Tasks**: 7
**Estimated Total Effort**: 3.5-5.5 hours

---

## Quick Start

### 1. Read the Implementation Guide First

📖 **[IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md)** - Complete strategy, architecture, and execution plan

### 2. Execute in Waves

**Wave 1** (Parallel - Day 1):
```bash
# Start all 4 simultaneously using Conductor
cd ~/Projects/appmilla_github/guardkit
conductor create-workspace bdd-wave1-investigate TASK-BDD-001
conductor create-workspace bdd-wave1-docs TASK-BDD-002
conductor create-workspace bdd-wave1-claude-md TASK-BDD-007

cd ~/Projects/require-kit
conductor create-workspace bdd-wave1-requirekit TASK-BDD-006
```

**Wave 2** (Sequential - Day 2):
```bash
# After Wave 1 merges
cd ~/Projects/appmilla_github/guardkit
conductor create-workspace bdd-wave2-flag TASK-BDD-003
# Wait for merge
conductor create-workspace bdd-wave2-workflow TASK-BDD-004
```

**Wave 3** (Integration - Day 3):
```bash
# After Wave 2 merges
conductor create-workspace bdd-wave3-testing TASK-BDD-005
```

---

## Task Overview

| Task | Title | Method | Wave | Effort | Status |
|------|-------|--------|------|--------|--------|
| **TASK-BDD-001** | Investigate mode implementation | Claude Code | 1 | 30 min | backlog |
| **TASK-BDD-002** | Create BDD documentation | Claude Code | 1 | 45 min | backlog |
| **TASK-BDD-006** | Update RequireKit agents | Claude Code | 1 | 1-2 hrs | backlog |
| **TASK-BDD-007** | Reinstate BDD in .claude/CLAUDE.md | Claude Code | 1 | 30 min | backlog |
| **TASK-BDD-003** | Restore --mode=bdd flag | `/task-work` | 2 | 1-2 hrs | backlog |
| **TASK-BDD-004** | Implement workflow routing | `/task-work` | 2 | 1-2 hrs | backlog |
| **TASK-BDD-005** | Integration testing | `/task-work` | 3 | 30-45 min | backlog |

---

## Wave Execution Details

### Wave 1: Foundation (4 parallel tasks)

**TASK-BDD-001**: Investigation
- Where is `--mode=tdd` implemented?
- Where should BDD logic go?
- Document integration points

**TASK-BDD-002**: Documentation
- Create BDD workflow guide for agentic systems
- LangGraph case study
- Update CLAUDE.md

**TASK-BDD-006**: RequireKit Agents (Different Repo)
- Add discovery metadata to bdd-generator
- Add ALWAYS/NEVER/ASK boundaries
- Update other RequireKit agents

**TASK-BDD-007**: Reinstate BDD Documentation
- Update `.claude/CLAUDE.md` to include BDD workflow
- Position BDD as optional for agentic systems
- Keep standard workflow as primary focus
- Add RequireKit installation instructions

**Dependencies**: None (all start together)

### Wave 2: Implementation (2 sequential tasks)

**TASK-BDD-003**: Flag Restoration
- Add `--mode=bdd` to valid options
- Implement marker file detection
- Add error messages
- Update command documentation

**TASK-BDD-004**: Workflow Routing
- Load Gherkin scenarios from RequireKit
- Route to bdd-generator agent
- Run BDD tests in Phase 4
- Implement fix loop for BDD tests

**Dependencies**:
- TASK-BDD-003 depends on TASK-BDD-001
- TASK-BDD-004 depends on TASK-BDD-003

### Wave 3: Integration (1 task)

**TASK-BDD-005**: End-to-End Testing
- Test LangGraph complexity routing
- Test error scenarios
- Validate documentation accuracy
- Test RequireKit integration

**Dependencies**: All previous tasks must complete

---

## Key Design Decisions

### 1. Marker File Detection

**Pattern**: `~/.agentecflow/require-kit.marker`

**Why**:
- Simple, reliable detection
- No package manager dependencies
- Cross-platform compatibility
- Already created by RequireKit installer

### 2. Error-First Design

**Philosophy**: Clear, actionable errors when prerequisites missing

**Example**:
```bash
ERROR: BDD mode requires RequireKit installation

  Repository: https://github.com/requirekit/require-kit
  Installation: cd ~/Projects/require-kit && ./installer/scripts/install.sh

  Alternative modes:
    --mode=tdd      # Test-first development
    --mode=standard # Default workflow
```

### 3. Agentic Systems Focus

**BDD is NOT for**:
- General CRUD features
- Simple UI components
- Bug fixes

**BDD IS for**:
- Agentic orchestration (LangGraph)
- Safety-critical workflows
- Formal specifications

### 4. Delegation Architecture

**Principle**: TaskWright delegates to RequireKit for BDD logic

**No Duplication**:
- ❌ BDD agents NOT in guardkit
- ✅ BDD agents in RequireKit only
- ✅ TaskWright calls RequireKit agents

---

## Success Criteria

### Functionality
- ✅ `/task-work TASK-XXX --mode=bdd` executes
- ✅ Error if RequireKit not installed
- ✅ Error if scenarios not linked
- ✅ Gherkin scenarios load from RequireKit
- ✅ BDD tests execute
- ✅ Fix loop works

### Quality
- ✅ All quality gates enforced
- ✅ Architectural review ≥ 60/100
- ✅ 100% test pass rate
- ✅ Code review approved
- ✅ Documentation complete

### Architecture
- ✅ No DIP violations
- ✅ Clean delegation pattern
- ✅ No code duplication
- ✅ Feature detection maintained

---

## Conductor Workflow Commands

### Wave 1 Setup
```bash
# GuardKit repo
cd ~/Projects/appmilla_github/guardkit
conductor create-workspace bdd-wave1-investigate TASK-BDD-001
conductor create-workspace bdd-wave1-docs TASK-BDD-002
conductor create-workspace bdd-wave1-claude-md TASK-BDD-007

# RequireKit repo
cd ~/Projects/require-kit
conductor create-workspace bdd-wave1-requirekit TASK-BDD-006

# Work in all 4 workspaces simultaneously
```

### Wave 1 Merge
```bash
# In each workspace after completion
conductor merge-workspace
```

### Wave 2 Setup
```bash
cd ~/Projects/appmilla_github/guardkit
conductor create-workspace bdd-wave2-flag TASK-BDD-003
# Complete and merge
conductor create-workspace bdd-wave2-workflow TASK-BDD-004
# Complete and merge
```

### Wave 3 Setup
```bash
cd ~/Projects/appmilla_github/guardkit
conductor create-workspace bdd-wave3-testing TASK-BDD-005
# Complete and merge
```

---

## Files Created

### Implementation Artifacts
- `IMPLEMENTATION-GUIDE.md` - Complete strategy and architecture
- `TASK-BDD-001-investigate-mode-implementation.md` - Investigation task
- `TASK-BDD-002-create-bdd-documentation.md` - Documentation task
- `TASK-BDD-003-restore-mode-flag.md` - Flag implementation task
- `TASK-BDD-004-implement-workflow-routing.md` - Workflow task
- `TASK-BDD-005-integration-testing.md` - Testing task
- `TASK-BDD-006-update-requirekit-agents.md` - RequireKit task
- `TASK-BDD-007-reinstate-bdd-documentation.md` - Reinstate .claude/CLAUDE.md BDD section
- `README.md` (this file) - Quick reference

### Documentation to Create (via tasks)
- `docs/guides/bdd-workflow-for-agentic-systems.md` (TASK-BDD-002)
- `tasks/backlog/bdd-restoration/TASK-BDD-001-investigation-findings.md` (TASK-BDD-001)
- `tasks/backlog/bdd-restoration/TASK-BDD-005-test-results.md` (TASK-BDD-005)

### Code Changes (via tasks)
- `installer/global/commands/task-work.md` (TASK-BDD-003, TASK-BDD-004)
- `CLAUDE.md` (TASK-BDD-002)
- `.claude/CLAUDE.md` (TASK-BDD-007)
- Mode parsing logic (TASK-BDD-003)
- Workflow routing logic (TASK-BDD-004)
- RequireKit agents (TASK-BDD-006, different repo)

---

## References

### Source Documents
- [TASK-2E9E Architectural Review (Final)](./../../../.claude/reviews/TASK-2E9E-architectural-review-FINAL.md)
- [BDD Restoration Guide](../../../docs/research/restoring-bdd-feature.md)
- [BDD Removal Decision](../../../docs/research/bdd-mode-removal-decision.md)
- [TASK-037 Removal Task](../../completed/TASK-037/TASK-037-remove-bdd-mode.md)

### Research Documents
- LangGraph-Native_Orchestration_for_TaskWright_Technical_Architecture.md
- TaskWright_LangGraph_Orchestration_Build_Strategy.md

### Code References
- `installer/global/lib/feature_detection.py`
- `installer/global/commands/task-work.md`
- `.claude/agents/*.md` (agent format examples)

---

## Next Steps

1. ✅ **Read IMPLEMENTATION-GUIDE.md** - Understand full strategy
2. 🚀 **Start Wave 1** - Launch 3 parallel workspaces
3. 📝 **Execute Tasks** - Follow task acceptance criteria
4. 🔄 **Merge & Continue** - Complete waves 2 and 3
5. 🎉 **Dogfood** - Use BDD mode for LangGraph implementation

---

**Status**: Ready to begin
**Next Action**: Execute Wave 1 tasks in parallel
