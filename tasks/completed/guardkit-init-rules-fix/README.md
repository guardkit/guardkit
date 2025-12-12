# Feature: Fix guardkit init for Rules Structure Support

**Status: COMPLETED** (2025-12-11)

## Problem Statement

The `guardkit init` command did not copy the `.claude/rules/` directory from templates, breaking the rules structure feature that provides 60-70% context window reduction for users.

## Solution Implemented

Updated `init-project.sh` to:
1. Copy `.claude/rules/` directory from templates
2. Handle both CLAUDE.md locations consistently (`.claude/CLAUDE.md` takes precedence)
3. Add post-init verification with rule file count

## Subtasks

| Task ID | Title | Priority | Status |
|---------|-------|----------|--------|
| TASK-GI-001 | Add rules directory copying to init-project.sh | HIGH | ✅ COMPLETED |
| TASK-GI-002 | Handle both CLAUDE.md locations | MEDIUM | ✅ COMPLETED |
| TASK-GI-003 | Add post-init verification | LOW | ✅ COMPLETED |

## Changes Made

**File**: `installer/scripts/init-project.sh`

1. **Lines 195-202**: CLAUDE.md copy now checks both locations
2. **Lines 252-257**: Added `.claude/rules/` directory copying
3. **Lines 275-293**: Added `verify_rules_structure()` function
4. **Line 569**: Call verification after `copy_template_files`

## Source

Created from review: TASK-REV-INIT
Report: [.claude/reviews/TASK-REV-INIT-review-report.md](../../../.claude/reviews/TASK-REV-INIT-review-report.md)

## Verification

- [x] Run `guardkit init react-typescript` in test directory
- [x] Verify `.claude/rules/` directory is created with subdirectories
- [x] Verify CLAUDE.md is copied from correct location
- [x] Verify rule count verification message appears
