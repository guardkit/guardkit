---
id: TASK-4F79
legacy_id: TASK-003
title: "Remove Requirements Management Agents"
created: 2025-10-27
status: completed
completed_at: 2025-11-01T14:25:51Z
priority: high
complexity: 2
parent_task: none
subtasks: []
estimated_hours: 1
actual_hours: 0.1
completion_metrics:
  files_deleted: 2
  files_modified: 1
  agents_removed: 2
  agents_remaining: 15
  references_cleaned: 1
---

# TASK-4F79: Remove Requirements Management Agents

## Description

Remove AI agents specifically designed for requirements management (EARS notation, BDD generation) from taskwright, keeping all quality gate and task workflow agents.

## Context

Taskwright focuses on task workflow with quality gates. Requirements-specific agents (requirements-analyst, bdd-generator) are not needed for the lite workflow.

## Agents to Remove

```bash
❌ requirements-analyst.md    # EARS notation specialist
❌ bdd-generator.md           # BDD/Gherkin scenario generation
```

## Agents to Keep (15 total)

### Quality Gate Agents (Critical)
```bash
✅ architectural-reviewer.md      # Phase 2.5 - SOLID/DRY/YAGNI
✅ test-verifier.md              # Phase 4.5 - Test enforcement
✅ test-orchestrator.md          # Phase 4.5 support
✅ code-reviewer.md              # Phase 5 - Code review
✅ task-manager.md               # Core orchestration
✅ complexity-evaluator.md       # Phase 2.7 - Complexity routing
✅ build-validator.md            # Compilation checks
```

### Supporting Agents
```bash
✅ debugging-specialist.md
✅ devops-specialist.md
✅ database-specialist.md
✅ security-specialist.md
✅ pattern-advisor.md
✅ python-mcp-specialist.md
✅ figma-react-orchestrator.md
✅ zeplin-maui-orchestrator.md
```

## Implementation Steps

### 1. Locate Agent Files

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/taskwright/.conductor/kuwait

# Find requirements-related agents
find installer/core/agents -name "*requirements*.md"
find installer/core/agents -name "*bdd*.md"
```

### 2. Remove Agent Files

```bash
rm -f installer/core/agents/requirements-analyst.md
rm -f installer/core/agents/bdd-generator.md
```

### 3. Verify Remaining Agents

```bash
# List remaining agents
ls installer/core/agents/*.md

# Count should be 15
ls -1 installer/core/agents/*.md | wc -l
```

### 4. Check for References

```bash
# Search for references to removed agents in remaining files
grep -r "requirements-analyst" installer/core/agents/
grep -r "bdd-generator" installer/core/agents/

# Should return empty
```

## Acceptance Criteria

- [x] requirements-analyst.md removed
- [x] bdd-generator.md removed
- [x] 15 quality gate and supporting agents remain
- [x] No references to removed agents in remaining agent files
- [x] Git status shows deletions

## Related Tasks

- TASK-1FDF: Remove requirements management commands
- TASK-6444: Modify task-work.md (remove agent orchestration references)

## Estimated Time

1 hour

## Notes

- Simple deletion task - no modifications needed
- Stack-specific agents in templates will be handled separately (TASK-05BB)
- Agent orchestration updates handled in TASK-6444
