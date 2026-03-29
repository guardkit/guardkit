---
id: TASK-TI-014
title: Configurable adversarial intensity (full / light / solo)
status: backlog
created: 2026-03-27T22:00:00Z
updated: 2026-03-27T22:00:00Z
priority: p3
tags: [template, adversarial, configuration]
complexity: 4
parent_review: TASK-REV-TRF12
feature_id: FEAT-TI
wave: 4
implementation_mode: task-work
depends_on: [TASK-TI-009]
test_results:
  status: pending
  coverage: null
  last_run: null
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

- [ ] Three intensity levels implemented in orchestrator
- [ ] Configuration via YAML with sensible defaults
- [ ] Light mode samples at configurable rate
- [ ] Solo mode optionally bypasses validation
- [ ] Intensity can be changed without code changes
- [ ] Unit tests for each intensity level
- [ ] Logging indicates which mode is active

## Effort Estimate

1 day
