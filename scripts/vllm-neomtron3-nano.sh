#!/usr/bin/env bash
# vllm-nemotron3-nano.sh — Serve Nemotron 3 Nano models on DGX Spark GB10
#
# General-purpose instruction-following models. Fine-tuning base for GCSE tutor SLM.
#
# Usage:
#   ./scripts/vllm-nemotron3-nano.sh                  # Default: Nano 4B FP8
#   ./scripts/vllm-nemotron3-nano.sh nano-4b-nvfp4    # Nano 4B NVFP4 (Avarok image)
#   ./scripts/vllm-nemotron3-nano.sh nano-30b         # Nano 30B-A3B FP8
#   ./scripts/vllm-nemotron3-nano.sh nano-30b-nvfp4   # Nano 30B-A3B NVFP4 (65+ tok/s)
#   ./scripts/vllm-nemotron3-nano.sh custom org/model # Any custom model
#
# Environment variables:
#   VLLM_NEMOTRON_PORT=8003        Server port (default: 8003)
#   VLLM_NEMOTRON_GPU_UTIL=0.30   GPU memory utilization (0.0-1.0)
#   VLLM_NEMOTRON_MAX_LEN=8192    Max context length
#   VLLM_IMAGE=nvcr.io/nvidia/vllm:26.01-py3  Docker image (overridden by NVFP4 presets)
#
# DGX Spark (GB10) performance notes:
#   - FP8 models work with standard NGC image
#   - NVFP4 models need Avarok image (avarok/dgx-vllm-nvfp4-kernel:v22)
#     for SM 12.1 software E2M1 workaround (32x speedup)
#   - MoE models (30B-A3B) need VLLM_FLASHINFER_MOE_BACKEND=latency
#     to avoid CUTLASS kernel issues on SM 12.1 (60% speedup)
#   - See: https://blog.avarok.net/dgx-spark-nemotron3-and-nvfp4-getting-to-65-tps-8c5569025eb6

set -euo pipefail

# --- Configuration ---
PORT="${VLLM_NEMOTRON_PORT:-8003}"
GPU_UTIL="${VLLM_NEMOTRON_GPU_UTIL:-0.30}"
IMAGE="${VLLM_IMAGE:-nvcr.io/nvidia/vllm:26.01-py3}"
CONTAINER_NAME="vllm-nemotron3-nano"

# Extra environment variables for Docker (model-specific, populated by presets)
EXTRA_ENV=""

# --- Model selection ---
MODEL_PRESET="${1:-nano-4b}"

case "$MODEL_PRESET" in
  nano-4b|default|"")
    MODEL="nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8"
    GPU_UTIL="${VLLM_NEMOTRON_GPU_UTIL:-0.30}"
    MAX_LEN="${VLLM_NEMOTRON_MAX_LEN:-8192}"
    # Nano 4B is hybrid Mamba-2 (not MoE), so MoE-specific env vars not needed
    EXTRA_ARGS="--trust-remote-code --kv-cache-dtype fp8"
    echo "═══ Nemotron 3 Nano 4B FP8 (~4GB) ═══"
    echo "    Fine-tuning base for GCSE tutor SLM"
    ;;
  nano-4b-nvfp4)
    MODEL="nvidia/NVIDIA-Nemotron-3-Nano-4B-NVFP4"
    GPU_UTIL="${VLLM_NEMOTRON_GPU_UTIL:-0.20}"
    MAX_LEN="${VLLM_NEMOTRON_MAX_LEN:-8192}"
    IMAGE="${VLLM_IMAGE:-avarok/dgx-vllm-nvfp4-kernel:v22}"
    EXTRA_ARGS="--trust-remote-code --kv-cache-dtype fp8 --quantization modelopt_fp4"
    echo "═══ Nemotron 3 Nano 4B NVFP4 (~2GB, Avarok kernel) ═══"
    echo "    Smallest memory footprint, requires Avarok image"
    ;;
  nano-30b)
    MODEL="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8"
    GPU_UTIL="${VLLM_NEMOTRON_GPU_UTIL:-0.30}"
    MAX_LEN="${VLLM_NEMOTRON_MAX_LEN:-8192}"
    # 30B-A3B is MoE — needs FlashInfer latency backend for SM 12.1 (GB10)
    # See: https://blog.avarok.net/dgx-spark-nemotron3-and-nvfp4-getting-to-65-tps-8c5569025eb6
    EXTRA_ENV="-e VLLM_FLASHINFER_MOE_BACKEND=latency"
    EXTRA_ARGS="--trust-remote-code --tensor-parallel-size 1 --kv-cache-dtype fp8"
    echo "═══ Nemotron 3 Nano 30B-A3B FP8 (3.2B active, ~15GB) ═══"
    ;;
  nano-30b-nvfp4)
    MODEL="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4"
    GPU_UTIL="${VLLM_NEMOTRON_GPU_UTIL:-0.20}"
    MAX_LEN="${VLLM_NEMOTRON_MAX_LEN:-8192}"
    IMAGE="${VLLM_IMAGE:-avarok/dgx-vllm-nvfp4-kernel:v22}"
    # MoE + NVFP4: use Avarok image + Marlin backend for SM 12.1
    EXTRA_ENV="-e VLLM_FLASHINFER_MOE_BACKEND=latency \
      -e VLLM_USE_FLASHINFER_MOE_FP4=0 \
      -e VLLM_TEST_FORCE_FP8_MARLIN=1 \
      -e VLLM_NVFP4_GEMM_BACKEND=marlin"
    EXTRA_ARGS="--trust-remote-code --tensor-parallel-size 1 \
      --kv-cache-dtype fp8 --quantization modelopt_fp4"
    echo "═══ Nemotron 3 Nano 30B-A3B NVFP4 (3.2B active, ~8GB, Avarok kernel) ═══"
    echo "    65+ tok/s with MoE latency backend"
    ;;
  custom)
    MODEL="${2:?Usage: $0 custom org/model-name}"
    GPU_UTIL="${VLLM_NEMOTRON_GPU_UTIL:-0.30}"
    MAX_LEN="${VLLM_NEMOTRON_MAX_LEN:-8192}"
    EXTRA_ARGS="--trust-remote-code"
    echo "═══ Custom model: $MODEL ═══"
    ;;
  *)
    echo "Unknown preset: $MODEL_PRESET"
    echo ""
    echo "Available presets:"
    echo ""
    echo "  FP8 (standard NGC image):"
    echo "    nano-4b       Nemotron 3 Nano 4B FP8 (default, ~4GB)"
    echo "    nano-30b      Nemotron 3 Nano 30B-A3B FP8 (3.2B active, ~15GB)"
    echo ""
    echo "  NVFP4 (requires Avarok image — smaller memory, faster on GB10):"
    echo "    nano-4b-nvfp4   Nemotron 3 Nano 4B NVFP4 (~2GB)"
    echo "    nano-30b-nvfp4  Nemotron 3 Nano 30B-A3B NVFP4 (~8GB, 65+ tok/s)"
    echo ""
    echo "  Other:"
    echo "    custom     Any model: $0 custom org/model-name"
    echo ""
    echo "Default port: $PORT  (override: VLLM_NEMOTRON_PORT=XXXX)"
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
echo "  Nemotron 3 Nano — DGX Spark GB10"
echo "========================================"
echo "  Model:    $MODEL"
echo "  Port:     $PORT"
echo "  GPU util: $GPU_UTIL"
echo "  Max len:  $MAX_LEN"
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
echo "  Logs:   docker logs -f $CONTAINER_NAME"
echo "  Health: curl http://localhost:${PORT}/health"
echo "  Models: curl http://localhost:${PORT}/v1/models"
echo ""
