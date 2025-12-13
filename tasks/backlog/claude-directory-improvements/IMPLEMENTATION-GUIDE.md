# Implementation Guide: Claude Directory Improvements

## Wave Breakdown

### Wave 1: High Priority Fixes (3 tasks, parallel)

These tasks address the most impactful gaps from the TASK-REV-79E0 review.

#### TASK-CDI-001: Create orchestrators.md pattern file
**Method**: Direct (simple file creation)
**Effort**: 30-45 minutes
**Workspace**: `claude-improvements-wave1-orchestrators`

Create `.claude/rules/patterns/orchestrators.md` with:
- Path pattern: `**/*orchestrator.py, **/*_orchestrator.py`
- Multi-step workflow patterns from GuardKit codebase
- Checkpoint-resume patterns
- State management patterns

#### TASK-CDI-002: Narrow dataclasses.md path pattern
**Method**: Direct (simple edit)
**Effort**: 15 minutes
**Workspace**: `claude-improvements-wave1-dataclasses`

Update `.claude/rules/patterns/dataclasses.md`:
- Change from: `paths: "**/*.py"`
- Change to: `paths: "**/state*.py, **/*_state.py, **/*result*.py, **/*context*.py"`

#### TASK-CDI-003: Split debugging-specialist.md
**Method**: task-work (significant refactoring)
**Effort**: 1 hour
**Workspace**: `claude-improvements-wave1-debug-split`

Split `.claude/agents/debugging-specialist.md` (1,140 lines) into:
- Core file: 300-400 lines (Quick Start, Boundaries, Capabilities)
- Extended file: 700-800 lines (Detailed examples, Best practices)

---

### Wave 2: Medium/Low Priority Fixes (2 tasks, parallel)

#### TASK-CDI-004: Fix testing.md path overlap
**Method**: Direct (simple edit)
**Effort**: 15 minutes
**Workspace**: `claude-improvements-wave2-testing`

Update `.claude/rules/testing.md`:
- Consolidate overlapping path patterns
- Ensure no duplicate rule loading

#### TASK-CDI-005: Update review task status
**Method**: Direct (task state update)
**Effort**: 5 minutes

Move TASK-REV-79E0 from backlog to completed with review_results metadata.

---

## Execution Commands

### Wave 1 (Parallel via Conductor)

```bash
# Workspace 1: orchestrators.md
/task-work TASK-CDI-001  # or direct implementation

# Workspace 2: dataclasses.md
/task-work TASK-CDI-002  # or direct implementation

# Workspace 3: debugging-specialist split
/task-work TASK-CDI-003
```

### Wave 2 (After Wave 1 merge)

```bash
# Quick fixes
/task-work TASK-CDI-004  # or direct implementation
/task-complete TASK-REV-79E0
```

---

## Dependencies

```
TASK-REV-79E0 (completed review)
    │
    ├── Wave 1 (parallel)
    │   ├── TASK-CDI-001 (orchestrators.md)
    │   ├── TASK-CDI-002 (dataclasses.md path)
    │   └── TASK-CDI-003 (debugging-specialist split)
    │
    └── Wave 2 (after Wave 1)
        ├── TASK-CDI-004 (testing.md path)
        └── TASK-CDI-005 (close review task)
```

---

## Validation

After implementation, verify:

1. **Rules loading correctly**
   ```bash
   # Check orchestrators.md loads for orchestrator files
   # Check dataclasses.md only loads for state/result/context files
   ```

2. **Progressive disclosure working**
   ```bash
   # Check debugging-specialist.md is under 400 lines
   # Check debugging-specialist-ext.md exists with remaining content
   ```

3. **No path overlaps**
   ```bash
   # Verify testing.md has single consolidated path pattern
   ```

---

## Patterns for orchestrators.md

Extract from GuardKit's actual orchestrator files:

### From `implement_orchestrator.py`
- Pipeline step execution
- State management with dataclasses
- Error handling and recovery
- Progress reporting

### From `template_qa_orchestrator.py`
- Multi-phase workflow
- Checkpoint-resume pattern
- Validation chain

### From `agent_enhancement/orchestrator.py`
- AI/static/hybrid strategy routing
- State persistence
- Dry-run mode
