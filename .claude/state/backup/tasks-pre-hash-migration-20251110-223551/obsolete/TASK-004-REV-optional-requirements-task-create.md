---
id: TASK-004-REV
title: "Make task-create.md Requirements Features Optional"
created: 2025-10-27
status: obsolete
priority: high
complexity: 4
parent_task: none
subtasks: []
estimated_hours: 2
depends_on: TASK-012
supersedes: TASK-004
---

# TASK-004-REV: Make task-create.md Requirements Features Optional

## Overview

**SUPERSEDES TASK-004** - New approach based on shared installation strategy (TASK-012).

Instead of removing epic/feature/requirements fields, make them **optional** and **conditionally available** based on whether require-kit is installed.

## Strategic Context

- **guardkit only**: Task creation without epic/feature/requirements
- **require-kit installed**: Full epic/feature/requirements linking available
- **Graceful degradation**: Commands work in both scenarios

## Changes Required

### 1. Frontmatter Template - Keep All Fields

```yaml
---
id: {TASK_ID}
title: "{title}"
created: {date}
status: obsolete
priority: {priority}
complexity: 0
parent_task: none
subtasks: []
# Optional (only used if require-kit installed):
epic: none
feature: none
requirements: []
---
```

**Key**: All fields present, but epic/feature/requirements default to "none" or empty.

### 2. Add Feature Detection

```bash
# At top of task-create command logic
REQUIRE_KIT_INSTALLED=false
if [ -f "$HOME/.agentecflow/require-kit.marker" ]; then
  REQUIRE_KIT_INSTALLED=true
fi
```

### 3. Conditional Flag Parsing

```bash
# Parse command arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    priority:*)
      PRIORITY="${1#*:}"
      ;;
    --parent)
      PARENT="$2"
      shift
      ;;
    epic:*)
      if [ "$REQUIRE_KIT_INSTALLED" = true ]; then
        EPIC="${1#*:}"
      else
        echo "⚠️  Warning: Epic linking requires require-kit to be installed"
        echo "   Install: https://github.com/requirekit/require-kit"
      fi
      ;;
    feature:*)
      if [ "$REQUIRE_KIT_INSTALLED" = true ]; then
        FEATURE="${1#*:}"
      else
        echo "⚠️  Warning: Feature linking requires require-kit to be installed"
      fi
      ;;
    requirements:*)
      if [ "$REQUIRE_KIT_INSTALLED" = true ]; then
        REQUIREMENTS="${1#*:}"
      else
        echo "⚠️  Warning: Requirements linking requires require-kit"
      fi
      ;;
  esac
  shift
done
```

### 4. Conditional Help Text

```bash
show_help() {
  cat << EOF
Usage: /task-create "title" [options]

Options:
  priority:high|medium|low    Set task priority (default: medium)
  --parent TASK-XXX          Create as subtask of TASK-XXX

EOF

  if [ "$REQUIRE_KIT_INSTALLED" = true ]; then
    cat << EOF
Requirements Management (require-kit):
  epic:EPIC-XXX              Link to epic
  feature:FEAT-XXX           Link to feature
  requirements:[REQ-001,...]  Link to requirements

EOF
  fi

  cat << EOF
Examples:
  /task-create "Add user authentication"
  /task-create "Fix login bug" priority:high
  /task-create "Update tests" --parent TASK-042
EOF

  if [ "$REQUIRE_KIT_INSTALLED" = true ]; then
    cat << EOF
  /task-create "Auth API" epic:EPIC-001 feature:FEAT-005
  /task-create "Login flow" requirements:[REQ-012,REQ-013]
EOF
  fi
}
```

### 5. Conditional Validation

```bash
# Validate epic/feature links (only if require-kit installed)
if [ "$REQUIRE_KIT_INSTALLED" = true ]; then
  if [ -n "$EPIC" ] && [ "$EPIC" != "none" ]; then
    # Validate epic exists
    if [ ! -f "docs/epics/$EPIC.md" ]; then
      echo "⚠️  Epic $EPIC not found"
      echo "   Create with: /epic-create"
    fi
  fi

  if [ -n "$FEATURE" ] && [ "$FEATURE" != "none" ]; then
    # Validate feature exists
    if [ ! -f "docs/features/$FEATURE.md" ]; then
      echo "⚠️  Feature $FEATURE not found"
    fi
  fi
fi
```

## Implementation Steps

### 1. Backup Current File

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit/.conductor/kuwait
cp installer/global/commands/task-create.md installer/global/commands/task-create.md.backup
```

### 2. Add Feature Detection Logic

Add at the top of the command logic:
- Check for require-kit.marker file
- Set REQUIRE_KIT_INSTALLED variable

### 3. Update Flag Parsing

- Keep all flag parsing (epic, feature, requirements)
- Add warnings when flags used without require-kit
- Suggest require-kit installation

### 4. Update Help Text

- Show basic usage always
- Show requirements features section only if require-kit installed
- Update examples conditionally

### 5. Update Validation Logic

- Only validate epic/feature/requirements if require-kit installed
- Skip validation if guardkit only

### 6. Test Both Scenarios

Test with and without require-kit.marker file.

## Validation Checklist

### With guardkit Only
- [ ] `/task-create "Task"` works
- [ ] `/task-create "Task" priority:high` works
- [ ] `/task-create "Task" epic:EPIC-001` shows warning
- [ ] Help text excludes requirements features
- [ ] Frontmatter includes epic/feature fields (set to "none")

### With Both Installed
- [ ] `/task-create "Task" epic:EPIC-001` works
- [ ] `/task-create "Task" requirements:[REQ-001]` works
- [ ] Help text includes requirements features
- [ ] Epic/feature validation runs
- [ ] Frontmatter includes actual epic/feature values

### Edge Cases
- [ ] Epic link when epic doesn't exist → warning
- [ ] Requirements link when requirements don't exist → warning
- [ ] Multiple flags together work
- [ ] Invalid flags show error

## Testing

```bash
# Test guardkit only scenario
rm ~/.agentecflow/require-kit.marker

cd /tmp/test-guardkit
/task-create "Test task"
cat tasks/backlog/TASK-001-test-task.md
# Should have: epic: none, feature: none, requirements: []

/task-create "Test" epic:EPIC-001
# Should show: "⚠️  Warning: Epic linking requires require-kit"

/task-create --help
# Should NOT show epic/feature/requirements options

# Test with both installed
touch ~/.agentecflow/require-kit.marker

cd /tmp/test-both
/task-create "Test task" epic:EPIC-001 requirements:[REQ-001]
cat tasks/backlog/TASK-001-test-task.md
# Should have: epic: EPIC-001, requirements: [REQ-001]

/task-create --help
# SHOULD show epic/feature/requirements options
```

## Documentation Updates

### In task-create.md

Add section:
```markdown
## Requirements Management Integration

When require-kit is installed, task-create supports:
- Epic linking: `epic:EPIC-XXX`
- Feature linking: `feature:FEAT-XXX`
- Requirements linking: `requirements:[REQ-001,REQ-002]`

These features are optional. Without require-kit, tasks work standalone.

Install require-kit: https://github.com/requirekit/require-kit
```

## Acceptance Criteria

- [ ] task-create.md updated with conditional logic
- [ ] Feature detection implemented
- [ ] Flag parsing includes warnings
- [ ] Help text adapts to installed packages
- [ ] Frontmatter always includes all fields
- [ ] Works with guardkit only (no errors)
- [ ] Works with both installed (full features)
- [ ] Tests pass for both scenarios

## Related Tasks

- **DEPENDS ON**: TASK-012 (Shared Installation Strategy)
- **SUPERSEDES**: TASK-004 (old removal approach)
- **SIMILAR TO**: TASK-005-REV, TASK-006-REV
- TASK-010: Update manifest (needs install_to field)

## Estimated Time

2 hours (was 1.5h, added 0.5h for conditional logic)

## Notes

- This approach is more complex than removal, but more flexible
- Preserves backward compatibility when both packages installed
- Users can start with guardkit, add require-kit later
- No data loss or migration needed
- **IMPORTANT**: Old TASK-004 should be marked as superseded/cancelled

---

## ✅ TASK CLOSED - Superseded by TASK-012

**Closure Date**: 2025-10-28
**Closure Reason**: Superseded by TASK-012 bidirectional integration implementation
**Git Commit**: d85f17a

### What Was Implemented

TASK-012 implemented the complete bidirectional optional integration approach, which includes all the functionality planned in this task:

1. ✅ **Feature Detection** - `installer/global/lib/feature_detection.py` provides `supports_requirements()`
2. ✅ **Conditional Display** - `task-create.md` splits examples into Core vs Integration sections
3. ✅ **Help Text Adaptation** - Documentation shows which options require require-kit
4. ✅ **Graceful Warnings** - User sees helpful messages when integration features unavailable

### Implementation Location

- **File Modified**: `installer/global/commands/task-create.md`
- **Changes**: Added bidirectional integration notes, split options into Core and Integration sections
- **Documentation**: `docs/architecture/bidirectional-integration.md`

### Why This Task Is Obsolete

TASK-012 took a more comprehensive approach by:
- Implementing feature detection library (shared with require-kit)
- Updating ALL commands (task-create, task-work, spec_drift_detector)
- Creating complete architecture documentation
- Aligning with require-kit's existing implementation

This task's goals are fully achieved through TASK-012's implementation.

**See**: `tasks/backlog/TASK-012-shared-installation-strategy.md` for complete implementation details.
