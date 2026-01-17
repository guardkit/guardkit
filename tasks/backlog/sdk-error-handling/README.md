# Feature: SDK Error Handling Improvements

## Overview

Improve Claude Agent SDK error handling to provide accurate diagnostics instead of misleading "not installed" messages when the SDK is actually installed but fails to import for other reasons.

## Problem Statement

When running `/feature-build` or `guardkit autobuild`, users see "Claude Agent SDK not installed" even when the SDK IS correctly installed. This is caused by overly broad error handling that catches all `ImportError` exceptions and reports them as installation failures.

## Solution Approach

1. Improve error messages with diagnostic information
2. Add pre-flight SDK availability check at CLI startup
3. Create `guardkit doctor` command for environment diagnostics
4. Update documentation for optional dependency installation

## Subtasks

| Task ID | Title | Mode | Wave | Priority |
|---------|-------|------|------|----------|
| TASK-SDK-001 | Improve SDK error message with diagnostics | task-work | 1 | HIGH |
| TASK-SDK-002 | Add SDK pre-flight check in CLI | task-work | 1 | MEDIUM |
| TASK-SDK-003 | Add guardkit doctor command | task-work | 2 | MEDIUM |
| TASK-SDK-004 | Document optional dependency installation | direct | 2 | LOW |

## Dependencies

- None (standalone improvement)

## Source

- Review Task: TASK-REV-SDK1
- Review Report: `.claude/reviews/TASK-REV-SDK1-review-report.md`

## Acceptance Criteria

- [ ] SDK import failures show actual error + Python path + sys.path
- [ ] AutoBuild CLI checks SDK availability before starting orchestration
- [ ] `guardkit doctor` command validates all dependencies
- [ ] Installation docs clearly explain optional dependencies
