#!/usr/bin/env bash
# vllm-serve.sh — Start VLLM server on Dell Pro Max GB10 / DGX Spark
#
# Usage:
#   ./scripts/vllm-serve.sh                    # Default: Qwen3-Coder-Next FP8
#   ./scripts/vllm-serve.sh 30b                # Qwen3-Coder-30B (faster, smaller)
#   ./scripts/vllm-serve.sh minimax            # MiniMax M2.5 NVFP4 (Claude API backup)
#   ./scripts/vllm-serve.sh minimax-gguf       # MiniMax M2.5 via llama.cpp (quick backup)
#   ./scripts/vllm-serve.sh custom org/model   # Any custom model
#
# Environment variables (override defaults):
#   VLLM_PORT=8000          Server port
#   VLLM_GPU_UTIL=0.8       GPU memory utilization (0.0-1.0)
#   VLLM_MAX_LEN=262144     Max context length (Qwen3-Coder-Next supports 256K natively)
#   VLLM_IMAGE=nvcr.io/nvidia/vllm:26.01-py3  Docker image
#   HF_TOKEN=...            Hugging Face token (for gated models)
#
# Resilience strategy:
#   Primary (AutoBuild):     ./vllm-serve.sh              → Qwen3-Coder-Next FP8
#   Backup (Claude API down): ./vllm-serve.sh minimax     → MiniMax M2.5 NVFP4
#   Quick backup (no Docker):  ./vllm-serve.sh minimax-gguf → llama.cpp server
#
#   All presets serve on the same port with the same model alias, so downstream
#   tooling (AutoBuild, autobuild-vllm wrapper) works without changes.
#   Only ONE model runs at a time — the script stops any existing container first.

set -euo pipefail

# --- Configuration ---
PORT="${VLLM_PORT:-8000}"
GPU_UTIL="${VLLM_GPU_UTIL:-0.8}"
MAX_LEN="${VLLM_MAX_LEN:-262144}"
IMAGE="${VLLM_IMAGE:-nvcr.io/nvidia/vllm:26.01-py3}"
CONTAINER_NAME="vllm-server"

# IMPORTANT: SERVED_MODEL_NAME must match the model ID used by the bundled claude CLI.
# The Claude Agent SDK's bundled 'claude' binary sends requests using its own default model ID.
# As of Claude Code Sonnet 4.6: the CLI default is "claude-sonnet-4-6".
# If you upgrade guardkit-py or claude-agent-sdk and autobuild starts failing with 404,
# check the new CLI default: ANTHROPIC_BASE_URL=http://localhost:8000 claude --version
# then update SERVED_MODEL_NAME below to match.
# See: docs/guides/simple-local-autobuild.md#model-alignment for full details.
# History: misalignment caused TASK-REV-AB3D (Player 404) and TASK-REV-ED10 (Coach SDK error).
SERVED_MODEL_NAME="claude-sonnet-4-6"

# Extra environment variables for Docker (model-specific, populated by presets)
EXTRA_ENV=""

# Flag for llama.cpp mode (bypasses Docker/vLLM entirely)
USE_LLAMACPP=false

# --- Model selection ---
MODEL_PRESET="${1:-next}"

case "$MODEL_PRESET" in
  next|default|"")
    MODEL="Qwen/Qwen3-Coder-Next-FP8"
    TOOL_PARSER="qwen3_coder"
    GPU_UTIL="${VLLM_GPU_UTIL:-0.8}"
    MAX_LEN="${VLLM_MAX_LEN:-262144}"
    echo "═══ Qwen3-Coder-Next FP8 (80B MoE, ~92GB, ~43 tok/s, 256K ctx) ═══"
    echo "    Primary model for AutoBuild"
    ;;
  30b)
    MODEL="Qwen/Qwen3-Coder-30B-A3B-Instruct"
    TOOL_PARSER="qwen3_coder"
    GPU_UTIL="${VLLM_GPU_UTIL:-0.5}"
    MAX_LEN="${VLLM_MAX_LEN:-32768}"
    echo "═══ Qwen3-Coder-30B-A3B (30B MoE, ~30GB FP8, fast) ═══"
    ;;
  next-nvfp4)
    MODEL="Qwen/Qwen3-Coder-Next-NVFP4"
    TOOL_PARSER="qwen3_coder"
    GPU_UTIL="${VLLM_GPU_UTIL:-0.5}"
    MAX_LEN="${VLLM_MAX_LEN:-262144}"
    echo "Model: Qwen3-Coder-Next NVFP4 (80B MoE, ~50GB, ~35 tok/s)"
    ;;

  # --- MiniMax M2.5 presets (Claude API backup / spec-writing) ---
  minimax|minimax-nvfp4)
    MODEL="lukealonso/MiniMax-M2.5-REAP-139B-A10B-NVFP4"
    TOOL_PARSER="minimax_m2"
    GPU_UTIL="${VLLM_GPU_UTIL:-0.85}"
    MAX_LEN="${VLLM_MAX_LEN:-60000}"
    # NVFP4-specific env vars from DGX Spark community (mjpansa, Feb 2026)
    # See: https://forums.developer.nvidia.com/t/minimax-2-5-reap-nvfp4-on-single-dgx-spark/361248
    EXTRA_ENV="-e CUDA_DEVICE_ORDER=PCI_BUS_ID \
      -e SAFETENSORS_FAST_GPU=1 \
      -e VLLM_NVFP4_GEMM_BACKEND=cutlass \
      -e VLLM_USE_FLASHINFER_MOE_FP4=0 \
      -e NCCL_IB_DISABLE=1 \
      -e OMP_NUM_THREADS=8"
    # Override image to use Avarok's NVFP4-optimised build if available
    # Fallback: the standard NGC image works but slower (~17 tok/s vs ~30 tok/s)
    # To use Avarok image: VLLM_IMAGE=avarok/dgx-vllm:latest ./vllm-serve.sh minimax
    echo "═══ MiniMax M2.5 NVFP4 (230B MoE/10B active, ~17-30 tok/s) ═══"
    echo "    Claude API backup — frontier-level spec writing & planning"
    echo "    SWE-Bench Verified: 80.2% | Multi-SWE-Bench: 51.3%"
    echo ""
    echo "    TIP: For faster inference, use the Avarok NVFP4 image:"
    echo "    VLLM_IMAGE=avarok/dgx-vllm:latest ./vllm-serve.sh minimax"
    ;;
  minimax-awq)
    MODEL="cyankiwi/MiniMax-M2.5-AWQ-4bit"
    TOOL_PARSER="minimax_m2"
    GPU_UTIL="${VLLM_GPU_UTIL:-0.85}"
    MAX_LEN="${VLLM_MAX_LEN:-65536}"
    echo "═══ MiniMax M2.5 AWQ 4-bit (230B MoE/10B active, ~15 tok/s) ═══"
    echo "    Claude API backup (AWQ quant, more tested but slower than NVFP4)"
    ;;

  # --- llama.cpp mode (no Docker, no vLLM) ---
  minimax-gguf|llamacpp)
    USE_LLAMACPP=true
    GGUF_MODEL="unsloth/MiniMax-M2.5-GGUF:UD-Q3_K_XL"
    echo "═══ MiniMax M2.5 GGUF Q3 (230B MoE, ~101GB, ~20 tok/s) ═══"
    echo "    Quick backup via llama.cpp — no Docker required"
    echo "    Requires: llama.cpp built locally (~/llama.cpp/build/bin/llama-server)"
    ;;

  custom)
    MODEL="${2:?Usage: $0 custom org/model-name}"
    TOOL_PARSER="${VLLM_TOOL_PARSER:-qwen3_coder}"
    echo "═══ Custom model: $MODEL ═══"
    ;;
  *)
    echo "Unknown preset: $MODEL_PRESET"
    echo ""
    echo "Available presets:"
    echo ""
    echo "  PRIMARY (AutoBuild implementation):"
    echo "    next         Qwen3-Coder-Next FP8 (default, best quality)"
    echo "    30b          Qwen3-Coder-30B-A3B (faster, smaller)"
    echo "    next-nvfp4   Qwen3-Coder-Next NVFP4 (smaller memory footprint)"
    echo ""
    echo "  BACKUP (Claude API down / Max quota / spec-writing):"
    echo "    minimax      MiniMax M2.5 NVFP4 — frontier-level, best backup"
    echo "    minimax-awq  MiniMax M2.5 AWQ — more tested, slightly slower"
    echo "    minimax-gguf MiniMax M2.5 GGUF via llama.cpp — quickest to deploy"
    echo ""
    echo "  OTHER:"
    echo "    custom       Any model: $0 custom org/model-name"
    echo ""
    echo "  All presets serve on port ${PORT} as '${SERVED_MODEL_NAME}'"
    echo "  so AutoBuild works without changes."
    exit 1
    ;;
esac

# ============================================================
# llama.cpp mode — completely separate serving path
# ============================================================
if [ "$USE_LLAMACPP" = true ]; then
  LLAMA_SERVER="${LLAMA_SERVER:-$HOME/llama.cpp/build/bin/llama-server}"

  if [ ! -x "$LLAMA_SERVER" ]; then
    echo ""
    echo "ERROR: llama-server not found at $LLAMA_SERVER"
    echo ""
    echo "To build llama.cpp on the GB10:"
    echo "  git clone https://github.com/ggml-org/llama.cpp.git ~/llama.cpp"
    echo "  cd ~/llama.cpp && cmake -B build -DGGML_CUDA=ON && cmake --build build -j$(nproc)"
    echo ""
    echo "Or set LLAMA_SERVER=/path/to/llama-server"
    exit 1
  fi

  # Stop any running vLLM container on the same port
  if docker ps -q --filter "name=$CONTAINER_NAME" 2>/dev/null | grep -q .; then
    echo "Stopping existing vLLM container: $CONTAINER_NAME"
    docker stop "$CONTAINER_NAME" && docker rm "$CONTAINER_NAME"
  fi

  # Kill any existing llama-server on our port
  if lsof -ti :"$PORT" >/dev/null 2>&1; then
    echo "Stopping existing process on port $PORT"
    kill $(lsof -ti :"$PORT") 2>/dev/null || true
    sleep 2
  fi

  echo ""
  echo "========================================"
  echo "  llama.cpp Server — Dell Pro Max GB10"
  echo "========================================"
  echo "  Model:  $GGUF_MODEL"
  echo "  Port:   $PORT"
  echo "  Alias:  $SERVED_MODEL_NAME"
  echo "========================================"
  echo ""
  echo "Downloading model (if not cached)..."

  # llama-server can download directly from HF with -hf flag
  # --alias makes it appear as our expected model name
  # -np 1: single parallel slot (critical for throughput, per community advice)
  # --fit: auto-maximise context for available memory (default in recent llama.cpp)
  # Recent llama.cpp defaults: --no-mmap, --jinja, -ngl 999, --flash-attn
  nohup "$LLAMA_SERVER" \
    -hf "$GGUF_MODEL" \
    --alias "$SERVED_MODEL_NAME" \
    --host 0.0.0.0 \
    --port "$PORT" \
    -np 1 \
    > /tmp/llama-minimax.log 2>&1 &

  LLAMA_PID=$!
  echo "llama-server started (PID: $LLAMA_PID)"
  echo ""
  echo "Waiting for model to load (may take 5-10 min for first download)..."
  echo "  Logs:   tail -f /tmp/llama-minimax.log"
  echo "  Health: curl http://localhost:${PORT}/health"
  echo "  Stop:   kill $LLAMA_PID"
  echo ""
  echo "Once ready, use AutoBuild with:"
  echo "  ANTHROPIC_BASE_URL=http://localhost:${PORT} ANTHROPIC_API_KEY=vllm-local guardkit autobuild task TASK-XXX"
  echo ""
  echo "NOTE: llama.cpp serves an OpenAI-compatible API, not Anthropic Messages API."
  echo "AutoBuild should work if using the OpenAI-compatible path. If you hit issues"
  echo "with Anthropic-specific message format, use the vLLM minimax preset instead."
  exit 0
fi

# ============================================================
# vLLM mode (Docker) — all non-llamacpp presets
# ============================================================

# --- Stop existing container if running ---
if docker ps -q --filter "name=$CONTAINER_NAME" | grep -q .; then
  echo "Stopping existing container: $CONTAINER_NAME"
  docker stop "$CONTAINER_NAME" && docker rm "$CONTAINER_NAME"
fi

# Also clean up stopped containers with same name
if docker ps -aq --filter "name=$CONTAINER_NAME" | grep -q .; then
  docker rm "$CONTAINER_NAME" 2>/dev/null || true
fi

# --- Build extra vLLM args for MiniMax models ---
EXTRA_VLLM_ARGS=""
case "$MODEL_PRESET" in
  minimax|minimax-nvfp4)
    # MiniMax M2.5 needs reasoning parser and --trust-remote-code
    # --disable-custom-all-reduce required for single-GPU NVFP4 on Spark
    EXTRA_VLLM_ARGS="--trust-remote-code \
      --tensor-parallel-size 1 \
      --disable-custom-all-reduce \
      --reasoning-parser minimax_m2_append_think"
    ;;
  minimax-awq)
    EXTRA_VLLM_ARGS="--trust-remote-code \
      --tensor-parallel-size 1"
    ;;
esac

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

# Note: EXTRA_ENV and EXTRA_VLLM_ARGS are intentionally unquoted to allow
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
    --served-model-name "$SERVED_MODEL_NAME" \
    --enable-auto-tool-choice \
    --tool-call-parser "$TOOL_PARSER" \
    --gpu-memory-utilization "$GPU_UTIL" \
    --max-model-len "$MAX_LEN" \
    --attention-backend flashinfer \
    --enable-prefix-caching \
    --load-format auto \
    ${EXTRA_VLLM_ARGS}

echo "Container started: $CONTAINER_NAME"
echo ""

# Model-specific load time estimate
case "$MODEL_PRESET" in
  minimax|minimax-nvfp4|minimax-awq)
    echo "Waiting for model to load (5-8 min for MiniMax 230B)..."
    ;;
  next|default|"")
    echo "Waiting for model to load (3-5 min for 80B)..."
    ;;
  *)
    echo "Waiting for model to load..."
    ;;
esac

echo "  Logs:   docker logs -f $CONTAINER_NAME"
echo "  Health: curl http://localhost:${PORT}/health"
echo "  Models: curl http://localhost:${PORT}/v1/models"
echo ""
echo "Once ready, use AutoBuild with:"
echo "  ANTHROPIC_BASE_URL=http://localhost:${PORT} ANTHROPIC_API_KEY=vllm-local guardkit autobuild task TASK-XXX"
