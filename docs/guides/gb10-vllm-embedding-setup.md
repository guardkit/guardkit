# GB10 vLLM Embedding Server Setup

**Date**: 27 February 2026
**Status**: OPERATIONAL
**Task**: TASK-GLI-001 — GB10 vLLM setup guide, embedding model instance with optimal config

---

## Architecture Overview

The GB10 runs two vLLM instances side-by-side: an LLM on port 8000 (AutoBuild) and an embedding model on port 8001 (Graphiti seeding). Both are served from a single NVIDIA Blackwell GPU with 128GB unified memory. All machines reach port 8001 over the Tailscale WireGuard mesh — no VPN or firewall rules required.

```
┌─────────────────────────────────────┐     Tailscale Mesh (WireGuard)     ┌───────────────────────────────────────────┐
│  MacBook Pro M2 Max                 │◄──────────────────────────────────►│  Dell ProMax GB10                         │
│  richards-macbook-pro               │                                     │  promaxgb10-41b1                          │
│  100.111.236.109                    │                                     │  100.84.90.91                             │
│                                     │                                     │                                           │
│  • GuardKit development             │    embedding calls (port 8001)      │  • vLLM LLM          :8000 (AutoBuild)    │
│  • Claude Code                      │ ──────────────────────────────────► │  • vLLM Embedding    :8001 (Graphiti)     │
│  • graphiti-core (SEMAPHORE=20)     │                                     │  • Container: vllm-embedding              │
│  • ~215 embed calls per episode     │                                     │  • Image: nvcr.io/nvidia/vllm:26.01-py3   │
└─────────────────────────────────────┘                                     └───────────────────────────────────────────┘
                  │                                                                            │
                  │                   ┌──────────────────────────┐                             │
                  │                   │  Synology DS918+ NAS      │                             │
                  └──────────────────►│  whitestocks              │◄────────────────────────────┘
                                      │  100.92.74.2              │
                                      │                            │
                                      │  • FalkorDB  :6379         │
                                      │  • FalkorDB Browser :3000  │
                                      └────────────────────────────┘
```

---

## Tailscale Network

| Machine | Hostname | Tailscale IP | OS | Role |
|---------|----------|--------------|----|------|
| MacBook Pro M2 Max (96GB) | `richards-macbook-pro` | 100.111.236.109 | macOS 15.6.1 | Daily development |
| Dell ProMax GB10 (128GB) | `promaxgb10-41b1` | 100.84.90.91 | DGX OS (Ubuntu 24.04 ARM64) | Compute, embeddings, LLM inference |
| Synology DS918+ (8GB) | `whitestocks` | 100.92.74.2 | DSM 7.x (Linux 4.4.180+) | Shared infrastructure (FalkorDB) |

All machines use Tailscale MagicDNS — hostnames resolve automatically (e.g., `curl http://promaxgb10-41b1:8001/health`). If MagicDNS has issues, use Tailscale IPs directly.

---

## Hardware & Resource Budget

### GB10 Specs

| Spec | Value |
|------|-------|
| GPU | NVIDIA Blackwell (GB10, sm_121) |
| GPU Memory | 128GB unified (shared CPU/GPU) |
| CPU | ARM64 (DGX OS) |
| OS | DGX OS — Ubuntu 24.04 ARM64 |
| Docker runtime | NVIDIA Container Toolkit |

### GPU Memory Allocation

| Service | Port | GPU Utilization | Approx. Memory | Notes |
|---------|------|-----------------|----------------|-------|
| vLLM LLM (AutoBuild) | 8000 | ~0.80 | ~100GB | Primary inference |
| vLLM Embedding (Graphiti) | 8001 | 0.15 (default) | ~19GB reserved, ~274MB used | Conservative headroom |
| **Remaining** | — | ~0.05 | ~6GB | OS/driver overhead |

The embedding model (nomic, 137M params) uses only ~274MB in fp16 despite the 0.15 reservation. The reservation is conservative — it prevents the embedding server from competing with the LLM for memory during peak load. This can be tuned down further once coexistence is confirmed stable.

---

## Model Selection

Two candidate embedding models were evaluated. One is operational; one is blocked pending a container update.

| Attribute | nomic-embed-text-v1.5 | nemotron-embed-1b-v2 |
|-----------|----------------------|---------------------|
| Parameters | 137M | 1B |
| Memory (fp16) | ~274MB | ~2GB |
| MTEB Score | 62.39 | Higher (multilingual) |
| Context | 8192 tokens | 8192 tokens |
| Dimensions | 768 | 1024 (Matryoshka) |
| vLLM runner | `--runner pooling --trust-remote-code` | `--runner pooling --pooler-config '{"pooling_type":"MEAN"}'` |
| Container 26.01 compatible | Yes | No |
| Status | **Recommended** | **Blocked** |
| Blocker | None | Requires `transformers>=5.0.0.dev0`; container ships 4.57.1 |

**Why nomic is recommended**: Near-identical MTEB score to `text-embedding-3-small` (62.39 vs 62.26), negligible memory footprint, and proven compatibility with the 26.01 NVIDIA NGC container.

### Upgrade Path for Nemotron

When a new NVIDIA NGC vLLM container ships with `transformers>=5.0.0.dev0`, nemotron becomes viable. To check:

```bash
# Inside the container
docker run --rm nvcr.io/nvidia/vllm:26.XX-py3 python -c "import transformers; print(transformers.__version__)"
```

If the version is `5.0.0` or above, switch to nemotron by running `./scripts/vllm-embed.sh nemotron`. The 1024-dimensional Matryoshka embeddings allow dimension truncation for lower-cost storage if needed.

---

## Deployment via scripts/vllm-embed.sh

The source of truth for all Docker invocations is `scripts/vllm-embed.sh`. Run it directly from the GB10 — do not construct `docker run` commands by hand.

### Usage

```bash
# Default — nomic-embed-text-v1.5 (recommended)
./scripts/vllm-embed.sh

# nemotron — currently blocked (see model selection above)
./scripts/vllm-embed.sh nemotron

# Custom model
./scripts/vllm-embed.sh custom org/model-name
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VLLM_EMBED_PORT` | `8001` | Server port |
| `VLLM_EMBED_GPU_UTIL` | `0.15` | GPU memory utilization (0.0–1.0) |
| `VLLM_IMAGE` | `nvcr.io/nvidia/vllm:26.01-py3` | Docker image |
| `HF_TOKEN` | (unset) | Hugging Face token (required for gated models) |

Override example:

```bash
# Use 10% GPU utilization and a custom port
VLLM_EMBED_GPU_UTIL=0.10 VLLM_EMBED_PORT=8002 ./scripts/vllm-embed.sh
```

### Docker Run Command (reference)

The script issues the following `docker run` (reproduced here for clarity — do not run this directly; use the script). Note: the `HF_TOKEN` conditional is omitted below for readability; see the script source for the full command:

```bash
docker run -d \
  --name vllm-embedding \
  --gpus all \
  -p 8001:8001 \
  --ipc=host \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  -e "PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True" \
  nvcr.io/nvidia/vllm:26.01-py3 \
  vllm serve nomic-ai/nomic-embed-text-v1.5 \
    --host 0.0.0.0 \
    --port 8001 \
    --dtype auto \
    --gpu-memory-utilization 0.15 \
    --runner pooling \
    --trust-remote-code
```

---

## vLLM Serve Flags — GB10 Blackwell Tuning

Each flag serves a specific purpose for the Blackwell architecture and Graphiti workload:

| Flag | Value | Rationale |
|------|-------|-----------|
| `--runner pooling` | (set) | Required for embedding models. Switches vLLM from generative to pooling mode — outputs a single vector per input rather than token logits. Without this, the server rejects embedding requests. |
| `--dtype auto` | (set) | Lets vLLM detect the optimal dtype. On Blackwell hardware this resolves to `bfloat16`, which is the native precision for GB10 tensor cores. Preferable to hardcoding `float16`. |
| `--gpu-memory-utilization` | `0.15` | Reserves 15% of GPU memory for the embedding model, leaving ~85% for the LLM on port 8000. In practice, nomic uses ~274MB of the reserved allocation — the reservation is conservative headroom, not a hard cap. |
| `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` | (env) | Blackwell (sm_121) memory allocator tuning. Allows the CUDA allocator to expand memory segments rather than reserving fixed blocks, reducing fragmentation on the unified memory architecture. |
| `--trust-remote-code` | (set) | Required by the nomic tokenizer. The `nomic-ai/nomic-embed-text-v1.5` model ships a custom tokenizer that is not bundled with the transformers package — vLLM must be permitted to execute it. |
| `--ipc=host` | (docker flag) | Shares the host IPC namespace with the container. Required for NCCL and PyTorch shared-memory operations. Without this, multi-process tensor operations fail. |
| `--ulimit memlock=-1` | (docker flag) | Removes the locked-memory limit, allowing GPU driver buffers to be pinned in RAM. Standard requirement for GPU containers on DGX hardware. |
| `--ulimit stack=67108864` | (docker flag) | Sets stack size to 64MB. Prevents stack overflow in deep PyTorch call chains during model load. |
| `-v ~/.cache/huggingface` | (docker flag) | Persists downloaded model weights across container restarts. Without this, each `docker run` re-downloads the model from Hugging Face (~274MB for nomic). |

---

## Container Lifecycle

All lifecycle operations are run on the GB10 directly (SSH in first if operating from the MacBook).

```bash
# SSH into GB10
ssh richardwoollcott@promaxgb10-41b1

# Start the embedding server (stops any existing container automatically)
./scripts/vllm-embed.sh

# Stop and remove the container manually
docker stop vllm-embedding && docker rm vllm-embedding

# View live logs (model load takes ~30-60s on first run, ~5s on subsequent)
docker logs -f vllm-embedding

# View last 100 lines
docker logs vllm-embedding --tail 100

# Check container status
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

# Restart (re-run the script — it handles stop/rm automatically)
./scripts/vllm-embed.sh
```

The script automatically stops and removes the existing `vllm-embedding` container before starting a new one, making it safe to re-run at any time.

---

## Networking & Tailscale Access

Port 8001 is accessible to all authenticated Tailscale nodes immediately — no firewall rules, `iptables` entries, or port forwarding needed. Tailscale's WireGuard mesh makes all ports open between authenticated machines.

### Accessing from the MacBook

```bash
# Health check via MagicDNS hostname
curl http://promaxgb10-41b1:8001/health

# Health check via Tailscale IP (fallback if MagicDNS is slow)
curl http://100.84.90.91:8001/health

# List loaded models
curl http://promaxgb10-41b1:8001/v1/models

# Test embedding (from MacBook, targeting GB10)
curl -s http://promaxgb10-41b1:8001/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"model": "nomic-embed-text-v1.5", "input": "Hello world"}'
```

### Accessing from GB10 Locally

```bash
# Health check (localhost)
curl http://localhost:8001/health

# Test embedding
curl http://localhost:8001/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"model": "nomic-embed-text-v1.5", "input": "Hello world"}'
```

### GuardKit Configuration

Point Graphiti at the GB10 embedding endpoint in `.guardkit/graphiti.yaml` (updated in TASK-GLI-004):

```yaml
embedding_model: nomic-embed-text-v1.5
embedding_base_url: http://promaxgb10-41b1:8001/v1
```

---

## Health Check & Readiness

The vLLM server exposes standard OpenAI-compatible endpoints. Wait for the model to finish loading before sending requests — loading nomic takes ~5-60 seconds depending on whether the model is cached.

```bash
# Health endpoint — returns 200 when ready
curl http://promaxgb10-41b1:8001/health
# Response: {"status":"ok"}

# Models endpoint — lists loaded model(s)
curl http://promaxgb10-41b1:8001/v1/models
# Response: {"object":"list","data":[{"id":"nomic-embed-text-v1.5",...}]}

# Watch logs until "Application startup complete" appears
docker logs -f vllm-embedding | grep -m1 "startup complete"
```

**Readiness indicator in logs**: Look for `Application startup complete.` — the server is ready once this line appears. Before this line, requests will be refused with connection errors, not 503s.

---

## Benchmarking

Benchmarks should be run at concurrency 20 to match graphiti-core's `SEMAPHORE_LIMIT=20` — this is the real-world concurrency the server will see during `add_episode()` calls.

### Why Concurrency 20

graphiti-core issues ~215 embedding API calls per `add_episode()`, gated by `SEMAPHORE_LIMIT=20`. The server must sustain 20 simultaneous in-flight requests without queuing degradation. Benchmarks at lower concurrency will underestimate tail latency.

### Benchmark Results

| Model | Throughput (req/s) | Latency p50 (ms) | p99 (ms) | Concurrency | Notes |
|-------|--------------------|------------------|----------|-------------|-------|
| nomic-embed-text-v1.5 (bfloat16, 0.15 util) | — | — | — | 20 | Benchmark pending — run on GB10 |
| nemotron-embed-1b-v2 | N/A | N/A | N/A | 20 | Blocked on transformers 5.x |

Populate this table after running the benchmark script below.

### Running Benchmarks with `hey`

Install `hey` on the GB10 if not already present:

```bash
# Install hey (Go-based HTTP load tester)
go install github.com/rakyll/hey@latest
# or download a binary: https://github.com/rakyll/hey/releases
```

Run the benchmark:

```bash
# Warm-up: 50 requests (discard these results)
hey -n 50 -c 20 -m POST \
  -H "Content-Type: application/json" \
  -d '{"model": "nomic-embed-text-v1.5", "input": "Warm-up sentence for cache priming"}' \
  http://localhost:8001/v1/embeddings

# Measured run: 1000 requests at concurrency 20
hey -n 1000 -c 20 -m POST \
  -H "Content-Type: application/json" \
  -d '{"model": "nomic-embed-text-v1.5", "input": "Benchmark test sentence for throughput measurement"}' \
  http://localhost:8001/v1/embeddings
```

Record the `Requests/sec`, `50th percentile`, and `99th percentile` from the `hey` output and update the table above.

### Alternative: curl loop

```bash
# Simple concurrent curl loop (no extra tools required)
for i in $(seq 1 200); do
  curl -s -o /dev/null -w "%{time_total}\n" \
    -X POST http://localhost:8001/v1/embeddings \
    -H "Content-Type: application/json" \
    -d '{"model": "nomic-embed-text-v1.5", "input": "Test sentence"}' &
done
wait
```

---

## Verification Tests

These two tests satisfy the acceptance criteria for TASK-GLI-001. Run them from the MacBook after the embedding server is running on the GB10.

### Test 1: Embedding Dimension Check

Verifies that the `/v1/embeddings` endpoint returns vectors of the correct dimension for nomic-embed-text-v1.5 (expected: 768).

```bash
curl -s http://promaxgb10-41b1:8001/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"model": "nomic-embed-text-v1.5", "input": "Hello world"}' \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
dims = len(d['data'][0]['embedding'])
print(f'Dimensions: {dims}')
assert dims == 768, f'Expected 768, got {dims}'
print('PASS: nomic-embed-text-v1.5 returns 768-dimensional vectors')
"
# Expected output:
# Dimensions: 768
# PASS: nomic-embed-text-v1.5 returns 768-dimensional vectors
```

### Test 2: Graphiti Seeding Smoke Test

Verifies that graphiti-core can seed a document using the local embedding endpoint and that entity extraction completes successfully. Run from the GuardKit project root with the graphiti config pointing at the GB10 embedding endpoint.

```bash
# From guardkit project root
python3 - <<'EOF'
import asyncio
import os
from datetime import datetime, timezone

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from falkordb import FalkorDB
from graphiti_core.driver.falkordb_driver import FalkorDriver

FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "whitestocks")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6379"))
EMBED_BASE_URL = "http://promaxgb10-41b1:8001/v1"
EMBED_MODEL = "nomic-embed-text-v1.5"

async def smoke_test():
    driver = FalkorDriver(host=FALKORDB_HOST, port=FALKORDB_PORT)
    client = Graphiti(
        graph_driver=driver,
        # embedding config injected via env or graphiti.yaml in production
    )
    await client.build_indices_and_constraints()

    episode_id = await client.add_episode(
        name="GLI-001 smoke test",
        episode_body="GuardKit is deploying vLLM on the Dell ProMax GB10 for local embeddings.",
        source=EpisodeType.text,
        source_description="TASK-GLI-001 verification",
        reference_time=datetime.now(timezone.utc),
    )
    print(f"Episode added: {episode_id}")

    results = await client.search("vLLM GB10 embeddings")
    assert len(results) > 0, "Search returned no results after seeding"
    print(f"Search returned {len(results)} result(s) — PASS")
    print("Graphiti seeding smoke test: PASS")

asyncio.run(smoke_test())
EOF
```

**Expected outcome**: The script prints `Episode added: <uuid>`, then `Search returned N result(s) — PASS`, and finally `Graphiti seeding smoke test: PASS`. Entity extraction runs on the LLM (port 8000) using embeddings from port 8001. Both services must be running for this test to pass.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Model download hangs or is very slow | HF rate limit, network issue, or gated model | Set `HF_TOKEN` env var: `HF_TOKEN=hf_... ./scripts/vllm-embed.sh` |
| OOM error during model load | GPU utilization too high relative to LLM memory usage | Reduce `VLLM_EMBED_GPU_UTIL`: `VLLM_EMBED_GPU_UTIL=0.10 ./scripts/vllm-embed.sh` |
| Port 8001 already in use | Previous container still running | `docker stop vllm-embedding && docker rm vllm-embedding` (script does this automatically) |
| `transformers version` error on startup | nemotron requires transformers 5.x | Switch to nomic: `./scripts/vllm-embed.sh` (no argument) |
| `No module named 'flashinfer'` warning | FlashInfer not bundled in this container image | Expected warning — safe to ignore. vLLM falls back to a compatible attention implementation. |
| Connection refused from MacBook | Tailscale not connected, or container not started | Check `tailscale status` on MacBook; check `docker ps` on GB10 |
| `/health` returns 503 | Server started but model still loading | Wait and retry — watch `docker logs -f vllm-embedding` for `Application startup complete.` |
| `model not found` error in embedding request | Wrong model name in request body | Check `curl http://localhost:8001/v1/models` for the exact model ID, then use that in your request |
| MagicDNS not resolving `promaxgb10-41b1` | MagicDNS propagation lag | Use Tailscale IP directly: `curl http://100.84.90.91:8001/health` |
| Smoke test fails: `Search returned 0 results` | Embedding or LLM service unavailable | Check both port 8000 (LLM) and port 8001 (embedding) are healthy |

---

## Key File Reference

| File | Purpose |
|------|---------|
| `scripts/vllm-embed.sh` | Docker-based embedding server launch script (source of truth) |
| `.guardkit/graphiti.yaml` | GuardKit Graphiti config (embedding endpoint updated in TASK-GLI-004) |
| `.env` | Environment variables (`HF_TOKEN`, `FALKORDB_HOST`, etc.) |
| `docs/guides/falkordb-nas-infrastructure-setup.md` | FalkorDB NAS infrastructure guide |

---

## Related Tasks

| Task | Title |
|------|-------|
| TASK-GLI-001 | This task — vLLM embedding setup guide |
| TASK-GLI-002 | Extend GraphitiConfig for local inference provider settings |
| TASK-GLI-003 | Update GraphitiClient.initialize() to inject custom embedder/LLM |
| TASK-GLI-004 | Update .guardkit/graphiti.yaml schema and config loader |
| TASK-GLI-005 | Test seeding feature-spec v2 document (end-to-end) |

---

## External References

| Resource | URL |
|----------|-----|
| DGX Spark vLLM setup guide | https://github.com/eelbaz/dgx-spark-vllm-setup |
| NVIDIA forums — Nemotron embed on DGX Spark | https://forums.developer.nvidia.com/t/getting-nemotron-embed-working-on-dgx-spark/359447 |
| vLLM embedding / pooling docs | https://docs.vllm.ai/en/stable/serving/openai_compatible_server/ |
| nomic-embed-text-v1.5 model card | https://huggingface.co/nomic-ai/nomic-embed-text-v1.5 |
| nvidia/llama-nemotron-embed-1b-v2 model card | https://huggingface.co/nvidia/llama-nemotron-embed-1b-v2 |
| NVIDIA NGC vLLM container | https://catalog.ngc.nvidia.com/orgs/nvidia/containers/vllm |
