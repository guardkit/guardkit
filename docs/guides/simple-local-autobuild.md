# Simple Local AutoBuild Setup

Run GuardKit AutoBuild against a local vLLM server instead of the Anthropic API.

## Prerequisites

- NVIDIA GPU with sufficient VRAM (80GB+ for Qwen3-Coder-Next)
- Docker with NVIDIA Container Toolkit
- GuardKit installed (`pip install guardkit-py[autobuild]`)

## Quick Start

```bash
# 1. Start the vLLM server
./scripts/vllm-serve.sh

# 2. Wait for the model to load (3-5 min for 80B)
docker logs -f vllm-qwen3-coder

# 3. Verify the server is ready
curl http://localhost:8000/health
curl http://localhost:8000/v1/models

# 4. Run AutoBuild
ANTHROPIC_BASE_URL=http://localhost:8000 \
ANTHROPIC_API_KEY=vllm-local \
guardkit autobuild task TASK-XXX
```

## Model Alignment

**This is the most common cause of local AutoBuild failures.**

The vLLM server exposes your local model under an alias (`SERVED_MODEL_NAME` in `scripts/vllm-serve.sh`). The Claude Agent SDK's bundled `claude` CLI sends requests using its own hardcoded default model ID. These two values **must match exactly**, or every SDK request will return a 404.

### Why it matters

When AutoBuild invokes the Player or Coach agent, it uses the Claude Agent SDK which shells out to the bundled `claude` CLI. That CLI sends requests like:

```
POST /v1/messages
{ "model": "claude-sonnet-4-6", ... }
```

vLLM only responds to model names it knows about. If `SERVED_MODEL_NAME` is set to something different (e.g. `claude-sonnet-4-5-20241022`), vLLM returns 404 and the agent fails.

### How to verify alignment

```bash
# 1. Check what vLLM is serving
curl -s http://localhost:8000/v1/models | python3 -m json.tool
# Look for the "id" field — this is the served model name

# 2. Check what the CLI expects
ANTHROPIC_BASE_URL=http://localhost:8000 claude --version
# The default model ID is shown in the output
```

If they don't match, update `SERVED_MODEL_NAME` in `scripts/vllm-serve.sh` and restart the container.

### What breaks when they diverge

| Symptom | Cause |
|---------|-------|
| Player agent gets 404 on `/v1/messages` | `SERVED_MODEL_NAME` doesn't match CLI default |
| Coach SDK error: "model not found" | Same mismatch, hit during coach verification |
| AutoBuild stalls after "Invoking agent..." | Request rejected, retry loop exhausts attempts |

### Historical examples

- **TASK-REV-AB3D**: Player agent failed with 404 because `SERVED_MODEL_NAME` was set to an older model ID after a SDK upgrade.
- **TASK-REV-ED10**: Coach SDK invocation failed with the same root cause, discovered independently.

### When to check

Re-verify alignment whenever you:
- Upgrade `guardkit-py` or `claude-agent-sdk`
- Change the model preset in `vllm-serve.sh`
- See unexpected 404 errors in AutoBuild logs

## Model Presets

| Preset | Model | VRAM | Speed | Command |
|--------|-------|------|-------|---------|
| `next` (default) | Qwen3-Coder-Next FP8 | ~92GB | ~43 tok/s | `./scripts/vllm-serve.sh` |
| `30b` | Qwen3-Coder-30B-A3B | ~30GB | faster | `./scripts/vllm-serve.sh 30b` |
| `next-nvfp4` | Qwen3-Coder-Next NVFP4 | ~50GB | ~35 tok/s | `./scripts/vllm-serve.sh next-nvfp4` |
| `custom` | Any model | varies | varies | `./scripts/vllm-serve.sh custom org/model` |

## Troubleshooting

### Server won't start
```bash
# Check GPU availability
nvidia-smi

# Check Docker GPU support
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

### Out of memory
Reduce GPU utilization or switch to a smaller model:
```bash
VLLM_GPU_UTIL=0.6 ./scripts/vllm-serve.sh 30b
```

### Slow generation
Enable prefix caching (already enabled by default) and ensure `flashinfer` attention backend is supported on your GPU.
