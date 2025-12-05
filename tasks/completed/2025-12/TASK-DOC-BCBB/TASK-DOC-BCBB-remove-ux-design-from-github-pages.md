---
id: TASK-DOC-BCBB
title: Remove UX Design Integration references from GitHub Pages docs
status: completed
created: 2025-12-05T10:30:00Z
updated: 2025-12-05T15:05:00Z
completed: 2025-12-05T15:05:00Z
priority: medium
tags: [documentation, github-pages, cleanup]
complexity: 4
test_results:
  status: passed
  coverage: N/A
  last_run: 2025-12-05T15:00:00Z
---

# Task: Remove UX Design Integration references from GitHub Pages docs

## Description

Remove all references to UX Design Integration (Figma/Zeplin) from the GitHub Pages documentation site. The design-to-code features have been archived until the design feature of the task-work command is implemented.

This follows up on TASK-DOC-CD18 which cleaned up the README.md, but the GitHub Pages docs site still contains these references.

## Changes Required

### 1. Update mkdocs.yml - Remove navigation entries

**File**: `mkdocs.yml`

**Actions**:
- Remove `- MCP Integration: mcp-integration.md` from main navigation (line 82)
- Remove `- UX Design Integration: workflows/ux-design-integration-workflow.md` from Workflows section (line 102)
- Remove entire `- MCP Setup:` section (lines 111-113):
  ```yaml
  - MCP Setup:
      - Figma MCP Setup: mcp-setup/figma-mcp-setup.md
      - Zeplin MCP Setup: mcp-setup/zeplin-mcp-setup.md
  ```

### 2. Update docs/mcp-integration.md

**File**: `docs/mcp-integration.md`

**Actions**:
- Remove "Design MCPs" section (lines 16-22)
- Remove "Design MCPs (Only if Using Design-to-Code Workflows)" section (lines 31-34)
- Remove Design MCPs from Token Budgets table (lines 46-47)
- Remove "Figma & Zeplin MCPs" section (lines 96-117)
- Remove "Install Design MCPs If" section (lines 157-161)
- Remove "Design Workflow" from Next Steps (line 169)

### 3. Update docs/advanced.md - Remove UX Design Integration section

**File**: `docs/advanced.md`

**Actions**:
- Remove entire "🖼️ [UX Design Integration]" section (lines 36-62)
- Update Next Steps section if it references UX Design

### 4. Move or archive design-related docs

**Files to handle** (archive, don't delete - for future reference):

- `docs/workflows/ux-design-integration-workflow.md` - Move to `docs/archive/`
- `docs/mcp-setup/figma-mcp-setup.md` - Move to `docs/archive/`
- `docs/mcp-setup/zeplin-mcp-setup.md` - Move to `docs/archive/`

### 5. Search and remove other UX references

**Search for**: `figma`, `zeplin`, `ux-design`, `UX Design`, `design-to-code`

**Files to check** (from Grep results):
- `docs/guides/guardkit-workflow.md` - Check for UX references
- `docs/guides/claude-code-web-setup.md` - Check for UX references
- `docs/troubleshooting.md` - Check for UX references

## Acceptance Criteria

- [x] `mkdocs.yml` navigation no longer includes MCP Integration page
- [x] `mkdocs.yml` navigation no longer includes UX Design Integration workflow
- [x] `mkdocs.yml` navigation no longer includes MCP Setup section
- [x] `docs/mcp-integration.md` has no Design MCP references
- [x] `docs/advanced.md` has no UX Design Integration section
- [x] Design workflow files moved to `docs/archive/`
- [x] No broken links in documentation site
- [x] `mkdocs build` completes without errors
- [x] Site renders correctly with Material theme

## Test Requirements

- [x] Run `mkdocs build` to verify no broken links
- [x] Verify site navigation is correct
- [x] Search docs for remaining UX/Figma/Zeplin references
- [x] Verify archived files are in correct location

## Implementation Notes

This is a documentation cleanup task. The design-to-code features (Figma/Zeplin) have been archived until the design feature of the task-work command is implemented.

**Related Task**: TASK-DOC-CD18 (README.md cleanup - completed)

## Test Execution Log

**2025-12-05T15:00:00Z** - Task executed successfully

### Changes Made:

1. **mkdocs.yml**:
   - Removed `- MCP Integration: mcp-integration.md` from navigation
   - Removed `- UX Design Integration: workflows/ux-design-integration-workflow.md` from Workflows
   - Removed entire `- MCP Setup:` section with Figma and Zeplin entries

2. **docs/mcp-integration.md**:
   - Removed Design MCPs section from MCP Types
   - Removed Design MCPs setup links
   - Removed figma-dev-mode and zeplin from Token Budgets table
   - Removed Figma & Zeplin MCPs section
   - Removed "Install Design MCPs If" section
   - Removed Design Workflow from Next Steps

3. **docs/advanced.md**:
   - Removed entire "🖼️ [UX Design Integration]" section (27 lines)

4. **docs/guides/guardkit-workflow.md**:
   - Removed figma-dev-mode and zeplin from AVAILABLE TOOLS example
   - Removed figma-dev-mode and zeplin sections from Supported MCP Tools

5. **docs/troubleshooting.md**:
   - Removed "Figma/Zeplin MCP Failing" section
   - Removed "Zeplin + .NET MAUI Icon Issues" section and link

6. **Files Archived to docs/archive/**:
   - `ux-design-integration-workflow.md`
   - `figma-mcp-setup.md`
   - `zeplin-mcp-setup.md`
   - `zeplin-maui-icon-issues.md`

7. **Directories Removed**:
   - `docs/mcp-setup/` (empty after archiving files)
   - `docs/troubleshooting/` (empty after archiving file)

### Verification:
- `mkdocs build --strict` completed successfully
- No new broken links introduced by changes
- All design-related files preserved in docs/archive/ for future reference
- Remaining UX/Figma/Zeplin references are in archived or internal planning docs

## Completion Summary

**Completed**: 2025-12-05T15:00:00Z
**Files Modified**: 5 (mkdocs.yml, mcp-integration.md, advanced.md, guardkit-workflow.md, troubleshooting.md)
**Files Archived**: 4 (ux-design-integration-workflow.md, figma-mcp-setup.md, zeplin-mcp-setup.md, zeplin-maui-icon-issues.md)
**Directories Removed**: 2 (docs/mcp-setup/, docs/troubleshooting/)
