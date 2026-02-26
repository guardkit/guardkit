# Implementation Guide: vLLM AutoBuild Fixes (FEAT-VL01)

## Execution Strategy: Sequential (3 Waves)

All tasks executed sequentially within each wave. Wave N+1 starts only after all Wave N tasks pass.

---

## Wave 1: Critical Bug Fixes (3 tasks)

**Goal**: Fix the two verified bugs that cause 0% criteria verification, and prevent recurrence.

### TASK-FIX-VL01: Path-hardened player report recovery
- **File**: `guardkit/orchestrator/agent_invoker.py` (lines 1844-1879)
- **Change**: Add repo-root fallback path check in Fix 2 recovery block
- **Risk**: Low — additive change, existing worktree-path check is preserved
- **Test**: Unit test with player report at repo root vs worktree path
- **Run**: `/task-work TASK-FIX-VL01`

### TASK-FIX-VL02: Fix 5 - Use TaskLoader for AC extraction
- **File**: `guardkit/orchestrator/agent_invoker.py` (lines 1884-1896)
- **Change**: Replace `_load_task_metadata()` with `TaskLoader.load_task()` in Fix 5
- **Risk**: Low — TaskLoader is the canonical parser already used elsewhere
- **Test**: Unit test with AC in markdown body (not YAML frontmatter)
- **Run**: `/task-work TASK-FIX-VL02`

### TASK-FIX-VL03: Absolute paths in execution protocol
- **Files**: `guardkit/orchestrator/prompts/autobuild_execution_protocol.md`, `guardkit/orchestrator/agent_invoker.py` (~line 3322)
- **Change**: Add `{worktree_path}` placeholder, substitute with absolute path
- **Risk**: Low — prevents path ambiguity for all models
- **Test**: Verify substitution produces absolute path; verify Anthropic models unaffected
- **Run**: `/task-work TASK-FIX-VL03`

### Wave 1 Validation
```bash
pytest tests/ -v -k "player_report or taskloader or protocol" --cov=guardkit/orchestrator
```

---

## Wave 2: Parallel Safety + Performance (2 tasks)

**Goal**: Prevent git race conditions and make timeouts workable for local inference.

### TASK-FIX-VL04: Git operation threading lock
- **File**: `guardkit/orchestrator/agent_invoker.py` (class-level + `_detect_git_changes()`)
- **Change**: Add `threading.RLock()` class-level lock around git operations
- **Risk**: Low — serialises only git commands, tasks still run concurrently
- **Dependency**: None (can run in parallel with VL05 if desired)
- **Run**: `/task-work TASK-FIX-VL04`

### TASK-FIX-VL05: Timeout scaling for local backends
- **Files**: `guardkit/orchestrator/feature_orchestrator.py`, `guardkit/orchestrator/agent_invoker.py`
- **Change**: Auto-detect localhost backend, apply 4x timeout multiplier
- **Risk**: Low — only affects timeout values, default multiplier is 1.0
- **Dependency**: None
- **Run**: `/task-work TASK-FIX-VL05`

### Wave 2 Validation
```bash
pytest tests/ -v -k "git_lock or timeout" --cov=guardkit/orchestrator
```

---

## Wave 3: Defence-in-Depth (2 tasks)

**Goal**: Improve accuracy of parallel git detection and support local model paraphrasing.

### TASK-FIX-VL06: Per-task baseline commit hash
- **File**: `guardkit/orchestrator/agent_invoker.py`
- **Change**: Record `git rev-parse HEAD` before task start, use as diff baseline
- **Risk**: Medium — changes git detection reference point
- **Dependency**: TASK-FIX-VL04 (needs git lock in place)
- **Run**: `/task-work TASK-FIX-VL06`

### TASK-FIX-VL07: Semantic matching + enhanced synthetic promises
- **Files**: `guardkit/orchestrator/quality_gates/coach_validator.py`, `guardkit/orchestrator/synthetic_report.py`, `guardkit/orchestrator/feature_orchestrator.py`
- **Change**: Configurable matching strategy (text/semantic/auto) + improved file regex patterns
- **Risk**: Medium — changes validation behaviour when semantic mode enabled
- **Dependency**: TASK-FIX-VL02 (Fix 5 must work correctly first)
- **Run**: `/task-work TASK-FIX-VL07`

### Wave 3 Validation
```bash
pytest tests/ -v -k "baseline_commit or semantic or synthetic" --cov=guardkit/orchestrator
```

---

## Full Regression

After all waves complete:

```bash
pytest tests/ -v --cov=guardkit --cov-report=term --cov-report=json
```

## Key Files Summary

| File | Tasks Touching It |
|------|-------------------|
| `guardkit/orchestrator/agent_invoker.py` | VL01, VL02, VL03, VL04, VL05, VL06 |
| `guardkit/orchestrator/feature_orchestrator.py` | VL05, VL07 |
| `guardkit/orchestrator/quality_gates/coach_validator.py` | VL07 |
| `guardkit/orchestrator/synthetic_report.py` | VL07 |
| `guardkit/orchestrator/prompts/autobuild_execution_protocol.md` | VL03 |

## Architecture Guardrails

**Do NOT**:
- Remove or bypass Fix 2, Fix 3, or Fix 5 — they are load-bearing recovery mechanisms
- Change `TaskArtifactPaths` path construction — it is the canonical path builder
- Remove the diagnostic dump in coach_validator — it is essential for debugging
- Change the promise-based → hybrid → text matching pipeline order

**Do**:
- Preserve existing behaviour when `matching_strategy=text` (default)
- Use `TaskLoader` as the canonical task parser (not `_load_task_metadata()`)
- Keep all git operations within the `_git_lock` context manager (after VL04)
- Log all fallback activations for observability
