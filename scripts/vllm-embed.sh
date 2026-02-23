#!/usr/bin/env bash
# vllm-embed.sh — Start VLLM embedding server on Dell Pro Max GB10 / DGX Spark
#
# Serves an embedding model on port 8001 alongside the LLM on port 8000.
# Designed for Graphiti seeding workloads (~215 embedding calls per add_episode).
#
# Usage:
#   ./scripts/vllm-embed.sh                      # Default: nomic-embed-text-v1.5
#   ./scripts/vllm-embed.sh nemotron              # nvidia/llama-nemotron-embed-1b-v2
#   ./scripts/vllm-embed.sh custom org/model      # Any custom embedding model
#
# NOTE: nemotron uses a custom bidirectional encoder architecture that falls back to
# the Transformers backend in vLLM. The 26.01 container ships transformers==4.57.1,
# but encoder model support requires transformers>=5.0.0.dev0. Use nomic until a
# newer container with transformers 5.x is released.
#
# Environment variables (override defaults):
#   VLLM_EMBED_PORT=8001        Server port
#   VLLM_EMBED_GPU_UTIL=0.15    GPU memory utilization (0.0-1.0)
#   VLLM_IMAGE=nvcr.io/nvidia/vllm:26.01-py3  Docker image
#   HF_TOKEN=...                Hugging Face token (for gated models)

set -euo pipefail

# --- Configuration ---
PORT="${VLLM_EMBED_PORT:-8001}"
GPU_UTIL="${VLLM_EMBED_GPU_UTIL:-0.15}"
IMAGE="${VLLM_IMAGE:-nvcr.io/nvidia/vllm:26.01-py3}"
CONTAINER_NAME="vllm-embedding"

# --- Model selection ---
MODEL_PRESET="${1:-nomic}"

case "$MODEL_PRESET" in
  nomic|default|"")
    MODEL="nomic-ai/nomic-embed-text-v1.5"
    EXTRA_ARGS="--runner pooling --trust-remote-code"
    echo "Model: nomic-embed-text-v1.5 (137M, ~274MB, 8192 context)"
    ;;
  nemotron)
    MODEL="nvidia/llama-nemotron-embed-1b-v2"
    EXTRA_ARGS="--runner pooling --pooler-config {\"pooling_type\":\"MEAN\"} --trust-remote-code"
    echo "Model: nvidia/llama-nemotron-embed-1b-v2 (1B, ~2GB, Matryoshka embeddings)"
    echo "WARNING: Requires transformers>=5.0.0.dev0; container 26.01 has 4.57.1 — likely to fail."
    ;;
  custom)
    MODEL="${2:?Usage: $0 custom org/model-name}"
    EXTRA_ARGS="${VLLM_EMBED_EXTRA_ARGS:---task embed}"
    echo "Model: $MODEL (custom)"
    ;;
  *)
    echo "Unknown preset: $MODEL_PRESET"
    echo ""
    echo "Available presets:"
    echo "  nomic     nomic-ai/nomic-embed-text-v1.5 (default, 137M, works with 26.01)"
    echo "  nemotron  nvidia/llama-nemotron-embed-1b-v2 (1B, requires transformers 5.x)"
    echo "  custom    Any model: $0 custom org/model-name"
    exit 1
    ;;
esac

# --- Stop existing container if running ---
if docker ps -q --filter "name=$CONTAINER_NAME" | grep -q .; then
  echo "Stopping existing container: $CONTAINER_NAME"
  docker stop "$CONTAINER_NAME" && docker rm "$CONTAINER_NAME"
fi

# --- Start VLLM embedding server ---
echo ""
echo "========================================"
echo "  VLLM Embedding Server — GB10"
echo "========================================"
echo "  Model:    $MODEL"
echo "  Port:     $PORT"
echo "  GPU util: $GPU_UTIL"
echo "========================================"
echo ""

docker run -d \
  --name "$CONTAINER_NAME" \
  --gpus all \
  -p "${PORT}:8001" \
  --ipc=host \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  ${HF_TOKEN:+-e "HF_TOKEN=$HF_TOKEN"} \
  -e "PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True" \
  "$IMAGE" \
  vllm serve "$MODEL" \
    --host 0.0.0.0 \
    --port 8001 \
    --dtype auto \
    --gpu-memory-utilization "$GPU_UTIL" \
    $EXTRA_ARGS

echo "Container started: $CONTAINER_NAME"
echo ""
echo "Waiting for model to load..."
echo "  Logs:   docker logs -f $CONTAINER_NAME"
echo "  Health: curl http://localhost:${PORT}/health"
echo "  Models: curl http://localhost:${PORT}/v1/models"
echo ""
echo "Test embeddings:"
echo "  curl http://localhost:${PORT}/v1/embeddings \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"model\": \"$(basename "$MODEL")\", \"input\": \"Hello world\"}'"
