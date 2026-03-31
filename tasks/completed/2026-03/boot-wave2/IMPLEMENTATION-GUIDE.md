# FEAT-BOOT Wave 2 Implementation Guide

## Execution Strategy

### Wave 1: Root Cause Fixes + Diagnostics (P0/P1)

**Must complete B032 and F632 together for tests to pass.** 754A can be parallel.

| Task | Description | Parallel? |
|------|-------------|-----------|
| TASK-BOOT-B032 | Fix requires_infrastructure propagation | Yes (independent) |
| TASK-BOOT-F632 | Dependency-only install for incomplete projects | Yes (independent) |
| TASK-BOOT-754A | Structured diagnostic logging | Yes (independent) |

All three are independent — no code dependencies between them. Can use Conductor for parallel execution.

**B032** modifies `autobuild.py` (orchestrate signature) and `feature_orchestrator.py` (_execute_task call site).
**F632** modifies `environment_bootstrap.py` (DetectedManifest methods, bootstrap logic).
**754A** modifies `coach_validator.py` (conditional approval log) and `environment_bootstrap.py` (subprocess output logging).

**File conflict note**: F632 and 754A both modify `environment_bootstrap.py` but in different methods (`bootstrap()` vs `_run_install()`). Low merge conflict risk.

### Wave 2: Cache + Regression Prevention (P2)

**Can run in parallel after Wave 1 merges.**

| Task | Description | Parallel? |
|------|-------------|-----------|
| TASK-BOOT-0F53 | State-aware hash persistence | Yes |
| TASK-BOOT-99A5 | Integration test for propagation | Yes (depends on B032 being merged) |

**0F53** modifies `environment_bootstrap.py` (_save_state, _should_skip).
**99A5** creates new test files — no source conflicts.

## Key Architecture Decisions

### Detection-first install strategy (F632)

The bootstrap checks `manifest.is_project_complete()` BEFORE attempting install. This avoids:
- Wasting 30 seconds on a doomed full install
- Side effects from partial build execution
- Confusing error messages in logs

### Explicit parameter > implicit loading (B032)

The `orchestrate()` method now accepts `requires_infrastructure` as an optional parameter with precedence:
1. Explicit parameter (from feature YAML via FeatureOrchestrator)
2. Frontmatter (from task .md file, for single-task mode)
3. Empty list (no infrastructure declared)

This follows Dependency Inversion — the caller injects the value rather than the callee resolving it independently.

### Time-based retry cooldown (0F53)

Failed bootstrap attempts are retried after a configurable cooldown (default 60s). This is simpler than source_tree_hash and covers the same cases:
- Manifest changed → retry (hash mismatch)
- Manifest same, install failed → retry after cooldown
- Manifest same, install succeeded → skip

## Verification Plan

After implementing all Wave 1 tasks:

1. Re-run FEAT-BA28 with `--max-turns 10 --fresh`
2. Verify: Bootstrap detects incomplete project and installs dependencies individually
3. Verify: `requires_infrastructure=[postgresql]` reaches the Coach
4. Verify: Docker lifecycle attempted (or conditional approval fires if Docker unavailable)
5. Verify: TASK-DB-003 does NOT stall
6. Verify: Conditional approval evaluation is logged with all 5 condition values

## Files Changed

| File | Tasks | Changes |
|------|-------|---------|
| `guardkit/orchestrator/autobuild.py` | B032 | `orchestrate()` signature, precedence logic |
| `guardkit/orchestrator/feature_orchestrator.py` | B032 | `_execute_task()` passes requires_infrastructure |
| `guardkit/orchestrator/environment_bootstrap.py` | F632, 754A, 0F53 | Detection methods, install strategy, logging, state |
| `guardkit/orchestrator/quality_gates/coach_validator.py` | 754A | Conditional approval debug log |
| `tests/unit/test_requires_infra_propagation.py` | B032 | NEW |
| `tests/unit/test_environment_bootstrap.py` | F632, 0F53 | Extended |
| `tests/unit/test_coach_validator_logging.py` | 754A | NEW |
| `tests/integration/test_requires_infra_propagation.py` | 99A5 | NEW |
| `tests/integration/test_docker_smoke.py` | 99A5 | NEW |
