---
id: TASK-002
title: "Remove Requirements Management Commands"
created: 2025-10-27
status: backlog
priority: high
complexity: 3
parent_task: none
subtasks: []
estimated_hours: 2
---

# TASK-002: Remove Requirements Management Commands

## Description

Remove all commands related to requirements management (EARS, BDD, Epic/Feature hierarchy) from taskwright repository, keeping only task-focused workflow commands.

## Context

Taskwright is the "lite" version (formerly Agentecflow Lite) focusing on task workflow with quality gates. Requirements management features (EARS, BDD, epics, features) are being removed to reduce complexity.

## Commands to Remove

### Requirements Management
```bash
❌ gather-requirements.md
❌ formalize-ears.md
❌ generate-bdd.md
```

### Epic/Feature Hierarchy
```bash
❌ epic-create.md
❌ epic-status.md
❌ epic-sync.md
❌ epic-generate-features.md
❌ feature-create.md
❌ feature-status.md
❌ feature-sync.md
❌ feature-generate-tasks.md
```

### PM Tool Integration & Visualization
```bash
❌ task-sync.md (PM tool synchronization)
❌ hierarchy-view.md
❌ portfolio-dashboard.md
```

## Commands to Keep

### Core Task Workflow
```bash
✅ task-create.md (needs modification)
✅ task-work.md (needs modification)
✅ task-complete.md
✅ task-status.md (needs modification)
✅ task-refine.md (needs simplification)
```

### Development Tools
```bash
✅ debug.md
✅ figma-to-react.md
✅ zeplin-to-maui.md
```

## Implementation Steps

### 1. Identify Command Files to Delete

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/taskwright/.conductor/kuwait

# Find all requirements-related commands
find installer/global/commands -name "*requirements*.md"
find installer/global/commands -name "*ears*.md"
find installer/global/commands -name "*bdd*.md"
find installer/global/commands -name "*epic*.md"
find installer/global/commands -name "*feature*.md"
find installer/global/commands -name "hierarchy*.md"
find installer/global/commands -name "portfolio*.md"
find installer/global/commands -name "*sync*.md"
```

### 2. Remove Command Files

```bash
# Remove requirements commands
rm -f installer/global/commands/gather-requirements.md
rm -f installer/global/commands/formalize-ears.md
rm -f installer/global/commands/generate-bdd.md

# Remove epic commands
rm -f installer/global/commands/epic-create.md
rm -f installer/global/commands/epic-status.md
rm -f installer/global/commands/epic-sync.md
rm -f installer/global/commands/epic-generate-features.md

# Remove feature commands
rm -f installer/global/commands/feature-create.md
rm -f installer/global/commands/feature-status.md
rm -f installer/global/commands/feature-sync.md
rm -f installer/global/commands/feature-generate-tasks.md

# Remove visualization/sync commands
rm -f installer/global/commands/hierarchy-view.md
rm -f installer/global/commands/portfolio-dashboard.md
rm -f installer/global/commands/task-sync.md
```

### 3. Verify Removal

```bash
# List remaining commands
ls installer/global/commands/*.md

# Expected files:
# - task-create.md
# - task-work.md
# - task-complete.md
# - task-status.md
# - task-refine.md
# - debug.md
# - figma-to-react.md
# - zeplin-to-maui.md
```

## Acceptance Criteria

- [ ] All 13 requirements-related command files removed
- [ ] 8 core task workflow and development commands remain
- [ ] No broken references in remaining commands
- [ ] Git status shows all deletions

## Related Tasks

- TASK-003: Remove requirements-related agents
- TASK-004: Modify task-create.md (remove epic/feature frontmatter)
- TASK-005: Modify task-work.md (remove requirements loading)
- TASK-006: Modify task-status.md (remove epic/feature filters)

## Estimated Time

2 hours

## Notes

- This is a pure deletion task - no modifications to remaining files
- File modifications will be handled in separate tasks (TASK-004, 005, 006)
- Keep documentation about what was removed for reference
