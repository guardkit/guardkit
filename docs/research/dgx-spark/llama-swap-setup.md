# llama-swap Setup Guide for GB10 Dark Factory

**Status:** Ready to implement
**Companion doc:** [`dark-factory-economics-and-model-serving.md`](./dark-factory-economics-and-model-serving.md) — read that first for context and rationale.
**Target hardware:** Dell Pro Max GB10 (Blackwell SM121, 128 GB unified memory)

This guide documents how to stand up `mostlygeek/llama-swap` as the unified inference front door for the GuardKit dark factory, with the full fleet config for Jarvis + Forge + architect-agent + Graphiti + embeddings + AutoBuild.

---

## 1. Prerequisites

| Requirement | Why |
|---|---|
| GB10 running DGX OS with CUDA toolkit | `nvcc` available at `/usr/local/cuda/bin/nvcc` |
| Existing vLLM Graphiti on `:8000` (Qwen2.5-14B-Instruct-FP8-dynamic) | Proxied by llama-swap, lifecycle delegated to existing `vllm-graphiti.sh` |
| Existing vLLM embedder on `:8001` (nomic-embed-text-v1.5) | Proxied by llama-swap, lifecycle delegated to existing `vllm-embed.sh` |
| llama.cpp built with SM121 support | Serves the swap-members (Coder-Next, GPT-OSS 120B) |
| ~70 GB free disk space | Cache for the GGUF model files |
| Tailscale mesh up | So MacBook Pro can hit the llama-swap front door directly |

## 2. Install llama-swap

Two install paths — pick whichever fits:

### Docker (recommended for cleaner teardown)

```bash
# On GB10
docker pull ghcr.io/mostlygeek/llama-swap:cuda

# Create config and model directories
sudo mkdir -p /opt/llama-swap/config
sudo mkdir -p /opt/llama-swap/models
sudo chown -R $USER:$USER /opt/llama-swap
```

### Binary (simpler if you want systemd management)

```bash
# On GB10
cd /tmp
wget https://github.com/mostlygeek/llama-swap/releases/latest/download/llama-swap_linux_arm64.tar.gz
tar xzf llama-swap_linux_arm64.tar.gz
sudo mv llama-swap /usr/local/bin/
llama-swap --version
```

Pin a release version in automation rather than floating `latest` — the llama-swap release cadence is fast (several versions per week).

## 3. Build llama.cpp with SM121 support (if not already done)

```bash
# On GB10
sudo apt-get install libcurl4-openssl-dev clang cmake

git clone https://github.com/ggml-org/llama.cpp.git ~/llama.cpp
cd ~/llama.cpp

export CUDACXX=/usr/local/cuda/bin/nvcc
export PATH=/usr/local/cuda/bin:$PATH

cmake -B build \
  -DGGML_CUDA=ON \
  -DLLAMA_CURL=ON \
  -DGGML_CUDA_FA_ALL_QUANTS=ON \
  -DCMAKE_CUDA_ARCHITECTURES=121a-real \
  -DGGML_NATIVE=ON

cmake --build build --config Release -j 20

sudo cp build/bin/llama-server /usr/local/bin/
sudo cp build/bin/llama-cli    /usr/local/bin/
sudo cp build/bin/llama-bench  /usr/local/bin/

llama-server --version
```

> Compilation takes 5–15 minutes. The `CMAKE_CUDA_ARCHITECTURES=121a-real` target is specifically for Blackwell SM121 with real (not PTX-compiled) kernels, which is what eugr recommends for maximum performance on GB10.

## 4. Pre-download the GGUF models

```bash
# On GB10 — install uv if not already present
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env

# Use HF_HUB_ENABLE_HF_TRANSFER=1 for Rust-backed fast downloads
export HF_HUB_ENABLE_HF_TRANSFER=1

# Qwen3-Coder-Next (FP8) — ~60 GB
uv run --with "huggingface_hub>=0.24" --with hf_transfer \
  huggingface-cli download Qwen/Qwen3-Coder-Next-FP8-GGUF \
  Qwen3-Coder-Next-FP8.gguf \
  --local-dir /opt/llama-swap/models/qwen3-coder-next

# Qwen3-Coder-Next (int4-AutoRound) — ~35 GB, 2× faster generation
# Added 2026-04-24: martinB78's benchmarks show 66.7 tok/s vs 32.9 tok/s FP8.
# Test against FP8 before switching — if quality matches, this is strictly better.
uv run --with "huggingface_hub>=0.24" --with hf_transfer \
  huggingface-cli download Intel/Qwen3-Coder-Next-int4-AutoRound \
  --local-dir /opt/llama-swap/models/qwen3-coder-next-int4

# GPT-OSS 120B (MXFP4) — ~63 GB, use the Blackwell-optimised build
uv run --with "huggingface_hub>=0.24" --with hf_transfer \
  huggingface-cli download sowilow/gpt-oss-120b-DGX-Spark-GGUF \
  gpt-oss-120b-q4_mxfp4.gguf \
  --local-dir /opt/llama-swap/models/gpt-oss-120b
```

> The `sowilow/gpt-oss-120b-DGX-Spark-GGUF` repo specifically optimises for Blackwell SM121. Do not use the generic GPT-OSS GGUFs; they miss the Blackwell kernel tuning.

## 5. The config.yaml for the GuardKit fleet

Save as `/opt/llama-swap/config/config.yaml`:

```yaml
# GuardKit dark factory fleet config
# ----------------------------------
# Single front door at :9000 serving all agents.
# - Graphiti LLM + embeddings: delegated to existing vLLM services (always on)
# - Swap members: AutoBuild coder + reasoning/orchestration model
#
# Everything speaks either OpenAI /v1/chat/completions or Anthropic /v1/messages.
# Route by the "model" field in each request.

healthCheckTimeout: 600          # 10 min — GPT-OSS 120B cold-load can take 4 min
globalTTL: 1800                  # 30 min idle → unload swap members
startPort: 5800                  # llama-swap auto-assigns internal ports from here
includeAliasesInList: true
logLevel: info

# Optional: uncomment to require API key for all requests
# apiKeys:
#   - "${env.LLAMASWAP_API_KEY}"

models:
  # ============================================================
  # FOREVER GROUP — delegated to existing vLLM services
  # Lifecycle managed by existing vllm-graphiti.sh / vllm-embed.sh
  # llama-swap treats these as external; never starts or stops them.
  # ============================================================

  "qwen-graphiti":
    name: "Graphiti entity extraction (Qwen2.5-14B FP8, delegated)"
    # No cmd — llama-swap won't try to start this.
    # proxy: point at the already-running vLLM on :8000
    proxy: http://127.0.0.1:8000
    checkEndpoint: /health
    ttl: 0                       # Never unload from llama-swap's perspective
    aliases:
      - "neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic"  # current model id
      - "graphiti-llm"
    # If vllm-graphiti.sh isn't running, requests will 502.
    # That's correct behaviour — llama-swap isn't the vLLM supervisor.

  "nomic-embed":
    name: "Embeddings (nomic-embed-text-v1.5, delegated)"
    proxy: http://127.0.0.1:8001
    checkEndpoint: /health
    ttl: 0
    aliases:
      - "nomic-embed-text-v1.5"
      - "nomic-ai/nomic-embed-text-v1.5"
      - "embeddings"

  # ============================================================
  # BUILDERS GROUP — llama.cpp-managed, swap as needed
  # Native /v1/messages support for AutoBuild via Claude Agent SDK.
  # ============================================================

  "qwen-coder-next":
    name: "AutoBuild Player (Qwen3-Coder-Next FP8)"
    cmd: |
      llama-server
      --port ${PORT}
      --host 0.0.0.0
      --model /opt/llama-swap/models/qwen3-coder-next/Qwen3-Coder-Next-FP8.gguf
      --alias qwen-coder-next
      --ctx-size 131072
      --batch-size 2048
      --ubatch-size 2048
      --threads 16
      -ngl 999
      --no-mmap
      --flash-attn on
      --cache-type-k q8_0
      --cache-type-v q8_0
      --jinja
      --reasoning off
      --temp 0.1
      --top-p 0.95
    checkEndpoint: /health
    ttl: 1800                    # 30 min idle → unload
    concurrencyLimit: 4          # Up to 4 parallel Player requests
    aliases:
      - "Qwen/Qwen3-Coder-Next-FP8"
      - "autobuild-player"
      - "claude-sonnet-4-6"      # For Claude Agent SDK default-model fallbacks
      - "claude-opus-4-7"        # ditto

  "gpt-oss-120b":
    name: "Jarvis / Architect / Coach (GPT-OSS 120B MXFP4)"
    cmd: |
      llama-server
      --port ${PORT}
      --host 0.0.0.0
      --model /opt/llama-swap/models/gpt-oss-120b/gpt-oss-120b-q4_mxfp4.gguf
      --alias gpt-oss-120b
      --ctx-size 131072
      --batch-size 2048
      --ubatch-size 2048
      --threads 16
      -ngl 999
      --no-mmap
      --flash-attn on
      --cache-type-k q8_0
      --cache-type-v q8_0
      --jinja
      --chat-template-kwargs '{"reasoning_effort":"medium"}'
      --temp 0.6
      --top-p 0.95
    checkEndpoint: /health
    ttl: 1800
    concurrencyLimit: 2          # Reasoning tasks are heavier, fewer parallel
    aliases:
      - "openai/gpt-oss-120b"
      - "jarvis-reasoner"
      - "architect-reasoner"
      - "coach"

groups:
  # Always-on group — Graphiti + embeddings
  # persistent=true: builders group can't evict these
  # swap=false: run together, no eviction within group
  "forever":
    persistent: true
    swap: false
    exclusive: false
    members:
      - "qwen-graphiti"
      - "nomic-embed"

  # Swappable builders — one at a time
  # swap=true: only one loaded at a time within this group
  # exclusive=true: loading a builder doesn't touch the forever group
  "builders":
    swap: true
    exclusive: true
    members:
      - "qwen-coder-next"
      - "gpt-oss-120b"

# Preload qwen-coder-next on startup so the first Forge request doesn't pay cold load
hooks:
  on_startup:
    preload:
      - "qwen-coder-next"
```

### Key decisions baked into this config

| Decision | Reason |
|---|---|
| `--no-mmap` everywhere | DGX Spark unified memory: mmap causes severe slowdowns (confirmed in NVIDIA forum guide) |
| `--cache-type-k/v q8_0` | f16 KV cache on Qwen3.5 family causes quality degradation; q8_0 is the recommended setting for SM121 |
| `--reasoning off` on Coder-Next | Coder-Next doesn't produce thinking blocks anyway, but explicit suppression avoids the llama.cpp Issue #20090 thinking-block-drop bug |
| `--jinja` flag everywhere | Required for tool use (Claude Agent SDK sends `tool_use`/`tool_result` blocks) |
| Claude model aliases on Coder-Next | Claude Agent SDK sometimes requests by default model name; aliases catch those without requiring SDK-side config |
| `preload: qwen-coder-next` on startup | First AutoBuild request of the day doesn't pay the 2-4 min cold-load |
| Graphiti and embedder via `proxy:` only | Delegates lifecycle to existing scripts; llama-swap doesn't double-manage |
| `concurrencyLimit: 4` on Coder-Next | Memory bandwidth ceiling — more concurrent requests cause sub-linear throughput |
| `concurrencyLimit: 2` on GPT-OSS 120B | 120B with long reasoning chains saturates the memory bus faster |

## 6. Start llama-swap

### Docker

```bash
docker run -d \
  --name llama-swap \
  --runtime nvidia \
  --gpus all \
  --ipc=host \
  --restart unless-stopped \
  -p 9000:8080 \
  -v /opt/llama-swap/config:/app/config \
  -v /opt/llama-swap/models:/opt/llama-swap/models \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/mostlygeek/llama-swap:cuda \
  --config /app/config/config.yaml --listen 0.0.0.0:8080
```

### Binary (systemd)

> **Production note (2026-04-29):** the deployed unit on `promaxgb10-41b1` is a **user unit** at `~/.config/systemd/user/llama-swap.service`, not the system unit shown below — see [`llama-swap-systemd-supervision.md`](./llama-swap-systemd-supervision.md) for the actual deployed unit, the `-watch-config` flag wiring, validation results, and the pending one-shot sudo cleanup of a legacy stale system unit. New installs may pick either user-unit or system-unit form; the deployed-on-prod version is currently the user unit.

System unit form (alternative — single-user box, no desktop session):

```ini
[Unit]
Description=llama-swap — unified inference front door for dark factory
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=richardwoollcott
ExecStart=/usr/local/bin/llama-swap \
  -config /opt/llama-swap/config/config.yaml \
  -listen :9000 \
  -watch-config
Restart=always
RestartSec=10
# Let the subprocess tree (llama-server instances) live outside the unit
KillMode=control-group

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now llama-swap
sudo systemctl status llama-swap
```

> **Flag notes** (corrections from the 2026-04-29 deployment):
> - `llama-swap` v208 expects single-dash flags (`-config`, `-listen`), not GNU double-dash. `--config` will fail to parse.
> - `-watch-config` makes llama-swap re-read the config file when its mtime changes — eliminates the need for a manual `kill -HUP <llama-swap pid>` after every config edit. Strongly recommended.

## 7. Smoke tests

Run these from GB10 (or any Tailscale node — replace `localhost` with `promaxgb10-41b1`).

### 7.1 llama-swap is up

```bash
curl -s http://localhost:9000/health
# Expected: OK
```

### 7.2 Forever group is routing

```bash
# Graphiti LLM via OpenAI format
curl -s http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-graphiti",
    "messages": [{"role":"user","content":"Extract entities: Alice met Bob."}],
    "max_tokens": 64
  }' | python3 -m json.tool | head -30

# Embedder
curl -s http://localhost:9000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nomic-embed",
    "input": "test"
  }' | python3 -m json.tool | head -10
```

### 7.3 Builders group swap behaviour

```bash
# First request — triggers cold load of Coder-Next (or instant if preload succeeded)
time curl -s http://localhost:9000/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: dummy" \
  -d '{
    "model": "qwen-coder-next",
    "max_tokens": 256,
    "messages": [{"role":"user","content":"Write a Python function to check if a number is prime."}]
  }' | python3 -m json.tool | head -30

# Check what's loaded
curl -s http://localhost:9000/running

# Swap to GPT-OSS 120B (will unload Coder-Next since exclusive=true, swap=true)
time curl -s http://localhost:9000/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: dummy" \
  -d '{
    "model": "gpt-oss-120b",
    "max_tokens": 256,
    "messages": [{"role":"user","content":"Explain why the Forge collapses planning and build into one pipeline."}]
  }' | python3 -m json.tool | head -30

# Confirm the swap happened
curl -s http://localhost:9000/running
```

### 7.4 Tool use (the real AutoBuild test)

```bash
curl -s http://localhost:9000/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: dummy" \
  -d '{
    "model": "qwen-coder-next",
    "max_tokens": 512,
    "tools": [{
      "name": "get_weather",
      "description": "Get the current weather in a location",
      "input_schema": {
        "type": "object",
        "properties": {
          "location": {"type": "string"}
        },
        "required": ["location"]
      }
    }],
    "messages": [{"role":"user","content":"What is the weather in Bristol?"}]
  }' | python3 -m json.tool | head -60
```

Expect a `tool_use` content block in the response. If you get plain text instead, the `--jinja` flag isn't active or the model's chat template doesn't support tools — check the server logs.

## 8. Point AutoBuild at llama-swap

In the AutoBuild environment (shell rc or `~/.claude/settings.json`):

```bash
export ANTHROPIC_BASE_URL=http://promaxgb10-41b1:9000
export ANTHROPIC_AUTH_TOKEN=dummy
export ANTHROPIC_API_KEY=""                # must be empty, not unset
export CLAUDE_CODE_ATTRIBUTION_HEADER=0    # critical — prevents KV cache busting

# Optional: force AutoBuild to request Coder-Next by name
export ANTHROPIC_MODEL=qwen-coder-next
```

Then from any GuardKit repo:

```bash
guardkit autobuild task TASK-XXX
```

AutoBuild will talk to llama-swap on port 9000. llama-swap routes to the Coder-Next llama.cpp instance (or swaps to it if another model is loaded).

## 9. Operational monitoring

### 9.1 Web UI

Browse to `http://promaxgb10-41b1:9000/ui` for:
- Currently loaded models
- Per-request latency and token metrics
- Upstream logs from each running llama-server
- Manual model load/unload controls (useful for debugging)
- Real-time swap event log

### 9.2 Key endpoints

| Endpoint | Purpose |
|---|---|
| `GET /running` | JSON list of currently loaded models |
| `GET /log` | Tail of llama-swap's own logs |
| `POST /models/unload` | Manually unload a specific model |
| `GET /v1/models` | OpenAI-format model list (what agents see) |

### 9.3 Cost watch

Even though everything is local, watch for:
- Excessive swap churn (more than ~3 swaps/hour during Forge runs) — indicates the Forge Player→Coach loop is misordering work
- Long queue wait times (requests timing out before reaching the model) — `healthCheckTimeout` may need raising for cold loads on a just-booted GB10
- Cold-load TTL expiry (GPT-OSS 120B unloads after 30 min idle, then next architect session pays the 3-4 min load again) — either extend the TTL or add the reasoner to the `preload` hook

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Connection refused` on :9000 | llama-swap not running | `systemctl status llama-swap` or `docker logs llama-swap` |
| `502 Bad Gateway` on Graphiti requests | vLLM :8000 not running | Start `vllm-graphiti.sh` — llama-swap doesn't supervise it |
| First request takes 3-4 min | Cold model load | Either ensure `preload` hook worked, or accept it for first-of-day |
| AutoBuild returns plain text instead of `tool_use` | `--jinja` flag missing or model chat template broken | Check `/log` for chat-template errors |
| Swaps happening every few requests | Forge sending alternating Player/Coach requests | Reorder Forge loop to batch several Player turns before switching |
| Model never unloads despite TTL | Active request holding it open | `curl -s /running` to see active-request counts |
| `413 Request Entity Too Large` on big prompts | Client `max_tokens` + context > 128K | Either reduce prompt context or bump `--ctx-size` per model |
| OOM kill during swap | Previous model hadn't fully released memory | Check `cmdStop` — vLLM models need `docker stop <n>` for clean teardown |
| 504 during cold load | `healthCheckTimeout` too short for 120B load | Raise to 600+ seconds |

## 11. What stays unchanged

**Do not replace or edit these files** during llama-swap rollout:

- `scripts/vllm-serve.sh` — continues to manage AutoBuild vLLM on :8002 as a fallback
- `scripts/vllm-graphiti.sh` — continues to manage Graphiti vLLM on :8000
- `scripts/vllm-embed.sh` — continues to manage nomic-embed on :8001
- `.guardkit/llm-provider-switching.md` — continues to document the provider toggle for emergencies (Gemini/MacBook Ollama fallback paths)

llama-swap sits **on top** of the existing infrastructure, not as a replacement. If llama-swap has issues, the underlying scripts and services continue to work; you can point agents directly at :8000/:8001/:8002 as before.

## 12. Dynamic VRAM launcher for large models

> Added 2026-04-24 based on martinB78's full-stack guide review (see research doc §3.7).
> Source: ["Running a Full LLM Stack on DGX Spark GB10"](https://forums.developer.nvidia.com/t/running-a-full-llm-stack-on-dgx-spark-gb10-your-application-litellm-llama-swap-vllm-llama-cpp-ollama/367580)

When swapping large models (GPT-OSS 120B, Qwen3.5-122B) on GB10's unified memory, a recurring failure occurs: after the previous model container exits, CUDA doesn't immediately return all memory to the free pool. vLLM's startup check `free_memory >= gpu_memory_utilization × total` fails with a hardcoded high utilisation value.

Save as `/opt/llama-swap/scripts/launch-large-model.sh`:

```bash
#!/bin/bash
# Dynamically sets --gpu-memory-utilization based on actually-free VRAM at launch time.
# Adapted from martinB78's dgx-spark full-stack guide (April 2026).
# Usage: launch-large-model.sh PORT HOST MODEL_PATH MODEL_NAME
set -euo pipefail

PORT="${1}"; HOST="${2}"; MODEL_PATH="${3}"; MODEL_NAME="${4}"

MEM_LINE=$(nvidia-smi --query-gpu=memory.free,memory.total --format=csv,noheaders,nounits | head -1)
FREE_MIB=$(echo "$MEM_LINE" | awk -F',' '{gsub(/ /,"",$1); print $1+0}')
TOTAL_MIB=$(echo "$MEM_LINE" | awk -F',' '{gsub(/ /,"",$2); print $2+0}')

# GB10: nvidia-smi reports 128 GiB (131072 MiB); CUDA sees 121.69 GiB (124610 MiB).
GMEM=$(awk -v f="$FREE_MIB" -v t_nv="$TOTAL_MIB" 'BEGIN {
    cuda_t = 124610; safety = 3072;
    overhead = (t_nv > cuda_t) ? t_nv - cuda_t : 0;
    cuda_free = f - overhead - safety;
    if (cuda_free < 0) cuda_free = 0;
    u = cuda_free / cuda_t;
    if (u > 0.85) u = 0.85; if (u < 0.60) u = 0.60;
    printf "%.2f", u;
}')

[ -z "$GMEM" ] || [ "$FREE_MIB" = "0" ] && GMEM="0.75"
echo "[auto-gmem] free=${FREE_MIB}MiB / total=${TOTAL_MIB}MiB → util=${GMEM}"

exec llama-server --port "${PORT}" --host "${HOST}" \
    --model "${MODEL_PATH}" --alias "${MODEL_NAME}" \
    --ctx-size 131072 --batch-size 2048 --ubatch-size 2048 \
    --threads 16 -ngl 999 --no-mmap --flash-attn on \
    --cache-type-k q8_0 --cache-type-v q8_0 --jinja --temp 0.6 --top-p 0.95
```

```bash
chmod +x /opt/llama-swap/scripts/launch-large-model.sh
```

Reference from `config.yaml` for any L-tier model:

```yaml
  "gpt-oss-120b":
    cmd: /opt/llama-swap/scripts/launch-large-model.sh ${PORT} 0.0.0.0 /opt/llama-swap/models/gpt-oss-120b/gpt-oss-120b-q4_mxfp4.gguf gpt-oss-120b
    cmdStop: "pkill -f 'llama-server.*gpt-oss-120b'"
```

## 13. LiteLLM routing layer (Phase 4)

> Added 2026-04-24 based on griffith.mark's three-stage model and martinB78's full-stack guide review.
> See research doc §3.8 for the rationale.

LiteLLM sits in front of llama-swap and adds routing intelligence, cloud fallbacks, and usage logging. This is Phase 4 — implement after llama-swap is stable.

```bash
pip install litellm[proxy] --break-system-packages
```

Save as `/opt/litellm/config.yaml`:

```yaml
model_list:
  - model_name: qwen-coder-next
    litellm_params:
      model: openai/qwen-coder-next
      api_base: "http://localhost:9000/v1"
      api_key: "dummy"
  - model_name: gpt-oss-120b
    litellm_params:
      model: openai/gpt-oss-120b
      api_base: "http://localhost:9000/v1"
      api_key: "dummy"
      supports_reasoning: true
  - model_name: claude-sonnet-4-6        # Claude Agent SDK catch-all
    litellm_params:
      model: openai/qwen-coder-next
      api_base: "http://localhost:9000/v1"
      api_key: "dummy"
  - model_name: gemini-3.1-pro           # Cloud fallback — interactive only
    litellm_params:
      model: gemini/gemini-3.1-pro
      api_key: "os.environ/GEMINI_API_KEY"

litellm_settings:
  drop_params: true
```

Start: `litellm --config /opt/litellm/config.yaml --port 14000 --host 0.0.0.0`

Monitor at `http://promaxgb10-41b1:14000/ui` for per-model token counts, latency, and cost breakdown.

## 14. Future enhancements

- **Fine-tuned specialist models** — once Gemma 4 31B fine-tunes land (GCSE tutor validated first on Bedrock, then other specialists), register them as additional members of the builders group
- **Preload tuning** — if Jarvis becomes the most-invoked agent, swap the preload target to `gpt-oss-120b` instead of `qwen-coder-next`
- **Peer federation** — if a second machine is added (second GB10, Mac Studio), enable llama-swap peers so agents on either node see a unified model list
- **API key enforcement** — once multi-user (James, Mark with scoped access), add `apiKeys` and per-key rate limits to separate concerns
- **Concurrency tuning from real data** — after two weeks of Forge runs, analyse the web UI metrics for actual parallelism patterns and adjust `concurrencyLimit` per model
- **Qwen3-Coder-Next int4-AutoRound A/B test** — martinB78's benchmarks show 66.7 tok/s vs 32.9 tok/s FP8, at ~35 GB vs ~60 GB. If quality matches, switch to int4 as the default Player model (Phase 2b)
- **Qwen3.6-27B multi-purpose evaluation** — once community benchmarks are available, test as a single always-loaded model for coding + reasoning + extraction (Phase 5)
- **Dataset factory via llama-swap** — point agentic-dataset-factory at :9000 with model=gpt-oss-120b for co-existence with Graphiti (Phase 2c, see research doc §3.11)
- **sparkrun adoption** — monitor dbsci's sparkrun for maturity
- **martinB78's Docker-based model serving** — evaluate `--network container:llama-swap` pattern for cleaner network isolation

## 15. Rollback

If llama-swap misbehaves:

```bash
# Stop the front door
sudo systemctl stop llama-swap   # or: docker stop llama-swap

# Agents revert to direct endpoints via existing env vars
# (AutoBuild: ANTHROPIC_BASE_URL=http://promaxgb10-41b1:8002 for vLLM Coder-Next)
# (Graphiti: already pointing at :8000 directly via .guardkit/graphiti.yaml)
```

No data loss — llama-swap is stateless. The only thing that changes is the routing layer.
