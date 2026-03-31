# Implementation Guide: Seeding Production Readiness (FEAT-SPR)

## Wave Breakdown

### Wave 1: Critical Fixes (Parallel)

These two tasks address the P0 blockers — circuit breaker cascade and rules failure rate.

| Task | Description | Mode | Complexity |
|------|-------------|------|------------|
| TASK-SPR-5399 | Reset circuit breaker between categories | task-work | 4 |
| TASK-SPR-18fc | Split rules into per-template batches | task-work | 5 |

**No file conflicts** — SPR-5399 modifies `graphiti_client.py` + `seeding.py` orchestrator loop; SPR-18fc modifies `seed_rules.py` + optionally `seeding.py` categories list. Can run in parallel.

**Expected interface**: After Wave 1, `seeding.py` should call `client.reset_circuit_breaker()` before each category, and rules should be seeded per-template with separate `group_id`s.

```bash
# Execute in parallel
/task-work TASK-SPR-5399
/task-work TASK-SPR-18fc
```

### Wave 2: UX Improvements (Sequential)

These tasks improve seed output clarity. SPR-2cf7 must complete first as SPR-9d9b builds on its result data.

| Task | Description | Mode | Complexity |
|------|-------------|------|------------|
| TASK-SPR-2cf7 | Change ✓/⚠/✗ status display | task-work | 3 |
| TASK-SPR-9d9b | Add summary statistics | direct | 2 |

**Dependency**: SPR-9d9b depends on SPR-2cf7 (both modify seed output).

```bash
/task-work TASK-SPR-2cf7
# Then:
/task-work TASK-SPR-9d9b  # or direct edit
```

### Wave 3: Resilience (Independent)

| Task | Description | Mode | Complexity |
|------|-------------|------|------------|
| TASK-SPR-47f8 | LLM connection retry/health check | task-work | 3 |

**Independent** — can run at any time.

```bash
/task-work TASK-SPR-47f8
```

## Verification Plan

After Wave 1+2, run a clean seed to verify:

```bash
guardkit graphiti clear --confirm
guardkit graphiti seed --force
```

Expected improvements:
- Rules success: 1/72 → 50+/72 (per-template batching + circuit breaker reset)
- project_overview: 0/3 → 3/3 (no cascade from rules)
- project_architecture: 0/3 → 3/3 (no cascade from rules)
- Status display: ✓/⚠/✗ instead of all ✓
- Summary: "Total: X/Y episodes created (Z%)"

## Predecessor Features

| Feature | Status | Relationship |
|---------|--------|-------------|
| FEAT-ISF | Completed (6/6) | Init seeding fixes — sequential sync, ext files |
| FEAT-SQF | Completed (3/3) | Seed quality fixes — timeouts, logging, paths |
| FEAT-SPR | This feature | Seeding production readiness — circuit breaker, UX |

## Related Features (Decoupled)

| Feature | Relationship |
|---------|-------------|
| FEAT-CR01 | Context reduction — independent, not blocked by FEAT-SPR |
| FEAT-GE | Graphiti enhancements — episode splitting is complementary |
