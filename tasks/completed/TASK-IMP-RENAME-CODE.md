---
id: TASK-IMP-RENAME-CODE
title: "Update Python Code and Templates for GuardKit Rename"
status: completed
task_type: implementation
created: 2025-12-03T10:35:00Z
updated: 2025-12-03T10:47:00Z
completed: 2025-12-03T10:50:00Z
priority: high
tags: [rename, code, templates, guardkit]
complexity: 5
parent: TASK-REV-803B
dependencies: [TASK-IMP-RENAME-INFRA]
duration_minutes: 15
files_modified: 2
occurrences_updated: 17
---

# Implementation Task: Update Code and Templates

## Context

Part of the GuardKit → GuardKit rename initiative. This task updates Python code, templates, and related files.

**Parent Review**: TASK-REV-803B
**GitHub Rename**: ✅ Complete (https://github.com/guardkit/guardkit)

## Scope

### 1. Python Code Updates

| File | Occurrences | Notes |
|------|-------------|-------|
| `installer/global/lib/constants.py` | 1 | RequireKit config |
| `installer/global/commands/lib/distribution_helpers.py` | 16 | Package distribution |
| `installer/global/commands/lib/template_packager.py` | 4 | Template packaging |
| `installer/global/commands/lib/agent_discovery.py` | 1 | Agent discovery |
| `installer/global/commands/lib/template_create_orchestrator.py` | 4 | Template creation |
| `installer/global/commands/lib/template_init/ai_generator.py` | 2 | AI generation |
| `scripts/audit_requirekit.py` | 3 | Audit script |
| `installer/global/commands/agent-enhance.py` | 3 | Agent enhancement |
| `installer/global/commands/agent-format.py` | 1 | Agent formatting |
| `installer/global/commands/agent-validate.py` | 2 | Agent validation |

### 2. Command Specification Updates

| File | Occurrences | Notes |
|------|-------------|-------|
| `installer/global/commands/task-create.md` | 5 | Task creation spec |
| `installer/global/commands/task-work.md` | 11 | Task work spec |
| `installer/global/commands/task-status.md` | 2 | Task status spec |
| `installer/global/commands/template-create.md` | 9 | Template creation |
| `installer/global/commands/template-init.md` | 5 | Template init |
| `installer/global/commands/template-qa.md` | 1 | Template QA |
| `installer/global/commands/agent-enhance.md` | 1 | Agent enhance |
| `installer/global/commands/agent-validate.md` | 2 | Agent validate |

### 3. Template Updates

**Template Manifests**:
- `installer/global/templates/fastapi-python/manifest.json`
- `installer/global/templates/nextjs-fullstack/manifest.json`
- `installer/global/templates/react-fastapi-monorepo/manifest.json`

**Template READMEs**:
- `installer/global/templates/fastapi-python/README.md`
- `installer/global/templates/nextjs-fullstack/README.md`
- `installer/global/templates/react-fastapi-monorepo/README.md`

**Template CLAUDE.md**:
- `installer/global/templates/nextjs-fullstack/CLAUDE.md`

**Template Validation Reports**:
- `installer/global/templates/react-typescript/validation-report.md`
- `installer/global/templates/react-fastapi-monorepo/validation-report.md`

### 4. Agent Updates

| File | Occurrences | Notes |
|------|-------------|-------|
| `installer/global/agents/task-manager.md` | 5 | Task manager agent |
| `installer/global/agents/agent-content-enhancer.md` | 4 | Content enhancer |

### 5. Solution File Rename

| Current | New |
|---------|-----|
| `guardkit.sln` | `guardkit.sln` |

## Acceptance Criteria

- [x] All Python code references updated
- [x] All command specs updated
- [x] All template manifests updated
- [x] All template READMEs updated
- [x] Agent files updated
- [x] Solution file renamed (N/A - no .sln file in this worktree)
- [x] No "taskwright" in installer/global/**/* (verified)
- [x] Python imports still work correctly (tested)

## Testing

```bash
# Test Python imports
cd ~/.agentecflow/commands
python3 -c "from lib.distribution_helpers import *; print('OK')"

# Test agent discovery
python3 -c "from lib.agent_discovery import *; print('OK')"

# Verify no remaining references
grep -ri "guardkit" installer/global/ --include="*.py" --include="*.md" --include="*.json"
```

## Estimated Effort

1-2 hours

---

## Completion Report

### Summary
**Task**: Update Python Code and Templates for GuardKit Rename
**Completed**: 2025-12-03T10:50:00Z
**Duration**: 15 minutes
**Final Status**: ✅ COMPLETED

### Deliverables
- Files modified: 2
  - `installer/global/commands/lib/distribution_helpers.py`
  - `installer/global/lib/codebase_analyzer/prompt_builder.py`
- Occurrences updated: 17
  - distribution_helpers.py: 16 references changed
  - prompt_builder.py: 1 reference changed
- All references from "taskwright" to "guardkit" updated

### Quality Metrics
- All acceptance criteria met: ✅ 8/8
- Python imports verified: ✅
- Zero remaining "taskwright" references: ✅
- No breaking changes introduced: ✅

### Changes Made
1. **distribution_helpers.py**: Updated all CLI command references in:
   - Usage instructions templates
   - Installation verification scripts
   - Sharing guide documentation
   - Package distribution examples

2. **prompt_builder.py**: Updated template scaffolding documentation

### Testing Results
```bash
✓ Python imports (distribution_helpers) - OK
✓ Python imports (agent_discovery) - OK
✓ No remaining "taskwright" references - Verified
```

### Lessons Learned
- **What went well**: The task was already mostly complete from previous commits (95905d9). Only 2 files needed updates.
- **Efficiency**: Systematic search-and-replace approach identified all remaining references quickly.
- **Verification**: Automated testing of Python imports ensured no breaking changes.

### Related Commits
- d108b21: Complete GuardKit rename: Update remaining Taskwright references
- e807efc: Move TASK-IMP-RENAME-CODE to in_review
- ccfb664: Update task status to in_review
