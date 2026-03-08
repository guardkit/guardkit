# Local Backend AutoBuild Guide

**Version**: 1.0.0
**Last Updated**: 2026-02-27
**Compatibility**: GuardKit v1.0+, Claude Agent SDK v0.1.0+
**Based on**: TASK-REV-C960 vLLM/Qwen3 GB10 production review

---

GuardKit AutoBuild can run against local LLM backends (vLLM, Ollama) instead of the Anthropic API. This guide covers when to use a local backend, how to configure it for best results, and how to troubleshoot common issues.

For basic vLLM server setup and model alignment, see [Simple Local AutoBuild Setup](simple-local-autobuild.md).

---

## Table of Contents

- [When to Use Local vs API](#when-to-use-local-vs-api)
- [Configuration](#configuration)
- [Performance Characteristics](#performance-characteristics)
- [Recommended Settings](#recommended-settings)
- [Troubleshooting](#troubleshooting)
- [Reference Data](#reference-data)

---

## When to Use Local vs API

### Decision Matrix

| Factor | Local (vLLM/Ollama) | Anthropic API |
|--------|---------------------|---------------|
| **Time pressure** | Overnight / unattended builds | Interactive / time-critical |
| **Cost** | Electricity only | $3-8 per feature build |
| **Connectivity** | Offline / air-gapped | Requires internet |
| **Task complexity** | Well-defined acceptance criteria | Ambiguous / nuanced requirements |
| **First-pass accuracy** | ~50% (expect retry turns) | ~100% |
| **Throughput** | 2.7-5.9x slower per task | Baseline |
| **Parallelism** | GPU-constrained (2-3 tasks max) | API-rate-limited (higher ceiling) |

### Use local when

- You can run builds overnight or during off-hours
- Cost matters more than speed (e.g., large feature builds with 8+ tasks)
- You're working offline or on an air-gapped network
- Tasks have clear, specific acceptance criteria with minimal ambiguity
- You have an NVIDIA GPU with 80GB+ VRAM available

### Use the Anthropic API when

- You need results within minutes, not hours
- Requirements are complex, ambiguous, or need interpretation
- You're iterating interactively and want fast feedback
- First-pass accuracy matters (avoids retry overhead)
- You don't have a suitable GPU available

---

## Configuration

### Environment Variables

AutoBuild detects a local backend automatically when `ANTHROPIC_BASE_URL` points to `localhost` or `127.0.0.1`.

```bash
# Point to your local vLLM server
export ANTHROPIC_BASE_URL=http://localhost:8000
export ANTHROPIC_API_KEY=vllm-local  # Any non-empty string works

# Optional overrides
export GUARDKIT_TIMEOUT_MULTIPLIER=4.0   # Override auto-detected multiplier
export GUARDKIT_MAX_PARALLEL_TASKS=2     # Override parallel task limit
```

### Auto-Detection Behavior

When a local backend is detected, GuardKit automatically adjusts:

| Setting | API Default | Local Auto-Detect |
|---------|-------------|-------------------|
| `timeout_multiplier` | 1.0 | 4.0 |
| `max_parallel` | unlimited | 2 |
| SDK max turns | 100 | 50 |

These defaults are based on measured production data from TASK-REV-C960.

### CLI Flags

```bash
guardkit autobuild task TASK-XXX \
  --max-turns 5 \              # Player-Coach iteration limit (default: 5)
  --sdk-timeout 1200 \         # Base SDK timeout in seconds (default: 1200)
  --timeout-multiplier 4.0 \   # Multiplied into SDK timeout (auto: 4.0 for local)
  --max-parallel 2 \           # Max concurrent tasks in feature builds
  --model claude-sonnet-4-5-20250929 \  # Model name (must match vLLM served name)
  --fresh                      # Start fresh, ignore previous state
```

### Priority Resolution

Configuration values resolve in this order (highest priority first):

1. Environment variable (`GUARDKIT_TIMEOUT_MULTIPLIER`, `GUARDKIT_MAX_PARALLEL_TASKS`)
2. CLI flag (`--timeout-multiplier`, `--max-parallel`)
3. Auto-detection (based on `ANTHROPIC_BASE_URL`)

---

## Performance Characteristics

The following data comes from the TASK-REV-C960 review, which ran an 8-task feature build on a GB10 system with Qwen3-Coder-Next (FP8) via vLLM.

### Per-Task Timing

| Metric | vLLM/Qwen3 | Anthropic Claude | Ratio |
|--------|-------------|------------------|-------|
| Average time (all tasks) | 22.8 min | 8.4 min | 2.7x slower |
| Tasks needing 2 turns | 47 min avg | ~8 min | 5.9x slower |
| Tasks completing in 1 turn | ~12 min | ~8 min | 1.5x slower |

### Accuracy

| Metric | vLLM/Qwen3 | Anthropic Claude |
|--------|-------------|------------------|
| First-pass success rate | 50% | 100% |
| Tasks needing retry | 4 of 8 | 0 of 5 |
| SDK turn ceiling hits (first pass) | 67% | 0% |

### Parallelism

| Configuration | Wall-Clock Overhead |
|---------------|---------------------|
| 1 task at a time | Baseline |
| 2 parallel tasks | Minimal GPU contention |
| 3 parallel tasks | 1.7x per-task slowdown from GPU contention |

Parallel execution still saves 2.6-2.7x wall-clock time despite the contention penalty. The sweet spot is `--max-parallel 2`.

### Total Build Time

For an 8-task feature build:

| Backend | Total Wall-Clock | Per-Task Average |
|---------|-----------------|------------------|
| vLLM/Qwen3 (3 parallel) | ~183 min (~3 hours) | 22.8 min |
| Anthropic API (estimated) | ~42 min | 8.4 min |
| Ratio | 4.3x slower | 2.7x slower |

### SDK Timeout Calculation

The effective SDK timeout is calculated as:

```
effective_timeout = base_timeout x mode_multiplier x complexity_multiplier x backend_multiplier
```

Example for a local backend with a medium-complexity task:

```
1200s x 1.5 (mode) x 1.5 (complexity) x 4.0 (local) = 10,800s (3 hours)
```

---

## Recommended Settings

### Single Task

```bash
ANTHROPIC_BASE_URL=http://localhost:8000 \
ANTHROPIC_API_KEY=vllm-local \
guardkit autobuild task TASK-XXX --max-turns 5
```

Let auto-detection handle timeout multiplier and SDK turn ceiling.

### Feature Build (Multiple Tasks)

```bash
ANTHROPIC_BASE_URL=http://localhost:8000 \
ANTHROPIC_API_KEY=vllm-local \
guardkit autobuild task TASK-XXX --max-turns 5 --max-parallel 2 --fresh
```

Use `--max-parallel 2` to avoid GPU contention. The `--fresh` flag ensures clean state for overnight runs.

### Maximizing First-Pass Success

Local models perform best with:

- **Specific acceptance criteria** — avoid vague requirements like "improve performance"
- **Smaller task scope** — split large tasks into focused subtasks
- **Standard mode** — TDD mode increases turn count and compounds the local slowdown

---

## Troubleshooting

### SDK Turn Ceiling Hits

**Symptom**: Tasks run for a long time, then the Coach reports incomplete work. Logs show `SDK max turns reduced to 50 for local backend`.

**Cause**: The SDK limits local backends to 50 turns per invocation (vs 100 for API). Complex tasks may exhaust this budget on the first pass.

**Fix**:
- This is expected — the Player-Coach loop will retry. 50% of tasks succeed on first pass, the rest on the second.
- If tasks consistently fail after all retry turns, simplify the acceptance criteria or split the task.
- Monitor ceiling hit rates: a rate above 60% triggers a warning in the build summary.

### GPU Contention / Slow Generation

**Symptom**: Tasks take much longer than expected. `nvidia-smi` shows high GPU utilization from multiple vLLM worker processes.

**Cause**: Running too many parallel tasks saturates GPU compute/memory bandwidth.

**Fix**:
```bash
# Reduce parallelism
guardkit autobuild task TASK-XXX --max-parallel 2

# Or via environment variable
export GUARDKIT_MAX_PARALLEL_TASKS=2
```

Measured impact: 3 parallel tasks cause a 1.7x per-task slowdown. 2 parallel tasks have minimal contention.

### Timeout Errors

**Symptom**: `SDK timeout exceeded` or tasks marked as BLOCKED after a long wait.

**Cause**: The effective timeout wasn't large enough for the task complexity on a local backend.

**Fix**:
```bash
# Increase the timeout multiplier (default auto-detects 4.0 for local)
export GUARDKIT_TIMEOUT_MULTIPLIER=6.0

# Or increase the base SDK timeout
guardkit autobuild task TASK-XXX --sdk-timeout 1800
```

The timeout formula is: `base_timeout x mode_multiplier x complexity_multiplier x backend_multiplier`. Check the build log for the calculated effective timeout.

### Model Alignment Errors (404)

**Symptom**: Player or Coach agent fails with 404 on `/v1/messages`. AutoBuild stalls after "Invoking agent...".

**Cause**: The model name served by vLLM doesn't match what the Claude Agent SDK expects.

**Fix**: See [Model Alignment](simple-local-autobuild.md#model-alignment) in the setup guide. Verify with:
```bash
# Check what vLLM is serving
curl -s http://localhost:8000/v1/models | python3 -m json.tool

# The "id" field must match the CLI's default model name
```

### Stream / Connection Errors

**Symptom**: Intermittent SSE stream errors or connection resets in the build log.

**Cause**: vLLM occasionally drops SSE connections under heavy load or during long generations.

**Fix**: GuardKit retries automatically (1 retry with 30s backoff). If errors persist:
- Check vLLM server logs: `docker logs vllm-qwen3-coder`
- Reduce parallelism to lower server load
- Ensure no other processes are competing for GPU resources

### vLLM Server Health Check

Quick diagnostic commands:

```bash
# Server health
curl http://localhost:8000/health

# Available models
curl -s http://localhost:8000/v1/models | python3 -m json.tool

# GPU status
nvidia-smi

# vLLM container logs
docker logs --tail 50 vllm-qwen3-coder
```

---

## Reference Data

### Source

All performance data in this guide comes from the **TASK-REV-C960** review, which analyzed an 8-task database feature build on:

- **Hardware**: NVIDIA GB10 (desktop Grace Blackwell)
- **Model**: Qwen3-Coder-Next (FP8 quantization, ~92GB VRAM)
- **Server**: vLLM with flashinfer attention backend
- **AutoBuild config**: `--max-turns 5`, `timeout_multiplier=4.0`, SDK max turns 50

### Key Constants

| Constant | Value | Location |
|----------|-------|----------|
| `DEFAULT_SDK_TIMEOUT` | 1200s (20 min) | `guardkit/orchestrator/agent_invoker.py` |
| `MAX_SDK_TIMEOUT` | 3600s (1 hour) | `guardkit/orchestrator/agent_invoker.py` |
| `TASK_WORK_SDK_MAX_TURNS` | 100 (API), 50 (local) | `guardkit/orchestrator/agent_invoker.py` |
| `MAX_SDK_STREAM_RETRIES` | 1 | `guardkit/orchestrator/agent_invoker.py` |
| `SDK_STREAM_RETRY_BACKOFF` | 30s | `guardkit/orchestrator/agent_invoker.py` |
| Ceiling warning threshold | 60% | `guardkit/orchestrator/sdk_ceiling.py` |

### Related Documentation

- [Simple Local AutoBuild Setup](simple-local-autobuild.md) — vLLM server setup and model alignment
- [AutoBuild Workflow Guide](autobuild-workflow.md) — Full AutoBuild architecture and usage
- [AutoBuild Instrumentation Guide](autobuild-instrumentation-guide.md) — Event types, token tracking, vLLM metrics, and prompt profile A/B comparison
- [CLI vs Claude Code](cli-vs-claude-code.md) — When to use the CLI vs slash commands
