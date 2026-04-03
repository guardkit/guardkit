#!/usr/bin/env bash
# vllm-agentic-factory.sh — Serve LLM for agentic-dataset-factory on DGX Spark GB10
#
# Uses the locally-built vllm-node image from eugr/spark-vllm-docker for
# optimised Spark inference. Runs directly via docker run (no Ray overhead).
#
# Serves a model with tool-calling support for the Player-Coach adversarial
# cooperation pipeline. The Player agent needs tool-calling (rag_retrieval,
# write_output) while the Coach only needs text generation.
#
# Usage:
#   ./scripts/vllm-agentic-factory.sh                      # Default: Qwen3.5-35B-A3B FP8
#   ./scripts/vllm-agentic-factory.sh nano-4b               # Nemotron 3 Nano 4B
#   ./scripts/vllm-agentic-factory.sh nano-30b              # Nemotron 3 Nano 30B-A3B
#   ./scripts/vllm-agentic-factory.sh custom org/model       # Any custom model
#
# Environment variables:
#   VLLM_FACTORY_PORT=8002         Server port (default: 8002)
#   VLLM_FACTORY_GPU_UTIL=0.80     GPU memory utilization (0.0-1.0)
#   VLLM_FACTORY_MAX_LEN=262144   Max context length
#   VLLM_MAX_NUM_SEQS=4           Max concurrent sequences
#   SPARK_VLLM_DIR=~/Projects/spark-vllm-docker  Path to spark-vllm-docker repo
#
# Prerequisites:
#   git clone https://github.com/eugr/spark-vllm-docker.git ~/Projects/spark-vllm-docker
#   cd ~/Projects/spark-vllm-docker && ./build-and-copy.sh
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
MAX_NUM_SEQS="${VLLM_MAX_NUM_SEQS:-4}"
SPARK_VLLM_DIR="${SPARK_VLLM_DIR:-$HOME/Projects/spark-vllm-docker}"
CONTAINER_NAME="vllm-agentic-factory"

# --- Select image ---
# Override with VLLM_IMAGE env var, or auto-select best available.
# Priority: env override > vllm-node-tf5 > vllm-node > cu130-nightly
if [ -n "${VLLM_IMAGE:-}" ]; then
  : # use env override as-is
elif docker image inspect vllm-node-tf5 > /dev/null 2>&1; then
  VLLM_IMAGE="vllm-node-tf5"
elif docker image inspect vllm-node > /dev/null 2>&1; then
  VLLM_IMAGE="vllm-node"
elif docker image inspect vllm/vllm-openai:cu130-nightly > /dev/null 2>&1; then
  VLLM_IMAGE="vllm/vllm-openai:cu130-nightly"
  echo "NOTE: Using cu130-nightly fallback. For spark-vllm optimisations, build:"
  echo "  cd ${SPARK_VLLM_DIR} && ./build-and-copy.sh --tf5"
else
  echo "ERROR: No vLLM Docker image found."
  echo ""
  echo "Either pull the nightly:"
  echo "  docker pull vllm/vllm-openai:cu130-nightly"
  echo ""
  echo "Or build spark-vllm-docker (recommended):"
  echo "  git clone https://github.com/eugr/spark-vllm-docker.git ${SPARK_VLLM_DIR}"
  echo "  cd ${SPARK_VLLM_DIR} && ./build-and-copy.sh --tf5"
  exit 1
fi

# --- Model selection ---
MODEL_PRESET="${1:-qwen35}"
EXTRA_ARGS=""

case "$MODEL_PRESET" in
  qwen35|default|"")
    MODEL="Qwen/Qwen3.5-35B-A3B-FP8"
    GPU_UTIL="${VLLM_FACTORY_GPU_UTIL:-0.70}"
    MAX_LEN="${VLLM_FACTORY_MAX_LEN:-262144}"
    # Flags from spark-arena #1 recipe (50.75 tok/s single node):
    # https://spark-arena.com/leaderboard — Qwen3.5-35B-A3B-FP8
    EXTRA_ARGS="--trust-remote-code \
      --enable-auto-tool-choice \
      --tool-call-parser qwen3_coder \
      --reasoning-parser qwen3 \
      --enable-prefix-caching \
      --kv-cache-dtype fp8 \
      --attention-backend flashinfer \
      --max-num-batched-tokens 32768 \
      --max-num-seqs 10 \
      --max-cudagraph-capture-size 10 \
      --mamba-ssm-cache-dtype float16"
    # Apply mod at runtime (Transformers rope fix for Qwen3.5)
    APPLY_MOD="${SPARK_VLLM_DIR}/mods/fix-qwen3.5-autoround"
    echo "═══ Qwen3.5-35B-A3B FP8 (3B active, ~70GB) — Tool-calling ═══"
    echo "    spark-arena #1 recipe | target: 50 tok/s | Context: ${MAX_LEN}"
    ;;
  nano-4b)
    MODEL="nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8"
    GPU_UTIL="${VLLM_FACTORY_GPU_UTIL:-0.35}"
    MAX_LEN="${VLLM_FACTORY_MAX_LEN:-16384}"
    EXTRA_ARGS="--trust-remote-code --kv-cache-dtype fp8 \
      --enable-auto-tool-choice \
      --tool-call-parser qwen3_coder \
      --enable-prefix-caching \
      --enable-chunked-prefill"
    echo "═══ Nemotron 3 Nano 4B FP8 (~4GB) — Tool-calling enabled ═══"
    echo "    Tool parser: qwen3_coder | Context: ${MAX_LEN}"
    ;;
  nano-30b)
    MODEL="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8"
    GPU_UTIL="${VLLM_FACTORY_GPU_UTIL:-0.30}"
    MAX_LEN="${VLLM_FACTORY_MAX_LEN:-16384}"
    EXTRA_ARGS="--trust-remote-code --tensor-parallel-size 1 --kv-cache-dtype fp8 \
      --enable-auto-tool-choice \
      --tool-call-parser qwen3_coder \
      --enable-prefix-caching \
      --enable-chunked-prefill"
    echo "═══ Nemotron 3 Nano 30B-A3B FP8 (3.2B active, ~15GB) — Tool-calling ═══"
    echo "    MoE with FlashInfer latency backend | Context: ${MAX_LEN}"
    ;;
  custom)
    MODEL="${2:?Usage: $0 custom org/model-name}"
    GPU_UTIL="${VLLM_FACTORY_GPU_UTIL:-0.35}"
    MAX_LEN="${VLLM_FACTORY_MAX_LEN:-16384}"
    EXTRA_ARGS="--trust-remote-code \
      --enable-auto-tool-choice \
      --tool-call-parser qwen3_coder"
    echo "═══ Custom model: $MODEL — Tool-calling enabled ═══"
    ;;
  *)
    echo "Unknown preset: $MODEL_PRESET"
    echo ""
    echo "Available presets:"
    echo "  qwen35        Qwen3.5-35B-A3B FP8 (default, ~70GB)"
    echo "  nano-4b       Nemotron 3 Nano 4B FP8 (~4GB)"
    echo "  nano-30b      Nemotron 3 Nano 30B-A3B FP8 (~15GB)"
    echo "  custom        Any model: $0 custom org/model-name"
    exit 1
    ;;
esac

# --- Stop existing container if running ---
if docker ps -q --filter "name=$CONTAINER_NAME" | grep -q .; then
  echo "Stopping existing container: $CONTAINER_NAME"
  docker stop "$CONTAINER_NAME" && docker rm "$CONTAINER_NAME"
fi
if docker ps -aq --filter "name=$CONTAINER_NAME" | grep -q .; then
  docker rm "$CONTAINER_NAME" 2>/dev/null || true
fi

# --- Banner ---
echo ""
echo "========================================"
echo "  Agentic Dataset Factory — DGX Spark GB10"
echo "========================================"
echo "  Model:    $MODEL"
echo "  Port:     $PORT"
echo "  GPU util: $GPU_UTIL"
echo "  Max len:  $MAX_LEN"
echo "  Image:    $VLLM_IMAGE"
echo "  Mod:      ${APPLY_MOD:-none}"
echo "========================================"
echo ""

# --- Launch directly with docker run ---
# Uses the locally-built vllm-node image from spark-vllm-docker.
# Direct docker run avoids Ray overhead for single-node workloads.
# Uses --network host so --port maps directly to the host.
#
# Env vars match leaderboard recipe (only VLLM_MARLIN_USE_ATOMIC_ADD).
# VLLM_USE_V1 intentionally omitted — not in any top recipe and may
# cause regressions in 0.18.x.
# shellcheck disable=SC2086
docker run -d \
  --name "$CONTAINER_NAME" \
  --gpus all \
  --network host \
  --ipc=host \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  -v "$HOME/.cache/vllm:/root/.cache/vllm" \
  ${HF_TOKEN:+-e "HF_TOKEN=$HF_TOKEN"} \
  -e "VLLM_MARLIN_USE_ATOMIC_ADD=1" \
  --entrypoint vllm \
  "$VLLM_IMAGE" \
  serve "$MODEL" \
    --host 0.0.0.0 \
    --port "$PORT" \
    --gpu-memory-utilization "$GPU_UTIL" \
    --max-model-len "$MAX_LEN" \
    --load-format fastsafetensors \
    $EXTRA_ARGS

# --- Apply mod (runtime patch) if specified ---
if [ -n "${APPLY_MOD:-}" ] && [ -d "$APPLY_MOD" ]; then
  echo "Applying mod: $APPLY_MOD"
  docker cp "$APPLY_MOD/." "$CONTAINER_NAME:/tmp/mod/"
  docker exec "$CONTAINER_NAME" bash -c "cd /tmp/mod && bash run.sh" || true
fi

echo ""
echo "Container started: $CONTAINER_NAME"
echo ""
echo "Waiting for model to load..."
echo "  Logs:   docker logs -f $CONTAINER_NAME"
echo "  Health: curl http://localhost:${PORT}/health"
echo "  Models: curl http://localhost:${PORT}/v1/models"
echo ""
echo "Resume dataset generation:"
echo "  cd ~/Projects/appmilla_github/agentic-dataset-factory"
echo "  ./scripts/run-on-gb10.sh --resume"
