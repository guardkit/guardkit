---
id: TASK-FIX-VL05
title: Add timeout scaling configuration for localhost/vLLM backends
status: completed
created: 2026-02-26T13:00:00Z
updated: 2026-02-26T18:00:00Z
completed: 2026-02-26T18:00:00Z
completed_location: tasks/completed/TASK-FIX-VL05/
priority: high
tags: [autobuild, vllm, enhancement, timeout, local-llm, configuration]
complexity: 3
task_type: enhancement
parent_review: TASK-REV-8A94
feature_id: FEAT-VL01
wave: 2
implementation_mode: task-work
dependencies: []
---

# Task: Add timeout scaling configuration for localhost/vLLM backends

## Description

vLLM/Qwen3 on GB10 hardware generates tokens ~4x slower than Anthropic API. The current timeout values (40-minute task timeout, SDK timeouts) are calibrated for Anthropic cloud inference speed. When running via `ANTHROPIC_BASE_URL=http://localhost:8000`, tasks hit timeout boundaries before completion, triggering cascading failures.

**Root Cause**: Fixed timeout values with no awareness of backend inference speed. TASK-DB-002 ran for 1200+ seconds on turn 2 before cancellation. TASK-DB-004 ran for 450+ seconds before cancellation.

## Requirements

Add a `timeout_multiplier` configuration option that scales all autobuild timeouts when using localhost or non-Anthropic backends. The multiplier should be detectable from `ANTHROPIC_BASE_URL` or explicitly configurable.

## Acceptance Criteria

- New `timeout_multiplier` config option (default: 1.0) available in autobuild configuration
- Auto-detection: if `ANTHROPIC_BASE_URL` contains `localhost` or `127.0.0.1`, suggest multiplier of 4.0
- `sdk_timeout`, `task_timeout`, and `wave_timeout` are all scaled by the multiplier
- CLI flag `--timeout-multiplier N` overrides auto-detection
- Existing Anthropic API behaviour unchanged (multiplier=1.0 by default)
- Configuration logged at autobuild startup for visibility
- Unit test verifies timeout scaling logic

## Files to Modify

- `guardkit/orchestrator/feature_orchestrator.py` (timeout configuration and application)
- `guardkit/orchestrator/agent_invoker.py` (SDK timeout usage)
- `guardkit/cli/autobuild_cli.py` (CLI flag, if exists)

## Implementation Notes

```python
# Auto-detect from environment
import os

def detect_timeout_multiplier() -> float:
    """Detect appropriate timeout multiplier from backend URL."""
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
    if "localhost" in base_url or "127.0.0.1" in base_url:
        return 4.0  # Local inference is ~4x slower
    return 1.0

# Apply to timeouts
class FeatureOrchestrator:
    def __init__(self, ..., timeout_multiplier: Optional[float] = None):
        self.timeout_multiplier = timeout_multiplier or detect_timeout_multiplier()
        self.task_timeout = int(2400 * self.timeout_multiplier)  # 40min * multiplier
        self.sdk_timeout = int(300 * self.timeout_multiplier)    # 5min * multiplier
```
