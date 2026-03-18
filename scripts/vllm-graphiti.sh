#!/usr/bin/env bash
# vllm-graphiti.sh — Serve LLM for Graphiti knowledge graph on DGX Spark GB10
#
# Graphiti uses this LLM at ingestion time for entity extraction and fact
# deduplication. It sends structured JSON prompts that require a general-purpose
# instruction-following model — NOT a coding model.
#
# Context requirement: Graphiti's system prompts use ~7800-8100 tokens of
# baseline overhead, so the model MUST have a context window > 10K tokens.
# The default preset (qwen3-30b) provides 32K native context.
#
# Port allocation (DGX Spark GB10):
#   8000 — Graphiti LLM      (this script)
#   8001 — Embedding model   (vllm-embed.sh)       nomic-embed-text-v1.5
#   8002 — AutoBuild LLM     (vllm-serve.sh)        Qwen3-Coder-Next
#   8003 — Nemotron 3 Nano   (vllm-nemotron3-nano.sh)
#
# Usage:
#   ./scripts/vllm-graphiti.sh                   # Default: Qwen3-30B-A3B FP8
#   ./scripts/vllm-graphiti.sh qwen3-14b         # Smaller fallback (~16GB)
#   ./scripts/vllm-graphiti.sh qwen3-8b          # Lightest option (~9GB)
#   ./scripts/vllm-graphiti.sh custom org/model  # Any custom model
#
# Environment variables (override defaults):
#   VLLM_GRAPHITI_PORT=8000        Server port
#   VLLM_GRAPHITI_GPU_UTIL=0.30   GPU memory utilization (0.0-1.0)
#   VLLM_GRAPHITI_MAX_LEN=32768   Max context length
#   VLLM_IMAGE=nvcr.io/nvidia/vllm:26.01-py3  Docker image
#
# DGX Spark (GB10) notes:
#   - SM 12.1 (ARM64) — FP8 is the stable quantisation; NVFP4 has ARM64 bugs
#   - MoE models need VLLM_FLASHINFER_MOE_BACKEND=latency on SM 12.1
#   - --enable-prefix-caching is essential: Graphiti's repeated system prompts
#     benefit enormously (TTFT 28s → 2-3s with shared prefix cache)
#   - --reasoning-parser qwen3 strips <think>...</think> blocks from Qwen3
#     responses so Graphiti receives clean JSON output
#   - See TASK-REV-DGX1 and forum: https://forums.developer.nvidia.com/t/362200
#
# Memory budget (128GB unified):
#   qwen3-30b  ~33GB  | qwen3-14b  ~17GB  | qwen3-8b  ~10GB
#   + nomic-embed (port 8001) ~0.5GB
#   + Qwen3-Coder-Next (port 8002) ~32-45GB
#   Total with all ports: ~66-79GB — comfortable headroom

set -euo pipefail

# --- Configuration ---
PORT="${VLLM_GRAPHITI_PORT:-8000}"
GPU_UTIL="${VLLM_GRAPHITI_GPU_UTIL:-0.30}"
IMAGE="${VLLM_IMAGE:-nvcr.io/nvidia/vllm:26.01-py3}"
CONTAINER_NAME="vllm-graphiti"

# Extra environment variables for Docker (model-specific, populated by presets)
EXTRA_ENV=""

# --- Model selection ---
MODEL_PRESET="${1:-qwen3-30b}"

case "$MODEL_PRESET" in
  qwen3-30b|default|"")
    MODEL="Qwen/Qwen3-30B-A3B-FP8"
    GPU_UTIL="${VLLM_GRAPHITI_GPU_UTIL:-0.30}"
    MAX_LEN="${VLLM_GRAPHITI_MAX_LEN:-32768}"
    # MoE model — latency backend required for SM 12.1 (GB10), ~60% speedup
    EXTRA_ENV="-e VLLM_FLASHINFER_MOE_BACKEND=latency"
    # --reasoning-parser qwen3: strips <think>...</think> blocks server-side
    # Graphiti needs clean JSON — do not remove this flag
    EXTRA_ARGS="--trust-remote-code --tensor-parallel-size 1 --kv-cache-dtype fp8 \
      --enable-prefix-caching --reasoning-parser qwen3 --load-format fastsafetensors"
    echo "═══ Qwen3-30B-A3B FP8 (3.3B active, ~32.5GB, 32K ctx) ═══"
    echo "    Graphiti entity extraction & fact deduplication"
    echo "    ~52-66 tok/s on GB10 | reasoning-parser strips <think> blocks"
    ;;
  qwen3-14b)
    MODEL="Qwen/Qwen3-14B-FP8"
    GPU_UTIL="${VLLM_GRAPHITI_GPU_UTIL:-0.15}"
    MAX_LEN="${VLLM_GRAPHITI_MAX_LEN:-32768}"
    # Dense model — no MoE backend needed
    EXTRA_ARGS="--trust-remote-code --kv-cache-dtype fp8 \
      --enable-prefix-caching --reasoning-parser qwen3 --load-format fastsafetensors"
    echo "═══ Qwen3-14B FP8 (~16.3GB, 32K ctx) ═══"
    echo "    Fallback: lower memory, slightly less entity extraction quality"
    echo "    ~80-120 tok/s on GB10 | reasoning-parser strips <think> blocks"
    ;;
  qwen3-8b)
    MODEL="Qwen/Qwen3-8B-FP8"
    GPU_UTIL="${VLLM_GRAPHITI_GPU_UTIL:-0.10}"
    MAX_LEN="${VLLM_GRAPHITI_MAX_LEN:-32768}"
    # Dense model — no MoE backend needed
    EXTRA_ARGS="--trust-remote-code --kv-cache-dtype fp8 \
      --enable-prefix-caching --reasoning-parser qwen3 --load-format fastsafetensors"
    echo "═══ Qwen3-8B FP8 (~9.4GB, 32K ctx) ═══"
    echo "    Lightest option — adequate JSON quality, highest throughput"
    echo "    ~120-180 tok/s on GB10 | reasoning-parser strips <think> blocks"
    ;;
  custom)
    MODEL="${2:?Usage: $0 custom org/model-name}"
    GPU_UTIL="${VLLM_GRAPHITI_GPU_UTIL:-0.30}"
    MAX_LEN="${VLLM_GRAPHITI_MAX_LEN:-32768}"
    EXTRA_ARGS="--trust-remote-code"
    echo "═══ Custom model: $MODEL ═══"
    ;;
  *)
    echo "Unknown preset: $MODEL_PRESET"
    echo ""
    echo "Available presets:"
    echo ""
    echo "  FP8 (standard NGC image, recommended for GB10 ARM64):"
    echo "    qwen3-30b   Qwen3-30B-A3B FP8 (default, 3.3B active, ~33GB, 32K ctx)"
    echo "    qwen3-14b   Qwen3-14B FP8 (~17GB, 32K ctx, lower memory fallback)"
    echo "    qwen3-8b    Qwen3-8B FP8 (~10GB, 32K ctx, highest throughput)"
    echo ""
    echo "  Other:"
    echo "    custom   Any model: $0 custom org/model-name"
    echo ""
    echo "  NOTE: All Qwen3 presets use --reasoning-parser qwen3 to strip"
    echo "        <think> blocks. Graphiti requires clean JSON output."
    echo ""
    echo "Port allocation:"
    echo "  8000 — Graphiti LLM (this script)"
    echo "  8001 — Embeddings (vllm-embed.sh)"
    echo "  8002 — AutoBuild LLM (vllm-serve.sh)"
    echo "  8003 — Nemotron 3 Nano (vllm-nemotron3-nano.sh)"
    echo ""
    echo "Default port: $PORT  (override: VLLM_GRAPHITI_PORT=XXXX)"
    exit 1
    ;;
esac

# --- Stop existing container if running ---
if docker ps -q --filter "name=$CONTAINER_NAME" | grep -q .; then
  echo "Stopping existing container: $CONTAINER_NAME"
  docker stop "$CONTAINER_NAME" && docker rm "$CONTAINER_NAME"
fi

# Also clean up stopped containers with same name
if docker ps -aq --filter "name=$CONTAINER_NAME" | grep -q .; then
  docker rm "$CONTAINER_NAME" 2>/dev/null || true
fi

# --- Start server ---
echo ""
echo "========================================"
echo "  VLLM Graphiti LLM — DGX Spark GB10"
echo "========================================"
echo "  Model:    $MODEL"
echo "  Port:     $PORT"
echo "  GPU util: $GPU_UTIL"
echo "  Max len:  $MAX_LEN"
echo "  Purpose:  Graphiti entity extraction"
echo "========================================"
echo ""

# Note: EXTRA_ENV and EXTRA_ARGS are intentionally unquoted to allow
# word splitting — they contain multiple flags that must be separate args.
# shellcheck disable=SC2086
docker run -d \
  --name "$CONTAINER_NAME" \
  --gpus all \
  -p "${PORT}:8000" \
  --ipc=host \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  -v "$HOME/.cache/vllm:/root/.cache/vllm" \
  ${HF_TOKEN:+-e "HF_TOKEN=$HF_TOKEN"} \
  -e "PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True" \
  ${EXTRA_ENV} \
  "$IMAGE" \
  vllm serve "$MODEL" \
    --host 0.0.0.0 \
    --port 8000 \
    --gpu-memory-utilization "$GPU_UTIL" \
    --max-model-len "$MAX_LEN" \
    --dtype auto \
    $EXTRA_ARGS

echo "Container started: $CONTAINER_NAME"
echo ""
echo "Waiting for model to load (~2-5 min for 32.5GB FP8)..."
echo "  Logs:   docker logs -f $CONTAINER_NAME"
echo "  Health: curl http://localhost:${PORT}/health"
echo "  Models: curl http://localhost:${PORT}/v1/models"
echo ""
echo "Graphiti will use this automatically (port 8000 matches graphiti.yaml)."
echo ""
echo "To also start other services:"
echo "  VLLM_PORT=8001 ./scripts/vllm-embed.sh"
echo "  VLLM_PORT=8002 ./scripts/vllm-serve.sh"
