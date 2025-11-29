---
id: TASK-292E
legacy_id: TASK-038
title: Rename dotnet-microservice template to dotnet-fastendpoints
created: 2025-11-03
completed: 2025-11-03
priority: medium
status: completed
tags: [templates, dotnet, refactoring]
---

# TASK-292E: Rename dotnet-microservice template to dotnet-fastendpoints

## Overview

The current `dotnet-microservice` template is opinionated towards FastEndpoints with ErrorOr/Result patterns. This should be renamed to `dotnet-fastendpoints` to be more explicit about the technology stack and distinguish it from other .NET API approaches.

## Current State

**Template Location**: `installer/global/templates/dotnet-microservice/`

**Current Features**:
- FastEndpoints framework
- REPR (Request-Endpoint-Response) pattern
- ErrorOr/Result pattern for error handling
- Vertical slice architecture
- Domain-driven design patterns

## Acceptance Criteria

- [ ] Rename directory: `dotnet-microservice` → `dotnet-fastendpoints`
- [ ] Update template.json to reflect new name
- [ ] Update all documentation references to use new name
- [ ] Update installer scripts to recognize new template name
- [ ] Maintain backward compatibility or provide migration notice
- [ ] Update CLAUDE.md and README.md with new template name
- [ ] Update template selection guide

## Files to Update

### 1. Rename Template Directory
- [ ] Rename: `installer/global/templates/dotnet-microservice/` → `dotnet-fastendpoints/`
- [ ] Update `template.json` inside the renamed directory

### 2. Installer Scripts (install.sh)
Update these lines in `installer/scripts/install.sh`:
- [ ] Line ~249: `mkdir` command - change `dotnet-microservice` to `dotnet-fastendpoints`
- [ ] Line ~468: `stack-agents` mkdir - change `dotnet-microservice` to `dotnet-fastendpoints`
- [ ] Line ~502: Template list display - update description and name
- [ ] Line ~509: Example command - change `dotnet-microservice` to `dotnet-fastendpoints`
- [ ] Line ~570: Another example - change `dotnet-microservice` to `dotnet-fastendpoints`
- [ ] Line ~1089: Template case statement - update case name
- [ ] Line ~1117: Example command - change `dotnet-microservice` to `dotnet-fastendpoints`

### 3. CLI Commands (taskwright-init)
- [ ] Line ~476-520 in install.sh: Update `taskwright-init` help text
- [ ] Change template description from "dotnet-microservice" to "dotnet-fastendpoints"
- [ ] Update description: ".NET microservice with FastEndpoints"  → ".NET API with FastEndpoints + REPR pattern"

### 4. Documentation Updates
- [ ] `README.md` - Update template table (line ~120-140)
- [ ] `CLAUDE.md` - Update template list and descriptions
- [ ] `docs/guides/maui-template-selection.md` - Check if referenced
- [ ] `docs/research/dotnet-api-templates-research-2025.md` - Update references

### 5. Template Messages
Update post-installation messages shown to users:
- [ ] Install script success message (line ~500-520)
- [ ] `taskwright doctor` command output
- [ ] Any "Next Steps" sections

### 6. Stack-Specific Agent References
Search for agents that reference "dotnet-microservice":
- [ ] Check `installer/global/agents/*.md` files
- [ ] Update any hardcoded template references

## Implementation Checklist

Following the template creation guide principles:

**Step 1**: Rename Directory
```bash
cd installer/global/templates/
mv dotnet-microservice dotnet-fastendpoints
```

**Step 2**: Update template.json
```json
{
  "name": "dotnet-fastendpoints",
  "description": ".NET API with FastEndpoints, REPR pattern, and ErrorOr"
}
```

**Step 3**: Update All install.sh References
- Search and replace all occurrences
- Test each template directory path
- Verify mkdir commands create correct paths

**Step 4**: Update User-Facing Text
- Update all help text
- Update all example commands
- Update all descriptions

**Step 5**: Verify Installation
```bash
./installer/scripts/install.sh
taskwright-init --help  # Should show dotnet-fastendpoints
taskwright doctor      # Should list dotnet-fastendpoints
```

## Impact

- **Breaking Change**: No (can support both names temporarily with symlink)
- **Migration Path**:
  ```bash
  # Optional: Create symlink for backward compatibility
  ln -s dotnet-fastendpoints dotnet-microservice
  ```
- **Documentation**: Update all references
- **User Communication**: Add note to CHANGELOG about rename

## Related

- TASK-FBC2: Create dotnet-aspnetcontroller template
- TASK-7F18: Create dotnet-minimalapi template
- See: `docs/guides/template-creation-workflow.md` for template creation process
