---
id: TASK-GWR-001
title: Remove dead quality gate config from Graphiti (PATH 10)
status: backlog
created: 2026-02-14T10:30:00Z
priority: high
tags: [graphiti, dead-code, cleanup, quality-gates]
parent_review: TASK-REV-GROI
feature_id: FEAT-GWR
implementation_mode: task-work
wave: 1
complexity: 3
task_type: refactor
depends_on: []
---

# Task: Remove Dead Quality Gate Config from Graphiti (PATH 10)

## Description

The TASK-REV-GROI review conclusively proved that PATH 10 (Quality Gate Config from Graphiti) is dead code. The query infrastructure exists but is intentionally disconnected from the validation flow — Coach always uses hardcoded `DEFAULT_PROFILES` from `task_types.py`.

Remove the dead code to reduce noise before wiring the other disconnected reads.

## What to Remove

### 1. `guardkit/orchestrator/quality_gates/coach_validator.py`

Remove the following:

- **Lines 44-50**: The `GRAPHITI_AVAILABLE` conditional import block:
  ```python
  try:
      from guardkit.knowledge.quality_gate_queries import get_quality_gate_config
      GRAPHITI_AVAILABLE = True
  except ImportError:
      GRAPHITI_AVAILABLE = False
      get_quality_gate_config = None
  ```

- **`get_graphiti_thresholds()` static method** (~line 355-417): Queries `quality_gate_configs` group. Never called from production code.

- **`validate_with_graphiti_thresholds()` async method** (~line 501-580): Builds context then calls `validate()` which ignores it. Never called from `autobuild.py`.

### 2. Delete `guardkit/knowledge/quality_gate_queries.py`

Entire file — provides `get_quality_gate_config()` that is only imported conditionally and never used.

### 3. Delete `guardkit/knowledge/seed_quality_gate_configs.py`

Entire file — seeds data that nobody reads.

### 4. `guardkit/knowledge/seeding.py`

Remove `quality_gate_configs` entry from the categories list in `seed_all_system_context()` (~line 167):
```python
("quality_gate_configs", "seed_quality_gate_configs_wrapper"),  # REMOVE
```

Also remove the `seed_quality_gate_configs_wrapper()` function (~lines 90-95).

## Acceptance Criteria

- [ ] AC-F3-01: `guardkit/knowledge/quality_gate_queries.py` deleted
- [ ] AC-F3-02: `guardkit/knowledge/seed_quality_gate_configs.py` deleted
- [ ] AC-F3-03: `get_graphiti_thresholds()` and `validate_with_graphiti_thresholds()` removed from `coach_validator.py`
- [ ] AC-F3-04: `GRAPHITI_AVAILABLE` import block removed from `coach_validator.py`
- [ ] AC-F3-05: All existing coach_validator tests pass unchanged
- [ ] AC-F3-06: Seeding orchestrator no longer includes `quality_gate_configs`
- [ ] AC-F3-07: `guardkit graphiti seed` still works without the removed category

## Implementation Notes

- This is pure deletion — no new code needed
- Run `pytest tests/unit/test_coach_validator.py -v` after changes to verify nothing breaks
- Check for any other imports of the deleted modules: `grep -r "quality_gate_queries\|seed_quality_gate_configs" guardkit/`
- The `build_coach_context` import (line 52-54) must be KEPT — that's for Fix 1 (PATH 1 wiring)
