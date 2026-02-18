---
id: TASK-BOOT-99A5
title: Integration test for cross-component requires_infrastructure propagation
status: completed
created: 2026-02-18T00:00:00Z
updated: 2026-02-18T12:00:00Z
completed: 2026-02-18T12:00:00Z
completed_location: tasks/completed/TASK-BOOT-99A5/
priority: high
tags: [autobuild, environment-bootstrap, integration-test, regression-prevention]
task_type: feature
complexity: 4
parent_review: TASK-REV-C9E5
feature_id: FEAT-BOOT
wave: 2
implementation_mode: task-work
dependencies:
  - TASK-BOOT-B032
---

# Task: Integration test for cross-component requires_infrastructure propagation

## Description

Unit tests verify individual components but no test exercises the full `FeatureOrchestrator` → `AutoBuildOrchestrator` → `CoachValidator` chain with `requires_infrastructure` flowing through. This propagation gap went undetected despite comprehensive unit test coverage.

This task adds integration tests that verify the cross-component data flow and a Docker smoke test to validate the Docker lifecycle path is reachable.

See: `.claude/reviews/TASK-REV-C9E5-review-report.md` (Revision 3) — Finding 9 (F9) and Recommendation 5 (R5).

## Context

Existing Docker-related tests in `tests/unit/test_docker_fixtures.py` and `tests/unit/test_docker_available_wiring.py` mock `subprocess.run`. They verify the component interfaces but not the data flow between them. The propagation gap (F3) passed all unit tests because each component was correct in isolation.

## Acceptance Criteria

- [x] Integration test: `FeatureOrchestrator._execute_task()` passes `requires_infrastructure` to `orchestrate()` (validates R1/TASK-BOOT-B032)
- [x] Integration test: `AutoBuildOrchestrator` propagates `requires_infrastructure` to Coach task dict
- [x] Integration test: `CoachValidator` receives correct `requires_infrastructure` value and enters Docker lifecycle guard
- [x] Integration test: frontmatter fallback works when `requires_infrastructure` parameter is None (single-task mode)
- [x] Docker smoke test: `_is_docker_available()` returns a boolean (not mocked) to verify Docker reachability in test environment
- [x] All tests use generic service name (e.g., `["test-service"]`) — stack-agnostic
- [x] Tests are fast (mock external calls, only test data flow)

## Implementation Notes

### Integration test 1: End-to-end propagation

```python
def test_requires_infrastructure_propagates_from_feature_to_coach():
    """Verify requires_infrastructure flows: Feature YAML → FeatureOrchestrator → AutoBuild → Coach."""
    # Setup: mock feature YAML with requires_infrastructure: [test-service]
    # Setup: mock TaskLoader to return task WITHOUT requires_infrastructure in frontmatter
    # Setup: mock AutoBuildOrchestrator.orchestrate() to capture args

    # Act: call FeatureOrchestrator._execute_task()

    # Assert: orchestrate() was called WITH requires_infrastructure=[test-service]
```

### Integration test 2: Coach receives correct value

```python
def test_coach_receives_requires_infrastructure_in_task_dict():
    """Verify CoachValidator.validate() receives requires_infrastructure from orchestrate()."""
    # Setup: mock _invoke_coach_safely to capture task dict
    # Setup: call orchestrate() with requires_infrastructure=["test-service"]

    # Assert: task dict contains {"requires_infrastructure": ["test-service"]}
    # Assert: Docker lifecycle guard is entered (if requires_infra is truthy)
```

### Integration test 3: Frontmatter fallback

```python
def test_frontmatter_fallback_when_no_explicit_parameter():
    """Verify orchestrate() falls back to frontmatter when requires_infrastructure=None."""
    # Setup: mock TaskLoader to return task WITH requires_infrastructure in frontmatter
    # Setup: call orchestrate() WITHOUT requires_infrastructure parameter

    # Assert: requires_infrastructure loaded from frontmatter
```

### Docker smoke test

```python
@pytest.mark.skipif(not shutil.which("docker"), reason="Docker not installed")
def test_is_docker_available_returns_boolean():
    """Smoke test: _is_docker_available() returns a boolean without mocking."""
    validator = CoachValidator(task_id="test", worktree_path=tmp_path)
    result = validator._is_docker_available()
    assert isinstance(result, bool)
    # Note: we don't assert True/False — Docker may or may not be running.
    # This test verifies the method executes without error.
```

## Files to Modify

| File | Changes |
|------|---------|
| `tests/integration/test_requires_infra_propagation.py` | NEW: end-to-end propagation tests |
| `tests/integration/test_docker_smoke.py` | NEW: Docker reachability smoke test |

## Source Review

- Review report: `.claude/reviews/TASK-REV-C9E5-review-report.md` (Revision 3)
- Evidence: `docs/reviews/autobuild-fixes/db_failed_after_env_changes.md`
- Existing tests: `tests/unit/test_docker_fixtures.py`, `tests/unit/test_docker_available_wiring.py`
