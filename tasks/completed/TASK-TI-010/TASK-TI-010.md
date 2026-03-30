---
id: TASK-TI-010
title: Three-role orchestrator scaffold (Orchestrator + Player + Coach)
status: completed
created: 2026-03-27T22:00:00Z
updated: 2026-03-29T11:15:00Z
completed: 2026-03-29T11:15:00Z
completed_location: tasks/completed/TASK-TI-010/
priority: p3
tags: [template, adversarial, orchestration]
complexity: 6
parent_review: TASK-REV-TRF12
feature_id: FEAT-TI
wave: 4
implementation_mode: task-work
depends_on: [TASK-TI-009]
test_results:
  status: passing
  coverage: null
  last_run: 2026-03-29T11:00:00Z
  tests_passed: 45
  tests_total: 45
---

# Task: Three-Role Orchestrator Scaffold

## Description

Create the Jinja2 template that generates the three-role orchestration pattern: Orchestrator (Planner) + Player (Generator) + Coach (Evaluator). This encodes the adversarial cooperation architecture proven across 11 runs of the agentic-dataset-factory.

## What to Build

### Orchestrator Role
- Owns the generation loop: iterate over targets, coordinate Player and Coach
- Owns write authority (from TI-003 gated writes pattern)
- Manages retry logic with configurable caps
- Pre-fetches domain context (RAG results, curriculum data) before Player turn
- Extracts structured content from Player response using JsonExtractor (TI-001)

### Player Role (Generator)
- Receives domain context + target specification
- Produces structured content (JSON training examples, etc.)
- Tool access: domain-specific tools ONLY (e.g., rag_retrieval)
- NO write authority, NO filesystem access
- Factory uses `create_restricted_agent()` (TI-004)

### Coach Role (Evaluator)
- Receives Player output + evaluation criteria
- Returns structured verdict (JSON with scores, feedback, accept/reject)
- Tool access: EMPTY (evaluation only)
- Factory uses `create_restricted_agent()` (TI-004)
- Symmetric content extraction with Player (TRF-026 lesson)

### Generated Code Structure
```python
# orchestrator.py (generated)
class AdversarialOrchestrator:
    def __init__(self, player, coach, write_gate, pipeline):
        ...

    async def process_target(self, target):
        # 1. Pre-fetch domain context
        context = await self.prefetch_context(target)
        # 2. Player generates content
        player_output = await self.player.invoke(context)
        # 3. Extract structured content
        extracted = self.pipeline.extract(player_output)
        # 4. Coach evaluates
        verdict = await self.coach.invoke(extracted)
        # 5. Write gate (if accepted)
        if verdict.accepted:
            await self.write_gate.attempt_write(extracted)
```

## Acceptance Criteria

- [x] Three-role wiring with clear separation of concerns
- [x] Orchestrator owns write authority exclusively
- [x] Player and Coach use `create_restricted_agent()` with tool allowlists
- [x] Pre-fetch pattern for domain context
- [x] Retry logic with configurable caps
- [x] Content extraction using JsonExtractor
- [x] Unit tests for orchestration flow
- [x] Integration test with mock Player and Coach

## Effort Estimate

2 days
