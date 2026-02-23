#!/usr/bin/env bash
# vllm-serve.sh — Start VLLM server on Dell Pro Max GB10 / DGX Spark
#
# Usage:
#   ./scripts/vllm-serve.sh                    # Default: Qwen3-Coder-Next FP8
#   ./scripts/vllm-serve.sh 30b                # Qwen3-Coder-30B (faster, smaller)
#   ./scripts/vllm-serve.sh custom org/model   # Any custom model
#
# Environment variables (override defaults):
#   VLLM_PORT=8000          Server port
#   VLLM_GPU_UTIL=0.8       GPU memory utilization (0.0-1.0)
#   VLLM_MAX_LEN=65536      Max context length
#   VLLM_IMAGE=nvcr.io/nvidia/vllm:26.01-py3  Docker image
#   HF_TOKEN=...            Hugging Face token (for gated models)

set -euo pipefail

# --- Configuration ---
PORT="${VLLM_PORT:-8000}"
GPU_UTIL="${VLLM_GPU_UTIL:-0.8}"
MAX_LEN="${VLLM_MAX_LEN:-65536}"
IMAGE="${VLLM_IMAGE:-nvcr.io/nvidia/vllm:26.01-py3}"
CONTAINER_NAME="vllm-qwen3-coder"
SERVED_MODEL_NAME="claude-sonnet-4-5-20250929"

# --- Model selection ---
MODEL_PRESET="${1:-next}"

case "$MODEL_PRESET" in
  next|default|"")
    MODEL="Qwen/Qwen3-Coder-Next-FP8"
    TOOL_PARSER="qwen3_coder"
    GPU_UTIL="${VLLM_GPU_UTIL:-0.8}"
    MAX_LEN="${VLLM_MAX_LEN:-65536}"
    echo "Model: Qwen3-Coder-Next FP8 (80B MoE, ~92GB, ~43 tok/s)"
    ;;
  30b)
    MODEL="Qwen/Qwen3-Coder-30B-A3B-Instruct"
    TOOL_PARSER="qwen3_coder"
    GPU_UTIL="${VLLM_GPU_UTIL:-0.5}"
    MAX_LEN="${VLLM_MAX_LEN:-32768}"
    echo "Model: Qwen3-Coder-30B-A3B (30B MoE, ~30GB FP8, fast)"
    ;;
  next-nvfp4)
    MODEL="Qwen/Qwen3-Coder-Next-NVFP4"
    TOOL_PARSER="qwen3_coder"
    GPU_UTIL="${VLLM_GPU_UTIL:-0.5}"
    MAX_LEN="${VLLM_MAX_LEN:-65536}"
    echo "Model: Qwen3-Coder-Next NVFP4 (80B MoE, ~50GB, ~35 tok/s)"
    ;;
  custom)
    MODEL="${2:?Usage: $0 custom org/model-name}"
    TOOL_PARSER="${VLLM_TOOL_PARSER:-qwen3_coder}"
    echo "Model: $MODEL (custom)"
    ;;
  *)
    echo "Unknown preset: $MODEL_PRESET"
    echo ""
    echo "Available presets:"
    echo "  next       Qwen3-Coder-Next FP8 (default, best quality)"
    echo "  30b        Qwen3-Coder-30B-A3B (faster, smaller)"
    echo "  next-nvfp4 Qwen3-Coder-Next NVFP4 (smaller memory footprint)"
    echo "  custom     Any model: $0 custom org/model-name"
    exit 1
    ;;
esac

# --- Stop existing container if running ---
if docker ps -q --filter "name=$CONTAINER_NAME" | grep -q .; then
  echo "Stopping existing container: $CONTAINER_NAME"
  docker stop "$CONTAINER_NAME" && docker rm "$CONTAINER_NAME"
fi

# --- Start VLLM server ---
echo ""
echo "========================================"
echo "  VLLM Server — Dell Pro Max GB10"
echo "========================================"
echo "  Model:    $MODEL"
echo "  Port:     $PORT"
echo "  GPU util: $GPU_UTIL"
echo "  Max len:  $MAX_LEN"
echo "  Alias:    $SERVED_MODEL_NAME"
echo "========================================"
echo ""

docker run -d \
  --name "$CONTAINER_NAME" \
  --gpus all \
  -p "${PORT}:8000" \
  --ipc=host \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  ${HF_TOKEN:+-e "HF_TOKEN=$HF_TOKEN"} \
  -e "PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True" \
  "$IMAGE" \
  vllm serve "$MODEL" \
    --host 0.0.0.0 \
    --port 8000 \
    --served-model-name "$SERVED_MODEL_NAME" \
    --enable-auto-tool-choice \
    --tool-call-parser "$TOOL_PARSER" \
    --gpu-memory-utilization "$GPU_UTIL" \
    --max-model-len "$MAX_LEN" \
    --attention-backend flashinfer \
    --enable-prefix-caching \
    --load-format fastsafetensors

echo "Container started: $CONTAINER_NAME"
echo ""
echo "Waiting for model to load (3-5 min for 80B)..."
echo "  Logs:   docker logs -f $CONTAINER_NAME"
echo "  Health: curl http://localhost:${PORT}/health"
echo "  Models: curl http://localhost:${PORT}/v1/models"
echo ""
echo "Once ready, use AutoBuild with:"
echo "  ANTHROPIC_BASE_URL=http://localhost:${PORT} ANTHROPIC_API_KEY=vllm-local guardkit autobuild task TASK-XXX"
