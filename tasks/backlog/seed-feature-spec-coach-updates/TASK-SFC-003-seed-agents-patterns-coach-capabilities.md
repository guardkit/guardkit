---
id: TASK-SFC-003
title: Update seed_agents.py and seed_patterns.py with Coach capabilities
task_type: implementation
status: backlog
created: 2026-02-23T14:00:00Z
updated: 2026-02-23T14:00:00Z
priority: high
tags: [graphiti, seeding, autobuild-coach, seed-agents, seed-patterns]
complexity: 2
parent_review: TASK-REV-5FA4
feature_id: FEAT-SFC
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Update seed_agents.py and seed_patterns.py with Coach Capabilities

## Description

Update the `agent_autobuild_coach` episode in `seed_agents.py` to include Promise Verification and Honesty Verification capabilities, and update the `pattern_player_coach` episode in `seed_patterns.py` to include these new concepts.

This addresses findings F5 (HIGH) and F10 (MEDIUM) from the TASK-REV-5FA4 review.

## Context

- Source of truth: `.claude/agents/autobuild-coach.md`
- `seed_agents.py` provides lightweight agent metadata for semantic search
- `seed_patterns.py` provides design pattern descriptions

## Changes Required

### 1. Update `agent_autobuild_coach` in `seed_agents.py`

Replace the existing episode with:

```python
("agent_autobuild_coach", {
    "entity_type": "agent",
    "id": "autobuild-coach",
    "name": "AutoBuild Coach Agent",
    "role": "Validates Player implementations in Player-Coach pattern",
    "capabilities": [
        "Implementation validation",
        "Independent test execution",
        "Acceptance criteria verification",
        "Promise Verification (criteria_verification with criterion_id tracking)",
        "Honesty Verification (pre-validated by CoachVerifier, honesty_score 0.0-1.0)"
    ],
    "critical_note": "Coach has READ-ONLY access, validates but cannot modify"
}),
```

### 2. Update `pattern_player_coach` in `seed_patterns.py`

Replace the existing episode with:

```python
("pattern_player_coach", {
    "entity_type": "pattern",
    "id": "player_coach_adversarial",
    "name": "Player-Coach Adversarial Pattern",
    "category": "agent_orchestration",
    "description": "Adversarial cooperation where Player implements and Coach validates, with structured Promise and Honesty Verification.",
    "benefits": [
        "Quality assurance",
        "Iterative improvement",
        "Trust but verify",
        "Structured criteria tracking via criteria_verification",
        "Honesty enforcement via CoachVerifier pre-validation"
    ],
    "templates_using": ["guardkit-default"]
}),
```

## Acceptance Criteria

- [ ] `agent_autobuild_coach` capabilities list includes Promise Verification and Honesty Verification
- [ ] `pattern_player_coach` description mentions Promise and Honesty Verification
- [ ] `pattern_player_coach` benefits list includes criteria tracking and honesty enforcement
- [ ] `ruff check guardkit/knowledge/seed_agents.py` passes
- [ ] `ruff check guardkit/knowledge/seed_patterns.py` passes

## Files to Modify

| File | Action |
|------|--------|
| `guardkit/knowledge/seed_agents.py` | Modify (update 1 episode) |
| `guardkit/knowledge/seed_patterns.py` | Modify (update 1 episode) |
