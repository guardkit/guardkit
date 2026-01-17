---
id: TASK-INT-i9j0
title: Add integration tests for intensity system
status: in_review
created: 2026-01-17T14:30:00Z
updated: 2026-01-17T19:55:00Z
previous_state: in_progress
state_transition_reason: "All quality gates passed - ready for human review"
quality_gates:
  compilation: passed
  tests_passing: "42/42 (100%)"
  line_coverage: "100%"
  branch_coverage: "100%"
  code_review_score: "HIGH"
priority: medium
tags:
  - intensity-system
  - testing
  - integration
complexity: 3
parent_review: TASK-REV-FB16
feature: provenance-intensity
wave: 3
implementation_mode: task-work
estimated_minutes: 90
conductor_workspace: provenance-int-wave3-1
dependencies:
  - TASK-INT-e5f6
  - TASK-INT-g7h8
---

# Add Integration Tests for Intensity System

## Description

Create integration tests that verify the complete intensity system works end-to-end:

1. Provenance field detection
2. Auto-detection logic
3. Phase skipping behavior
4. Flag override functionality

## Acceptance Criteria

- [ ] Test: Task with parent_review triggers minimal intensity
- [ ] Test: Task with feature_id triggers light intensity
- [ ] Test: Fresh task uses complexity-based detection
- [ ] Test: --intensity flag overrides auto-detection
- [ ] Test: --micro works as alias for --intensity=minimal
- [ ] Test: High-risk keywords force strict intensity
- [ ] Test: Phase configuration matches intensity level
- [ ] All tests pass in CI

## Technical Approach

### 1. Test Fixtures

Create test task files:

```yaml
# tests/fixtures/intensity/task-from-review.md
---
id: TASK-TEST-001
title: Test task from review
complexity: 3
parent_review: TASK-REV-TEST
---

# tests/fixtures/intensity/task-from-feature.md
---
id: TASK-TEST-002
title: Test task from feature plan
complexity: 4
feature_id: FEAT-TEST
---

# tests/fixtures/intensity/task-fresh-simple.md
---
id: TASK-TEST-003
title: Fix typo in readme
complexity: 2
---

# tests/fixtures/intensity/task-fresh-complex.md
---
id: TASK-TEST-004
title: Implement authentication system
complexity: 8
---
```

### 2. Test Cases

```python
# tests/integration/test_intensity_system.py

class TestIntensityDetection:
    """Test provenance-aware intensity detection."""

    def test_task_from_review_gets_minimal(self):
        """Task with parent_review should get minimal intensity."""
        task = load_task("tests/fixtures/intensity/task-from-review.md")
        intensity = determine_intensity(task)
        assert intensity == Intensity.MINIMAL

    def test_task_from_feature_gets_light(self):
        """Task with feature_id should get light intensity."""
        task = load_task("tests/fixtures/intensity/task-from-feature.md")
        intensity = determine_intensity(task)
        assert intensity == Intensity.LIGHT

    def test_fresh_simple_gets_minimal(self):
        """Fresh task with complexity ≤3 should get minimal."""
        task = load_task("tests/fixtures/intensity/task-fresh-simple.md")
        intensity = determine_intensity(task)
        assert intensity == Intensity.MINIMAL

    def test_fresh_complex_gets_strict(self):
        """Fresh task with complexity 8 should get strict."""
        task = load_task("tests/fixtures/intensity/task-fresh-complex.md")
        intensity = determine_intensity(task)
        assert intensity == Intensity.STRICT


class TestIntensityOverride:
    """Test --intensity flag override behavior."""

    def test_flag_overrides_auto_detection(self):
        """Explicit --intensity flag should override auto-detection."""
        task = load_task("tests/fixtures/intensity/task-from-review.md")
        intensity = resolve_intensity(task, flag_value="strict")
        assert intensity == Intensity.STRICT

    def test_micro_flag_is_minimal_alias(self):
        """--micro should be alias for --intensity=minimal."""
        intensity = parse_intensity(micro=True, intensity=None)
        assert intensity == Intensity.MINIMAL


class TestPhaseConfiguration:
    """Test that phases are configured correctly per intensity."""

    def test_minimal_skips_planning(self):
        """Minimal intensity should skip Phase 2."""
        config = get_phase_config(Intensity.MINIMAL)
        assert Phase.PLANNING not in config.active_phases

    def test_light_includes_brief_planning(self):
        """Light intensity should include brief Phase 2."""
        config = get_phase_config(Intensity.LIGHT)
        assert Phase.PLANNING in config.active_phases
        assert config.planning_mode == PlanningMode.BRIEF

    def test_strict_has_blocking_checkpoint(self):
        """Strict intensity should have blocking checkpoint."""
        config = get_phase_config(Intensity.STRICT)
        assert config.checkpoint_timeout is None  # Blocking
```

## Files to Create

- `tests/integration/test_intensity_system.py` - Main test file
- `tests/fixtures/intensity/*.md` - Test task fixtures

## Test Requirements

- [ ] All tests pass locally
- [ ] Tests run in CI pipeline
- [ ] Coverage report shows intensity module covered
- [ ] Edge cases tested (empty provenance, invalid intensity)

## Notes

Focus on behavioral tests that verify the system works as documented. Don't over-test implementation details - the goal is to catch regressions if the intensity logic changes.

These tests validate the user feedback: tasks from `/task-review` should get minimal intensity and complete in 10-20 minutes instead of 65+ minutes.
