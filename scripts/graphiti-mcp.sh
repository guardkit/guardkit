#!/usr/bin/env bash
# graphiti-mcp.sh — Start the Graphiti MCP HTTP server on the GB10.
#
# Runs the standalone graphiti-mcp container (built by graphiti-mcp-build.sh)
# with --network host so it can reach:
#   - vllm-graphiti   on localhost:8000 (LLM)
#   - vllm-embedding  on localhost:8001 (embedder)
#   - FalkorDB        on whitestocks:6379 via Tailscale (host network)
#
# Exposes MCP at: http://promaxgb10-41b1:8004/mcp  (note: no trailing slash —
# the /mcp/ form 307-redirects to /mcp, which breaks Claude Code's POST handling)
#
# Port allocation (DGX Spark GB10):
#   8000 — vllm-graphiti        (vllm-graphiti.sh)     Qwen2.5-14B LLM
#   8001 — vllm-embedding       (vllm-embed.sh)        nomic-embed-text-v1.5
#   8002 — vllm-serve           AutoBuild LLM
#   8003 — vllm-nemotron3-nano
#   8004 — graphiti-mcp         (this script)          HTTP MCP server
#
# Usage:
#   ./scripts/graphiti-mcp.sh                 # start detached
#   ./scripts/graphiti-mcp.sh --foreground    # stream logs in terminal
#
# Env overrides:
#   GRAPHITI_MCP_PORT=8004
#   GRAPHITI_MCP_IMAGE=graphiti-mcp-standalone:local
#   GRAPHITI_MCP_CONFIG=<absolute path to config yaml>
#
# LLM routing (passed through to the container; the YAML config reads these):
#   LLM_API_URL      OpenAI-compatible LLM endpoint (default from YAML: localhost:8000/v1)
#   LLM_MODEL        model identifier (default from YAML: Qwen2.5-14B FP8)
#   OPENAI_API_KEY   required by graphiti-core's reranker even for local vLLM
#                    (the OpenAI SDK refuses to construct without one). Defaults
#                    to a dummy string here; only override for paid providers.
# See graphiti-stack-up.sh --llm=mac|custom for the common switchover flow.

set -euo pipefail

# --- Resolve script dir so the config mount works from any CWD ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Configuration ---
CONTAINER_NAME="graphiti-mcp"
PORT="${GRAPHITI_MCP_PORT:-8004}"
IMAGE="${GRAPHITI_MCP_IMAGE:-graphiti-mcp-standalone:local}"
CONFIG_FILE="${GRAPHITI_MCP_CONFIG:-$SCRIPT_DIR/graphiti-mcp-config.yaml}"

FOREGROUND=0
for arg in "$@"; do
  case "$arg" in
    --foreground|-f) FOREGROUND=1 ;;
    -h|--help)
      sed -n '2,25p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown arg: $arg"
      exit 1
      ;;
  esac
done

# --- Pre-flight checks ---
if [ ! -f "$CONFIG_FILE" ]; then
  echo "ERROR: Config not found: $CONFIG_FILE" >&2
  exit 1
fi

if ! docker image inspect "$IMAGE" &>/dev/null; then
  echo "ERROR: Image '$IMAGE' not found locally." >&2
  echo "       Run ./scripts/graphiti-mcp-build.sh first." >&2
  exit 1
fi

# --- Stop existing container if running ---
if docker ps -aq --filter "name=^${CONTAINER_NAME}$" | grep -q .; then
  echo "Stopping existing container: $CONTAINER_NAME"
  docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
  docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
fi

# --- Build pass-through env for LLM routing ---
# The YAML config reads ${LLM_API_URL} and ${LLM_MODEL} with localhost defaults,
# so only pass them when the caller set something non-default in the shell.
DOCKER_ENV_ARGS=()
if [ -n "${LLM_API_URL:-}" ]; then
  DOCKER_ENV_ARGS+=(-e "LLM_API_URL=$LLM_API_URL")
fi
if [ -n "${LLM_MODEL:-}" ]; then
  DOCKER_ENV_ARGS+=(-e "LLM_MODEL=$LLM_MODEL")
fi
# Always pass OPENAI_API_KEY. graphiti-core instantiates OpenAIRerankerClient()
# with no args, which reads from env directly and rejects empty strings — so
# local vLLM would crash on startup without this. vLLM ignores the value; only
# override when routing to a paid provider.
DOCKER_ENV_ARGS+=(-e "OPENAI_API_KEY=${OPENAI_API_KEY:-not-needed-vllm-local}")
if [ -n "${EMBEDDING_API_URL:-}" ]; then
  DOCKER_ENV_ARGS+=(-e "EMBEDDING_API_URL=$EMBEDDING_API_URL")
fi
if [ -n "${FALKORDB_URI:-}" ]; then
  DOCKER_ENV_ARGS+=(-e "FALKORDB_URI=$FALKORDB_URI")
fi

# --- Start container ---
echo ""
echo "========================================"
echo "  Graphiti MCP — GB10"
echo "========================================"
echo "  Image:   $IMAGE"
echo "  Port:    $PORT"
echo "  Config:  $CONFIG_FILE"
echo "  URL:     http://promaxgb10-41b1:${PORT}/mcp"
echo "  LLM:     ${LLM_API_URL:-<YAML default: localhost:8000/v1>}"
echo "  Model:   ${LLM_MODEL:-<YAML default: Qwen2.5-14B FP8>}"
echo "========================================"
echo ""

RUN_FLAGS=(-d)
if [ "$FOREGROUND" = "1" ]; then
  RUN_FLAGS=(--rm)
fi

# --network host so the container reaches vLLM on localhost and FalkorDB via
# the host's Tailscale DNS. With host networking, the container binds $PORT on
# the host directly — the config file's `server.port` must match.
BOOTSTRAP_FILE="$SCRIPT_DIR/graphiti-mcp-bootstrap.py"
if [ ! -f "$BOOTSTRAP_FILE" ]; then
  echo "ERROR: Bootstrap not found: $BOOTSTRAP_FILE" >&2
  exit 1
fi

# bootstrap.py monkey-patches MCP's DNS rebinding protection off before
# importing graphiti's main(). Needed because graphiti-mcp-server constructs
# FastMCP() with the default host=127.0.0.1, which auto-enables protection
# with a localhost-only Host allow-list; any non-loopback client (Tailscale
# hostname, bare IP) then gets 421. See the bootstrap file for full context.
docker run "${RUN_FLAGS[@]}" \
  --name "$CONTAINER_NAME" \
  --network host \
  -v "$CONFIG_FILE:/app/mcp/config/config.yaml:ro" \
  -v "$BOOTSTRAP_FILE:/app/mcp/bootstrap.py:ro" \
  -e CONFIG_PATH=/app/mcp/config/config.yaml \
  -e MCP_SERVER_HOST=0.0.0.0 \
  -e PYTHONUNBUFFERED=1 \
  "${DOCKER_ENV_ARGS[@]}" \
  "$IMAGE" \
  uv run --no-sync bootstrap.py

if [ "$FOREGROUND" = "0" ]; then
  echo "Container started: $CONTAINER_NAME"
  echo ""
  echo "  Logs:    docker logs -f $CONTAINER_NAME"
  echo "  Health:  curl http://localhost:${PORT}/health"
  echo "  MCP:     http://promaxgb10-41b1:${PORT}/mcp"
fi
