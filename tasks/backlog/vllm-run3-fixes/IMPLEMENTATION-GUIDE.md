# Implementation Guide: vLLM Run 3 Fixes (FEAT-VR3)

## Wave 1 (Parallel)

### TASK-FIX-GPLI: Fix _preflight_check() Lazy Init

**File**: `guardkit/orchestrator/feature_orchestrator.py`
**Method**: `_preflight_check()` (line ~1194)
**Effort**: ~5 lines of code + tests

**Change**:
```python
# BEFORE (line 1194-1196):
from guardkit.knowledge.graphiti_client import get_factory
factory = get_factory()
if factory is None or not factory.config.enabled:

# AFTER:
from guardkit.knowledge.graphiti_client import get_factory, get_graphiti
factory = get_factory()
if factory is None:
    # Trigger lazy initialization — loads .guardkit/graphiti.yaml,
    # creates GraphitiClientFactory. Synchronous, no asyncio objects
    # created (GLF-003: thread clients have pending_init=True).
    get_graphiti()
    factory = get_factory()
if factory is None or not factory.config.enabled:
```

**Tests**: Add to existing `_preflight_check` test suite:
1. Mock `get_factory()` → None first call, valid factory second call; verify `get_graphiti()` called
2. Mock `get_factory()` → valid factory; verify `get_graphiti()` NOT called
3. Verify factory config has correct `falkordb_host` from YAML
4. Verify graceful degradation when `_try_lazy_init()` fails

**Risk**: Low. `_try_lazy_init()` is synchronous, creates factory without asyncio. GLF-003 ensures thread clients are uninitialized stubs.

---

### TASK-VPT-002: Tune Parameters

**File**: `guardkit/orchestrator/agent_invoker.py`
**Effort**: 2 constant changes

**Changes**:
1. Find `sdk_max_turns` reduction for local backends (currently 75) → change to 100
2. Find `timeout_multiplier` default for local backends (currently 3.0) → change to 4.0

**Tests**: Verify existing tests pass with updated defaults. Check log output confirms new values.

---

## Verification

After both tasks complete:

```bash
# 1. Run unit tests
pytest tests/ -v -k "preflight or agent_invoker" --tb=short

# 2. Reinstall
pip install -e .

# 3. Verify Graphiti init (from vllm-profiling project)
cd ~/Projects/appmilla_github/vllm-profiling
guardkit graphiti search "test"  # Should work (existing path)

# 4. Verify preflight fix (look for the NEW log message)
ANTHROPIC_BASE_URL=http://localhost:8000 ANTHROPIC_API_KEY=vllm-local \
  guardkit autobuild feature FEAT-XXXX --max-turns 1 --verbose 2>&1 | \
  grep -E "(pre-flight|factory|Graphiti)"
# Expected: "FalkorDB pre-flight TCP check passed"
# NOT: "Graphiti factory not available"
```
