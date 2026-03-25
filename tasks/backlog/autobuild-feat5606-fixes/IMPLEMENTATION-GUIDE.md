# Implementation Guide: AutoBuild FEAT-5606 Fixes

## Feature: FEAT-8BC0 — AutoBuild Reliability Improvements

**Parent Review**: TASK-REV-8BC0
**Origin**: Analysis of FEAT-5606 ("GOAL.md Parser and Strict Validation") failure in agentic-dataset-factory

---

## Wave Execution Strategy

### Wave 1: Critical Fixes (Parallel)

Two independent high-priority fixes that address the most impactful issues.

| Task | Title | Mode | Complexity | Est. Turns |
|------|-------|------|------------|------------|
| TASK-FIX-GEN1 | Fix direct-mode generator lifecycle | task-work | 4 | 1-2 |
| TASK-FIX-OBS2 | Add per-task progress logs | task-work | 5 | 2-3 |

**Parallel execution**: These tasks modify different files and have no conflicts.
- GEN1 modifies `agent_invoker.py` (lines 2039-2099)
- OBS2 modifies `feature_orchestrator.py`, adds new logging infrastructure

### Wave 2: Configuration + Instrumentation (Parallel)

Two lower-priority fixes that depend on Wave 1 understanding but not code changes.

| Task | Title | Mode | Complexity | Est. Turns | Depends On |
|------|-------|------|------------|------------|------------|
| TASK-FIX-MODE3 | Default to task-work mode | task-work | 3 | 1 | TASK-FIX-GEN1 |
| TASK-FIX-EMIT4 | Fix JSONLFileBackend lock | direct | 2 | 1 | — |

**Parallel execution**: No file conflicts.
- MODE3 modifies routing logic in `agent_invoker.py` (different section from GEN1)
- EMIT4 modifies `emitter.py` only

**Note**: MODE3 depends on GEN1 for design validation — understanding the fixed generator lifecycle informs what complexity threshold to use. EMIT4 is fully independent.

### Wave 3: Enhancement (Sequential)

| Task | Title | Mode | Complexity | Est. Turns | Depends On |
|------|-------|------|------------|------------|------------|
| TASK-FIX-SYNTH5 | Improve synthetic report verification | task-work | 5 | 2-3 | GEN1, MODE3 |

**Sequential**: Depends on understanding the residual cases where synthetic reports are still generated after GEN1 and MODE3 are applied.

---

## Execution Commands

### Wave 1

```bash
# Option A: Sequential
guardkit autobuild task TASK-FIX-GEN1 --max-turns 5
guardkit autobuild task TASK-FIX-OBS2 --max-turns 5

# Option B: Parallel via Conductor
# Workspace: autobuild-feat5606-wave1-gen1
# Workspace: autobuild-feat5606-wave1-obs2
```

### Wave 2

```bash
guardkit autobuild task TASK-FIX-MODE3 --max-turns 3
guardkit autobuild task TASK-FIX-EMIT4 --max-turns 3
```

### Wave 3

```bash
guardkit autobuild task TASK-FIX-SYNTH5 --max-turns 5
```

---

## Verification Strategy

After all waves complete:

1. **Re-run FEAT-5606** in agentic-dataset-factory with the fixes applied
2. **Verify**: Direct-mode tasks no longer show CancelledError from generator cleanup
3. **Verify**: Parallel task timeouts produce diagnostic log files
4. **Verify**: Non-trivial tasks default to task-work mode
5. **Verify**: No "bound to a different event loop" warnings in parallel execution
6. **Verify**: Synthetic reports (if still generated) include code pattern evidence

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| GEN1 generator drain may hang if SDK sends infinite messages | Drain loop has a try/except and gen is set to None after timeout |
| MODE3 may break existing features that rely on direct mode | Feature YAML `implementation_mode: direct` still overrides |
| EMIT4 sync lock may reduce throughput | File I/O under lock is < 1ms; no measurable impact |
| SYNTH5 AST parsing may fail on non-Python files | Use regex fallback, not AST; graceful degradation |
