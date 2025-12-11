---
id: TASK-GI-002
title: Handle both CLAUDE.md locations in init-project.sh
status: completed
priority: medium
created: 2025-12-11T19:45:00Z
updated: 2025-12-11T22:45:00Z
completed: 2025-12-11T22:45:00Z
complexity: 2
tags: [guardkit-init, claudemd, consistency]
related_to: [TASK-REV-INIT, TASK-GI-001]
implementation_mode: direct
---

# Task: Handle Both CLAUDE.md Locations

## Problem

Templates have inconsistent CLAUDE.md placement:
- `react-typescript/CLAUDE.md` (root level)
- `default/.claude/CLAUDE.md` (inside .claude)
- `fastapi-python/CLAUDE.md` AND `fastapi-python/.claude/CLAUDE.md` (both exist)

The current code only checks `$template_dir/CLAUDE.md`, missing `.claude/CLAUDE.md` in some templates.

## Solution

Update the CLAUDE.md copy logic to check both locations, with `.claude/CLAUDE.md` taking precedence.

## Implementation

### File to Modify

`installer/scripts/init-project.sh`

### Current Code (lines 195-199)

```bash
# Copy CLAUDE.md context file
if [ -f "$template_dir/CLAUDE.md" ]; then
    cp "$template_dir/CLAUDE.md" .claude/
    print_success "Copied project context file"
fi
```

### New Code

```bash
# Copy CLAUDE.md context file (check both locations, .claude/ takes precedence)
if [ -f "$template_dir/.claude/CLAUDE.md" ]; then
    cp "$template_dir/.claude/CLAUDE.md" .claude/
    print_success "Copied project context file (from .claude/)"
elif [ -f "$template_dir/CLAUDE.md" ]; then
    cp "$template_dir/CLAUDE.md" .claude/
    print_success "Copied project context file"
fi
```

## Acceptance Criteria

- [x] CLAUDE.md copied from `.claude/CLAUDE.md` if it exists
- [x] Falls back to root `CLAUDE.md` if `.claude/CLAUDE.md` doesn't exist
- [x] Works with all 5 reference templates
- [x] Output message indicates source location

## Testing

```bash
# Test with template having .claude/CLAUDE.md
guardkit init default
# Should see: "Copied project context file (from .claude/)"

# Test with template having root CLAUDE.md
guardkit init react-typescript
# Should see: "Copied project context file"
```

## Complexity

- **Effort**: Low (~15 minutes)
- **Risk**: Low
- **Lines**: ~3 changed lines

## Implementation Notes

**Date**: 2025-12-11
**Status**: ✅ Completed

### Changes Made

Modified `installer/scripts/init-project.sh` (lines 195-202):
- Added precedence check for `.claude/CLAUDE.md` first
- Falls back to root `CLAUDE.md` if `.claude/` version doesn't exist
- Updated success message to indicate source location

### Verification

The implementation:
1. ✅ Checks `.claude/CLAUDE.md` first (takes precedence)
2. ✅ Falls back to root `CLAUDE.md` if needed
3. ✅ Provides clear feedback on which location was used
4. ✅ Works with all template structures:
   - Templates with root CLAUDE.md only (react-typescript, fastapi-python)
   - Templates with .claude/CLAUDE.md only (default)
   - Templates with both (fastapi-python - .claude/ takes precedence)

### Commit

Commit: `b79ed0f` - "Handle both CLAUDE.md locations in init-project.sh"
