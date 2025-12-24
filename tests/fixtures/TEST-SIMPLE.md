---
id: TEST-SIMPLE
title: Simple task for AutoBuild testing
status: backlog
created: 2025-12-24T00:00:00Z
updated: 2025-12-24T00:00:00Z
assignee: test_user
priority: medium
complexity: 2
requirements: []
autobuild:
  enabled: true
  max_turns: 5
  base_branch: main
  expected_turns: 1
---

# Simple task for AutoBuild testing

## Description
This is a simple test task that should complete in 1-2 turns.
The implementation is straightforward and should not require iteration.

## Acceptance Criteria
- [ ] Create a simple utility function
- [ ] Add basic unit tests
- [ ] Ensure tests pass

## Implementation Notes
This task is designed to test the happy path of AutoBuild orchestration:
- Single-turn approval expected
- Minimal complexity
- Quick execution
