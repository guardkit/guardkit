---
id: TASK-ASF-002
title: Add pre-flight FalkorDB connectivity check before autobuild
task_type: feature
parent_review: TASK-REV-SFT1
feature_id: FEAT-ASF
wave: 1
implementation_mode: direct
complexity: 2
dependencies: []
priority: high
status: backlog
tags: [autobuild, stall-fix, R2, phase-1, graphiti]
---

# Task: Add pre-flight FalkorDB connectivity check before autobuild

## Description

Add a pre-flight connectivity check for FalkorDB/Graphiti before autobuild launches. During the FEAT-AC1A run, FalkorDB at `whitestocks:6379` became unreachable mid-run (Turn 4+), adding 5-10 seconds of retry latency per context load without providing value. The Graphiti client degrades gracefully (returns empty context) but the retry cycles waste time.

Additionally, this addresses the newly identified **ghost thread interference** issue (Q8 from diagnostic diagrams): when Feature N fails and its ghost thread keeps running, that thread continues hitting Graphiti, consuming connection pool slots and API credits. A pre-flight check ensures the infrastructure is healthy before committing resources.

## Root Cause Addressed

- **F6**: Graphiti connection loss added latency without value
- **Q8** (new from diagrams): Ghost thread interference across features — ghost threads consume Graphiti connection pool

## Implementation

Add a `_preflight_check()` method to the feature orchestrator that runs before wave execution:

```python
# feature_orchestrator.py
async def _preflight_check(self) -> bool:
    """Verify infrastructure before launching autobuild."""
    checks = []

    # Check FalkorDB connectivity
    if self.graphiti_enabled:
        try:
            # Quick ping — timeout after 5 seconds
            result = await asyncio.wait_for(
                self._ping_falkordb(), timeout=5.0
            )
            checks.append(("FalkorDB", result))
        except asyncio.TimeoutError:
            checks.append(("FalkorDB", False))
            logger.warning("FalkorDB not reachable — disabling Graphiti context")
            self.graphiti_enabled = False

    return all(ok for _, ok in checks)
```

## Files to Modify

1. `guardkit/orchestrator/feature_orchestrator.py` — Add `_preflight_check()` method, call before wave execution
2. `guardkit/orchestrator/autobuild.py` — Accept `graphiti_enabled` flag to skip Graphiti context loading when infrastructure is down

## Acceptance Criteria

- [ ] Pre-flight check runs FalkorDB ping before first wave
- [ ] If FalkorDB is unreachable, Graphiti context loading is disabled for the entire run
- [ ] Warning logged when FalkorDB connectivity check fails
- [ ] Autobuild proceeds without Graphiti (graceful degradation, not a blocker)
- [ ] Pre-flight check completes within 5 seconds

## Regression Risk

**Low** — This is an additive pre-flight check. It disables Graphiti context loading when the infrastructure is down, which is the same behavior as the current graceful degradation but without the retry latency.

## Reference

- Review report: `.claude/reviews/TASK-REV-SFT1-review-report.md` (Finding 6, Recommendation R2)
- Diagnostic diagrams: `docs/reviews/feature-build/autobuild-diagnostic-diagrams.md` (Diagram 7, Q8)
