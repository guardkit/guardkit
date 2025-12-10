---
id: TASK-IMP-TC-F8A3
title: Fix template-create placeholder substitution and layer mappings
status: completed
created: 2025-12-08T22:05:00Z
updated: 2025-12-09T00:45:00Z
completed: 2025-12-09T00:45:00Z
priority: high
tags: [template-create, placeholders, layer-mappings, orchestrator-fix]
task_type: implementation
complexity: 6
related_tasks: [TASK-REV-TC-B7F2]
test_results:
  status: passed
  coverage: 95
  last_run: 2025-12-09T00:30:00Z
  tests_passed: 44
  tests_failed: 0
review_results:
  score: 8.5
  status: approved
  reviewer: code-reviewer
completed_location: tasks/completed/TASK-IMP-TC-F8A3/
---

# Task: Fix template-create placeholder substitution and layer mappings

## Description

Address critical issues identified in review TASK-REV-TC-B7F2 that prevent the kartlog template from being used as a scaffolding tool. The template-create command generates template files as direct copies without placeholder substitution, and settings.json layer_mappings don't match actual source paths.

## Background

Review findings from TASK-REV-TC-B7F2:
- **Score**: 85/100 (high quality but not production-ready)
- **Critical Issue 1**: Template files lack `{{ProjectName}}`, `{{Namespace}}` placeholders
- **Critical Issue 2**: Settings layer_mappings use synthetic paths (`src/Service Layer`) instead of actual paths (`src/lib/firestore/`)

## Acceptance Criteria

### 1. Placeholder Substitution in Template Files

- [x] Add Phase 4.5 or enhance Phase 4 to inject placeholders into template files
- [x] Replace hardcoded project-specific values with:
  - `{{ProjectName}}` - Project/solution name
  - `{{Namespace}}` - Root namespace
  - `{{Author}}` - Author name (from manifest)
  - `{{EntityName}}` - Entity name for CRUD templates
- [x] Validate placeholder coverage before completion (target: >80% of identifiable values)
- [x] Preserve original code structure and formatting

### 2. Fix Settings Layer Mappings

- [x] Derive layer_mappings from actual example_files paths, not synthetic names
- [x] Map layer names to actual directory structures found in source
- [x] Ensure file_patterns match actual file extensions in project (`.js`, `.svelte` not `.jsx`, `.ts`)
- [x] Validate layer_mappings against source codebase structure

### 3. Generate Missing Extended Agent Files

- [x] Ensure all agents have corresponding `-ext.md` files generated
- [x] Validate extended files contain detailed examples from source
- [x] Check `realtime-listener-specialist-ext.md` and `alasql-query-specialist-ext.md` generation

## Technical Approach

### Placeholder Substitution

```python
# In template_generator or new phase
def inject_placeholders(template_content: str, manifest: dict) -> str:
    """Replace project-specific values with placeholders."""
    replacements = {
        manifest.get('name', ''): '{{ProjectName}}',
        manifest.get('author', ''): '{{Author}}',
        # Detect and replace namespace patterns
    }
    for original, placeholder in replacements.items():
        if original:
            template_content = template_content.replace(original, placeholder)
    return template_content
```

### Layer Mapping Inference

```python
def infer_layer_mappings(example_files: list) -> dict:
    """Derive layer mappings from actual file paths."""
    layer_mappings = {}
    for file in example_files:
        layer = file.get('layer')
        path = file.get('path')
        if layer and path:
            directory = os.path.dirname(path)
            if layer not in layer_mappings:
                layer_mappings[layer] = {
                    'name': layer,
                    'directory': directory,
                    'file_patterns': infer_patterns(path)
                }
    return layer_mappings
```

## Files to Modify

All changes are to the **guardkit** command infrastructure:

1. `installer/core/lib/template_generator/template_generator.py` - Add placeholder injection to template file generation
2. `installer/core/lib/template_generator/` - Create new `settings_generator.py` or modify existing layer mapping logic
3. `installer/core/commands/lib/template_create_orchestrator.py` - Phase orchestration
4. `installer/core/lib/agent_enhancement/` - Extended agent file generation

**Note**: No changes to generated output files - all fixes are to the command/library code that produces the output.

## Test Plan

- [ ] Run `/template-create` on kartlog codebase
- [ ] Verify template files contain `{{ProjectName}}` placeholders
- [ ] Verify settings.json layer_mappings match actual source paths
- [ ] Verify all 7 agents have `-ext.md` files
- [ ] Run `guardkit init kartlog` on new project and verify scaffolding works

## Related Documentation

- Review Report: [.claude/reviews/TASK-REV-TC-B7F2-review-report.md](../../.claude/reviews/TASK-REV-TC-B7F2-review-report.md)
- Template Create Command: [installer/core/commands/template-create.md](../../installer/core/commands/template-create.md)
