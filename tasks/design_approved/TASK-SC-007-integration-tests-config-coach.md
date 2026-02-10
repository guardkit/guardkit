---
complexity: 5
created: 2026-02-10 11:20:00+00:00
dependencies:
- TASK-SC-002
- TASK-SC-004
feature_id: FEAT-SC-001
id: TASK-SC-007
implementation_mode: task-work
parent_review: TASK-REV-AEA7
priority: high
status: design_approved
tags:
- integration-tests
- config
- coach
- seams
task_type: testing
title: 'Integration tests: config round-trip + coach validator wiring'
updated: 2026-02-10 11:20:00+00:00
wave: 3
---

# Task: Integration tests for config round-trip and coach validator wiring

## Description

Create integration tests that verify:
1. **Config round-trip**: `.guardkit/config.yaml` can be written, read, and updated correctly across context switches
2. **Coach context builder integration**: `build_coach_context()` correctly wires into the coach validation pipeline

These tests target two technology seams: YAML config persistence and the Graphiti → coach prompt assembly pipeline.

## Key Implementation Details

### Test Files

1. **`tests/integration/test_context_switch_config.py`**
2. **`tests/integration/test_coach_context_integration.py`**

### Config Round-Trip Tests

Use `tmp_path` fixture for isolated file system:

```python
@pytest.fixture
def config_dir(tmp_path):
    """Create a temporary .guardkit directory with config."""
    guardkit_dir = tmp_path / ".guardkit"
    guardkit_dir.mkdir()
    config_file = guardkit_dir / "config.yaml"
    config_file.write_text(yaml.safe_dump({
        "project": {
            "id": "guardkit",
            "name": "GuardKit CLI",
            "graphiti_prefix": "guardkit",
        },
        "known_projects": [
            {
                "id": "guardkit",
                "name": "GuardKit CLI",
                "path": str(tmp_path / "guardkit"),
                "last_accessed": "2026-02-09T10:30:00Z",
            },
            {
                "id": "requirekit",
                "name": "RequireKit",
                "path": str(tmp_path / "requirekit"),
                "last_accessed": "2026-02-08T14:00:00Z",
            },
        ],
    }))
    return guardkit_dir
```

#### Tests

- `test_switch_persists_to_config` — switch project, reload config, verify active project changed
- `test_switch_round_trip` — switch A→B→A, verify all state preserved
- `test_switch_updates_timestamp` — verify `last_accessed` is updated to current time
- `test_config_handles_missing_known_projects` — config without `known_projects` key
- `test_config_handles_empty_file` — empty config.yaml → graceful default
- `test_config_handles_corrupt_yaml` — invalid YAML → graceful error handling
- `test_config_concurrent_writes` — two rapid switches don't corrupt file
- `test_config_preserves_unknown_fields` — extra YAML fields not lost on save

### Coach Context Integration Tests

These verify the full pipeline: `build_coach_context()` → `SystemPlanGraphiti` → `condense_for_injection()` → formatted string.

```python
@pytest.fixture
def mock_client_with_arch():
    """Client with realistic architecture facts for coach context testing."""
    # Returns a MockGraphitiClient pre-loaded with arch facts
```

#### Tests

- `test_coach_context_complexity_gating` — verify each tier (1-3, 4-6, 7-8, 9-10)
- `test_coach_context_includes_overview` — complexity 5 → overview section present
- `test_coach_context_includes_impact` — complexity 7 → both overview + impact present
- `test_coach_context_respects_budget` — output token count within budget
- `test_coach_context_graphiti_down` — client.enabled=False → empty string, no error
- `test_coach_context_no_architecture` — no facts → empty string, no error
- `test_coach_context_impact_exception` — impact analysis raises → overview still returned
- `test_coach_context_output_format` — verify "## Architecture Context" and "## Task Impact" headers

### Cross-Module Integration Tests

These verify the seam between modules:

- `test_overview_to_coach_pipeline` — `get_system_overview` → `condense_for_injection` → `build_coach_context`
- `test_impact_to_coach_pipeline` — `run_impact_analysis` → `condense_impact_for_injection` → `build_coach_context`
- `test_full_coach_pipeline_realistic` — realistic facts → full pipeline → verify sensible output

## Acceptance Criteria

- [ ] 2 integration test files created
- [ ] At least 8 config round-trip tests
- [ ] At least 8 coach context integration tests
- [ ] At least 3 cross-module pipeline tests
- [ ] Config tests use `tmp_path` for file isolation
- [ ] Coach tests use mock Graphiti client (no Neo4j required)
- [ ] All tests pass with `pytest tests/integration/ -v`
- [ ] Edge cases covered: corrupt YAML, missing fields, Graphiti down

## Test Requirements

This IS the test task. Verify tests pass:
```bash
pytest tests/integration/test_context_switch_config.py tests/integration/test_coach_context_integration.py -v
```

## Implementation Notes

- Use `tmp_path` (pytest built-in) for config file tests
- Use `yaml.safe_load`/`yaml.safe_dump` matching production code
- Coach context tests reuse `MockGraphitiClient` from TASK-SC-006
- Consider extracting `MockGraphitiClient` to `tests/conftest.py` or `tests/helpers/`
- `pytest.mark.asyncio` for all async tests