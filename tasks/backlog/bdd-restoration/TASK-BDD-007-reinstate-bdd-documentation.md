---
id: TASK-BDD-007
title: Reinstate and update BDD documentation with agentic systems focus
status: backlog
created: 2025-11-28T15:27:39.493246+00:00
updated: 2025-11-28T15:27:39.493246+00:00
priority: high
tags: [bdd-restoration, documentation, wave1]
complexity: 2
task_type: documentation
estimated_effort: 30 minutes
wave: 1
parallel: true
implementation_method: claude-code-direct
parent_epic: bdd-restoration
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Reinstate and update BDD documentation with agentic systems focus

## Context

On November 26, 2025, `.claude/CLAUDE.md` was changed from a BDD-centric description ("Software Engineering Lifecycle System that uses EARS notation for requirements, BDD/Gherkin for test specifications") to a task workflow description ("Lightweight Task Workflow System with built-in quality gates").

The old version is preserved in `.claude/CLAUDE.md.backup` and shows:
- **Old title**: "Claude Code Software Engineering Lifecycle System"
- **Old description**: "uses EARS notation for requirements, BDD/Gherkin for test specifications"
- **Old workflow**: "Gather Requirements → Formalize with EARS → Generate BDD → Implement → Verify → Track"
- **Old getting started**: "Run `/gather-requirements` to begin"

**We need to reinstate BDD documentation**, but updated to reflect:
1. BDD mode is **optional** (requires RequireKit)
2. BDD is for **agentic systems** (LangGraph, safety-critical), not general features
3. TaskWright starts at Phase 2 (no `/gather-requirements`)
4. Workflow is `/task-work TASK-XXX --mode=bdd`

**Parent Epic**: BDD Mode Restoration
**Wave**: 1 (Foundation - runs in parallel with TASK-BDD-001, TASK-BDD-002, TASK-BDD-006)
**Implementation**: Use Claude Code directly (documentation task)

## Description

Update `.claude/CLAUDE.md` to accurately describe TaskWright's **dual nature**:
1. **Primary workflow**: Lightweight task management (standard/tdd modes)
2. **Optional BDD workflow**: For agentic systems with RequireKit integration

The backup file shows BDD was completely removed from the project description. We need to add it back, but positioned correctly as an optional, specialized workflow.

## Acceptance Criteria

### Primary Deliverable

**File**: `.claude/CLAUDE.md`

**Changes Required**:

#### 1. Update Project Context (lines 3-5)

**Current (Task-Only)**:
```markdown
This is an AI-powered task workflow system with built-in quality gates that prevents broken code from reaching production. The system is technology-agnostic with stack-specific plugins.
```

**New (Task + Optional BDD)**:
```markdown
This is an AI-powered task workflow system with built-in quality gates that prevents broken code from reaching production. The system is technology-agnostic with stack-specific plugins.

For formal agentic system development (LangGraph, multi-agent coordination), TaskWright integrates with RequireKit to provide EARS notation, BDD scenarios, and requirements traceability.
```

#### 2. Update Core Principles (lines 9-13)

**Add 6th principle**:
```markdown
6. **Optional Formality**: Standard workflow for features, BDD workflow for agentic systems
```

#### 3. Update Workflow Overview (lines 24-27)

**Current**:
```markdown
1. **Create Task**: Define what needs to be done
2. **Work on Task**: AI implements with quality gates (Phases 2-5.5)
3. **Review**: Human reviews approved implementation
4. **Complete**: Archive and track
```

**Add BDD Alternative**:
```markdown
### Standard Workflow (Most Tasks)
1. **Create Task**: Define what needs to be done
2. **Work on Task**: AI implements with quality gates (Phases 2-5.5)
3. **Review**: Human reviews approved implementation
4. **Complete**: Archive and track

### BDD Workflow (Agentic Systems - Requires RequireKit)
1. **Formalize Requirements**: Create EARS requirements in RequireKit
2. **Generate Scenarios**: Convert EARS → Gherkin scenarios
3. **Implement with BDD**: Run `/task-work TASK-XXX --mode=bdd`
4. **Verify**: BDD tests ensure requirements met
5. **Complete**: Archive with full traceability

**Use BDD for**: LangGraph state machines, safety-critical workflows, formal behavior specifications
**Use Standard for**: General features, bug fixes, UI components, CRUD operations
```

#### 4. Update Technology Stack Detection (lines 33-37)

**Current**:
```markdown
- Python API → pytest
```

**Update to**:
```markdown
- Python API → pytest (pytest-bdd for BDD mode)
```

#### 5. Update Getting Started (lines 41-42)

**Current**:
```markdown
Run `/task-create "Your task"` to begin a new task, then use `/task-work TASK-XXX` to implement it with automatic quality gates.
```

**Update to**:
```markdown
### Standard Tasks
Run `/task-create "Your task"` to begin a new task, then use `/task-work TASK-XXX` to implement it with automatic quality gates.

### BDD Mode (Agentic Systems)
For formal agentic systems, first install RequireKit:
```bash
cd ~/Projects/require-kit
./installer/scripts/install.sh
```

Then use BDD workflow:
```bash
# In RequireKit: Create requirements
/req-create "System behavior"
/formalize-ears REQ-001
/generate-bdd REQ-001

# In TaskWright: Implement from scenarios
/task-create "Implement behavior" requirements:[REQ-001]
/task-work TASK-042 --mode=bdd
```

See [BDD Workflow Guide](../docs/guides/bdd-workflow-for-agentic-systems.md) for complete details.
```

### Secondary Actions

**Keep the backup file**:
- DO NOT delete `.claude/CLAUDE.md.backup`
- It serves as historical reference for the old BDD-centric approach
- Useful for understanding the evolution of the project

**No changes to**:
- `CLAUDE.md` (root) - already has correct references to RequireKit
- `README.md` - already mentions BDD in appropriate places

## Success Criteria

- [ ] `.claude/CLAUDE.md` updated with BDD workflow section
- [ ] BDD positioned as **optional** for agentic systems
- [ ] Standard workflow remains primary focus
- [ ] RequireKit installation instructions included
- [ ] References to `/gather-requirements` removed (that was old workflow)
- [ ] Clear decision criteria: when to use BDD vs Standard
- [ ] Backup file preserved for historical reference
- [ ] Documentation is accurate and not misleading

## Testing Checklist

- [ ] Read updated `.claude/CLAUDE.md`
- [ ] Verify BDD is positioned as optional
- [ ] Verify standard workflow is primary
- [ ] Check RequireKit installation instructions are correct
- [ ] Ensure no references to deprecated commands (`/gather-requirements`)
- [ ] Validate decision criteria are clear

## Related Tasks

**Depends On**: None (Wave 1 parallel starter)
**Parallel With**:
- TASK-BDD-001 (investigation)
- TASK-BDD-002 (user-facing BDD guide)
- TASK-BDD-006 (RequireKit agents)
**Blocks**: TASK-BDD-005 (testing validates documentation accuracy)

## References

- [.claude/CLAUDE.md.backup](../../../.claude/CLAUDE.md.backup) (old BDD-centric version)
- [Implementation Guide](./IMPLEMENTATION-GUIDE.md)
- [TASK-BDD-002](./TASK-BDD-002-create-bdd-documentation.md) (creates user-facing BDD guide)
- [BDD Restoration Guide](../../../docs/research/restoring-bdd-feature.md)

## Notes

### What Changed (November 26, 2025)

**Removed**:
- "Software Engineering Lifecycle System" branding
- "EARS notation for requirements, BDD/Gherkin for test specifications"
- Workflow: "Gather Requirements → Formalize with EARS → Generate BDD"
- Getting started: "Run `/gather-requirements`"

**Added**:
- "Lightweight Task Workflow System" branding
- Focus on quality gates and pragmatic approach
- Workflow: "Create Task → Work on Task → Review → Complete"
- Getting started: "Run `/task-create`"

**Why Removed**: BDD mode was removed from TaskWright (TASK-037, November 2, 2025)

**Why Reinstating**: BDD mode is being restored specifically for agentic systems (LangGraph, safety-critical workflows)

### Key Positioning

The documentation must reflect that:
1. **TaskWright is primarily a task workflow system** (NOT a BDD system)
2. **BDD is an optional mode** for specialized use cases
3. **RequireKit is required** for BDD mode (not bundled)
4. **Standard mode is the default** (covers 95% of use cases)
5. **BDD mode is for formal specifications** (agentic systems, not general features)

This is different from the old `.claude/CLAUDE.md.backup` which positioned BDD as the primary workflow.
