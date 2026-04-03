---
id: TASK-RBT-001
title: Fix nats-asyncio-service metadata
status: completed
created: 2026-04-03T22:00:00Z
completed: 2026-04-03T22:30:00Z
priority: high
tags: [template, nats-asyncio-service, metadata, dark-factory]
parent_review: TASK-REV-DF07
feature_id: FEAT-RBT
implementation_mode: task-work
wave: 1
complexity: 3
completed_location: tasks/completed/TASK-RBT-001/
---

# Task: Fix nats-asyncio-service metadata

## Description

Fix minor metadata issues in the nats-asyncio-service template at `~/.agentecflow/templates/nats-asyncio-service/` before it is copied to the builtin directory.

## Changes Required

### manifest.json

1. Remove `source_project` field (hardcoded absolute path)
2. Set `placeholders.Author.default_value` to `null` (currently "Richard Woollcott")
3. Consider reducing `complexity` from 10 to 7-8 (the architecture is well-defined)

### settings.json

1. Fix `test_location` from `"adjacent"` to `"separate"` (tests are in a separate `tests/` directory)
2. Fix layer_mappings directory paths from PascalCase to snake_case matching actual template structure:
   - `"src/Entry Point"` -> use actual package structure with placeholder (e.g., `"{{project_name}}/"`)
   - `"src/Application"` -> `"{{project_name}}/"`
   - `"src/Configuration"` -> `"{{project_name}}/config.py"`
   - `"src/Schemas"` -> `"{{project_name}}/schemas/"`
   - `"src/Handlers"` -> `"{{project_name}}/handlers/"`
   - `"src/Services"` -> `"{{project_name}}/services/"`
3. Fix namespace_pattern entries to use snake_case (e.g., `"{{project_name}}.entry point"` -> `"{{project_name}}"`)

## Acceptance Criteria

- [x] No hardcoded author paths in manifest.json
- [x] Author placeholder default is null
- [x] Layer mappings use Python-convention directory paths
- [x] test_location is "separate"
- [x] All changes are in the user-local template (will be copied in TASK-RBT-003)

## Implementation Summary

All changes made to `~/.agentecflow/templates/nats-asyncio-service/`:

**manifest.json:**
- Removed `source_project` field (was hardcoded to `/Users/richardwoollcott/Projects/...`)
- Set `Author.default_value` to `null` (was "Richard Woollcott")
- Reduced `complexity` from 10 to 7

**settings.json:**
- Changed `test_location` from `"adjacent"` to `"separate"`
- Fixed all 6 layer_mappings directories from PascalCase `src/...` to `{{project_name}}/...` paths
- Fixed namespace_patterns to remove spaces (e.g., `"entry point"` → clean Python module names)

## References

- Review report: `.claude/reviews/TASK-REV-DF07-review-report.md`
- Template location: `~/.agentecflow/templates/nats-asyncio-service/`
- Template spec: `docs/research/dark_factory/template-spec-nats-asyncio-service.md`
