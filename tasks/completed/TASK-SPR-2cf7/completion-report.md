# Completion Report: TASK-SPR-2cf7

## Summary

Changed seed status display from static checkmarks to differentiated indicators reflecting actual seeding outcomes.

## Changes

### `guardkit/knowledge/seeding.py`
- `seed_all_system_context` now returns a `dict` mapping category names to `(created, skipped)` tuples when seeding runs
- Early exits still return `True` (already seeded) or `False` (disabled/None) for backward compatibility
- The dict is truthy, so `if result:` checks remain valid

### `guardkit/cli/graphiti.py`
- Replaced static `✓` display with outcome-based indicators:
  - `✓` green — 100% success (0 skipped)
  - `⚠` yellow — Partial success (some skipped, ≤80% skip rate)
  - `✗` red — Failure (0 created, >80% skipped, or error)
- Episode counts displayed alongside each category

## Test Results

- All `seed_all` orchestration tests: 9/9 pass
- All CLI graphiti seed tests: 7/7 pass
- 2 pre-existing failures in unrelated seed modules (episode count mismatches)

## Acceptance Criteria

- [x] ✓ shown only for 100% success
- [x] ⚠ shown for partial success (1-99% success)
- [x] ✗ shown for failure (0% success or >80% skip rate)
- [x] Episode counts shown alongside indicators
- [x] Existing tests pass
