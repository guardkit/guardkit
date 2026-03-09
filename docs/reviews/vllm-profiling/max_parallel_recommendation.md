# max_parallel=2 Recommendation for vLLM Backends

**Task**: TASK-VRF-006
**Date**: 2026-03-09
**Status**: Investigation complete

## Context

- TASK-VPT-001 reduced `max_parallel` from 2 to 1 due to KV cache contention on vLLM
- With `max_parallel=1`, budget starvation occurs: FBP-007 had 2820s budget vs potential 9600s with `max_parallel=2` (3.4x difference)
- vLLM runs on single GPU (typically 24GB or 80GB VRAM) with Qwen3-Coder-Next (FP8)
- 3+ parallel tasks caused 1.7x per-task slowdown (from local backend guide benchmarks)

## Analysis

### KV Cache Contention (max_parallel=2 failure mode)

Two concurrent SDK invocations each load context windows into vLLM's KV cache. When VRAM is insufficient:
- KV cache entries are evicted, forcing recomputation
- SSE stream errors occur ("SDK API error in stream: unknown" - TASK-FIX-46F2)
- Turn must be fully retried, wasting budget

**Severity**: Hard failure -- requires full turn retry, loses all progress in that turn.

### Budget Starvation (max_parallel=1 failure mode)

Sequential execution means a wave with N tasks takes N * task_time wall-clock:
- Feature budget is fixed (task_timeout * timeout_multiplier)
- Later tasks in a wave receive progressively less remaining budget
- Tasks may timeout before completing, producing partial or no results
- FBP-007 example: 2820s available vs 9600s needed

**Severity**: Soft failure -- produces partial results, but tasks may not complete.

### GPU Memory as Decision Signal

GPU VRAM utilization before a wave starts is a strong signal for safe parallelism:
- **<60% VRAM used**: Safe for 2 concurrent tasks (enough headroom for dual KV caches)
- **60-80% VRAM used**: Marginal -- prefer 1 task to avoid eviction pressure
- **>80% VRAM used**: Unsafe -- definitely limit to 1 task

This can be read via `pynvml` (`nvmlDeviceGetMemoryInfo`) or `nvidia-smi` without overhead.

## Implementation Delivered (TASK-VRF-006)

### New Modules

1. **`guardkit/orchestrator/gpu_monitor.py`** -- GPU memory monitoring protocol
   - `GpuMemoryPressure` enum (LOW/MEDIUM/HIGH/UNKNOWN)
   - `GpuMemorySnapshot` dataclass with utilization calculation
   - `GpuMonitor` protocol for dependency injection
   - `NullGpuMonitor` fallback (returns UNKNOWN)
   - `classify_pressure()` threshold function

2. **`guardkit/orchestrator/parallel_strategy.py`** -- Strategy resolver
   - `MaxParallelMode` enum (STATIC/DYNAMIC/PER_WAVE)
   - `ParallelConfig` dataclass with `from_legacy()` backward compat
   - `resolve_max_parallel()` -- resolves effective limit per wave

### Modified Files

3. **`guardkit/orchestrator/feature_orchestrator.py`** -- Integration
   - Accepts `parallel_config` parameter (backward compatible)
   - Wave execution uses `resolve_max_parallel()` instead of raw int

4. **`guardkit/cli/autobuild.py`** -- CLI option
   - `--max-parallel-strategy static|dynamic` option added
   - Help text corrected (was "2", now "1" with TASK-VPT-001 reference)

## Recommendation

### Short term (this release)

**Keep `max_parallel=1` as default for local backends.** Add `--max-parallel-strategy=dynamic` as opt-in for users who want GPU-aware scaling.

Usage:
```bash
guardkit autobuild feature FEAT-XXX --max-parallel-strategy=dynamic
```

### Medium term (next release)

Implement `NvmlGpuMonitor` using `pynvml` (optional dependency):
```python
# guardkit/orchestrator/gpu_monitor.py -- future addition
class NvmlGpuMonitor:
    def snapshot(self, device_index=0):
        handle = pynvml.nvmlDeviceGetHandleByIndex(device_index)
        info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        utilization = (info.used / info.total) * 100
        return GpuMemorySnapshot(
            total_mib=info.total // (1024 * 1024),
            used_mib=info.used // (1024 * 1024),
            free_mib=info.free // (1024 * 1024),
            pressure=classify_pressure(utilization),
        )
```

Test with actual vLLM workloads on GB10/A100 hardware. If results are positive (no KV cache evictions at <60% utilization), promote `dynamic` mode to default.

### Long term (future)

Consider per-wave overrides in feature YAML:
```yaml
waves:
  - tasks: [TASK-001, TASK-002]
    max_parallel: 1  # conservative for setup tasks
  - tasks: [TASK-003, TASK-004, TASK-005]
    max_parallel: 2  # allow parallelism for independent tasks
```

The `PER_WAVE` mode in `parallel_strategy.py` already supports this -- only needs frontmatter parsing.

## Rationale

The KV cache contention failure is **harder to recover from** (requires full turn retry, loses all progress) than budget starvation (which at least produces partial results). Therefore:

- **Conservative default** (`max_parallel=1`) is safer for unattended AutoBuild runs
- **Dynamic mode** (`--max-parallel-strategy=dynamic`) is available for experimentation
- **The infrastructure** (protocol, strategy resolver, CLI option) is in place for future GPU-aware scaling

## Test Results

GPU memory monitoring cannot be tested in CI (no GPU). However:
- All strategy resolution paths are unit tested
- NullGpuMonitor provides clean fallback
- Backward compatibility verified (existing `max_parallel` int still works)
- Semaphore-based wave limiting tested in `test_max_parallel.py`
