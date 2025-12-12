# Template-Init Rules Structure & Progressive Disclosure Updates

## Overview

This feature brings `/template-init` (greenfield template creation) into alignment with `/template-create` (brownfield) for rules structure and progressive disclosure support.

**Source**: TASK-REV-TI01 architectural review
**Report**: [.claude/reviews/TASK-REV-TI01-review-report.md](../../../.claude/reviews/TASK-REV-TI01-review-report.md)

## Problem Statement

The `/template-init` command creates templates from Q&A sessions but currently:
- Does not generate `.claude/rules/` directory structure
- Does not generate agent split files (`-ext.md`)
- Missing `--use-rules-structure` and `--no-rules-structure` flags
- Documentation not aligned with `/template-create`

This creates inconsistency: templates created via `/template-create` get 60-70% context reduction from rules structure, but greenfield templates from `/template-init` do not.

## Solution Approach

Add rules structure generation capability to `/template-init` while maintaining backward compatibility:
1. Add command flags for rules structure control
2. Add generation phase for rules structure
3. Generate agent split files during agent generation
4. Update documentation for feature parity

## Subtasks Summary

| ID | Title | Method | Wave | Complexity |
|----|-------|--------|------|------------|
| TASK-TI-001 | Add rules structure flags to template-init | direct | 1 | 3/10 |
| TASK-TI-002 | Generate rules structure in template-init | task-work | 2 | 6/10 |
| TASK-TI-003 | Generate agent split files in template-init | task-work | 2 | 5/10 |
| TASK-TI-004 | Update template-init documentation | direct | 3 | 3/10 |
| TASK-TI-005 | Generate guidance files from agents | task-work | 3 | 5/10 |

## Parallel Execution Strategy

**Wave 1** (Foundation):
- TASK-TI-001 - Flags (direct, no dependencies)

**Wave 2** (Core Implementation - PARALLEL):
- TASK-TI-002 - Rules structure generation
- TASK-TI-003 - Agent split files
- *Can run in parallel using Conductor workspaces*

**Wave 3** (Polish - PARALLEL):
- TASK-TI-004 - Documentation
- TASK-TI-005 - Guidance file generation
- *Can run in parallel using Conductor workspaces*

## Estimated Effort

| Wave | Tasks | Effort | Parallel? |
|------|-------|--------|-----------|
| Wave 1 | 1 | 1-2 hours | No (foundation) |
| Wave 2 | 2 | 4-6 hours | Yes (2 workspaces) |
| Wave 3 | 2 | 3-4 hours | Yes (2 workspaces) |
| **Total** | **5** | **8-12 hours** | **~40% time savings** |

## Success Criteria

- [ ] `/template-init` generates `.claude/rules/` by default
- [ ] `--no-rules-structure` flag works for opt-out
- [ ] Agent files split into core + extended
- [ ] Documentation aligned with `/template-create`
- [ ] All existing tests pass
- [ ] New tests cover rules structure generation

## Related

- [TASK-REV-TI01](../TASK-REV-TI01-analyze-template-init-updates.md) - Source review task
- [template-create.md](../../../installer/core/commands/template-create.md) - Reference implementation
- [rules-structure-guide.md](../../../docs/guides/rules-structure-guide.md) - Rules structure documentation
