---
id: TASK-010
title: "Update Manifest and Configuration"
created: 2025-10-27
status: completed
priority: high
complexity: 2
parent_task: none
subtasks: []
estimated_hours: 1
actual_hours: 1
completed_date: 2025-11-01
quality_score: 9.5
architectural_score: 92
plan_audit_score: 95
requirements_met: 9/9
files_modified: 1
lines_changed: 20
test_iterations: 1
rework_cycles: 0
---

# TASK-010: Update Manifest and Configuration

## Description

Update manifest.json and any configuration files to reflect taskwright's focus on task workflow with quality gates, removing requirements management capabilities.

## Files to Update

### installer/global/manifest.json

**Current (likely)**:
```json
{
  "name": "agentecflow",
  "version": "1.0.0",
  "description": "Complete Agentecflow Implementation",
  "capabilities": [
    "requirements-engineering",
    "bdd-generation",
    "quality-gates",
    "state-tracking",
    "kanban-workflow",
    "task-management",
    "test-verification"
  ]
}
```

**Updated**:
```json
{
  "name": "taskwright",
  "version": "1.0.0",
  "description": "Lightweight AI-Assisted Development with Quality Gates",
  "capabilities": [
    "quality-gates",
    "state-tracking",
    "kanban-workflow",
    "task-management",
    "test-verification",
    "architectural-review",
    "test-enforcement"
  ]
}
```

### Changes Required

**Remove capabilities**:
- `requirements-engineering`
- `bdd-generation`
- Any epic/feature management capabilities

**Add capabilities** (if not present):
- `architectural-review` (Phase 2.5)
- `test-enforcement` (Phase 4.5)

**Update metadata**:
- Name: "taskwright" (not "agentecflow")
- Description: Emphasize lightweight + quality gates
- Version: Start at 1.0.0

## Other Configuration Files

### .claude/config.json (if exists)

Update any references to:
- Epic/feature directories
- Requirements directories
- BDD directories

### settings.json (template-level)

**Remove** (if present in any template):
```json
{
  "requirements_dir": "docs/requirements",
  "bdd_dir": "docs/bdd",
  "epics_dir": "docs/epics",
  "features_dir": "docs/features"
}
```

**Keep**:
```json
{
  "tasks_dir": "tasks",
  "stack": "react",  // or appropriate stack
  "quality_gates": {
    "architectural_review": true,
    "test_enforcement": true,
    "min_coverage": 80
  }
}
```

## Implementation Steps

### 1. Locate Configuration Files

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/taskwright/.conductor/kuwait

# Find all config files
find . -name "manifest.json"
find . -name "config.json"
find . -name "settings.json"
```

### 2. Update manifest.json

```bash
# Edit installer/global/manifest.json
# Update name, description, capabilities as shown above
```

### 3. Check Template Settings

```bash
# Check each template for settings.json
for template in installer/global/templates/*/; do
  if [ -f "$template/settings.json" ]; then
    echo "Found settings in $template"
  fi
done
```

### 4. Update Template Settings (if any)

Remove requirements-related paths, keep task-focused config.

### 5. Verify JSON Syntax

```bash
# Validate JSON syntax
for file in $(find . -name "manifest.json" -o -name "settings.json"); do
  python3 -m json.tool "$file" > /dev/null && echo "✓ $file valid" || echo "✗ $file invalid"
done
```

## Validation Checklist

### manifest.json
- [ ] Name updated to "taskwright"
- [ ] Description emphasizes quality gates
- [ ] "requirements-engineering" removed
- [ ] "bdd-generation" removed
- [ ] "quality-gates" present
- [ ] "architectural-review" added
- [ ] "test-enforcement" added

### Template settings
- [ ] No requirements_dir references
- [ ] No bdd_dir references
- [ ] No epics_dir references
- [ ] No features_dir references
- [ ] tasks_dir present
- [ ] quality_gates config present

### JSON Validity
- [ ] All JSON files valid syntax
- [ ] No parse errors

## Acceptance Criteria

- [ ] manifest.json updated
- [ ] Name changed to "taskwright"
- [ ] Capabilities list reflects lite workflow
- [ ] Template settings cleaned (if any exist)
- [ ] All JSON files have valid syntax
- [ ] No requirements-related configuration remains

## Testing

```bash
# Test manifest loading
python3 -c "
import json
with open('installer/global/manifest.json') as f:
    manifest = json.load(f)
    print(f\"Name: {manifest['name']}\")
    print(f\"Capabilities: {', '.join(manifest['capabilities'])}\")
    assert 'requirements-engineering' not in manifest['capabilities']
    assert 'quality-gates' in manifest['capabilities']
    print('✅ Manifest valid')
"
```

## Related Tasks

- TASK-002: Remove requirements management commands
- TASK-009: Remove requirements directory structure

## Estimated Time

1 hour

## Notes

- Keep version at 1.0.0 for initial release
- Capabilities list should match actual functionality
- Consider adding homepage/repository URLs to manifest
- Document capability changes in CHANGELOG
