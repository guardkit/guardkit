---
id: TASK-GDU-008
title: Refactor CLAUDE.md Graphiti content to progressive disclosure
status: completed
created: 2026-02-01T23:45:00Z
updated: 2026-02-02T00:15:00Z
priority: high
tags: [documentation, claude-md, progressive-disclosure, graphiti]
complexity: 5
parent_review: TASK-REV-BBE7
feature_id: FEAT-GDU
wave: 3
implementation_mode: task-work
conductor_workspace: graphiti-docs-wave3-3
---

# Task: Refactor CLAUDE.md Graphiti Content to Progressive Disclosure

## Description

The CLAUDE.md file contains ~350 lines of detailed Graphiti documentation (lines ~750-1140). This should be refactored to use progressive disclosure, moving detailed content to an ext file while keeping essential summary in the core file.

## Problem

Current state:
- CLAUDE.md has excessive detail about Graphiti features
- ~350 lines dedicated to Graphiti (Interactive Capture, Query Commands, Job-Specific Context, Turn States, Troubleshooting)
- This level of detail belongs in an ext file that loads on-demand
- Core CLAUDE.md should only contain essential quick-reference

## Solution

1. Create `.claude/rules/graphiti-knowledge.md` (or similar ext file)
2. Move detailed Graphiti content to ext file
3. Keep concise summary in CLAUDE.md (~50-80 lines max)
4. Add appropriate `paths:` frontmatter to ext file if needed

## Current Graphiti Sections in CLAUDE.md

| Section | Lines | Action |
|---------|-------|--------|
| Graphiti Knowledge Capture header | ~750-755 | Keep summary, move details |
| Interactive Knowledge Capture | ~794-901 | Move to ext |
| Knowledge Query Commands | ~903-1001 | Move to ext |
| Turn State Tracking | ~960-1001 | Move to ext |
| Job-Specific Context Retrieval | ~1056-1139 | Move to ext |
| Troubleshooting Graphiti | ~1003-1055 | Move to ext |

## Target Structure

### CLAUDE.md (keep ~50-80 lines)

```markdown
## Graphiti Knowledge Capture

GuardKit integrates with Graphiti for persistent knowledge across sessions.

### Quick Reference

**Interactive Capture**:
```bash
guardkit graphiti capture --interactive
guardkit graphiti capture --interactive --focus role-customization
```

**Query Commands**:
```bash
guardkit graphiti show FEAT-XXX
guardkit graphiti search "query" --group patterns
guardkit graphiti list features
guardkit graphiti status
```

**See**: `.claude/rules/graphiti-knowledge.md` for detailed usage, focus categories, job-specific context, and troubleshooting.
```

### .claude/rules/graphiti-knowledge.md (new ext file)

Contains all the detailed content:
- Interactive Knowledge Capture (full section)
- Focus Categories (all 9 categories with examples)
- Knowledge Query Commands (detailed)
- Turn State Tracking (full schema and examples)
- Job-Specific Context Retrieval (budget allocation, etc.)
- Troubleshooting Graphiti

## Acceptance Criteria

- [x] Created `.claude/rules/graphiti-knowledge.md` with detailed content (377 lines)
- [x] CLAUDE.md Graphiti section reduced to <100 lines (43 lines, down from ~350)
- [x] Essential commands and quick reference kept in CLAUDE.md
- [x] Ext file has appropriate frontmatter (title header)
- [x] All content preserved (nothing lost)
- [x] Cross-references work correctly (See link added)
- [x] No duplicate content between core and ext

## Testing

1. Verify CLAUDE.md loads quickly (reduced size)
2. Verify ext file loads when relevant (if paths: specified)
3. Verify all Graphiti commands still documented somewhere
4. Test with `claude` CLI to ensure context loads appropriately

## Estimated Effort

2 hours

## Notes

This task should use `/task-work` mode as it involves significant refactoring and requires careful validation that no content is lost during the move.
