#!/usr/bin/env bash
# infra-status.sh — One-screen summary of GB10 infrastructure state.
#
# Reports for each tier:
#   1. llama-swap   — endpoint reachable + models listed; last keepalive run.
#   2. graphiti-mcp — container state + Docker healthcheck status.
#   3. FalkorDB     — TCP reachable on whitestocks:6379 (NAS via Tailscale).
#   4. NATS tier    — sourced hook output (no-op until future task).
#   5. agents tier  — sourced hook output (no-op until future task).
#
# Preconditions: none.
# Postconditions: prints a multi-line summary; exits 0 regardless of state.
#
# Exit codes:
#   0  always — this is a status probe, not a gate. Parse stdout if you need
#              a programmatic verdict.
#
# Usage:
#   ./scripts/infra-status.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS_DIR="$SCRIPT_DIR/infra"

LLAMA_SWAP_URL="${LLAMA_SWAP_URL:-http://localhost:9000}"

for arg in "$@"; do
  case "$arg" in
    -h|--help) sed -n '2,21p' "$0"; exit 0 ;;
    *)         echo "ERROR: unknown arg: $arg" >&2; exit 1 ;;
  esac
done

echo ""
echo "════════════════════════════════════════════════════"
echo "  GB10 infrastructure — status"
echo "════════════════════════════════════════════════════"

# --- 1. llama-swap ---
echo ""
echo "── llama-swap (LLM + embed, :9000) ──"
models_json="$(curl -fsS --max-time 3 "$LLAMA_SWAP_URL/v1/models" 2>/dev/null || true)"
if [ -n "$models_json" ]; then
  has_qwen=$(printf '%s' "$models_json" | grep -q '"qwen-graphiti"' && echo "yes" || echo "no")
  has_embed=$(printf '%s' "$models_json" | grep -q '"nomic-embed"' && echo "yes" || echo "no")
  echo "  endpoint:    UP at $LLAMA_SWAP_URL"
  echo "  qwen-graphiti listed:  $has_qwen"
  echo "  nomic-embed   listed:  $has_embed"
else
  echo "  endpoint:    DOWN at $LLAMA_SWAP_URL (no /v1/models response)"
fi
last_keepalive="$(systemctl show llama-swap-keepalive.service -p ActiveEnterTimestamp --value 2>/dev/null)"
echo "  keepalive last ran:  ${last_keepalive:-unknown}"

# --- 2. graphiti-mcp ---
echo ""
echo "── graphiti-mcp (:8004) ──"
if docker ps -aq --filter "name=^graphiti-mcp$" | grep -q .; then
  state="$(docker inspect graphiti-mcp --format '{{.State.Status}}' 2>/dev/null || echo unknown)"
  health="$(docker inspect graphiti-mcp --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' 2>/dev/null || echo unknown)"
  uptime="$(docker inspect graphiti-mcp --format '{{.State.StartedAt}}' 2>/dev/null || echo unknown)"
  echo "  container:   $state"
  echo "  health:      $health"
  echo "  started at:  $uptime"
else
  echo "  container:   not present"
  echo "  health:      n/a"
fi

# --- 3. FalkorDB on NAS ---
echo ""
echo "── FalkorDB (whitestocks:6379, NAS via Tailscale) ──"
if (echo -e "PING\r"; sleep 0.3) | timeout 3 nc -w 2 whitestocks 6379 2>/dev/null | grep -q "PONG"; then
  echo "  reachable:   yes (PONG over Tailscale)"
else
  echo "  reachable:   NO — check Tailscale, NAS power, FalkorDB compose"
fi

# --- 4. NATS tier (hook) ---
echo ""
echo "── NATS tier ──"
# shellcheck source=scripts/infra/nats-status.sh
source "$HOOKS_DIR/nats-status.sh"

# --- 5. Agents tier (hook) ---
echo ""
echo "── Agents tier ──"
# shellcheck source=scripts/infra/agents-status.sh
source "$HOOKS_DIR/agents-status.sh"

echo ""
echo "════════════════════════════════════════════════════"
