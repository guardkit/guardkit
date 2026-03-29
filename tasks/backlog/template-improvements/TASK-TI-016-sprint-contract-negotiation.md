---
id: TASK-TI-016
title: Sprint contract negotiation pattern
status: backlog
created: 2026-03-27T22:00:00Z
updated: 2026-03-27T22:00:00Z
priority: p3
tags: [template, adversarial, orchestration, sprint]
complexity: 5
parent_review: TASK-REV-TRF12
feature_id: FEAT-TI
wave: 4
implementation_mode: task-work
depends_on: [TASK-TI-010, TASK-TI-015]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Sprint Contract Negotiation Pattern

## Description

Implement the sprint contract negotiation pattern from Anthropic's adversarial cooperation approach. Before generation begins, the Orchestrator and Player negotiate scope (what to generate, quality expectations, constraints) to reduce revision cycles.

## What to Build

### Sprint Contract
A structured agreement between Orchestrator and Player before generation:

```python
@dataclass
class SprintContract:
    targets: list[Target]           # What to generate
    quality_bar: QualityThreshold   # Minimum acceptance criteria
    constraints: list[str]          # Budget, format, domain rules
    max_turns: int                  # Max Player-Coach revision cycles
    escalation_policy: str          # What happens on repeated rejection
```

### Negotiation Flow
1. **Orchestrator proposes**: Initial contract based on GOAL.md and target batch
2. **Player reviews**: Checks feasibility (context window, tool availability, domain coverage)
3. **Player counter-proposes**: Adjusts targets, requests more context, flags constraints
4. **Orchestrator accepts/adjusts**: Final contract agreed
5. **Execution**: Player generates against agreed contract; Coach evaluates against same criteria

### Benefits
- Reduces revision cycles (Player knows expectations upfront)
- Prevents scope creep (agreed max_turns)
- Enables Player to request additional context before generation
- Matches Anthropic's recommended "negotiate before execute" pattern

### Escalation Policies
- `retry`: Coach rejection triggers retry with feedback (default)
- `escalate`: After N rejections, escalate to human (via HITL hooks)
- `skip`: After N rejections, skip target and log
- `abort`: After N rejections, abort entire sprint

## Acceptance Criteria

- [ ] SprintContract dataclass with all fields
- [ ] Negotiation flow: propose -> review -> counter-propose -> accept
- [ ] Player feasibility check (can it handle the targets?)
- [ ] Four escalation policies implemented
- [ ] Contract logged for audit trail
- [ ] Integration with HITL hooks for escalation
- [ ] Unit tests for negotiation flow and escalation
- [ ] Integration test: full negotiate -> execute -> evaluate cycle

## Effort Estimate

1-2 days
