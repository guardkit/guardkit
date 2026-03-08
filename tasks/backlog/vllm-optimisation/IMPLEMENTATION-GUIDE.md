# Implementation Guide: vLLM Optimisation (FEAT-VOPT)

## Wave 1 (Parallel — no file conflicts)

### TASK-VOPT-001: Context Reduction

**File**: `guardkit/orchestrator/agent_invoker.py` (protocol generation section)
**Effort**: Medium — create slim protocol variant
**Target**: Reduce inline protocol from ~19KB to ~10-12KB for local backends

### TASK-VOPT-002: Per-Turn Timing

**Files**: `guardkit/orchestrator/agent_invoker.py` (timing), `guardkit/knowledge/autobuild_context_loader.py` (Graphiti timing)
**Effort**: Low — add `time.monotonic()` instrumentation around SDK calls

### TASK-VOPT-003: Log Noise Suppression

**File**: `guardkit/knowledge/graphiti_client.py`
**Effort**: Trivial — set FalkorDB driver logger to WARNING

---

## Wave 2 (Depends on Wave 1)

### TASK-VOPT-004: Full Run 4 Benchmark

**Type**: Manual execution
**Depends on**: All Wave 1 tasks merged + `pip install -e .`
**Command**: `guardkit autobuild feature FEAT-1637 --max-turns 30 --verbose --fresh`

---

## Verification

After Wave 1 completion:

```bash
# 1. Run tests
pytest tests/ -v --tb=short

# 2. Verify slim protocol size
grep -n "protocol size" guardkit/orchestrator/agent_invoker.py

# 3. Reinstall
pip install -e .

# 4. Quick smoke test
ANTHROPIC_BASE_URL=http://localhost:8000 ANTHROPIC_API_KEY=vllm-local \
  guardkit autobuild feature FEAT-XXXX --max-turns 1 --verbose 2>&1 | \
  grep -E "(protocol size|SDK invocation|Context loaded|pre-flight)"
```
