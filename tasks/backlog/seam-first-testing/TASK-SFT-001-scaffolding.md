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
  current_turn: 3
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AC1A
  base_branch: main
  started_at: '2026-02-15T16:17:44.726437'
  last_updated: '2026-02-15T16:25:44.804940'
  turns:
  - turn: 1
    decision: feedback
    feedback: "- Not all acceptance criteria met:\n  \u2022 `tests/seam/` directory\
      \ exists with `__init__.py`\n  \u2022 `tests/seam/conftest.py` provides shared\
      \ fixtures:\n  \u2022 `graphiti_mock_client` \u2014 AsyncMock that records upsert\
      \ calls (protocol-level mock, not function mock\n  \u2022 `cli_runner` \u2014\
      \ Click CliRunner configured for seam testing\n  \u2022 `tmp_task_dir` \u2014\
      \ Temporary task directory with proper structure\n  (5 more)"
    timestamp: '2026-02-15T16:17:44.726437'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: "- Not all acceptance criteria met:\n  \u2022 `tests/seam/` directory\
      \ exists with `__init__.py`\n  \u2022 `tests/seam/conftest.py` provides shared\
      \ fixtures:\n  \u2022 `graphiti_mock_client` \u2014 AsyncMock that records upsert\
      \ calls (protocol-level mock, not function mock\n  \u2022 `cli_runner` \u2014\
      \ Click CliRunner configured for seam testing\n  \u2022 `tmp_task_dir` \u2014\
      \ Temporary task directory with proper structure\n  (5 more)"
    timestamp: '2026-02-15T16:21:51.614526'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 3
    decision: feedback
    feedback: "- Not all acceptance criteria met:\n  \u2022 `tests/seam/` directory\
      \ exists with `__init__.py`\n  \u2022 `tests/seam/conftest.py` provides shared\
      \ fixtures:\n  \u2022 `graphiti_mock_client` \u2014 AsyncMock that records upsert\
      \ calls (protocol-level mock, not function mock\n  \u2022 `cli_runner` \u2014\
      \ Click CliRunner configured for seam testing\n  \u2022 `tmp_task_dir` \u2014\
      \ Temporary task directory with proper structure\n  (5 more)"
    timestamp: '2026-02-15T16:23:39.229347'
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
