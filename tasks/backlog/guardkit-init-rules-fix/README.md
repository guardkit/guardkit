# Feature: Fix guardkit init for Rules Structure Support

## Problem Statement

The `guardkit init` command does not copy the `.claude/rules/` directory from templates, breaking the rules structure feature that provides 60-70% context window reduction for users.

## Solution Approach

Update `init-project.sh` to:
1. Copy `.claude/rules/` directory from templates
2. Handle both CLAUDE.md locations consistently
3. Add post-init verification

## Subtasks

| Task ID | Title | Priority | Mode | Status |
|---------|-------|----------|------|--------|
| TASK-GI-001 | Add rules directory copying to init-project.sh | HIGH | task-work | pending |
| TASK-GI-002 | Handle both CLAUDE.md locations | MEDIUM | direct | pending |
| TASK-GI-003 | Add post-init verification | LOW | direct | pending |

## Execution Strategy

**Wave 1** (Critical fix):
- TASK-GI-001: Add `.claude/rules/` copying logic

**Wave 2** (Improvements):
- TASK-GI-002 and TASK-GI-003 can run in parallel

## Source

Created from review: TASK-REV-INIT
Report: [.claude/reviews/TASK-REV-INIT-review-report.md](../../../.claude/reviews/TASK-REV-INIT-review-report.md)

## Verification

After implementation:
- [ ] Run `guardkit init react-typescript` in test directory
- [ ] Verify `.claude/rules/` directory is created with subdirectories
- [ ] Verify CLAUDE.md is copied from correct location
- [ ] Run `guardkit doctor` to verify health
