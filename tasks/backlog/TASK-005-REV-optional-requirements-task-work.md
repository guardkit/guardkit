---
id: TASK-005-REV
title: "Make task-work.md Requirements Features Optional"
created: 2025-10-27
status: backlog
priority: high
complexity: 5
parent_task: none
subtasks: []
estimated_hours: 2.5
depends_on: TASK-012
supersedes: TASK-005
---

# TASK-005-REV: Make task-work.md Requirements Features Optional

## Overview

**SUPERSEDES TASK-005** - New approach based on shared installation strategy (TASK-012).

Instead of removing requirements loading from Phase 1, make it **conditional** based on whether require-kit is installed AND task has requirements linked.

## Strategic Context

- **taskwright only**: Phase 1 analyzes task description only
- **require-kit installed + task has requirements**: Phase 1 loads EARS/BDD context
- **Graceful operation**: All quality gate phases always execute

## Changes Required

### 1. Add Feature Detection

```bash
# At top of task-work command
REQUIRE_KIT_INSTALLED=false
if [ -f "$HOME/.agentecflow/require-kit.marker" ]; then
  REQUIRE_KIT_INSTALLED=true
fi
```

### 2. Conditional Phase 1 Logic

**Phase 1: Task Analysis**

```bash
# ALWAYS load:
- Task frontmatter (id, title, status, priority, complexity)
- Task description and acceptance criteria
- Parent task context (if subtask)
- Technology stack detection

# CONDITIONAL (only if require-kit installed AND task has links):
if [ "$REQUIRE_KIT_INSTALLED" = true ]; then
  # Check task frontmatter
  EPIC=$(grep "^epic:" task.md | cut -d: -f2 | xargs)
  FEATURE=$(grep "^feature:" task.md | cut -d: -f2 | xargs)
  REQUIREMENTS=$(grep "^requirements:" task.md | cut -d: -f2 | xargs)

  # Load context if linked
  if [ "$EPIC" != "none" ] && [ -n "$EPIC" ]; then
    echo "📋 Loading epic context: $EPIC"
    # Load epic description
    # Pass to agents
  fi

  if [ "$FEATURE" != "none" ] && [ -n "$FEATURE" ]; then
    echo "📋 Loading feature context: $FEATURE"
    # Load feature description
  fi

  if [ -n "$REQUIREMENTS" ] && [ "$REQUIREMENTS" != "[]" ]; then
    echo "📋 Loading requirements context: $REQUIREMENTS"
    # Load EARS requirements
    # Load BDD scenarios
    # Pass to agents
  fi
fi
```

### 3. Keep All Quality Gate Phases

**NO CHANGES to**:
- Phase 2: Implementation Planning
- Phase 2.5: Architectural Review ✅
- Phase 2.6: Human Checkpoint ✅
- Phase 2.7: Complexity Evaluation ✅
- Phase 3: Implementation
- Phase 4: Testing
- Phase 4.5: Test Enforcement ✅
- Phase 5: Code Review
- Phase 5.5: Plan Audit ✅

### 4. Conditional Agent Orchestration

```bash
# Agent selection in Phase 1
AGENTS=("task-manager")

# Stack-specific agent
case $STACK in
  react) AGENTS+=("react-specialist") ;;
  python) AGENTS+=("python-specialist") ;;
  # ...
esac

# Requirements agents (only if require-kit installed and needed)
if [ "$REQUIRE_KIT_INSTALLED" = true ]; then
  if [ -n "$REQUIREMENTS" ] && [ "$REQUIREMENTS" != "[]" ]; then
    AGENTS+=("requirements-analyst")
  fi

  # Check if BDD mode requested
  if [ "$MODE" = "bdd" ]; then
    AGENTS+=("bdd-generator")
  fi
fi
```

### 5. Conditional Help Text

```bash
show_help() {
  cat << EOF
Usage: /task-work TASK-XXX [options]

Options:
  --mode=standard|tdd|bdd    Development mode (default: standard)
  --design-only              Execute Phases 1-2.6, stop at checkpoint
  --implement-only           Execute Phases 3-5 from saved plan
  --micro                    Simplified workflow for small tasks

Modes:
  standard    Normal implementation workflow
  tdd         Test-Driven Development (Red-Green-Refactor)
  bdd         Behavior-Driven Development (Scenarios → Implementation)

EOF

  if [ "$REQUIRE_KIT_INSTALLED" = true ]; then
    cat << EOF
Requirements Management (require-kit):
  When task has epic/feature/requirements linked, Phase 1 will:
  - Load EARS requirements context
  - Load BDD scenarios (if exist)
  - Load epic/feature context
  - Pass context to specialized agents

EOF
  fi

  cat << EOF
Quality Gates:
  Phase 2.5: Architectural Review (SOLID/DRY/YAGNI)
  Phase 2.6: Human Checkpoint (if complexity ≥7)
  Phase 4.5: Test Enforcement (auto-fix, 100% pass)
  Phase 5.5: Plan Audit (scope creep detection)

Examples:
  /task-work TASK-001
  /task-work TASK-001 --mode=tdd
  /task-work TASK-001 --design-only
EOF
}
```

### 6. Update Flag Handling

```bash
# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --mode=*)
      MODE="${1#*=}"
      ;;
    --design-only)
      DESIGN_ONLY=true
      ;;
    --implement-only)
      IMPLEMENT_ONLY=true
      ;;
    --micro)
      MICRO=true
      ;;
    --sync-progress)
      if [ "$REQUIRE_KIT_INSTALLED" = true ]; then
        SYNC_PROGRESS=true
      else
        echo "⚠️  Warning: --sync-progress requires require-kit"
      fi
      ;;
    --with-context)
      # This flag becomes default behavior for parent tasks
      # No longer needed, but kept for backward compatibility
      echo "ℹ️  Note: Context loading is now automatic"
      ;;
  esac
  shift
done
```

## Implementation Steps

### 1. Backup Current File

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/taskwright/.conductor/kuwait
cp installer/global/commands/task-work.md installer/global/commands/task-work.md.backup
```

### 2. Add Feature Detection

Add require-kit detection at command start.

### 3. Update Phase 1 Section

Rewrite Phase 1 with conditional logic:
- Always load task basics
- Conditionally load requirements context

### 4. Update Agent Orchestration

- Keep all quality gate agents
- Conditionally add requirements-analyst, bdd-generator

### 5. Update Help Text

- Show requirements integration section only if require-kit installed
- Keep all quality gate documentation

### 6. Test Both Scenarios

Test with and without require-kit, with and without requirements.

## Validation Checklist

### With taskwright Only
- [ ] `/task-work TASK-001` executes Phase 1 without requirements
- [ ] All quality gate phases execute (2.5, 2.6, 2.7, 4.5, 5.5)
- [ ] No errors about missing requirements files
- [ ] Help text excludes requirements features

### With Both Installed (Task with Requirements)
- [ ] Phase 1 loads EARS requirements
- [ ] Phase 1 loads BDD scenarios
- [ ] Phase 1 loads epic/feature context
- [ ] requirements-analyst agent invoked
- [ ] All quality gates still execute

### With Both Installed (Task without Requirements)
- [ ] Phase 1 skips requirements loading
- [ ] Works same as taskwright only
- [ ] No unnecessary file lookups

### Edge Cases
- [ ] Task with epic but no requirements → loads epic only
- [ ] Task with requirements but files missing → warning
- [ ] BDD mode without require-kit → warning
- [ ] --sync-progress without require-kit → warning

## Testing

```bash
# Test taskwright only scenario
rm ~/.agentecflow/require-kit.marker

cd /tmp/test-taskwright
/task-create "Simple feature"
/task-work TASK-001

# Should:
# - NOT load requirements
# - NOT invoke requirements-analyst
# - Execute all quality gate phases
# - Complete successfully

# Test with both installed (no requirements on task)
touch ~/.agentecflow/require-kit.marker

/task-create "Another feature"
/task-work TASK-002

# Should:
# - Check for requirements (finds none)
# - Skip requirements loading
# - Work same as taskwright only

# Test with both installed (requirements on task)
/task-create "Auth feature" epic:EPIC-001 requirements:[REQ-012]
/task-work TASK-003

# Should:
# - Load EPIC-001 context
# - Load REQ-012 context
# - Invoke requirements-analyst
# - Execute all quality gates
```

## Quality Gate Verification

**CRITICAL**: Verify all quality gates still work:

```bash
# Test Phase 2.5 (Architectural Review)
# Should execute regardless of require-kit

# Test Phase 2.6 (Human Checkpoint)
# Should trigger for complexity ≥7

# Test Phase 4.5 (Test Enforcement)
# Should auto-fix failing tests

# Test Phase 5.5 (Plan Audit)
# Should detect scope creep
```

## Documentation Updates

### In task-work.md

Add section:
```markdown
## Requirements Management Integration

When require-kit is installed AND task has requirements linked:

**Phase 1 Enhancement**:
- Loads EARS requirements from docs/requirements/
- Loads BDD scenarios from docs/bdd/
- Loads epic/feature context
- Passes context to requirements-analyst agent

**Without require-kit**:
- Phase 1 analyzes task description only
- All quality gates still execute
- No functional limitations for task workflow

Install require-kit for requirements features: https://github.com/you/require-kit
```

## Acceptance Criteria

- [ ] task-work.md updated with conditional logic
- [ ] Feature detection implemented
- [ ] Phase 1 loads requirements conditionally
- [ ] Agent orchestration conditional
- [ ] Help text adapts to installed packages
- [ ] All quality gate phases intact
- [ ] Works with taskwright only (no errors)
- [ ] Works with both installed (enhanced Phase 1)
- [ ] Tests pass for all scenarios

## Related Tasks

- **DEPENDS ON**: TASK-012 (Shared Installation Strategy)
- **SUPERSEDES**: TASK-005 (old removal approach)
- **SIMILAR TO**: TASK-004-REV, TASK-006-REV
- TASK-003: Remove agents (NO LONGER REMOVE - require-kit provides)

## Estimated Time

2.5 hours (was 2h, added 0.5h for conditional logic)

## Notes

- Most complex modification task
- Conditional logic adds complexity but preserves flexibility
- All quality gates remain intact - this is critical
- Phase 1 becomes "basic + optional enhancement"
- Test thoroughly - this is core workflow
- **IMPORTANT**: Old TASK-005 should be marked as superseded/cancelled
