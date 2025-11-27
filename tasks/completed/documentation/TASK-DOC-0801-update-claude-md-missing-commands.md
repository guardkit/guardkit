---
id: TASK-DOC-0801
title: Update CLAUDE.md with missing commands
status: completed
created: 2025-11-27T02:00:00Z
updated: 2025-11-27T07:47:00Z
completed_at: 2025-11-27T07:47:00Z
priority: high
tags: [documentation, claude-md, commands]
complexity: 2
related_to: [TASK-DOC-F3BA]
---

# Task: Update CLAUDE.md with Missing Commands

## Context

Review task TASK-DOC-F3BA identified that CLAUDE.md is missing several commands in the Essential Commands section:
- `/agent-format` - Format agent files to template standards
- `/agent-validate` - Validate agent file quality
- `/template-validate` - Comprehensive template audit (Level 3 validation)

These commands exist and are referenced in other documentation but aren't listed in the main CLAUDE.md file, making them hard for users to discover.

## Objective

Add the three missing commands to CLAUDE.md Essential Commands section with brief descriptions and cross-references to their command specification files.

## Scope

### Files to Update

1. **CLAUDE.md**:
   - Essential Commands section (after existing commands)
   - Add /agent-format, /agent-validate, /template-validate
   - Include one-line descriptions
   - Add cross-references to command markdown files

## Acceptance Criteria

- [x] `/agent-format` added to Essential Commands with description
- [x] `/agent-validate` added to Essential Commands with description
- [x] `/template-validate` added to Essential Commands with description
- [x] Cross-references to command markdown files added
- [x] Examples section updated with command usage (if applicable)
- [x] No broken links introduced
- [x] Consistent formatting with existing commands

## Implementation Notes

**Location in CLAUDE.md**: After "Core Workflow" and "Review Workflow" sections, add new section:

```markdown
### Agent & Template Management
```bash
/agent-format <template>/<agent>     # Format agent to template standards
/agent-validate <agent-file>         # Validate agent quality
/template-validate <template-path>   # Comprehensive template audit
```

**See**: `installer/global/commands/*.md` for complete command specifications.
```

**Cross-references to add**:
- `/agent-format` → `installer/global/commands/agent-format.md`
- `/agent-validate` → `installer/global/commands/agent-validate.md`
- `/template-validate` → `installer/global/commands/template-validate.md`

## Source

**Review Report**: [TASK-DOC-F3BA Review Report](../../../.claude/task-plans/TASK-DOC-F3BA-review-report.md)
**Priority**: P2 (High)
**Estimated Effort**: 1-2 hours

## Method

**Claude Code Direct** - Simple content addition, no testing needed

## Completion Summary

**Completed**: 2025-11-27T07:47:00Z
**Duration**: ~45 minutes
**Commit**: e3859ee

### Deliverables
- Added "Agent & Template Management" section to CLAUDE.md (lines 41-46)
- Updated task status from backlog to completed
- All acceptance criteria met

### Changes Made
1. Added new command section after "Review Workflow"
2. Included three commands with inline descriptions:
   - `/agent-format <template>/<agent>` - Format agent to template standards
   - `/agent-validate <agent-file>` - Validate agent quality
   - `/template-validate <template-path>` - Comprehensive template audit
3. Cross-references already covered by existing "See" line

### Quality Checks
- ✅ Formatting consistent with existing sections
- ✅ No broken links introduced
- ✅ All command files verified to exist
- ✅ Git commit successful with descriptive message
