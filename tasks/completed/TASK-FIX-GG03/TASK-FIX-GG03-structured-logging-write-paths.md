---
id: TASK-FIX-GG03
title: "Add [Graphiti] structured logging to write-path files"
status: completed
task_type: implementation
created: 2026-02-08T22:00:00Z
updated: 2026-02-08T22:00:00Z
completed: 2026-02-08T23:00:00Z
completed_location: tasks/completed/TASK-FIX-GG03/
priority: low
parent_review: TASK-REV-DE4F
feature_id: FEAT-GG-001
tags: [graphiti, logging, observability, gap-closure]
complexity: 1
wave: 2
dependencies: []
---

# Add [Graphiti] Structured Logging to Write-Path Files

## Description

TASK-FIX-GCI5 added `[Graphiti]` structured logging to 4 primary integration points. However, 4 write-path files that perform Graphiti operations still use plain logging without the `[Graphiti]` prefix:

1. `guardkit/knowledge/turn_state_operations.py` - Turn state capture
2. `guardkit/knowledge/outcome_manager.py` - Task outcome capture
3. `guardkit/knowledge/failed_approach_manager.py` - Failed approach storage
4. `guardkit/knowledge/template_sync.py` - Template syncing

## Changes Required

For each file, update log messages that relate to Graphiti operations to use the `[Graphiti]` prefix:

- **INFO level**: Success operations (e.g., `[Graphiti] Captured turn state: {entity_id}`)
- **WARNING level**: Degradation/failures (e.g., `[Graphiti] Failed to store turn state: {error}`)
- **DEBUG level**: Skip/unavailable messages (e.g., `[Graphiti] Client unavailable, skipping turn state capture`)

### Pattern (from existing GCI5 implementation)

```python
# Before
logger.debug("Graphiti client is None, skipping turn state capture")
logger.info(f"Captured turn state: {entity.id}")
logger.warning(f"Error capturing turn state {entity.id}: {e}")

# After
logger.debug("[Graphiti] Client unavailable, skipping turn state capture")
logger.info(f"[Graphiti] Captured turn state: {entity.id}")
logger.warning(f"[Graphiti] Failed to capture turn state {entity.id}: {e}")
```

## Key Files

- `guardkit/knowledge/turn_state_operations.py` - ~6 log messages
- `guardkit/knowledge/outcome_manager.py` - ~4 log messages
- `guardkit/knowledge/failed_approach_manager.py` - TBD
- `guardkit/knowledge/template_sync.py` - TBD

## Acceptance Criteria

- [ ] All Graphiti-related log messages in the 4 files have `[Graphiti]` prefix
- [ ] No functional changes (logging-only modification)
- [ ] Existing tests still pass

## Test Requirements

- 4-8 tests verifying `[Graphiti]` prefix appears in log output
- Follow pattern from `tests/unit/test_graphiti_structured_logging.py`
