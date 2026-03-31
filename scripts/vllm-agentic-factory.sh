#!/usr/bin/env bash
# vllm-agentic-factory.sh — Serve LLM for agentic-dataset-factory on DGX Spark GB10
#
# Serves a model with tool-calling support for the Player-Coach adversarial
# cooperation pipeline. The Player agent needs tool-calling (rag_retrieval,
# write_output) while the Coach only needs text generation.
#
# Key difference from vllm-graphiti.sh:
#   - Adds --enable-auto-tool-choice with model-appropriate --tool-call-parser
#   - Uses port 8002 (AutoBuild LLM slot)
#   - Higher GPU util (dedicated to generation, not shared with Graphiti)
#
# Tool-call parser: --tool-call-parser qwen3_coder (official NVIDIA recommendation
# for Nemotron 3 models). Using the wrong parser (e.g. hermes) causes tool_calls.args
# double-serialization — see TASK-REV-FRF2.
#
# Usage:
#   ./scripts/vllm-agentic-factory.sh                      # Default: Qwen3.5-35B-A3B FP8
#   ./scripts/vllm-agentic-factory.sh nano-4b               # Nemotron 3 Nano 4B
#   ./scripts/vllm-agentic-factory.sh nano-30b              # Nemotron 3 Nano 30B-A3B
#   ./scripts/vllm-agentic-factory.sh custom org/model       # Any custom model
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
#   qwen35       weights ~70GB, vLLM alloc ~102GB (@0.80) Total with Graphiti: ~153GB (standalone recommended)
#   nano-4b      weights ~4GB,  vLLM alloc ~45GB (@0.35)  Total with Graphiti: ~100GB
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
MODEL_PRESET="${1:-qwen35}"

# Track which parser is used for the summary banner
TOOL_PARSER=""

case "$MODEL_PRESET" in
  qwen35|default|"")
    MODEL="Qwen/Qwen3.5-35B-A3B-FP8"
    GPU_UTIL="${VLLM_FACTORY_GPU_UTIL:-0.80}"
    MAX_LEN="${VLLM_FACTORY_MAX_LEN:-262144}"
    TOOL_PARSER="qwen3_coder"
    IMAGE="${VLLM_IMAGE:-vllm/vllm-openai:cu130-nightly}"
    EXTRA_ARGS="--trust-remote-code \
      --enable-auto-tool-choice \
      --tool-call-parser qwen3_coder \
      --enable-prefix-caching \
      --guided-decoding-backend outlines"
    echo "═══ Qwen3.5-35B-A3B FP8 (3B active, ~70GB) — Tool-calling ═══"
    echo "    BFCL-V4: 67.3 | TAU2: 81.2 | 50 tok/s sustained"
    echo "    Tool parser: qwen3_coder | Guided: outlines | Context: ${MAX_LEN}"
    ;;
  nano-4b)
    MODEL="nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8"
    GPU_UTIL="${VLLM_FACTORY_GPU_UTIL:-0.35}"
    MAX_LEN="${VLLM_FACTORY_MAX_LEN:-16384}"
    TOOL_PARSER="qwen3_coder"
    # Nano 4B is hybrid Mamba-2 (not MoE), no MoE-specific env vars needed
    EXTRA_ARGS="--trust-remote-code --kv-cache-dtype fp8 \
      --enable-auto-tool-choice \
      --tool-call-parser qwen3_coder"
    echo "═══ Nemotron 3 Nano 4B FP8 (~4GB) — Tool-calling enabled ═══"
    echo "    Dataset factory Player + Coach inference"
    echo "    Tool parser: qwen3_coder | Context: ${MAX_LEN}"
    ;;
  nano-30b)
    MODEL="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8"
    GPU_UTIL="${VLLM_FACTORY_GPU_UTIL:-0.30}"
    MAX_LEN="${VLLM_FACTORY_MAX_LEN:-16384}"
    TOOL_PARSER="qwen3_coder"
    EXTRA_ENV="-e VLLM_FLASHINFER_MOE_BACKEND=latency"
    # 30B-A3B is MoE — needs FlashInfer latency backend for SM 12.1 (GB10)
    EXTRA_ARGS="--trust-remote-code --tensor-parallel-size 1 --kv-cache-dtype fp8 \
      --enable-auto-tool-choice \
      --tool-call-parser qwen3_coder"
    echo "═══ Nemotron 3 Nano 30B-A3B FP8 (3.2B active, ~15GB) — Tool-calling enabled ═══"
    echo "    MoE with FlashInfer latency backend"
    echo "    Tool parser: qwen3_coder | Context: ${MAX_LEN}"
    ;;
  custom)
    MODEL="${2:?Usage: $0 custom org/model-name}"
    GPU_UTIL="${VLLM_FACTORY_GPU_UTIL:-0.35}"
    MAX_LEN="${VLLM_FACTORY_MAX_LEN:-16384}"
    TOOL_PARSER="qwen3_coder"
    EXTRA_ARGS="--trust-remote-code \
      --enable-auto-tool-choice \
      --tool-call-parser qwen3_coder"
    echo "═══ Custom model: $MODEL — Tool-calling enabled ═══"
    ;;
  *)
    echo "Unknown preset: $MODEL_PRESET"
    echo ""
    echo "Available presets:"
    echo ""
    echo "  Qwen3.5 (recommended — best agentic tool-calling on DGX Spark):"
    echo "    qwen35        Qwen3.5-35B-A3B FP8 (default, ~70GB, 50 tok/s)"
    echo ""
    echo "  Nemotron 3 (native tool calling, qwen3_coder parser):"
    echo "    nano-4b       Nemotron 3 Nano 4B FP8 (~4GB)"
    echo "    nano-30b      Nemotron 3 Nano 30B-A3B FP8 (3.2B active, ~15GB)"
    echo ""
    echo "  Other:"
    echo "    custom        Any model: $0 custom org/model-name"
    echo ""
    echo "All presets include --enable-auto-tool-choice --tool-call-parser qwen3_coder"
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
echo "  Tools:    ${TOOL_PARSER} parser (auto tool choice)"
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
  --entrypoint vllm \
  "$IMAGE" \
  serve "$MODEL" \
    --host 0.0.0.0 \
    --port 8000 \
    --gpu-memory-utilization "$GPU_UTIL" \
    --max-model-len "$MAX_LEN" \
    --dtype auto \
    $EXTRA_ARGS

echo "Container started: $CONTAINER_NAME"
echo ""
echo "Waiting for model to load..."
echo "  Logs:   docker logs -f $CONTAINER_NAME"
echo "  Health: curl http://localhost:${PORT}/health"
echo "  Models: curl http://localhost:${PORT}/v1/models"
echo ""
echo "Update agent-config.yaml endpoint to:"
echo "  endpoint: http://promaxgb10-41b1:${PORT}/v1"
echo ""
