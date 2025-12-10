---
id: TASK-005
title: "Modify task-work.md - Remove Requirements Loading"
created: 2025-10-27
status: backlog
priority: high
complexity: 4
parent_task: none
subtasks: []
estimated_hours: 2
---

# TASK-005: Modify task-work.md - Remove Requirements Loading

## Description

Simplify task-work.md by removing EARS requirements loading, BDD scenario validation, and epic/feature context gathering from Phase 1, while keeping all quality gate phases intact.

## Changes Required

### 1. Simplify Phase 1 (Requirements Analysis → Task Analysis)

**Remove FROM Phase 1**:
- Loading EARS requirements from docs/requirements/
- Loading BDD scenarios from docs/bdd/
- Validating requirement links
- Epic/feature context gathering
- Requirements traceability checks

**Simplify TO**:
- Load task description and acceptance criteria
- Load parent task context (if subtask)
- Identify technology stack
- Analyze task complexity

### 2. Keep All Quality Gate Phases

**✅ Keep all phases**:
- Phase 1: Task Analysis (SIMPLIFIED - no requirements)
- Phase 2: Implementation Planning (Markdown format)
- Phase 2.5: Architectural Review (SOLID/DRY/YAGNI)
- Phase 2.6: Human Checkpoint (if triggered)
- Phase 2.7: Complexity Evaluation (routing logic)
- Phase 3: Implementation
- Phase 4: Testing (compilation + coverage)
- Phase 4.5: Test Enforcement (auto-fix loop)
- Phase 5: Code Review
- Phase 5.5: Plan Audit (scope creep detection)

### 3. Remove Command Flags

**Remove**:
- `--sync-progress` (PM tool synchronization)
- `--with-context` (epic/feature context - make parent context default)

**Keep**:
- `--mode=tdd|bdd|standard`
- `--design-only`
- `--implement-only`
- `--micro`

### 4. Update Agent Orchestration

**Remove agent references**:
- requirements-analyst
- bdd-generator

**Keep all other agents**:
- architectural-reviewer (Phase 2.5)
- complexity-evaluator (Phase 2.7)
- test-verifier (Phase 4.5)
- test-orchestrator (Phase 4.5 support)
- code-reviewer (Phase 5)
- All supporting agents

## Implementation Steps

### 1. Backup Current File

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit/.conductor/kuwait
cp installer/core/commands/task-work.md installer/core/commands/task-work.md.backup
```

### 2. Edit Phase 1 Section

Rewrite Phase 1 instructions to:
- Focus on task description analysis only
- Remove requirements file loading
- Remove BDD scenario loading
- Simplify to: task metadata + parent context + stack detection

### 3. Remove Agent References

Search and remove/update:
```bash
# Find agent references
grep -n "requirements-analyst\|bdd-generator" installer/core/commands/task-work.md

# Remove or comment out these orchestration calls
```

### 4. Update Flag Documentation

Remove `--sync-progress` and `--with-context` documentation:
- Remove flag descriptions
- Remove usage examples
- Update help text

### 5. Verify Phase Integrity

Ensure all quality gate phases (2.5, 2.6, 2.7, 4.5, 5.5) remain intact:
```bash
# Verify phases present
grep -i "phase 2\.5\|phase 2\.6\|phase 2\.7\|phase 4\.5\|phase 5\.5" \
  installer/core/commands/task-work.md
```

## Validation Checklist

### Phase 1 Changes
- [ ] No EARS requirements loading
- [ ] No BDD scenario loading
- [ ] No epic/feature context loading
- [ ] Parent task context retained
- [ ] Stack detection retained

### Agent Orchestration
- [ ] requirements-analyst removed
- [ ] bdd-generator removed
- [ ] All quality gate agents retained

### Flags
- [ ] --sync-progress removed
- [ ] --with-context removed/simplified
- [ ] All design-first flags retained
- [ ] --micro flag retained

### Quality Gates
- [ ] Phase 2.5 (Architectural Review) intact
- [ ] Phase 2.6 (Human Checkpoint) intact
- [ ] Phase 2.7 (Complexity Evaluation) intact
- [ ] Phase 4.5 (Test Enforcement) intact
- [ ] Phase 5.5 (Plan Audit) intact

## Acceptance Criteria

- [ ] task-work.md modified
- [ ] Phase 1 simplified (no requirements loading)
- [ ] Agent orchestration updated (2 agents removed)
- [ ] Command flags simplified (2 flags removed)
- [ ] All quality gate phases remain intact
- [ ] No references to EARS/BDD/epic/feature in active instructions
- [ ] Grep verification passes

## Testing

```bash
# Smoke test - verify task-work still executes
cd /tmp/test-project
/task-create "Simple test task"
/task-work TASK-001 --micro  # Should complete without errors

# Verify phases execute
# - Phase 1: Should NOT load requirements
# - Phase 2.5: Should still execute architectural review
# - Phase 4.5: Should still enforce tests
```

## Related Tasks

- TASK-002: Remove requirements management commands
- TASK-003: Remove requirements-related agents
- TASK-004: Modify task-create.md

## Estimated Time

2 hours

## Notes

- Most complex modification task - affects core workflow
- Be careful not to break quality gate phases
- Test thoroughly after changes
- Document what was simplified in comments
