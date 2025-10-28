---
id: TASK-006-REV
title: "Make task-status.md Requirements Features Optional"
created: 2025-10-27
status: obsolete
priority: medium
complexity: 3
parent_task: none
subtasks: []
estimated_hours: 1.5
depends_on: TASK-012
supersedes: TASK-006
---

# TASK-006-REV: Make task-status.md Requirements Features Optional

## Overview

**SUPERSEDES TASK-006** - New approach based on shared installation strategy (TASK-012).

Instead of removing epic/feature filters, make them **conditional** based on whether require-kit is installed.

## Strategic Context

- **taskwright only**: Simple kanban board with task-focused filters
- **require-kit installed**: Enhanced kanban with epic/feature columns and filters
- **Adaptive output**: Display adapts to what's installed

## Changes Required

### 1. Add Feature Detection

```bash
# At top of task-status command
REQUIRE_KIT_INSTALLED=false
if [ -f "$HOME/.agentecflow/require-kit.marker" ]; then
  REQUIRE_KIT_INSTALLED=true
fi
```

### 2. Conditional Filter Parsing

```bash
# Parse filters
while [[ $# -gt 0 ]]; do
  case $1 in
    --status)
      STATUS_FILTER="$2"
      shift
      ;;
    --priority)
      PRIORITY_FILTER="$2"
      shift
      ;;
    --complexity)
      COMPLEXITY_FILTER="$2"
      shift
      ;;
    --parent)
      PARENT_FILTER="$2"
      shift
      ;;
    --epic)
      if [ "$REQUIRE_KIT_INSTALLED" = true ]; then
        EPIC_FILTER="$2"
        shift
      else
        echo "⚠️  Warning: Epic filtering requires require-kit"
        echo "   Install: https://github.com/you/require-kit"
        exit 1
      fi
      ;;
    --feature)
      if [ "$REQUIRE_KIT_INSTALLED" = true ]; then
        FEATURE_FILTER="$2"
        shift
      else
        echo "⚠️  Warning: Feature filtering requires require-kit"
        exit 1
      fi
      ;;
    --requirements)
      if [ "$REQUIRE_KIT_INSTALLED" = true ]; then
        REQ_FILTER="$2"
        shift
      else
        echo "⚠️  Warning: Requirements filtering requires require-kit"
        exit 1
      fi
      ;;
  esac
  shift
done
```

### 3. Conditional Kanban Output

```bash
# Display kanban board
show_kanban() {
  # Always show these columns
  printf "%-10s %-40s %-12s %-10s %-10s" \
    "Task ID" "Title" "Status" "Priority" "Complexity"

  # Conditionally add epic/feature columns
  if [ "$REQUIRE_KIT_INSTALLED" = true ]; then
    printf " %-12s %-12s" "Epic" "Feature"
  fi

  printf "\n"
  printf "%s\n" "----------------------------------------..."

  # For each task
  for task in tasks/*/*.md; do
    ID=$(grep "^id:" "$task" | cut -d: -f2 | xargs)
    TITLE=$(grep "^title:" "$task" | cut -d: -f2 | xargs)
    STATUS=$(grep "^status:" "$task" | cut -d: -f2 | xargs)
    PRIORITY=$(grep "^priority:" "$task" | cut -d: -f2 | xargs)
    COMPLEXITY=$(grep "^complexity:" "$task" | cut -d: -f2 | xargs)

    # Apply basic filters
    [[ -n "$STATUS_FILTER" && "$STATUS" != "$STATUS_FILTER" ]] && continue
    [[ -n "$PRIORITY_FILTER" && "$PRIORITY" != "$PRIORITY_FILTER" ]] && continue

    # Apply requirements filters (if require-kit installed)
    if [ "$REQUIRE_KIT_INSTALLED" = true ]; then
      EPIC=$(grep "^epic:" "$task" | cut -d: -f2 | xargs)
      FEATURE=$(grep "^feature:" "$task" | cut -d: -f2 | xargs)

      [[ -n "$EPIC_FILTER" && "$EPIC" != "$EPIC_FILTER" ]] && continue
      [[ -n "$FEATURE_FILTER" && "$FEATURE" != "$FEATURE_FILTER" ]] && continue
    fi

    # Display row
    printf "%-10s %-40s %-12s %-10s %-10s" \
      "$ID" "$TITLE" "$STATUS" "$PRIORITY" "$COMPLEXITY"

    if [ "$REQUIRE_KIT_INSTALLED" = true ]; then
      printf " %-12s %-12s" "${EPIC:-none}" "${FEATURE:-none}"
    fi

    printf "\n"
  done
}
```

### 4. Conditional Help Text

```bash
show_help() {
  cat << EOF
Usage: /task-status [options]

Filters:
  --status backlog|in_progress|in_review|blocked|completed
  --priority high|medium|low
  --complexity N
  --parent TASK-XXX         Show subtasks of TASK-XXX

EOF

  if [ "$REQUIRE_KIT_INSTALLED" = true ]; then
    cat << EOF
Requirements Management Filters (require-kit):
  --epic EPIC-XXX           Show tasks for specific epic
  --feature FEAT-XXX        Show tasks for specific feature
  --requirements REQ-XXX    Show tasks linked to requirement

EOF
  fi

  cat << EOF
Views:
  --view=kanban             Kanban board (default)
  --view=list               Simple list
  --view=complexity         Complexity distribution
  --view=hierarchy          Parent/subtask tree

Examples:
  /task-status
  /task-status --status in_progress
  /task-status --priority high
  /task-status --parent TASK-001
EOF

  if [ "$REQUIRE_KIT_INSTALLED" = true ]; then
    cat << EOF
  /task-status --epic EPIC-001
  /task-status --feature FEAT-005 --status in_progress
EOF
  fi
}
```

### 5. Conditional View Types

```bash
# Keep all views
case $VIEW in
  kanban)
    show_kanban  # Adapts columns based on require-kit
    ;;
  list)
    show_list    # Simple list, always available
    ;;
  complexity)
    show_complexity_distribution  # Always available
    ;;
  hierarchy)
    show_hierarchy  # Parent/subtask tree, always available
    ;;
  epic-rollup)
    if [ "$REQUIRE_KIT_INSTALLED" = true ]; then
      show_epic_rollup
    else
      echo "⚠️  Epic rollup requires require-kit"
      exit 1
    fi
    ;;
  feature-progress)
    if [ "$REQUIRE_KIT_INSTALLED" = true ]; then
      show_feature_progress
    else
      echo "⚠️  Feature progress requires require-kit"
      exit 1
    fi
    ;;
esac
```

## Implementation Steps

### 1. Backup Current File

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/taskwright/.conductor/kuwait
cp installer/global/commands/task-status.md installer/global/commands/task-status.md.backup
```

### 2. Add Feature Detection

Add require-kit marker check at command start.

### 3. Update Filter Parsing

- Keep all filter parsing
- Add warnings for epic/feature/requirements filters without require-kit

### 4. Update Kanban Display

- Conditionally add epic/feature columns
- Apply epic/feature filters only if require-kit installed

### 5. Update Help Text

- Show requirements filters section only if require-kit installed
- Update examples conditionally

### 6. Update View Logic

- Keep all views
- Show warnings for epic-rollup/feature-progress without require-kit

## Validation Checklist

### With taskwright Only
- [ ] `/task-status` shows basic kanban (no epic/feature columns)
- [ ] `--status` filter works
- [ ] `--priority` filter works
- [ ] `--complexity` filter works
- [ ] `--parent` filter works
- [ ] `--epic` shows warning and exits
- [ ] `--feature` shows warning and exits
- [ ] Help text excludes epic/feature filters

### With Both Installed
- [ ] `/task-status` shows enhanced kanban (with epic/feature columns)
- [ ] All basic filters work
- [ ] `--epic EPIC-001` filters correctly
- [ ] `--feature FEAT-005` filters correctly
- [ ] `--view=epic-rollup` works
- [ ] `--view=feature-progress` works
- [ ] Help text includes epic/feature filters

### Views (Always Available)
- [ ] `--view=list` works (taskwright only)
- [ ] `--view=complexity` works (taskwright only)
- [ ] `--view=hierarchy` works (taskwright only)

## Testing

```bash
# Test taskwright only scenario
rm ~/.agentecflow/require-kit.marker

cd /tmp/test-taskwright
/task-create "Task 1"
/task-create "Task 2" priority:high

/task-status
# Should show:
# - Basic columns (ID, Title, Status, Priority, Complexity)
# - NO Epic or Feature columns
# - 2 tasks

/task-status --priority high
# Should show only Task 2

/task-status --epic EPIC-001
# Should show: "⚠️  Warning: Epic filtering requires require-kit"

/task-status --help
# Should NOT show epic/feature filter options

# Test with both installed
touch ~/.agentecflow/require-kit.marker

/task-create "Task 3" epic:EPIC-001
/task-create "Task 4" epic:EPIC-001 feature:FEAT-005

/task-status
# Should show:
# - All columns including Epic and Feature
# - 4 tasks with epic/feature values

/task-status --epic EPIC-001
# Should show only Task 3 and Task 4

/task-status --feature FEAT-005
# Should show only Task 4

/task-status --help
# SHOULD show epic/feature filter options
```

## Documentation Updates

### In task-status.md

Add section:
```markdown
## Requirements Management Integration

When require-kit is installed, task-status provides enhanced filtering:

**Additional Columns**:
- Epic: Shows linked epic (if any)
- Feature: Shows linked feature (if any)

**Additional Filters**:
- `--epic EPIC-XXX`: Filter tasks by epic
- `--feature FEAT-XXX`: Filter tasks by feature
- `--requirements REQ-XXX`: Filter tasks by requirement

**Additional Views**:
- `--view=epic-rollup`: Show progress by epic
- `--view=feature-progress`: Show progress by feature

Without require-kit, task-status provides standard task filtering.

Install require-kit: https://github.com/you/require-kit
```

## Acceptance Criteria

- [ ] task-status.md updated with conditional logic
- [ ] Feature detection implemented
- [ ] Filter parsing includes warnings
- [ ] Kanban output adapts to installed packages
- [ ] Help text adapts to installed packages
- [ ] All basic views always work
- [ ] Requirements views conditional
- [ ] Works with taskwright only (simple output)
- [ ] Works with both installed (enhanced output)
- [ ] Tests pass for both scenarios

## Related Tasks

- **DEPENDS ON**: TASK-012 (Shared Installation Strategy)
- **SUPERSEDES**: TASK-006 (old removal approach)
- **SIMILAR TO**: TASK-004-REV, TASK-005-REV

## Estimated Time

1.5 hours (same as original, conditional logic adds minimal overhead)

## Notes

- Simpler than task-work.md modifications
- Focus on output formatting and filter availability
- Keep hierarchy view (parent/subtask) - that's taskwright feature
- Epic-rollup/feature-progress are require-kit exclusive views
- **IMPORTANT**: Old TASK-006 should be marked as superseded/cancelled

---

## ✅ TASK CLOSED - Superseded by TASK-012

**Closure Date**: 2025-10-28
**Closure Reason**: Superseded by TASK-012 bidirectional integration implementation
**Git Commit**: d85f17a

### What Was Implemented

While TASK-012 focused primarily on task-create and task-work commands, the feature detection library it provides (`installer/global/lib/feature_detection.py`) can be used to implement conditional filtering in task-status when needed.

### Current Status

task-status.md does not currently require modification because:
1. It primarily displays task frontmatter fields (which always exist)
2. Epic/feature filters can simply return empty results if those fields are not populated
3. The graceful degradation happens naturally through empty field values

### If Future Implementation Needed

The feature detection library is available:
```python
from installer.global.lib.feature_detection import supports_epics

if supports_epics():
    # Show epic/feature columns
else:
    # Show basic kanban only
```

### Why This Task Is Low Priority / Obsolete

TASK-012 established the bidirectional integration architecture. The task-status command works correctly in both scenarios:

- **taskwright only**: Shows tasks with empty epic/feature fields (displays as "none")
- **Both installed**: Shows tasks with populated epic/feature fields

No breaking functionality exists in the current implementation, making this task obsolete for now.

### If Required Later

If enhanced epic/feature filtering becomes necessary:
1. Use `installer/global/lib/feature_detection.py`
2. Add conditional help text (show epic/feature filters only if require-kit installed)
3. Add user-friendly messages when filtering by epic/feature without require-kit

**See**: `tasks/backlog/TASK-012-shared-installation-strategy.md` for the bidirectional integration implementation that supersedes this task.
