---
id: TASK-SFT-001
title: Create tests/seam/ directory with conftest and pytest markers
task_type: scaffolding
parent_review: TASK-REV-AC1A
feature_id: FEAT-AC1A
wave: 1
implementation_mode: task-work
complexity: 2
dependencies: []
priority: high
status: blocked
autobuild_state:
  current_turn: 8
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AC1A
  base_branch: main
  started_at: '2026-02-14T09:55:45.174819'
  last_updated: '2026-02-14T11:43:35.645173'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Not all acceptance criteria met'
    timestamp: '2026-02-14T09:55:45.174819'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: '- task-work execution exceeded 1800s timeout'
    timestamp: '2026-02-14T10:03:32.477919'
    player_summary: '[RECOVERED via git_only] Original error: SDK timeout after 1800s:
      task-work execution exceeded 1800s timeout'
    player_success: true
    coach_success: true
  - turn: 3
    decision: feedback
    feedback: '- Not all acceptance criteria met'
    timestamp: '2026-02-14T10:33:59.054293'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 4
    decision: feedback
    feedback: '- task-work execution exceeded 1800s timeout'
    timestamp: '2026-02-14T10:36:25.956576'
    player_summary: '[RECOVERED via git_only] Original error: SDK timeout after 1800s:
      task-work execution exceeded 1800s timeout'
    player_success: true
    coach_success: true
  - turn: 5
    decision: feedback
    feedback: '- task-work execution exceeded 1800s timeout'
    timestamp: '2026-02-14T11:06:45.216593'
    player_summary: '[RECOVERED via git_only] Original error: SDK timeout after 1800s:
      task-work execution exceeded 1800s timeout'
    player_success: true
    coach_success: true
  - turn: 6
    decision: feedback
    feedback: '- Not all acceptance criteria met'
    timestamp: '2026-02-14T11:37:04.848051'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 7
    decision: feedback
    feedback: '- Not all acceptance criteria met'
    timestamp: '2026-02-14T11:38:44.293406'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 8
    decision: feedback
    feedback: '- Not all acceptance criteria met'
    timestamp: '2026-02-14T11:41:09.605076'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Create tests/seam/ Directory Structure

## Objective

Set up the `tests/seam/` directory with proper pytest configuration, conftest fixtures, and custom markers for seam tests.

## Acceptance Criteria

- [ ] `tests/seam/` directory exists with `__init__.py`
- [ ] `tests/seam/conftest.py` provides shared fixtures:
  - `graphiti_mock_client` — AsyncMock that records upsert calls (protocol-level mock, not function mock)
  - `cli_runner` — Click CliRunner configured for seam testing
  - `tmp_task_dir` — Temporary task directory with proper structure
  - `minimal_spec_fixture` — Path to minimal architecture spec for system-plan tests
- [ ] `pytest.ini` or `pyproject.toml` registers `@pytest.mark.seam` marker
- [ ] `tests/seam/` tests are discovered and run by `pytest tests/seam/`
- [ ] Existing tests in `tests/integration/test_system_plan_seams.py` and `tests/integration/test_planning_module_seams.py` are NOT moved (migration is a separate task)
- [ ] `tests/fixtures/minimal-spec.md` fixture file created for system-plan seam tests

## Implementation Notes

- Follow the existing `tests/e2e/conftest.py` pattern for fixture organisation
- The `graphiti_mock_client` must be an AsyncMock with `.enabled = True` so `SystemPlanGraphiti` treats it as a real client
- Do NOT add test files yet — this is scaffolding only
