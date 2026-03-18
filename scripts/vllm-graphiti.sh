#!/usr/bin/env bash
# vllm-graphiti.sh — Start lightweight LLM for Graphiti knowledge graph operations
#
# Serves a small, general-purpose model on port 8000 for Graphiti's entity
# extraction, relationship resolution, and fact deduplication. This replaces
# the coding-optimised Qwen3-Coder for Graphiti workloads, which caused
# extreme processing times (>600s per episode) due to poor structured JSON
# performance and graph density issues.
#
# Port allocation:
#   8000 — Graphiti LLM (this script)  — Nemotron 3 Nano 4B
#   8001 — Embedding model             — nomic-embed-text-v1.5 (vllm-embed.sh)
#   8002 — AutoBuild LLM              — Qwen3-Coder-Next (vllm-serve.sh)
#
# Usage:
#   ./scripts/vllm-graphiti.sh                  # Default: Nemotron 3 Nano 4B FP8
#   ./scripts/vllm-graphiti.sh nano-4b-nvfp4    # Nano 4B NVFP4 (smaller, needs Avarok image)
#   ./scripts/vllm-graphiti.sh nano-30b         # Nano 30B-A3B FP8 (better quality, more memory)
#   ./scripts/vllm-graphiti.sh nano-30b-nvfp4   # Nano 30B-A3B NVFP4 (65+ tok/s, Avarok image)
#   ./scripts/vllm-graphiti.sh custom org/model # Any custom model
#
# Environment variables (override defaults):
#   VLLM_GRAPHITI_PORT=8000         Server port
#   VLLM_GRAPHITI_GPU_UTIL=0.05    GPU memory utilization (0.0-1.0)
#   VLLM_IMAGE=nvcr.io/nvidia/vllm:26.01-py3  Docker image (overridden by NVFP4 presets)
#
# DGX Spark (GB10) performance notes:
#   - FP8 models work with standard NGC image
#   - NVFP4 models need Avarok image (avarok/dgx-vllm-nvfp4-kernel:v22)
#     for SM 12.1 software E2M1 workaround (32x speedup)
#   - MoE models (30B-A3B) need VLLM_FLASHINFER_MOE_BACKEND=latency
#     to avoid CUTLASS kernel issues on SM 12.1 (60% speedup)
#   - See: https://blog.avarok.net/dgx-spark-nemotron3-and-nvfp4-getting-to-65-tps-8c5569025eb6
#
# Background:
#   Graphiti uses the LLM only at ingestion time for entity extraction and
#   fact deduplication. It sends structured JSON prompts that require a
#   general-purpose instruction-following model, NOT a coding model.
#   The 4B Nano model handles these tasks in 10-30s vs 120-600s+ with
#   the 80B Qwen3-Coder. The embedding model (port 8001) is unchanged —
#   existing graph data remains valid when switching LLMs.
#
# See: TASK-REV-5B3A for the analysis that motivated this change.

set -euo pipefail

# --- Configuration ---
PORT="${VLLM_GRAPHITI_PORT:-8000}"
GPU_UTIL="${VLLM_GRAPHITI_GPU_UTIL:-0.05}"
# Default to standard NGC image; Avarok image recommended for NVFP4 models
# (has SM 12.1 software E2M1 workaround for 32x speedup on GB10)
IMAGE="${VLLM_IMAGE:-nvcr.io/nvidia/vllm:26.01-py3}"
CONTAINER_NAME="vllm-graphiti"

# Extra environment variables for Docker (model-specific, populated by presets)
EXTRA_ENV=""

# --- Model selection ---
MODEL_PRESET="${1:-nano-4b}"

case "$MODEL_PRESET" in
  nano-4b|default|"")
    MODEL="nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8"
    GPU_UTIL="${VLLM_GRAPHITI_GPU_UTIL:-0.05}"
    MAX_LEN="${VLLM_GRAPHITI_MAX_LEN:-8192}"
    # Nano 4B is hybrid Mamba-2 (not MoE), so MoE-specific env vars not needed
    EXTRA_ARGS="--trust-remote-code --kv-cache-dtype fp8"
    echo "═══ Nemotron 3 Nano 4B FP8 (~4GB, edge-optimised) ═══"
    echo "    Graphiti entity extraction & fact deduplication"
    echo "    Fine-tuning base for GCSE tutor SLM"
    ;;
  nano-4b-nvfp4)
    MODEL="nvidia/NVIDIA-Nemotron-3-Nano-4B-NVFP4"
    GPU_UTIL="${VLLM_GRAPHITI_GPU_UTIL:-0.05}"
    MAX_LEN="${VLLM_GRAPHITI_MAX_LEN:-8192}"
    IMAGE="${VLLM_IMAGE:-avarok/dgx-vllm-nvfp4-kernel:v22}"
    EXTRA_ARGS="--trust-remote-code --kv-cache-dtype fp8 --quantization modelopt_fp4"
    echo "═══ Nemotron 3 Nano 4B NVFP4 (~2GB, Avarok kernel) ═══"
    echo "    Smallest memory footprint, requires Avarok image"
    echo "    TIP: Falls back to NGC image if Avarok unavailable"
    ;;
  nano-30b)
    MODEL="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8"
    GPU_UTIL="${VLLM_GRAPHITI_GPU_UTIL:-0.15}"
    MAX_LEN="${VLLM_GRAPHITI_MAX_LEN:-8192}"
    # 30B-A3B is MoE — needs FlashInfer latency backend for SM 12.1 (GB10)
    # See: https://blog.avarok.net/dgx-spark-nemotron3-and-nvfp4-getting-to-65-tps-8c5569025eb6
    EXTRA_ENV="-e VLLM_FLASHINFER_MOE_BACKEND=latency"
    EXTRA_ARGS="--trust-remote-code --tensor-parallel-size 1 --kv-cache-dtype fp8"
    echo "═══ Nemotron 3 Nano 30B-A3B FP8 (3.2B active, ~15GB) ═══"
    echo "    Higher quality entity extraction, more memory"
    ;;
  nano-30b-nvfp4)
    MODEL="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4"
    GPU_UTIL="${VLLM_GRAPHITI_GPU_UTIL:-0.10}"
    MAX_LEN="${VLLM_GRAPHITI_MAX_LEN:-8192}"
    IMAGE="${VLLM_IMAGE:-avarok/dgx-vllm-nvfp4-kernel:v22}"
    # MoE + NVFP4: use Avarok image + Marlin backend for SM 12.1
    EXTRA_ENV="-e VLLM_FLASHINFER_MOE_BACKEND=latency \
      -e VLLM_USE_FLASHINFER_MOE_FP4=0 \
      -e VLLM_TEST_FORCE_FP8_MARLIN=1 \
      -e VLLM_NVFP4_GEMM_BACKEND=marlin"
    EXTRA_ARGS="--trust-remote-code --tensor-parallel-size 1 \
      --kv-cache-dtype fp8 --quantization modelopt_fp4"
    echo "═══ Nemotron 3 Nano 30B-A3B NVFP4 (3.2B active, ~8GB, Avarok kernel) ═══"
    echo "    Best quality/memory ratio, requires Avarok image"
    echo "    65+ tok/s with MoE latency backend"
    ;;
  custom)
    MODEL="${2:?Usage: $0 custom org/model-name}"
    GPU_UTIL="${VLLM_GRAPHITI_GPU_UTIL:-0.10}"
    MAX_LEN="${VLLM_GRAPHITI_MAX_LEN:-8192}"
    EXTRA_ARGS="--trust-remote-code"
    echo "═══ Custom model: $MODEL ═══"
    ;;
  *)
    echo "Unknown preset: $MODEL_PRESET"
    echo ""
    echo "Available presets:"
    echo ""
    echo "  FP8 (standard NGC image):"
    echo "    nano-4b       Nemotron 3 Nano 4B FP8 (default, ~4GB, fastest)"
    echo "    nano-30b      Nemotron 3 Nano 30B-A3B FP8 (3.2B active, ~15GB)"
    echo ""
    echo "  NVFP4 (requires Avarok image — smaller memory, faster on GB10):"
    echo "    nano-4b-nvfp4   Nemotron 3 Nano 4B NVFP4 (~2GB)"
    echo "    nano-30b-nvfp4  Nemotron 3 Nano 30B-A3B NVFP4 (~8GB, 65+ tok/s)"
    echo ""
    echo "  Other:"
    echo "    custom     Any model: $0 custom org/model-name"
    echo ""
    echo "Port allocation:"
    echo "  8000 — Graphiti LLM (this script)"
    echo "  8001 — Embeddings (vllm-embed.sh)"
    echo "  8002 — AutoBuild LLM (vllm-serve.sh)"
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

# --- Check if port 8000 is in use by vllm-server (AutoBuild) ---
if docker ps -q --filter "name=vllm-server" | grep -q .; then
  echo ""
  echo "WARNING: vllm-server (AutoBuild) is running on port 8000."
  echo "  It needs to move to port 8002 before starting the Graphiti LLM."
  echo ""
  echo "  Option 1: Stop it and restart on port 8002:"
  echo "    docker stop vllm-server && docker rm vllm-server"
  echo "    VLLM_PORT=8002 ./scripts/vllm-serve.sh"
  echo ""
  echo "  Option 2: Stop it (if you don't need AutoBuild right now):"
  echo "    docker stop vllm-server && docker rm vllm-server"
  echo ""
  read -r -p "  Stop vllm-server now? [y/N] " response
  if [[ "$response" =~ ^[Yy]$ ]]; then
    docker stop vllm-server && docker rm vllm-server
    echo "  Stopped vllm-server."
  else
    echo "  Aborted. Stop vllm-server first, then re-run this script."
    exit 1
  fi
fi

# --- Start VLLM Graphiti server ---
echo ""
echo "========================================"
echo "  VLLM Graphiti LLM — Dell Pro Max GB10"
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
echo "Waiting for model to load (should be quick — 4B model)..."
echo "  Logs:   docker logs -f $CONTAINER_NAME"
echo "  Health: curl http://localhost:${PORT}/health"
echo "  Models: curl http://localhost:${PORT}/v1/models"
echo ""
echo "Graphiti will use this automatically (port 8000 matches graphiti.yaml)."
echo ""
echo "To also run AutoBuild (Qwen3-Coder on port 8002):"
echo "  VLLM_PORT=8002 ./scripts/vllm-serve.sh"
echo ""
echo "Then use AutoBuild with:"
echo "  ANTHROPIC_BASE_URL=http://localhost:8002 ANTHROPIC_API_KEY=vllm-local guardkit autobuild task TASK-XXX"
