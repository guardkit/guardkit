#!/usr/bin/env bash
# vllm-agentic-factory.sh — Serve LLM for agentic-dataset-factory on DGX Spark GB10
#
# Serves a model with tool-calling support for the Player-Coach adversarial
# cooperation pipeline. The Player agent needs tool-calling (rag_retrieval,
# write_output) while the Coach only needs text generation.
#
# Key difference from vllm-graphiti.sh:
#   - Adds --enable-auto-tool-choice --tool-call-parser hermes
#   - Uses port 8002 (AutoBuild LLM slot)
#   - Higher GPU util (dedicated to generation, not shared with Graphiti)
#
# Usage:
#   ./scripts/vllm-agentic-factory.sh                      # Default: Qwen2.5-14B
#   ./scripts/vllm-agentic-factory.sh qwen2.5-32b          # Larger, higher quality
#   ./scripts/vllm-agentic-factory.sh nano-30b              # Nemotron 3 Nano 30B-A3B
#   ./scripts/vllm-agentic-factory.sh custom org/model      # Any custom model
#
# Environment variables:
#   VLLM_FACTORY_PORT=8002         Server port
#   VLLM_FACTORY_GPU_UTIL=0.35     GPU memory utilization (0.0-1.0)
#   VLLM_FACTORY_MAX_LEN=16384    Max context length
#   VLLM_IMAGE=nvcr.io/nvidia/vllm:26.01-py3  Docker image
#
# Port allocation (DGX Spark GB10):
#   8000 — Graphiti LLM      (vllm-graphiti.sh)       Qwen2.5-14B
#   8001 — Embedding model   (vllm-embed.sh)          nomic-embed-text-v1.5
#   8002 — Dataset Factory   (this script)
#   8003 — Nemotron 3 Nano   (vllm-nemotron3-nano.sh)
#
# Memory budget (128GB unified, with Graphiti on 8000 @ 0.40):
#   qwen2.5-14b  weights ~16GB, vLLM alloc ~45GB (@0.35)  Total with Graphiti: ~112GB
#   qwen2.5-32b  weights ~34GB, vLLM alloc ~38GB (@0.30)  Total with Graphiti: ~123GB
#   nano-30b     weights ~15GB, vLLM alloc ~38GB (@0.30)  Total with Graphiti: ~104GB

set -euo pipefail

# --- Configuration ---
PORT="${VLLM_FACTORY_PORT:-8002}"
GPU_UTIL="${VLLM_FACTORY_GPU_UTIL:-0.35}"
IMAGE="${VLLM_IMAGE:-nvcr.io/nvidia/vllm:26.01-py3}"
CONTAINER_NAME="vllm-agentic-factory"

# Extra environment variables for Docker (model-specific)
EXTRA_ENV=""

# --- Model selection ---
MODEL_PRESET="${1:-qwen2.5-14b}"

case "$MODEL_PRESET" in
  qwen2.5-14b|default|"")
    MODEL="neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic"
    GPU_UTIL="${VLLM_FACTORY_GPU_UTIL:-0.35}"
    MAX_LEN="${VLLM_FACTORY_MAX_LEN:-16384}"
    EXTRA_ARGS="--kv-cache-dtype fp8 \
      --enable-prefix-caching \
      --enable-auto-tool-choice \
      --tool-call-parser hermes"
    echo "═══ Qwen2.5-14B-Instruct FP8 (~16GB) — Tool-calling enabled ═══"
    echo "    Dataset factory Player + Coach inference"
    echo "    Tool parser: hermes | Context: ${MAX_LEN}"
    ;;
  qwen2.5-32b)
    MODEL="neuralmagic/Qwen2.5-32B-Instruct-FP8-dynamic"
    GPU_UTIL="${VLLM_FACTORY_GPU_UTIL:-0.30}"
    MAX_LEN="${VLLM_FACTORY_MAX_LEN:-16384}"
    EXTRA_ARGS="--kv-cache-dtype fp8 \
      --enable-prefix-caching \
      --enable-auto-tool-choice \
      --tool-call-parser hermes"
    echo "═══ Qwen2.5-32B-Instruct FP8 (~34GB) — Tool-calling enabled ═══"
    echo "    Higher quality generation"
    echo "    Tool parser: hermes | Context: ${MAX_LEN}"
    ;;
  nano-30b)
    MODEL="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8"
    GPU_UTIL="${VLLM_FACTORY_GPU_UTIL:-0.30}"
    MAX_LEN="${VLLM_FACTORY_MAX_LEN:-16384}"
    EXTRA_ENV="-e VLLM_FLASHINFER_MOE_BACKEND=latency"
    EXTRA_ARGS="--trust-remote-code --tensor-parallel-size 1 --kv-cache-dtype fp8 \
      --enable-auto-tool-choice \
      --tool-call-parser hermes"
    echo "═══ Nemotron 3 Nano 30B-A3B FP8 (3.2B active, ~15GB) — Tool-calling enabled ═══"
    echo "    MoE with FlashInfer latency backend"
    echo "    Tool parser: hermes | Context: ${MAX_LEN}"
    ;;
  custom)
    MODEL="${2:?Usage: $0 custom org/model-name}"
    GPU_UTIL="${VLLM_FACTORY_GPU_UTIL:-0.35}"
    MAX_LEN="${VLLM_FACTORY_MAX_LEN:-16384}"
    EXTRA_ARGS="--enable-auto-tool-choice \
      --tool-call-parser hermes"
    echo "═══ Custom model: $MODEL — Tool-calling enabled ═══"
    ;;
  *)
    echo "Unknown preset: $MODEL_PRESET"
    echo ""
    echo "Available presets:"
    echo ""
    echo "  Recommended:"
    echo "    qwen2.5-14b   Qwen2.5-14B-Instruct FP8 (default, ~16GB)"
    echo "    qwen2.5-32b   Qwen2.5-32B-Instruct FP8 (~34GB, higher quality)"
    echo "    nano-30b      Nemotron 3 Nano 30B-A3B FP8 (3.2B active, ~15GB)"
    echo ""
    echo "  Other:"
    echo "    custom        Any model: $0 custom org/model-name"
    echo ""
    echo "All presets include --enable-auto-tool-choice --tool-call-parser hermes"
    echo ""
    echo "Default port: $PORT  (override: VLLM_FACTORY_PORT=XXXX)"
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
echo "  Agentic Dataset Factory — DGX Spark GB10"
echo "========================================"
echo "  Model:    $MODEL"
echo "  Port:     $PORT"
echo "  GPU util: $GPU_UTIL"
echo "  Max len:  $MAX_LEN"
echo "  Tools:    hermes parser (auto tool choice)"
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
echo "Update agent-config.yaml endpoint to:"
echo "  endpoint: http://promaxgb10-41b1:${PORT}/v1"
echo ""
