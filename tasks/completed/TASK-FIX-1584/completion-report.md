# Completion Report: TASK-FIX-1584

## Summary

Synced `_cmd_seed()` display list with actual seeded categories in `seed_all_system_context()`.

## Change

**File**: `guardkit/cli/graphiti.py` (lines 127-146)

Added 5 missing categories to the display list:
- `project_overview`
- `project_architecture`
- `failed_approaches`
- `quality_gate_configs`
- `pattern_examples`

Display now shows all 18 categories in the same order as `seeding.py`.

## Acceptance Criteria

- [x] AC-001: `_cmd_seed()` display lists all 18 categories (13 existing + 5 new)
- [x] AC-002: Category order matches `seed_all_system_context()` order in `seeding.py`

## Test Results

- CLI tests: 12 passed
- Seeding tests: 46 passed, 2 skipped
- Zero regressions

## Context

- Parent review: TASK-REV-3ECA (FINDING-2)
- Complexity: 1/10
- Duration: ~1 minute
