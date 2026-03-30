---
id: TASK-TI-015
title: Human-in-the-loop checkpoint hooks
status: completed
created: 2026-03-27T22:00:00Z
updated: 2026-03-30T00:00:00Z
completed: 2026-03-30T00:00:00Z
completed_location: tasks/completed/TASK-TI-015/
priority: p3
tags: [template, adversarial, hitl, hooks]
complexity: 4
parent_review: TASK-REV-TRF12
feature_id: FEAT-TI
wave: 4
implementation_mode: task-work
depends_on: [TASK-TI-010]
test_results:
  status: passed
  tests: 57
  coverage: null
  last_run: 2026-03-30T00:00:00Z
---

# Task: Human-in-the-Loop Checkpoint Hooks

## Description

Add configurable HITL checkpoint hooks to the adversarial orchestrator, allowing human review at key pipeline stages. Supports both interactive (CLI) and async (webhook/queue) modes.

## What to Build

### Checkpoint Types
1. **pre-generation**: Before Player receives target — review target specification
2. **post-generation**: After Player output, before Coach — review raw output
3. **post-evaluation**: After Coach verdict, before write — review acceptance decision
4. **on-rejection**: When Coach rejects — human can override to accept or provide feedback
5. **on-exhaustion**: When retry cap reached — human can extend retries or skip target

### Hook Interface
```python
class CheckpointHook:
    async def on_checkpoint(self, stage: str, context: dict) -> CheckpointDecision:
        """Returns: proceed, skip, override, or abort"""
        ...

class CLICheckpointHook(CheckpointHook):
    """Interactive CLI prompts for human review"""
    ...

class WebhookCheckpointHook(CheckpointHook):
    """Posts to webhook URL, waits for response"""
    ...

class AutoApproveHook(CheckpointHook):
    """No-op hook for fully automated pipelines"""
    ...
```

### Configuration
```yaml
checkpoints:
  enabled: true
  mode: cli           # cli | webhook | auto
  stages:
    - post-evaluation  # Only check after Coach verdict by default
  webhook_url: null    # For webhook mode
```

## Acceptance Criteria

- [x] Five checkpoint types implemented
- [x] CLI mode with interactive prompts
- [x] Webhook mode with async response handling
- [x] Auto-approve mode for fully automated pipelines
- [x] Configurable which stages have checkpoints
- [x] CheckpointDecision: proceed, skip, override, abort
- [x] Unit tests for each hook type and decision
- [x] Integration test with CLI hook in orchestrator flow

## Effort Estimate

1-2 days
