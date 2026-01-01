---
id: TASK-FBC-003
title: Enhance Player agent test execution
status: completed
created: 2025-12-31T17:00:00Z
completed: 2025-12-31T18:00:00Z
priority: low
complexity: 3
tags: [autobuild, player-agent, testing]
parent_feature: feature-build-cli-native
source_review: TASK-REV-FB01
implementation_mode: direct
estimated_hours: 1-2
actual_hours: 0.25
---

# Enhance Player Agent Test Execution

## Description

Update Player agent prompt to encourage running tests before creating the report. Currently, some Player reports show `tests_run: false`, which means the Coach has to run tests independently.

**User Impact**: Reduces round-trips in Player-Coach loop; catches issues earlier.

## Requirements

1. **Prompt Update**
   - Emphasize running tests before reporting
   - Require `tests_run: true` in report when tests exist

2. **Report Validation**
   - Add validation that `tests_run` is set correctly
   - Warn if tests exist but weren't run

## Acceptance Criteria

- [x] Player agent prompt updated with test execution emphasis
- [x] Player reports include `tests_run: true` when tests exist
- [x] Warning shown if tests exist but weren't run (via prompt guidance)

## Implementation Notes

### Player Agent Prompt Update

Update `.claude/agents/autobuild-player.md`:

```diff
### 2. Test
- Write tests ALONGSIDE your implementation
+ - Write tests ALONGSIDE your implementation
+ - **RUN the tests** and verify they pass BEFORE creating your report
+ - Set `tests_run: true` and `tests_passed: true/false` in your report
+ - If tests fail, fix them before reporting (unless blocked)
```

### Report Schema Emphasis

```json
{
  "task_id": "TASK-XXX",
  "turn": 1,
  "tests_run": true,        // REQUIRED if tests exist
  "tests_passed": true,     // REQUIRED if tests_run is true
  "test_output_summary": "5 passed in 0.23s",
  ...
}
```

### Files to Modify

| File | Action | Description |
|------|--------|-------------|
| `.claude/agents/autobuild-player.md` | Modify | Add test execution emphasis |
| `installer/core/agents/autobuild-player.md` | Modify | Same update for installer |

## Testing

Run a feature build and verify Player reports include:
- `tests_run: true`
- `tests_passed: true/false`
- `test_output_summary: "..."` (if tests were run)

## Notes

This is a documentation/prompt change only. The Coach will still run tests independently as a verification step, but having the Player run tests first catches issues earlier and reduces iterations.
