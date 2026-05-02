#!/usr/bin/env bash
# graphiti-stack-up.sh — Start the Graphiti stack on the GB10.
#
# Preconditions:
#   - llama-swap is reachable on http://localhost:9000 and lists the models
#     `qwen-graphiti` (LLM) and `nomic-embed` (embeddings). llama-swap itself
#     is managed by systemd timers (llama-swap-keepalive.timer); this script
#     only consumes its endpoint and never starts/stops/modifies llama-swap.
#   - FalkorDB is reachable on whitestocks:6379 (NAS over Tailscale).
#   - The graphiti-mcp-standalone:local image exists locally
#     (run scripts/graphiti-mcp-build.sh once if not).
#
# Postconditions on success:
#   - The graphiti-mcp container is running, bound to :8004 with --network host,
#     reading scripts/graphiti-mcp-config.yaml, and serving /mcp/ for sessions.
#   - Re-running this script against the already-up state replaces the
#     graphiti-mcp container with a fresh one (idempotent).
#
# Exit codes:
#   0  graphiti-mcp is up and serving /mcp/
#   1  unknown CLI argument or invalid --llm mode
#   2  llama-swap precondition failed (unreachable, or required models missing)
#   3  FalkorDB precondition failed (whitestocks:6379 unreachable)
#   4  graphiti-mcp image missing — run graphiti-mcp-build.sh first
#   5  graphiti-mcp failed to become ready within $WAIT_MCP_SECONDS
#   6  GRAPHITI_LLM_API_URL/_MODEL missing under --llm=custom
#
# Usage:
#   ./scripts/graphiti-stack-up.sh                  # default: LLM via llama-swap on GB10
#   ./scripts/graphiti-stack-up.sh --llm=gb10       # same as default
#   ./scripts/graphiti-stack-up.sh --llm=mac        # route LLM at MacBook Ollama
#   ./scripts/graphiti-stack-up.sh --llm=custom     # route LLM via GRAPHITI_LLM_API_URL/_MODEL
#
# --llm=mac overrides:
#   MAC_LLM_API_URL  default: http://richards-macbook-pro.tailebf801.ts.net:8000/v1
#   MAC_LLM_MODEL    default: qwen2.5:14b-instruct
#
# --llm=custom required env:
#   GRAPHITI_LLM_API_URL   e.g. https://generativelanguage.googleapis.com/v1beta/openai/
#   GRAPHITI_LLM_MODEL     e.g. gemini-2.5-pro
#   OPENAI_API_KEY         if the provider validates it
#
# History:
#   Pre-2026-04-29 this script also booted vllm-graphiti (port 8000) and
#   vllm-embedding (port 8001) via per-container start scripts. Those were
#   superseded by llama-swap on :9000 and the start scripts moved to
#   scripts/archive-vllm/. The script no longer manages an LLM/embed tier.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MCP_PORT="${GRAPHITI_MCP_PORT:-8004}"
LLAMA_SWAP_URL="${LLAMA_SWAP_URL:-http://localhost:9000}"

# Tunable: max seconds to wait for graphiti-mcp's /mcp/ to respond.
WAIT_MCP_SECONDS="${WAIT_MCP_SECONDS:-60}"
# Tunable: how long to wait for llama-swap before giving up on the precondition.
WAIT_LLAMA_SECONDS="${WAIT_LLAMA_SECONDS:-15}"

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
      sed -n '2,55p' "$0"
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
    # Default — graphiti-mcp reads localhost:9000 from YAML; llama-swap serves
    # both qwen-graphiti and nomic-embed there.
    ;;
  mac)
    export LLM_API_URL="${MAC_LLM_API_URL:-http://richards-macbook-pro.tailebf801.ts.net:8000/v1}"
    export LLM_MODEL="${MAC_LLM_MODEL:-qwen2.5:14b-instruct}"
    echo ""
    echo "⚠  --llm=mac: Graphiti LLM calls will hit the MacBook. Confirm Ollama"
    echo "   is running there and serving '${LLM_MODEL}'. Embeddings still go"
    echo "   to llama-swap on the GB10 (nomic-embed)."
    ;;
  custom)
    if [ -z "${GRAPHITI_LLM_API_URL:-}" ] || [ -z "${GRAPHITI_LLM_MODEL:-}" ]; then
      echo "ERROR: --llm=custom requires GRAPHITI_LLM_API_URL and GRAPHITI_LLM_MODEL" >&2
      echo "       Example:" >&2
      echo "         GRAPHITI_LLM_API_URL=https://generativelanguage.googleapis.com/v1beta/openai/ \\" >&2
      echo "         GRAPHITI_LLM_MODEL=gemini-2.5-pro \\" >&2
      echo "         OPENAI_API_KEY=\$GOOGLE_API_KEY \\" >&2
      echo "         ./scripts/graphiti-stack-up.sh --llm=custom" >&2
      exit 6
    fi
    export LLM_API_URL="$GRAPHITI_LLM_API_URL"
    export LLM_MODEL="$GRAPHITI_LLM_MODEL"
    ;;
esac

echo ""
echo "════════════════════════════════════════"
echo "  Graphiti stack — starting on GB10"
echo "  LLM mode: $LLM_MODE"
if [ "$LLM_MODE" != "gb10" ]; then
  echo "  LLM URL:  ${LLM_API_URL}"
  echo "  LLM mdl:  ${LLM_MODEL}"
fi
echo "════════════════════════════════════════"

# --- Step 1: precondition — llama-swap on :9000 (LLM mode gb10 only) ---
echo ""
echo "── [1/3] llama-swap precondition ──"
if [ "$LLM_MODE" = "gb10" ]; then
  start="$(date +%s)"
  while true; do
    models_json="$(curl -fsS --max-time 3 "$LLAMA_SWAP_URL/v1/models" 2>/dev/null || true)"
    if [ -n "$models_json" ] \
       && printf '%s' "$models_json" | grep -q '"qwen-graphiti"' \
       && printf '%s' "$models_json" | grep -q '"nomic-embed"'; then
      echo "  ✓ llama-swap up at $LLAMA_SWAP_URL with qwen-graphiti + nomic-embed"
      break
    fi
    end="$(date +%s)"
    if [ $((end - start)) -ge "$WAIT_LLAMA_SECONDS" ]; then
      echo "  ✗ llama-swap did not list qwen-graphiti + nomic-embed within ${WAIT_LLAMA_SECONDS}s" >&2
      echo "    Probe:    curl $LLAMA_SWAP_URL/v1/models" >&2
      echo "    Recover:  sudo systemctl start llama-swap-keepalive.service" >&2
      echo "              (one-shot revive; the timer also runs every 5 min)" >&2
      exit 2
    fi
    sleep 1
  done
else
  echo "  (skipped — LLM_MODE=$LLM_MODE, llama-swap only used for embeddings)"
  emb_json="$(curl -fsS --max-time 3 "$LLAMA_SWAP_URL/v1/models" 2>/dev/null || true)"
  if ! printf '%s' "$emb_json" | grep -q '"nomic-embed"'; then
    echo "  ✗ llama-swap unreachable or missing nomic-embed (still required for embeddings)" >&2
    exit 2
  fi
  echo "  ✓ llama-swap reachable; nomic-embed available for embeddings"
fi

# --- Step 2: precondition — FalkorDB on whitestocks:6379 ---
echo ""
echo "── [2/3] FalkorDB precondition ──"
if (echo -e "PING\r"; sleep 0.3) | timeout 3 nc -w 2 whitestocks 6379 2>/dev/null | grep -q "PONG"; then
  echo "  ✓ FalkorDB reachable at whitestocks:6379"
else
  echo "  ✗ FalkorDB unreachable at whitestocks:6379" >&2
  echo "    Check: Tailscale up, NAS powered, FalkorDB compose up on whitestocks." >&2
  exit 3
fi

# --- Step 3: start graphiti-mcp ---
echo ""
echo "── [3/3] graphiti-mcp ──"
if ! docker image inspect graphiti-mcp-standalone:local &>/dev/null; then
  echo "  ✗ Image graphiti-mcp-standalone:local missing" >&2
  echo "    Build it: ./scripts/graphiti-mcp-build.sh" >&2
  exit 4
fi
"$SCRIPT_DIR/graphiti-mcp.sh"

# Wait for the FastMCP endpoint. /mcp/ requires a session and 4xxs without one,
# but a 4xx means the server is listening — that's "ready" for our purposes.
echo "  Waiting for graphiti-mcp at http://localhost:${MCP_PORT}/mcp/ (up to ${WAIT_MCP_SECONDS}s)..."
start="$(date +%s)"
ready=0
while true; do
  http_code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 "http://localhost:${MCP_PORT}/mcp/" 2>/dev/null || true)"
  case "$http_code" in
    2*|3*|4*)
      end="$(date +%s)"
      echo "  ✓ graphiti-mcp ready (HTTP $http_code) after $((end - start))s"
      ready=1
      break
      ;;
  esac
  end="$(date +%s)"
  if [ $((end - start)) -ge "$WAIT_MCP_SECONDS" ]; then
    break
  fi
  sleep 1
done

if [ "$ready" != "1" ]; then
  echo "  ✗ graphiti-mcp did NOT respond within ${WAIT_MCP_SECONDS}s" >&2
  echo "    Logs:  docker logs --tail 100 graphiti-mcp" >&2
  exit 5
fi

echo ""
echo "════════════════════════════════════════"
echo "  Stack is up"
echo "════════════════════════════════════════"
case "$LLM_MODE" in
  gb10)   echo "  LLM:    $LLAMA_SWAP_URL/v1  (llama-swap, qwen-graphiti)" ;;
  mac)    echo "  LLM:    ${LLM_API_URL}  (MacBook Ollama, ${LLM_MODEL})" ;;
  custom) echo "  LLM:    ${LLM_API_URL}  (custom, ${LLM_MODEL})" ;;
esac
echo "  Embed:  $LLAMA_SWAP_URL/v1  (llama-swap, nomic-embed, 768d)"
echo "  DB:     whitestocks:6379    (FalkorDB on NAS)"
echo "  MCP:    http://promaxgb10-41b1:${MCP_PORT}/mcp/"
echo ""
echo "  Stop with: ./scripts/graphiti-stack-down.sh"
