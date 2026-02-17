# FEAT-BOOT Implementation Guide

## Execution Strategy

### Wave 1: Root Cause Fixes (P0)

**Must complete before Wave 2.** These are the fixes that directly unblock TASK-DB-003.

| Task | Description | Parallel? |
|------|-------------|-----------|
| TASK-BOOT-E3C0 | ProjectEnvironmentDetector + bootstrap phase | Start first |
| TASK-BOOT-3CAF | Inter-wave bootstrap hook | After E3C0 (depends on it) |

**E3C0** creates the detector and bootstrapper module and integrates it into `_setup_phase()`. **3CAF** adds the inter-wave call in `_wave_phase()` — it's small but depends on E3C0's module existing.

### Wave 2: Defence-in-Depth (P1)

**Can run in parallel.** These provide additional protection and fix secondary gaps.

| Task | Description | Parallel? |
|------|-------------|-----------|
| TASK-BOOT-43DE | Coach subprocess with sys.executable | Yes |
| TASK-BOOT-214B | requires_infrastructure in FEAT-BA28 | Yes |
| TASK-BOOT-6D85 | Wire _docker_available in task dict | Yes |

All three are independent — no dependencies between them. Can use Conductor for parallel execution.

### Wave 3: Classification & Observability (P2)

**Can run in parallel.** Low-priority improvements.

| Task | Description | Parallel? |
|------|-------------|-----------|
| TASK-BOOT-F9C4 | Service-client lib classification | Yes |
| TASK-BOOT-7369 | Diagnostic logging | Yes |

## Key Architecture Decisions

### Bootstrap runs from orchestrator Python

The `_bootstrap_environment()` method uses `subprocess.run()` from the orchestrator process. This means:
- `pip install` uses the orchestrator's Python (`sys.executable`)
- `npm install` uses whatever `npm` is on PATH
- No SDK subprocess involved — eliminates any PATH resolution ambiguity

### Idempotent via content hash

Each manifest's content is hashed (SHA-256) and stored in `.guardkit/bootstrap_state.json`. On re-run, only NEW or CHANGED manifests trigger install. This prevents:
- Redundant installs on each wave
- Re-installing when manifests haven't changed
- But catches when Wave 1 creates a new manifest

### Warn-and-continue on failure

If `pip install` or `npm install` fails, the bootstrapper logs a warning but does NOT block execution. Rationale:
- The Player may handle the install itself
- Some projects may have intentionally minimal manifests
- Blocking would be worse than attempting (the Player has 50 turns to recover)

## Verification Plan

After implementing all Wave 1 tasks:

1. Re-run FEAT-BA28 with `--max-turns 10 --fresh`
2. Verify: Bootstrap detects `pyproject.toml` after Wave 1 creates it
3. Verify: `pip install -e .` runs between waves
4. Verify: TASK-DB-003 Coach tests pass (sqlalchemy importable)
5. Verify: No `UNRECOVERABLE_STALL`

## Files Changed

| File | Changes |
|------|---------|
| `guardkit/orchestrator/environment_bootstrap.py` | NEW: detector + bootstrapper |
| `guardkit/orchestrator/feature_orchestrator.py` | `_setup_phase()` + `_wave_phase()` hooks |
| `guardkit/orchestrator/quality_gates/coach_validator.py` | subprocess fallback, classification, logging |
| `guardkit/orchestrator/autobuild.py` | `_docker_available` in task dict |
| `guardkit-examples/fastapi/.guardkit/features/FEAT-BA28.yaml` | `requires_infrastructure` values |
| `tests/unit/test_environment_bootstrap.py` | NEW |
| `tests/unit/test_inter_wave_bootstrap.py` | NEW |
| `tests/unit/test_coach_subprocess_tests.py` | NEW |
| `tests/unit/test_docker_available_wiring.py` | NEW |
| `tests/unit/test_coach_failure_classification.py` | Extended |
