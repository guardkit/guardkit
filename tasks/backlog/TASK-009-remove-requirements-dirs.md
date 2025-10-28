---
id: TASK-009
title: "Remove Requirements Directory Structure"
created: 2025-10-27
status: backlog
priority: medium
complexity: 2
parent_task: none
subtasks: []
estimated_hours: 1
---

# TASK-009: Remove Requirements Directory Structure

## Description

Remove epic/feature/requirements directory structures from documentation and any sample/template files, keeping only task-focused directories.

## Directories to Remove

### From docs/
```bash
❌ docs/epics/
❌ docs/features/
❌ docs/requirements/
❌ docs/bdd/
❌ docs/state/  (if requirements-related)
```

### Keep in docs/
```bash
✅ docs/adr/           # Architecture Decision Records
✅ docs/guides/        # Workflow guides
✅ docs/workflows/     # Workflow documentation
✅ docs/patterns/      # Design patterns
✅ docs/testing/       # Testing guides
```

## Files to Check/Update

### installer/scripts/install.sh

**Remove directory creation**:
```bash
# DELETE:
mkdir -p docs/epics/{active,completed,cancelled}
mkdir -p docs/features/{active,in_progress,completed}
mkdir -p docs/requirements/{draft,approved,implemented}
mkdir -p docs/bdd
mkdir -p docs/state
```

**Keep**:
```bash
mkdir -p tasks/{backlog,in_progress,in_review,blocked,completed}
mkdir -p .claude/{agents,commands,instructions}
mkdir -p docs/adr
```

### installer/scripts/init-project.sh

**Remove**:
- Requirements template creation
- BDD template creation
- Epic/feature template creation

**Keep**:
- Task template creation
- Stack-specific setup
- Quality gate configuration

## Implementation Steps

### 1. Check What Exists

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/taskwright/.conductor/kuwait

# Check if requirements directories exist
ls -la docs/epics 2>/dev/null && echo "epics exists"
ls -la docs/features 2>/dev/null && echo "features exists"
ls -la docs/requirements 2>/dev/null && echo "requirements exists"
ls -la docs/bdd 2>/dev/null && echo "bdd exists"
```

### 2. Remove Directories (if they exist)

```bash
# Remove requirements directories
rm -rf docs/epics/
rm -rf docs/features/
rm -rf docs/requirements/
rm -rf docs/bdd/

# Note: Only remove docs/state if it's requirements-related
# Keep if it's task-related state
```

### 3. Update install.sh

```bash
# Edit installer/scripts/install.sh
# Remove mkdir commands for epic/feature/requirements dirs
```

### 4. Update init-project.sh

```bash
# Edit installer/scripts/init-project.sh
# Remove template creation for requirements features
```

### 5. Verify Task Directories Remain

```bash
# Ensure task directories are still created
ls -la tasks/
# Should see: backlog/, in_progress/, in_review/, blocked/, completed/
```

## Validation Checklist

### Directories Removed
- [ ] docs/epics/ removed or never existed
- [ ] docs/features/ removed or never existed
- [ ] docs/requirements/ removed or never existed
- [ ] docs/bdd/ removed or never existed

### Scripts Updated
- [ ] install.sh updated (no epic/feature/requirements mkdir)
- [ ] init-project.sh updated (no requirements templates)
- [ ] Task directory creation retained in scripts

### Directories Retained
- [ ] tasks/ structure intact
- [ ] docs/adr/ retained (if exists)
- [ ] docs/guides/ retained (if exists)
- [ ] docs/workflows/ retained (if exists)

## Acceptance Criteria

- [ ] No epic/feature/requirements directories in filesystem
- [ ] install.sh doesn't create requirements directories
- [ ] init-project.sh doesn't create requirements templates
- [ ] Task directory structure intact
- [ ] Documentation directories (adr, guides) intact

## Testing

```bash
# Test install script
cd /tmp/test-install
bash /path/to/installer/scripts/install.sh

# Verify structure
ls docs/
# Should NOT see: epics/, features/, requirements/, bdd/
# Should see: adr/ (or whatever docs are kept)

ls tasks/
# Should see: backlog/, in_progress/, in_review/, blocked/, completed/
```

## Related Tasks

- TASK-002: Remove requirements management commands
- TASK-010: Update installer manifest

## Estimated Time

1 hour

## Notes

- Some directories may not exist yet - that's fine
- Focus on scripts that CREATE these directories
- Don't accidentally remove task-related state
- Verify task directories remain intact after changes
