#!/usr/bin/env bash
# graphiti-stack-up.sh — Start the Graphiti stack in order.
#
# Boots, in order, with health-gated waits between each step:
#   1. vllm-graphiti   (LLM, port 8000)       ~60-120s to load   [skipped in --llm=mac|custom]
#   2. vllm-embedding  (embedder, port 8001)  ~15-30s
#   3. graphiti-mcp    (HTTP MCP, port 8004)  ~5-10s
#
# Idempotent — safe to re-run; each sub-script replaces any existing container
# with the same name.
#
# Usage:
#   ./scripts/graphiti-stack-up.sh                  # default: LLM on GB10 vLLM
#   ./scripts/graphiti-stack-up.sh --llm=gb10       # same as default
#   ./scripts/graphiti-stack-up.sh --llm=mac        # LLM on MacBook Ollama (frees GB10 GPU)
#   ./scripts/graphiti-stack-up.sh --llm=custom     # LLM from GRAPHITI_LLM_API_URL + _MODEL
#
# Skip flags (orthogonal to --llm):
#   SKIP_LLM=1   ./scripts/graphiti-stack-up.sh   # only embed + mcp
#   SKIP_EMBED=1 ./scripts/graphiti-stack-up.sh   # only llm + mcp
#   SKIP_MCP=1   ./scripts/graphiti-stack-up.sh   # only vllm services
#
# --llm=mac overrides (export before invoking if you don't want the defaults):
#   MAC_LLM_API_URL  default: http://richards-macbook-pro.tailebf801.ts.net:8000/v1
#   MAC_LLM_MODEL    default: qwen2.5:14b-instruct
#
# --llm=custom required env:
#   GRAPHITI_LLM_API_URL   e.g. https://generativelanguage.googleapis.com/v1beta/openai/
#   GRAPHITI_LLM_MODEL     e.g. gemini-2.5-pro
#   OPENAI_API_KEY         if the provider validates it

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

LLM_PORT="${VLLM_GRAPHITI_PORT:-8000}"
EMBED_PORT="${VLLM_EMBED_PORT:-8001}"
MCP_PORT="${GRAPHITI_MCP_PORT:-8004}"

# --- Parse --llm= flag ---
LLM_MODE="gb10"
for arg in "$@"; do
  case "$arg" in
    --llm=gb10)   LLM_MODE="gb10" ;;
    --llm=mac)    LLM_MODE="mac" ;;
    --llm=custom) LLM_MODE="custom" ;;
    --llm=*)
      echo "ERROR: unknown --llm mode: ${arg#--llm=}" >&2
      echo "       valid: gb10 | mac | custom" >&2
      exit 1
      ;;
    -h|--help)
      sed -n '2,31p' "$0"
      exit 0
      ;;
    *)
      echo "ERROR: unknown arg: $arg" >&2
      exit 1
      ;;
  esac
done

# --- Route the LLM based on mode ---
case "$LLM_MODE" in
  gb10)
    # Default — MCP container reads localhost:8000 from YAML; vllm-graphiti runs.
    ;;
  mac)
    # Skip the local vLLM LLM container and point MCP at the MacBook's Ollama.
    # Frees the GB10 GPU for fine-tuning / training data generation.
    SKIP_LLM=1
    export LLM_API_URL="${MAC_LLM_API_URL:-http://richards-macbook-pro.tailebf801.ts.net:8000/v1}"
    export LLM_MODEL="${MAC_LLM_MODEL:-qwen2.5:14b-instruct}"
    echo ""
    echo "⚠  --llm=mac: Graphiti LLM calls will hit the MacBook. Confirm Ollama is"
    echo "   running there and serving the model '${LLM_MODEL}'. Ingestion may see"
    echo "   occasional JSON parse failures (Ollama lacks vLLM+xgrammar's strict"
    echo "   token-level schema enforcement). Queries are unaffected."
    ;;
  custom)
    if [ -z "${GRAPHITI_LLM_API_URL:-}" ] || [ -z "${GRAPHITI_LLM_MODEL:-}" ]; then
      echo "ERROR: --llm=custom requires GRAPHITI_LLM_API_URL and GRAPHITI_LLM_MODEL" >&2
      echo "       Example:" >&2
      echo "         GRAPHITI_LLM_API_URL=https://generativelanguage.googleapis.com/v1beta/openai/ \\" >&2
      echo "         GRAPHITI_LLM_MODEL=gemini-2.5-pro \\" >&2
      echo "         OPENAI_API_KEY=\$GOOGLE_API_KEY \\" >&2
      echo "         ./scripts/graphiti-stack-up.sh --llm=custom" >&2
      exit 1
    fi
    SKIP_LLM=1
    export LLM_API_URL="$GRAPHITI_LLM_API_URL"
    export LLM_MODEL="$GRAPHITI_LLM_MODEL"
    ;;
esac

# Tunable: max seconds to wait for each service's /health to become ready.
WAIT_LLM_SECONDS="${WAIT_LLM_SECONDS:-300}"
WAIT_EMBED_SECONDS="${WAIT_EMBED_SECONDS:-120}"
WAIT_MCP_SECONDS="${WAIT_MCP_SECONDS:-60}"

wait_for_health() {
  local name="$1" url="$2" timeout="$3"
  echo "  Waiting for $name at $url (up to ${timeout}s)..."
  local start end
  start="$(date +%s)"
  while true; do
    if curl -fsS -o /dev/null "$url"; then
      end="$(date +%s)"
      echo "  ✓ $name ready after $((end - start))s"
      return 0
    fi
    end="$(date +%s)"
    if [ $((end - start)) -ge "$timeout" ]; then
      echo "  ✗ $name did NOT become ready within ${timeout}s" >&2
      echo "    Check: docker logs <container>" >&2
      return 1
    fi
    sleep 2
  done
}

echo ""
echo "════════════════════════════════════════"
echo "  Graphiti stack — starting on GB10"
echo "  LLM mode: $LLM_MODE"
if [ "$LLM_MODE" != "gb10" ]; then
  echo "  LLM URL:  ${LLM_API_URL}"
  echo "  LLM mdl:  ${LLM_MODEL}"
fi
echo "════════════════════════════════════════"

# --- Step 1: vllm-graphiti (LLM) ---
if [ "${SKIP_LLM:-0}" != "1" ]; then
  echo ""
  echo "── [1/3] vllm-graphiti (LLM) ──"
  "$SCRIPT_DIR/vllm-graphiti.sh"
  wait_for_health "vllm-graphiti" "http://localhost:${LLM_PORT}/health" "$WAIT_LLM_SECONDS"
else
  echo ""
  echo "── [1/3] vllm-graphiti — SKIPPED (SKIP_LLM=1) ──"
fi

# --- Step 2: vllm-embedding ---
if [ "${SKIP_EMBED:-0}" != "1" ]; then
  echo ""
  echo "── [2/3] vllm-embedding ──"
  "$SCRIPT_DIR/vllm-embed.sh"
  wait_for_health "vllm-embedding" "http://localhost:${EMBED_PORT}/health" "$WAIT_EMBED_SECONDS"
else
  echo ""
  echo "── [2/3] vllm-embedding — SKIPPED (SKIP_EMBED=1) ──"
fi

# --- Step 3: graphiti-mcp ---
if [ "${SKIP_MCP:-0}" != "1" ]; then
  echo ""
  echo "── [3/3] graphiti-mcp (HTTP) ──"
  "$SCRIPT_DIR/graphiti-mcp.sh"
  # The standalone graphiti-mcp image has no /health by default, but the
  # FastMCP endpoint responds on /mcp/. Treat a 4xx from the path as "up".
  wait_for_health "graphiti-mcp" "http://localhost:${MCP_PORT}/mcp/" "$WAIT_MCP_SECONDS" \
    || echo "  (hint: a 4xx here is normal — FastMCP requires a session. Check docker logs graphiti-mcp)"
else
  echo ""
  echo "── [3/3] graphiti-mcp — SKIPPED (SKIP_MCP=1) ──"
fi

echo ""
echo "════════════════════════════════════════"
echo "  Stack is up"
echo "════════════════════════════════════════"
case "$LLM_MODE" in
  gb10)   echo "  LLM:    http://promaxgb10-41b1:${LLM_PORT}/v1  (local vLLM)" ;;
  mac)    echo "  LLM:    ${LLM_API_URL}  (MacBook Ollama)" ;;
  custom) echo "  LLM:    ${LLM_API_URL}  (custom / ${LLM_MODEL})" ;;
esac
echo "  Embed:  http://promaxgb10-41b1:${EMBED_PORT}/v1"
echo "  MCP:    http://promaxgb10-41b1:${MCP_PORT}/mcp/"
echo ""
echo "  Stop with: ./scripts/graphiti-stack-down.sh"
