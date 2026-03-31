# Feature: Fix /feature-complete Command Availability

**Feature ID:** FEAT-FCD
**Parent Review:** TASK-REV-FCD
**Created:** 2026-01-24

## Overview

Fixes the `/feature-complete` command availability gap identified in TASK-REV-FCD. The CLI command works (`guardkit autobuild complete`) but the Claude Code skill file is missing.

## Root Cause

The feature-complete implementation (TASK-FC-001 through TASK-FC-005) focused on orchestrator and CLI layers but missed the skill registration layer.

## Tasks

| Task ID | Title | Complexity | Mode | Est. Time |
|---------|-------|------------|------|-----------|
| TASK-FCD-001 | Create feature-complete.md skill file | 2 | direct | 30 min |
| TASK-FCD-002 | Update CLAUDE.md documentation | 1 | direct | 15 min |

## Execution Order

Both tasks can run in parallel (no dependencies).

## Success Criteria

1. `/feature-complete FEAT-XXX` recognized as valid skill in Claude Code
2. Command successfully delegates to `guardkit autobuild complete`
3. CLAUDE.md lists `/feature-complete` in AutoBuild section

## Related Files

- [Review Report](../../../.claude/reviews/TASK-REV-FCD-review-report.md)
- [feature-build.md](../../../installer/core/commands/feature-build.md) (template)
- [guardkit/cli/autobuild.py](../../../guardkit/cli/autobuild.py) (CLI implementation)
