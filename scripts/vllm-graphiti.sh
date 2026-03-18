#!/usr/bin/env bash
# vllm-graphiti.sh — Serve LLM for Graphiti knowledge graph on DGX Spark GB10
#
# Graphiti uses this LLM at ingestion time for entity extraction and fact
# deduplication. It sends structured JSON prompts using response_format=json_schema,
# which requires a model + vLLM backend that enforces schema compliance.
#
# Context requirement: Graphiti's system prompts use ~7800-8100 tokens of
# baseline overhead, so the model MUST have a context window > 10K tokens.
#
# Why Qwen2.5-14B, not Qwen3:
#   Qwen3 models have a thinking mode that generates thousands of <think> tokens
#   internally before producing output. Even with --reasoning-parser qwen3 stripping
#   them, the model still spends the time generating them — causing 900s+ timeouts
#   on Graphiti episodes. Qwen2.5 is a pure instruct model with no thinking mode.
#
# Why --structured-outputs-config.backend xgrammar:
#   Graphiti uses response_format={"type":"json_schema",...} — it relies on the
#   server to enforce the schema, not just prompt the model. xgrammar enforces
#   the JSON schema at the token level, guaranteeing valid output regardless of
#   model behaviour. This is the vLLM v0.13+ flag (the old --guided-decoding-backend
#   flag was removed in v0.12). Default "auto" also selects xgrammar, but
#   explicit is better for Graphiti's correctness requirements.
#
# Port allocation (DGX Spark GB10):
#   8000 — Graphiti LLM      (this script)
#   8001 — Embedding model   (vllm-embed.sh)          nomic-embed-text-v1.5
#   8002 — AutoBuild LLM     (vllm-serve.sh)           Qwen3-Coder-Next
#   8003 — Nemotron 3 Nano   (vllm-nemotron3-nano.sh)
#
# Usage:
#   ./scripts/vllm-graphiti.sh                      # Default: Qwen2.5-14B-Instruct FP8
#   ./scripts/vllm-graphiti.sh qwen2.5-32b          # Larger option (~34GB, higher quality)
#   ./scripts/vllm-graphiti.sh qwen3-30b            # Legacy: Qwen3 MoE (has thinking mode)
#   ./scripts/vllm-graphiti.sh custom org/model     # Any custom model
#
# Environment variables (override defaults):
#   VLLM_GRAPHITI_PORT=8000        Server port
#   VLLM_GRAPHITI_GPU_UTIL=0.15   GPU memory utilization (0.0-1.0)
#   VLLM_GRAPHITI_MAX_LEN=32768   Max context length
#   VLLM_IMAGE=nvcr.io/nvidia/vllm:26.01-py3  Docker image
#
# DGX Spark (GB10) notes:
#   - SM 12.1 (ARM64) — FP8 is the stable quantisation; NVFP4 has ARM64 bugs
#   - --structured-outputs-config.backend xgrammar: enforces json_schema at
#     token level (Graphiti requires this — pure prompt-based JSON is unreliable)
#     NOTE: vLLM v0.13+ only — replaces old --guided-decoding-backend flag
#   - --enable-prefix-caching: Graphiti's repeated system prompts benefit
#     enormously (TTFT ~28s → 2-3s with shared prefix cache)
#   - MoE models need VLLM_FLASHINFER_MOE_BACKEND=latency on SM 12.1
#   - See TASK-REV-DGX1 review report for full model selection rationale
#
# Memory budget (128GB unified):
#   qwen2.5-14b  ~17GB  | qwen2.5-32b  ~35GB  | qwen3-30b  ~33GB
#   + nomic-embed (port 8001) ~0.5GB
#   + Qwen3-Coder-Next (port 8002) ~32-45GB
#   Total with all ports (14b default): ~50-63GB — comfortable headroom

set -euo pipefail

# --- Configuration ---
PORT="${VLLM_GRAPHITI_PORT:-8000}"
GPU_UTIL="${VLLM_GRAPHITI_GPU_UTIL:-0.15}"
IMAGE="${VLLM_IMAGE:-nvcr.io/nvidia/vllm:26.01-py3}"
CONTAINER_NAME="vllm-graphiti"

# Extra environment variables for Docker (model-specific, populated by presets)
EXTRA_ENV=""

# --- Model selection ---
MODEL_PRESET="${1:-qwen2.5-14b}"

case "$MODEL_PRESET" in
  qwen2.5-14b|default|"")
    MODEL="neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic"
    GPU_UTIL="${VLLM_GRAPHITI_GPU_UTIL:-0.15}"
    MAX_LEN="${VLLM_GRAPHITI_MAX_LEN:-32768}"
    # Dense model — no MoE backend needed
    # xgrammar enforces json_schema at token level (required for Graphiti)
    EXTRA_ARGS="--kv-cache-dtype fp8 \
      --enable-prefix-caching \
      --structured-outputs-config.backend xgrammar"
    echo "═══ Qwen2.5-14B-Instruct FP8 (~16GB, 128K ctx) ═══"
    echo "    Graphiti entity extraction & fact deduplication"
    echo "    No thinking mode | xgrammar enforces json_schema"
    ;;
  qwen2.5-32b)
    MODEL="neuralmagic/Qwen2.5-32B-Instruct-FP8-dynamic"
    GPU_UTIL="${VLLM_GRAPHITI_GPU_UTIL:-0.30}"
    MAX_LEN="${VLLM_GRAPHITI_MAX_LEN:-32768}"
    EXTRA_ARGS="--kv-cache-dtype fp8 \
      --enable-prefix-caching \
      --structured-outputs-config.backend xgrammar"
    echo "═══ Qwen2.5-32B-Instruct FP8 (~34GB, 128K ctx) ═══"
    echo "    Higher quality extraction — use if 14B misses entities"
    echo "    No thinking mode | xgrammar enforces json_schema"
    ;;
  qwen3-30b)
    MODEL="Qwen/Qwen3-30B-A3B-FP8"
    GPU_UTIL="${VLLM_GRAPHITI_GPU_UTIL:-0.30}"
    MAX_LEN="${VLLM_GRAPHITI_MAX_LEN:-32768}"
    # MoE model — latency backend required for SM 12.1 (GB10), ~60% speedup
    EXTRA_ENV="-e VLLM_FLASHINFER_MOE_BACKEND=latency"
    # WARNING: Qwen3 has thinking mode — generates thousands of <think> tokens
    # internally before each response, causing slow/timeout episodes in Graphiti.
    # Use qwen2.5-14b instead. This preset kept for testing/comparison only.
    EXTRA_ARGS="--trust-remote-code --tensor-parallel-size 1 --kv-cache-dtype fp8 \
      --enable-prefix-caching --reasoning-parser qwen3 \
      --structured-outputs-config.backend xgrammar"
    echo "═══ Qwen3-30B-A3B FP8 (3.3B active, ~32.5GB, 32K ctx) ═══"
    echo "    WARNING: thinking mode causes slow Graphiti episodes"
    echo "    Prefer qwen2.5-14b for Graphiti workloads"
    ;;
  custom)
    MODEL="${2:?Usage: $0 custom org/model-name}"
    GPU_UTIL="${VLLM_GRAPHITI_GPU_UTIL:-0.15}"
    MAX_LEN="${VLLM_GRAPHITI_MAX_LEN:-32768}"
    EXTRA_ARGS="--structured-outputs-config.backend xgrammar"
    echo "═══ Custom model: $MODEL ═══"
    ;;
  *)
    echo "Unknown preset: $MODEL_PRESET"
    echo ""
    echo "Available presets:"
    echo ""
    echo "  Recommended (no thinking mode, xgrammar json_schema enforcement):"
    echo "    qwen2.5-14b   Qwen2.5-14B-Instruct FP8 (default, ~16GB, 128K ctx)"
    echo "    qwen2.5-32b   Qwen2.5-32B-Instruct FP8 (~34GB, higher quality)"
    echo ""
    echo "  Legacy (Qwen3 — has thinking mode, may cause slow episodes):"
    echo "    qwen3-30b     Qwen3-30B-A3B FP8 (~33GB, 32K ctx)"
    echo ""
    echo "  Other:"
    echo "    custom   Any model: $0 custom org/model-name"
    echo ""
    echo "  NOTE: All presets use --structured-outputs-config.backend xgrammar"
    echo "        to enforce Graphiti's json_schema response format."
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
echo "Waiting for model to load (~1-2 min for 16GB FP8)..."
echo "  Logs:   docker logs -f $CONTAINER_NAME"
echo "  Health: curl http://localhost:${PORT}/health"
echo "  Models: curl http://localhost:${PORT}/v1/models"
echo ""
echo "Graphiti will use this automatically (port 8000 matches graphiti.yaml)."
echo ""
echo "To also start other services:"
echo "  VLLM_PORT=8001 ./scripts/vllm-embed.sh"
echo "  VLLM_PORT=8002 ./scripts/vllm-serve.sh"
