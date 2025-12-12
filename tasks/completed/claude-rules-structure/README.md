# Claude Code Rules Structure Adoption

## Overview

This feature implements support for Claude Code's modular `.claude/rules/` directory structure, enabling path-specific conditional loading of project instructions and agent guidance. This reduces context window usage by 60-70% compared to single-file approaches.

## Problem Statement

1. **CLAUDE.md size limits are too restrictive** - The default 10KB limit doesn't accommodate complex templates like `fastapi-python` (29.2KB)
2. **Context window inefficiency** - All instructions load regardless of which files are being edited
3. **No path-specific rules** - Can't have different guidance for different file types

## Solution

Implement Claude Code's 4-tier memory hierarchy with modular rules:

```
.claude/
├── CLAUDE.md                    # Core documentation (~5KB)
└── rules/
    ├── code-style.md            # paths: **/*.{ext}
    ├── testing.md               # paths: **/*.test.*, **/tests/**
    ├── patterns/
    │   └── {pattern}.md
    └── agents/
        └── {agent}.md           # paths: **/relevant/**
```

**Key Benefits:**
- Path-specific rules only load when editing relevant files
- Recursive discovery in subdirectories
- Conditional loading with `paths:` frontmatter
- 60-70% context window reduction

## Subtasks Summary

| ID | Title | Wave | Mode | Hours | Status | Workspace |
|----|-------|------|------|-------|--------|-----------|
| CRS-001 | Increase Size Limit to 25KB | 1 | direct | 1-2 | ⏳ Backlog | wave1-1 |
| CRS-002 | RulesStructureGenerator Class | 2 | task-work | 4-6 | ⏳ Backlog | wave2-1 |
| CRS-003 | CLI Flag --use-rules-structure | 3 | direct | 1-2 | ⏳ Backlog | wave3-1 |
| CRS-004 | Path Pattern Inference | 3 | task-work | 3-4 | ⏳ Backlog | wave3-2 |
| CRS-005 | template-create Documentation | 3 | direct | 0.5 | ✅ Complete | wave3-3 |
| CRS-014 | Agent-Enhance Rules Support | 3 | task-review | 3-4 | ⏳ Backlog | wave3-4 |
| CRS-006 | Refactor fastapi-python | 4 | task-work | 6-8 | ⏳ Backlog | wave4-1 |
| CRS-007 | Refactor react-typescript | 4 | task-work | 4-6 | ✅ Complete | wave4-2 |
| CRS-008 | Refactor nextjs-fullstack | 4 | task-work | 5-7 | ⏳ Backlog | wave4-3 |
| CRS-009 | Refactor react-fastapi-monorepo | 4 | task-work | 5-7 | ⏳ Backlog | wave4-4 |
| CRS-010 | Refactor default | 4 | direct | 1-2 | ⏳ Backlog | wave4-5 |
| CRS-011 | Quick-Start Guide | 5 | direct | 4-6 | ⏳ Backlog | wave5-1 |
| CRS-012 | Update Root CLAUDE.md | 5 | direct | 3-4 | ⏳ Backlog | wave5-2 |
| CRS-013 | Update Template READMEs | 5 | direct | 2-3 | ⏳ Backlog | wave5-3 |

**Total Effort**: 43.5-61.5 hours (2/14 tasks complete)
## Implementation Modes

### task-work (Full Quality Gates)
Use `/task-work TASK-CRS-XXX` for:
- CRS-002: RulesStructureGenerator (core implementation)
- CRS-004: Path Pattern Inference (complex logic)
- CRS-006-009: Template refactoring (high impact)

### task-review (Analysis/Decision)
Use `/task-review TASK-CRS-XXX` for:
- CRS-014: Agent-Enhance Rules Support (architectural review, may spawn implementation subtasks)

### direct (Direct Implementation)
Simple changes that can be implemented directly:
- CRS-001: Size limit change (2 lines)
- CRS-003: CLI flag addition (simple)
- CRS-005: Documentation update
- CRS-010: Default template (smallest)
- CRS-011-013: Documentation tasks

## Related Tasks

- **TASK-FIX-SIZE-F8G2**: Original task defining the problem and solution
- **TASK-REV-F1BA**: Architectural review that created this implementation plan

## References

- [Claude Code Memory Documentation](https://code.claude.com/docs/en/memory)
- [Review Report](.claude/reviews/TASK-REV-F1BA-review-report.md)
- [Progressive Disclosure Guide](docs/guides/progressive-disclosure.md)

## Success Criteria

1. Default size limit increased to 25KB (unblocks immediate issues)
2. `--use-rules-structure` flag working in `/template-create`
3. All 5 built-in templates refactored to rules structure
4. Documentation complete and accurate
5. Backward compatibility maintained (single-file still works)
