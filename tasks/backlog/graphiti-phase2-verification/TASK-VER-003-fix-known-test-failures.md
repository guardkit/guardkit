---
id: TASK-VER-003
title: Fix Known Test Failures in FEAT-0F4A
status: backlog
created: 2026-02-01T20:00:00Z
updated: 2026-02-01T20:00:00Z
priority: high
complexity: 3
implementation_mode: task-work
wave: 1
parallel_group: wave1
parent_review: TASK-REV-0F4A
feature_id: FEAT-VER-0F4A
tags: [verification, testing, bug-fix, graphiti]
estimated_minutes: 60
---

# Task: Fix Known Test Failures in FEAT-0F4A

## Description

Fix the known test failure identified during the architectural review. The `test_status_shows_seeding_state` test fails due to a mock configuration issue.

## Acceptance Criteria

- [ ] `test_status_shows_seeding_state` passes
- [ ] No new test failures introduced
- [ ] Mock properly returns awaitable for async calls
- [ ] All 256 tests pass (255 + fixed test)

## Known Failure Details

**Test**: `tests/cli/test_graphiti.py::TestGraphitiStatusCommand::test_status_shows_seeding_state`

**Error**: `'MagicMock' object can't be awaited`

**Root Cause**: The mock for the status command doesn't properly handle async/await. The graphiti client's async methods return `MagicMock` instead of `AsyncMock`.

## Implementation Steps

1. Navigate to worktree:
   ```bash
   cd .guardkit/worktrees/FEAT-0F4A
   ```

2. Read the failing test:
   ```bash
   cat tests/cli/test_graphiti.py | grep -A 30 "test_status_shows_seeding_state"
   ```

3. Identify mock configuration:
   - Find where `get_graphiti` is mocked
   - Check if async methods use `AsyncMock`

4. Fix the mock:
   ```python
   # Change from:
   mock_client.search = MagicMock(return_value=[...])

   # To:
   mock_client.search = AsyncMock(return_value=[...])
   ```

5. Run the specific test:
   ```bash
   pytest tests/cli/test_graphiti.py::TestGraphitiStatusCommand::test_status_shows_seeding_state -v
   ```

6. Run full test suite to verify no regressions:
   ```bash
   pytest tests/cli/test_graphiti*.py -v --tb=short
   ```

## Verification Command

```bash
cd .guardkit/worktrees/FEAT-0F4A && \
pytest tests/cli/test_graphiti.py::TestGraphitiStatusCommand::test_status_shows_seeding_state -v
```

## References

- Review Report: `.claude/reviews/TASK-REV-0F4A-review-report.md`
- Test file: `tests/cli/test_graphiti.py`
