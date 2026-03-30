---
id: TASK-TI-014
title: Configurable adversarial intensity (full / light / solo)
status: completed
created: 2026-03-27T22:00:00Z
updated: 2026-03-29T00:00:00Z
completed: 2026-03-29T00:00:00Z
completed_location: tasks/completed/TASK-TI-014/
priority: p3
tags: [template, adversarial, configuration]
complexity: 4
parent_review: TASK-REV-TRF12
feature_id: FEAT-TI
wave: 4
implementation_mode: task-work
depends_on: [TASK-TI-009]
previous_state: in_review
state_transition_reason: "All acceptance criteria met, 71/71 tests passing"
test_results:
  status: passed
  total: 71
  passed: 71
  failed: 0
  coverage: null
  last_run: 2026-03-29T00:00:00Z
organized_files:
  - TASK-TI-014.md
---

# Task: Configurable Adversarial Intensity

## Description

Make the adversarial cooperation pattern configurable with three intensity levels, allowing developers to start simple and increase rigour as needed.

## What to Build

### Intensity Levels

| Level | Coach Behaviour | Use Case |
|-------|----------------|----------|
| **full** | Coach evaluates every Player output | Production quality, high-stakes domains |
| **light** | Coach spot-checks (e.g., every 3rd output) | Development iteration, cost-sensitive |
| **solo** | No Coach — Player output accepted directly | Prototyping, single-agent testing |

### Configuration
```yaml
# adversarial-config.yaml
adversarial:
  intensity: full          # full | light | solo
  light_sample_rate: 0.33  # For light mode: fraction of outputs evaluated
  solo_bypass_validation: false  # In solo mode, still run validation pipeline?
```

### Orchestrator Behaviour
- `full`: Every output goes through Coach evaluation
- `light`: Random sampling with configurable rate; unevaluated outputs still pass through validation pipeline
- `solo`: Skip Coach entirely; optionally bypass validation (for rapid prototyping)

### Transition Support
- Developers can start in `solo` mode during development
- Switch to `light` during testing
- Deploy in `full` for production
- No code changes required — configuration only

## Acceptance Criteria

- [x] Three intensity levels implemented in orchestrator
- [x] Configuration via YAML with sensible defaults
- [x] Light mode samples at configurable rate
- [x] Solo mode optionally bypasses validation
- [x] Intensity can be changed without code changes
- [x] Unit tests for each intensity level
- [x] Logging indicates which mode is active

## Implementation Summary

### Files Modified
1. `installer/core/templates/langchain-deepagents-weighted-evaluation/config/adversarial_config.py`
   - Added `light_sample_rate` (default: 0.33) and `solo_bypass_validation` (default: False) to `DEFAULT_CONFIG`
   - Added `IntensityRouter` class with `should_evaluate()` and `should_validate()` routing methods
   - Logging on init (`logger.info`) and sampling decisions (`logger.debug`)

2. `installer/core/templates/langchain-deepagents-weighted-evaluation/scaffold/pipeline.py.j2`
   - Wired `IntensityRouter` into `WeightedEvaluationPipeline.__init__`
   - Exposed via `intensity_router` property

3. `installer/core/templates/langchain-deepagents-weighted-evaluation/tests/test_scaffold.py`
   - Added `TestIntensityRouter` class with 18 tests covering all modes, edge cases, YAML overrides, and logging
