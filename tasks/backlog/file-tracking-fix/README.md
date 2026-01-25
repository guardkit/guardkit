# Feature: Fix File Tracking Display in AutoBuild

## Problem Statement

The AutoBuild feature-build output shows "0 files created, 0 modified, 0 tests" even when implementations complete successfully. This causes user confusion about whether work was actually performed.

## Root Cause

The file tracking system in `agent_invoker.py` uses regex patterns that don't match Claude's actual output format:

```python
FILES_MODIFIED_PATTERN = re.compile(r"(?:Modified|Changed):\s*([^\s,]+)")
FILES_CREATED_PATTERN = re.compile(r"(?:Created|Added):\s*([^\s,]+)")
```

Claude's tool calls use different formatting (Write/Edit tool results, file content blocks) that these patterns don't capture.

## Solution Approach

Parse file operations from SDK tool call results instead of regex matching on stream output:
- Track Write tool calls → files_created
- Track Edit tool calls → files_modified
- Extract test counts from pytest output or test file creation

## Parent Review

- **Review Task**: TASK-REV-BRF
- **Report**: [.claude/reviews/TASK-REV-BRF-review-report.md](../../../.claude/reviews/TASK-REV-BRF-review-report.md)

## Subtasks

| ID | Title | Priority | Complexity | Implementation Mode |
|----|-------|----------|------------|---------------------|
| TASK-FTF-001 | Fix file tracking in agent_invoker.py | Medium | 4 | task-work |
| TASK-FTF-002 | Add test count extraction | Low | 3 | direct |

## Impact

- **User Experience**: Clearer feedback on what AutoBuild accomplished
- **Debugging**: Easier to verify implementations completed
- **Trust**: Users can see actual work performed

## Success Criteria

1. AutoBuild displays accurate file creation/modification counts
2. Test counts reflect actual tests written
3. No regression in existing functionality
