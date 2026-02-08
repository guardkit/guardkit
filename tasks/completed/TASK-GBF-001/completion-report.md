# TASK-GBF-001 Completion Report

## Summary
Unified episode serialization across all entities and seed modules to use a single canonical pattern: **client-level metadata injection** via `GraphitiClient.add_episode()` kwargs (`source`, `entity_type`).

## Canonical Pattern

```
Entity.to_episode_body() -> dict (domain data only, no metadata)
    -> json.dumps() -> str
    -> client.add_episode(episode_body=str, source="...", entity_type="...")
        -> client._inject_metadata() appends metadata block
```

**Key rule:** `to_episode_body()` returns ONLY domain data. Metadata (`entity_type`, `_metadata`, `created_at`, `updated_at`) is injected by `GraphitiClient`.

## Changes Made

### Source Fixes (2 files)
- **`seed_quality_gate_configs.py`** -- Added `source="guardkit_seeding"` and `entity_type="quality_gate_config"` to `add_episode()` call
- **`seed_role_constraints.py`** -- Added `source="guardkit_seeding"` and `entity_type="role_constraint"` to `add_episode()` call

### Test Fixes (3 files)
- **`tests/knowledge/test_quality_gate_configs.py`** -- Updated 3 tests: `entity_type` should NOT be in body (was expecting old pattern), fixed mock capture to use `AsyncMock` with kwargs
- **`tests/knowledge/test_role_constraints.py`** -- Updated 5 tests: `entity_type`/`created_at` should NOT be in body, fixed mock captures
- **`tests/knowledge/test_seeding.py`** -- Updated 1 test: verify metadata is delegated via kwargs, not embedded in body

### Previously Completed (commit 6dc1d0c2 + GBF-002)
- `_add_episodes()` helper: Removed `_metadata` body embedding, passes `source`/`entity_type` kwargs
- `TaskOutcome.to_episode_body()`: Changed from `str` to `dict` return type
- All 4 entities: Return dict without metadata fields
- 15 extracted seed modules: Use `_add_episodes()` helper with `entity_type=`
- Test suites: `test_episode_serialization.py` (23 tests), `test_seeding_metadata.py` (9 tests)

## Test Results
- **186 passed**, 2 skipped (integration tests requiring live Graphiti), 0 failed
- Test duration: 1.52s
