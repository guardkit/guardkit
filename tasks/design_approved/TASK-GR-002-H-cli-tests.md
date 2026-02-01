---
complexity: 3
conductor_workspace: gr-mvp-wave9-tests
created: 2026-01-30 00:00:00+00:00
depends_on:
- TASK-GR-002-F
feature_id: FEAT-GR-MVP
id: TASK-GR-002-H
implementation_mode: task-work
parent_review: TASK-REV-1505
priority: high
status: design_approved
tags:
- graphiti
- context-addition
- testing
- cli
- mvp-phase-2
task_type: testing
title: Tests for CLI command
updated: 2026-01-30 00:00:00+00:00
wave: 9
---

# Task: Tests for CLI command

## Description

Create comprehensive tests for the `guardkit graphiti add-context` CLI command.

## Acceptance Criteria

- [ ] Unit tests for command logic
- [ ] Tests for all flags (--type, --force, --dry-run, etc.)
- [ ] Integration tests with mocked Graphiti
- [ ] Tests for error handling
- [ ] 80%+ coverage for CLI code

## Implementation Notes

### Test Structure

```
tests/
├── unit/
│   └── cli/
│       └── commands/
│           └── test_graphiti_add_context.py
└── integration/
    └── cli/
        └── test_graphiti_cli_integration.py
```

### Test Cases

```python
class TestAddContextCommand:
    def test_add_single_file(self, tmp_path, mock_graphiti):
        """Test adding single file."""
        pass

    def test_add_directory(self, tmp_path, mock_graphiti):
        """Test adding directory with pattern."""
        pass

    def test_dry_run(self, tmp_path, mock_graphiti):
        """Test dry-run mode."""
        pass

    def test_force_overwrite(self, tmp_path, mock_graphiti):
        """Test --force flag."""
        pass

    def test_type_override(self, tmp_path, mock_graphiti):
        """Test --type flag."""
        pass

    def test_unsupported_file(self, tmp_path, mock_graphiti):
        """Test handling unsupported files."""
        pass

    def test_graphiti_unavailable(self, tmp_path, mock_unavailable):
        """Test graceful degradation."""
        pass
```

### Mock Fixtures

```python
@pytest.fixture
def mock_graphiti(mocker):
    """Mock GraphitiClient."""
    mock = mocker.patch("guardkit.integrations.graphiti.client.GraphitiClient")
    mock.return_value.upsert_episode.return_value = MagicMock()
    return mock

@pytest.fixture
def mock_unavailable(mocker):
    """Mock unavailable Graphiti."""
    mock = mocker.patch("guardkit.integrations.graphiti.client.GraphitiClient")
    mock.return_value.upsert_episode.side_effect = GraphitiUnavailable()
    return mock
```

### Files to Create

- `tests/unit/cli/commands/test_graphiti_add_context.py`
- `tests/integration/cli/test_graphiti_cli_integration.py`

## Test Requirements

- [ ] All tests pass
- [ ] 80%+ coverage for CLI code
- [ ] Error cases covered

## Notes

Tests complement parser tests (TASK-GR-002-G).

## References

- [FEAT-GR-002 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-002-context-addition-command.md)