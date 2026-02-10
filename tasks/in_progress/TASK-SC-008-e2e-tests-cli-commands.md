---
complexity: 5
created: 2026-02-10 11:20:00+00:00
dependencies:
- TASK-SC-005
- TASK-SC-006
- TASK-SC-007
feature_id: FEAT-SC-001
id: TASK-SC-008
implementation_mode: task-work
parent_review: TASK-REV-AEA7
priority: high
status: design_approved
tags:
- e2e-tests
- cli
- commands
task_type: testing
title: 'E2E tests: CLI command invocation for all 3 commands'
updated: 2026-02-10 11:20:00+00:00
wave: 4
---

# Task: E2E tests for CLI command invocation

## Description

Create end-to-end tests that verify the full command invocation path for all 3 new commands. These tests use Click's `CliRunner` to invoke the actual CLI commands and verify output format, error handling, and graceful degradation.

**Why this matters**: CLI wiring is a common failure point — commands that work in isolation can fail when registered in Click groups, when argument parsing encounters edge cases, or when output formatting breaks in terminal contexts.

## Key Implementation Details

### Test File

**`tests/e2e/test_system_context_commands.py`**

### Test Infrastructure

```python
import pytest
from click.testing import CliRunner
from guardkit.cli.main import cli  # Main Click group

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def mock_graphiti_available(monkeypatch):
    """Patch Graphiti to return realistic data without Neo4j."""
    # Patch get_graphiti() to return mock client
    # Patch SystemPlanGraphiti methods
    pass

@pytest.fixture
def mock_graphiti_unavailable(monkeypatch):
    """Patch Graphiti to simulate unavailability."""
    pass

@pytest.fixture
def config_env(tmp_path, monkeypatch):
    """Set up .guardkit/config.yaml in temporary directory."""
    pass
```

### /system-overview E2E Tests

- `test_system_overview_default` — `guardkit system-overview` → formatted display output
- `test_system_overview_verbose` — `--verbose` flag → extended output
- `test_system_overview_section_filter` — `--section=decisions` → only decisions section
- `test_system_overview_json_format` — `--format=json` → valid JSON output
- `test_system_overview_no_context` — no architecture → helpful suggestion message
- `test_system_overview_graphiti_down` — Graphiti unavailable → fallback message
- `test_system_overview_exit_code` — successful invocation → exit code 0

### /impact-analysis E2E Tests

- `test_impact_analysis_task_id` — `guardkit impact-analysis TASK-XXX` → formatted analysis
- `test_impact_analysis_topic` — `guardkit impact-analysis "add MFA"` → formatted analysis
- `test_impact_analysis_quick_depth` — `--depth=quick` → abbreviated output
- `test_impact_analysis_deep_depth` — `--depth=deep` → includes BDD section
- `test_impact_analysis_include_bdd` — `--include-bdd` flag
- `test_impact_analysis_no_context` — no architecture → suggestion message
- `test_impact_analysis_invalid_task_id` — nonexistent task → error message
- `test_impact_analysis_exit_code` — successful invocation → exit code 0

### /context-switch E2E Tests

- `test_context_switch_to_project` — `guardkit context-switch requirekit` → switch display
- `test_context_switch_list` — `guardkit context-switch --list` → project list
- `test_context_switch_no_args` — `guardkit context-switch` → current project
- `test_context_switch_unknown_project` — unknown name → error with suggestion
- `test_context_switch_graphiti_down` — switch works, overview shows warning
- `test_context_switch_exit_code` — successful invocation → exit code 0

### Cross-Command E2E Tests

These test realistic workflows spanning multiple commands:

- `test_overview_then_impact` — overview → impact-analysis → verify consistent data
- `test_switch_then_overview` — context-switch → system-overview → verify project context
- `test_all_commands_no_context` — all 3 commands on fresh project → all show helpful messages

### Output Format Verification

Tests should verify:
- Terminal box drawing characters present in display mode
- JSON is valid and parseable
- Risk bar format in impact analysis
- Section headers present
- Graceful degradation messages match spec

## Acceptance Criteria

- [ ] E2E test file created with at least 20 tests
- [ ] All 3 commands tested via Click CliRunner
- [ ] Each command tested for: success, no context, Graphiti down
- [ ] /system-overview: verbose, section filter, JSON format tested
- [ ] /impact-analysis: task ID, topic, depth tiers tested
- [ ] /context-switch: switch, list, no-args, unknown project tested
- [ ] Cross-command workflows tested (3+ workflow tests)
- [ ] Exit codes verified for all scenarios
- [ ] All tests pass without running Neo4j

## Test Requirements

This IS the test task. Verify tests pass:
```bash
pytest tests/e2e/test_system_context_commands.py -v
```

## Implementation Notes

- Click CliRunner provides `invoke()` method that captures output
- Use `result.exit_code`, `result.output`, `result.exception` for assertions
- `monkeypatch` to mock Graphiti at the import level
- Config tests need `tmp_path` for isolated config files
- `env` parameter in CliRunner for environment variable overrides
- Follow existing E2E test patterns if any exist in `tests/e2e/`
- If `tests/e2e/` doesn't exist, create it with appropriate `__init__.py` and `conftest.py`