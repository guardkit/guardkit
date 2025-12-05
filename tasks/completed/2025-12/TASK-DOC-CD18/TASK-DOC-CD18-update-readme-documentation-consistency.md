---
id: TASK-DOC-CD18
title: Update README.md - Documentation consistency and remove archived design features
status: completed
created: 2025-12-05T10:00:00Z
updated: 2025-12-05T10:20:00Z
completed: 2025-12-05T10:20:00Z
priority: medium
tags: [documentation, readme, cleanup]
complexity: 3
test_results:
  status: passed
  coverage: N/A
  last_run: 2025-12-05T10:15:00Z
---

# Task: Update README.md - Documentation consistency and remove archived design features

## Description

The README.md has several inconsistencies and references to archived design-to-code features (Figma/Zeplin) that need to be cleaned up. The design features have been archived until the design feature of the task-work command is implemented.

## Changes Required

### 1. Documentation Link Style Consistency

**Issue**: The "Documentation" section (lines 98-111) uses the preferred style with the clickable badge/link at the top. The "5-Minute Quickstart" section (line 115) uses a plain text link which is inconsistent.

**Fix**: Update the 5-Minute Quickstart section to match the Documentation section style:
- Current (line 115): `**📚 Full documentation: https://guardkit.github.io/guardkit/**`
- Should match the Documentation section style with: `📚 **[View Full Documentation](https://guardkit.github.io/guardkit/)**`

### 2. Remove UX Design Integration Section (lines 262-266)

**Location**: https://github.com/guardkit/guardkit?tab=readme-ov-file#ux-design-integration

**Action**: Remove the entire "UX Design Integration" subsection under "Available Commands":
```markdown
### UX Design Integration
```bash
/figma-to-react <file-key> [node-id]    # Figma → TypeScript React + Tailwind
/zeplin-to-maui <project-id> <screen-id> # Zeplin → .NET MAUI + XAML
```
```

**Reason**: These commands are archived until design feature implementation.

### 3. Remove Design MCPs Section (lines 427-437)

**Location**: https://github.com/guardkit/guardkit?tab=readme-ov-file#design-mcps-only-for-design-to-code-workflows

**Action**: Remove the entire "Design MCPs (Only for Design-to-Code Workflows)" section:
```markdown
### Design MCPs (Only for Design-to-Code Workflows)

**⚠️ Only set these up if you're using the specific design-to-code commands:**

| MCP | Purpose | Required For | Setup Time |
|-----|---------|--------------|------------|
| **figma-dev-mode** | Figma → React code | `/figma-to-react` command only | 10 min |
| **zeplin** | Zeplin → MAUI code | `/zeplin-to-maui` command only | 10 min |

**Skip these** if you're not converting Figma/Zeplin designs to code. They're not used during regular development.
```

**Reason**: Design MCPs are not needed with archived commands.

### 4. Remove Design MCPs from Setup Guides Section (lines 472-474)

**Location**: https://github.com/guardkit/guardkit?tab=readme-ov-file#setup-guides

**Action**: Remove these lines from the Setup Guides section:
```markdown
**Design MCPs** (only if using design-to-code commands):
- [Figma Setup](docs/mcp-setup/figma-mcp-setup.md) - For `/figma-to-react` command
- [Zeplin Setup](docs/mcp-setup/zeplin-mcp-setup.md) - For `/zeplin-to-maui` command
```

**Reason**: Design MCPs are not needed with archived commands.

### 5. Remove Design-First Workflow from Getting Started Section (line 484)

**Location**: https://github.com/guardkit/guardkit?tab=readme-ov-file#getting-started

**Action**: Remove this line:
```markdown
- [Design-First Workflow](docs/workflows/design-first-workflow.md) - When and how to split design/implementation
```

**Reason**: This refers to the design-to-code workflow which is archived.

### 6. Remove UX Design Integration from Advanced Section (line 487)

**Location**: https://github.com/guardkit/guardkit?tab=readme-ov-file#advanced

**Action**: Remove this line:
```markdown
- [UX Design Integration](docs/workflows/ux-design-integration-workflow.md) - Figma/Zeplin → Code
```

**Reason**: UX Design Integration refers to archived Figma/Zeplin commands.

## Acceptance Criteria

- [x] 5-Minute Quickstart documentation link matches Documentation section style
- [x] UX Design Integration commands section removed from Available Commands
- [x] Design MCPs section removed entirely
- [x] Design MCPs removed from Setup Guides
- [x] Design-First Workflow removed from Getting Started documentation list
- [x] UX Design Integration removed from Advanced documentation list
- [x] No broken internal references after changes
- [x] README renders correctly in GitHub

## Test Requirements

- [x] Verify all markdown renders correctly
- [x] Verify no broken links to removed sections
- [x] Verify documentation link style is consistent

## Implementation Notes

This is a documentation cleanup task. No code changes required, only markdown edits.

The design-to-code features (Figma/Zeplin) have been archived and will be re-added when the design feature of the task-work command is implemented.

## Test Execution Log

**2025-12-05T10:15:00Z** - Task executed successfully

### Changes Made:
1. **Line 115**: Changed `**📚 Full documentation: https://guardkit.github.io/guardkit/**` to `📚 **[View Full Documentation](https://guardkit.github.io/guardkit/)**` - Now matches Documentation section style
2. **Lines 262-266**: Removed UX Design Integration section with `/figma-to-react` and `/zeplin-to-maui` commands
3. **Lines 427-437**: Removed entire "Design MCPs (Only for Design-to-Code Workflows)" section
4. **Lines 472-474**: Removed Design MCPs from Setup Guides section
5. **Line 484**: Removed Design-First Workflow from Getting Started documentation list
6. **Line 487**: Removed UX Design Integration from Advanced documentation list

### Verification:
- All acceptance criteria verified via file reads
- No broken internal references detected
- Documentation link style is now consistent between Documentation and 5-Minute Quickstart sections

## Completion Summary

**Completed**: 2025-12-05T10:20:00Z
**Duration**: ~20 minutes
**Files Modified**: 1 (README.md)
**Lines Changed**: ~25 lines removed, 1 line modified
