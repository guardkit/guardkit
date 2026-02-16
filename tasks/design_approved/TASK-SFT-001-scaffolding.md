---
autobuild_state:
  base_branch: main
  current_turn: 3
  last_updated: '2026-02-15T20:33:40.105919'
  max_turns: 30
  started_at: '2026-02-15T20:25:16.325736'
  turns:
  - coach_success: true
    decision: feedback
    feedback: "- Not all acceptance criteria met:\n  • `pytest.ini` or `pyproject.toml`
      registers `@pytest.mark.seam` marker\n  • `tests/seam/` tests are discovered
      and run by `pytest tests/seam/`\n  • Existing tests in `tests/integration/test_system_plan_seams.py`
      and `tests/integration/test_planning\n  • `tests/fixtures/minimal-spec.md` fixture
      file created for system-plan seam tests"
    player_success: true
    player_summary: Implementation via task-work delegation
    timestamp: '2026-02-15T20:25:16.325736'
    turn: 1
  - coach_success: true
    decision: feedback
    feedback: "- Not all acceptance criteria met:\n  • `pytest.ini` or `pyproject.toml`
      registers `@pytest.mark.seam` marker\n  • `tests/seam/` tests are discovered
      and run by `pytest tests/seam/`\n  • Existing tests in `tests/integration/test_system_plan_seams.py`
      and `tests/integration/test_planning\n  • `tests/fixtures/minimal-spec.md` fixture
      file created for system-plan seam tests"
    player_success: true
    player_summary: Implementation via task-work delegation
    timestamp: '2026-02-15T20:28:46.981726'
    turn: 2
  - coach_success: true
    decision: feedback
    feedback: "- Not all acceptance criteria met:\n  • `pytest.ini` or `pyproject.toml`
      registers `@pytest.mark.seam` marker\n  • `tests/seam/` tests are discovered
      and run by `pytest tests/seam/`\n  • Existing tests in `tests/integration/test_system_plan_seams.py`
      and `tests/integration/test_planning\n  • `tests/fixtures/minimal-spec.md` fixture
      file created for system-plan seam tests"
    player_success: true
    player_summary: Implementation via task-work delegation
    timestamp: '2026-02-15T20:31:27.448881'
    turn: 3
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AC1A
complexity: 2
dependencies: []
feature_id: FEAT-AC1A
id: TASK-SFT-001
implementation_mode: task-work
parent_review: TASK-REV-AC1A
priority: high
status: design_approved
task_type: scaffolding
title: Create tests/seam/ directory with conftest and pytest markers
wave: 1
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