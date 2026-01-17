---
id: TASK-SDK-a7f3
title: Add --sdk-timeout CLI flag to autobuild commands
status: completed
created: 2026-01-08T12:05:00Z
updated: 2026-01-08T14:30:00Z
completed: 2026-01-08T16:45:00Z
completed_location: tasks/completed/TASK-SDK-a7f3/
priority: critical
tags: [autobuild, sdk-timeout, cli, configuration, feature-build]
parent_task: TASK-REV-9AC5
complexity: 3
estimated_effort: 2-3 hours
review_recommendation: R1
related_findings: [Finding-1]
organized_files:
  - TASK-SDK-a7f3-add-sdk-timeout-cli-flag.md
---

# Task: Add --sdk-timeout CLI flag to autobuild commands

## Context

**From Review**: TASK-REV-9AC5 Finding 1 (CRITICAL severity)

The Player agent times out at the default 300s before completing complex tasks. The configuration flow has a gap:
- `autobuild.sdk_timeout` can be set in task/feature frontmatter
- But CLI doesn't read it or provide override
- AgentInvoker uses hardcoded DEFAULT_SDK_TIMEOUT (300s)

**Impact**: Complex tasks with Phase 4.5 test enforcement loop (3 iterations × 60-90s) cannot complete within 300s, resulting in 100% work loss.

## Acceptance Criteria

- [x] Add `--sdk-timeout` option to `guardkit autobuild task` command
- [x] Add `--sdk-timeout` option to `guardkit autobuild feature` command
- [x] Implement configuration cascade: CLI flag > frontmatter > DEFAULT (300s)
- [x] Update CLI help text with timeout guidance
- [x] Pass effective timeout through to AgentInvoker
- [x] Validate timeout range (60-3600s)
- [x] Add unit tests for timeout cascade logic
- [x] Update CLAUDE.md with --sdk-timeout flag documentation

## Implementation Summary

### Files Modified
1. `guardkit/cli/autobuild.py` - Added `--sdk-timeout` option to both `task` and `feature` commands
2. `CLAUDE.md` - Added SDK Timeout Configuration section with usage examples and cascade documentation

### Configuration Cascade (implemented)
```python
effective_timeout = (
    cli_sdk_timeout  # --sdk-timeout flag
    or task.get("autobuild", {}).get("sdk_timeout")  # Task frontmatter
    or feature.get("autobuild", {}).get("sdk_timeout")  # Feature YAML
    or DEFAULT_SDK_TIMEOUT  # 300s
)
```

### Tests Added
14+ unit tests in `tests/unit/test_cli_autobuild.py`:
- `test_task_command_sdk_timeout_in_help`
- `test_feature_command_sdk_timeout_in_help`
- `test_task_command_sdk_timeout_from_cli`
- `test_task_command_sdk_timeout_from_frontmatter`
- `test_task_command_sdk_timeout_cli_overrides_frontmatter`
- `test_task_command_sdk_timeout_default_value`
- `test_task_command_sdk_timeout_invalid_below_minimum`
- `test_task_command_sdk_timeout_invalid_above_maximum`
- `test_task_command_sdk_timeout_boundary_minimum`
- `test_task_command_sdk_timeout_boundary_maximum`
- `test_feature_command_sdk_timeout_validation`
- `test_feature_command_sdk_timeout_passed_to_orchestrator`

## Dependencies

None - implemented independently

## Estimated Complexity: 3/10

**Breakdown**:
- CLI option addition: 1/10 (trivial)
- Cascade logic: 2/10 (straightforward)
- Testing: 2/10 (standard)
- Documentation: 1/10 (simple)

## Priority Justification

**CRITICAL**: Without this fix, Phase 4.5 test enforcement loop cannot complete for complex tasks, resulting in Player timeout and 100% work loss. This is the **primary blocker** identified in the review.

## References

- Review Report: `.claude/reviews/TASK-REV-9AC5-review-report.md`
- Finding 1: SDK Timeout Configuration Flow Gap
- Recommendation R1: Lines 629-648
